import base64
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from Configs.sql import get_session  # noqa: E402
from Models.models import Job, Thumbnail  # noqa: E402
from Routes import job_router  # noqa: E402
from Services import openai_service, thumbnail_service  # noqa: E402
from main import app  # noqa: E402


def make_test_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = make_test_engine()
        SQLModel.metadata.create_all(self.engine)

        def override_session():
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_session
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def test_cors_preflight_allows_vite(self):
        response = self.client.options(
            "/api/job",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://localhost:5173",
        )

    def test_upload_rejects_non_image(self):
        response = self.client.post(
            "/api/upload-headshot",
            files={"file": ("notes.txt", b"not an image", "text/plain")},
        )
        self.assertEqual(response.status_code, 415)

    def test_upload_rejects_spoofed_image_type(self):
        response = self.client.post(
            "/api/upload-headshot",
            files={"file": ("fake.png", b"not a png", "image/png")},
        )
        self.assertEqual(response.status_code, 415)

    def test_valid_upload_uses_unique_safe_name(self):
        png = b"\x89PNG\r\n\x1a\n" + b"test"
        with patch.object(
            job_router, "upload_file", return_value="https://example/image"
        ) as upload:
            response = self.client.post(
                "/api/upload-headshot",
                files={"file": ("../profile.png", png, "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"url": "https://example/image"})
        uploaded_name = upload.call_args.kwargs["file_name"]
        self.assertTrue(uploaded_name.endswith("-profile"))
        self.assertNotIn("..", uploaded_name)

    def test_job_rejects_untrusted_headshot_host(self):
        response = self.client.post(
            "/api/job",
            json={
                "prompt": "A useful thumbnail brief",
                "num_thumbnails": 1,
                "headshot_url": "https://example.com/headshot.png",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_valid_job_creates_requested_thumbnail_rows(self):
        with patch.object(job_router, "process_job", AsyncMock()) as process_job:
            response = self.client.post(
                "/api/job",
                json={
                    "prompt": "A useful thumbnail brief",
                    "num_thumbnails": 2,
                    "headshot_url": (
                        "https://res.cloudinary.com/demo/image/upload/headshot.png"
                    ),
                },
            )

        self.assertEqual(response.status_code, 200)
        with Session(self.engine) as session:
            jobs = session.exec(select(Job)).all()
            thumbnails = session.exec(select(Thumbnail)).all()
            self.assertEqual(len(jobs), 1)
            self.assertEqual(len(thumbnails), 2)
            self.assertEqual(
                [item.style_name for item in thumbnails],
                ["bold_dramatic", "clean_minimal"],
            )
        process_job.assert_awaited_once_with(response.json()["job_id"])


class ThumbnailServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = make_test_engine()
        SQLModel.metadata.create_all(self.engine)
        self.original_engine = thumbnail_service.engine
        thumbnail_service.engine = self.engine

    def tearDown(self):
        thumbnail_service.engine = self.original_engine
        self.engine.dispose()

    def add_job(self, styles=("bold_dramatic",)):
        with Session(self.engine) as session:
            job = Job(
                prompt="A useful thumbnail brief",
                num_thumbnails=len(styles),
                headshot_url="https://res.cloudinary.com/demo/headshot.png",
            )
            session.add(job)
            for style in styles:
                session.add(Thumbnail(job_id=job.id, style_name=style))
            session.commit()
            return job.id

    async def test_generation_failure_is_persisted(self):
        job_id = self.add_job()
        with Session(self.engine) as session:
            thumbnail_id = session.exec(
                select(Thumbnail).where(Thumbnail.job_id == job_id)
            ).one().id

        with patch.object(
            thumbnail_service,
            "generate_thumbnail",
            AsyncMock(side_effect=RuntimeError("provider unavailable")),
        ):
            result = await thumbnail_service.generate_one_thumbnail(
                thumbnail_id,
                "A useful thumbnail brief",
                "https://res.cloudinary.com/demo/headshot.png",
            )

        self.assertFalse(result)
        with Session(self.engine) as session:
            thumbnail = session.get(Thumbnail, thumbnail_id)
            self.assertEqual(thumbnail.status, "failed")
            self.assertEqual(
                thumbnail.error_message, "Image generation failed. Please try again."
            )

    async def test_process_job_never_leaves_non_terminal_thumbnails(self):
        job_id = self.add_job(("bold_dramatic", "clean_minimal"))

        async def fake_worker(thumbnail_id, prompt, headshot_url):
            with Session(self.engine) as session:
                thumbnail = session.get(Thumbnail, thumbnail_id)
                succeeded = thumbnail.style_name == "bold_dramatic"
                if succeeded:
                    thumbnail.status = "uploaded"
                    thumbnail.imagekit_url = "https://example/thumbnail.png"
                else:
                    thumbnail.status = "failed"
                    thumbnail.error_message = "test failure"
                session.add(thumbnail)
                session.commit()
            return succeeded

        with patch.object(
            thumbnail_service, "generate_one_thumbnail", side_effect=fake_worker
        ):
            await thumbnail_service.process_job(job_id)

        with Session(self.engine) as session:
            job = session.get(Job, job_id)
            thumbnails = session.exec(
                select(Thumbnail).where(Thumbnail.job_id == job_id)
            ).all()
            self.assertEqual(job.status, "completed")
            self.assertEqual(
                {thumbnail.status for thumbnail in thumbnails}, {"uploaded", "failed"}
            )

    def test_recovery_marks_interrupted_records_failed(self):
        job_id = self.add_job(("bold_dramatic", "clean_minimal"))
        thumbnail_service.recover_interrupted_jobs()

        with Session(self.engine) as session:
            job = session.get(Job, job_id)
            thumbnails = session.exec(
                select(Thumbnail).where(Thumbnail.job_id == job_id)
            ).all()
            self.assertEqual(job.status, "failed")
            self.assertTrue(all(item.status == "failed" for item in thumbnails))
            self.assertTrue(all(item.error_message for item in thumbnails))


class OpenAIServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_image_edit_returns_decoded_bytes(self):
        expected = b"generated image"
        response = SimpleNamespace(
            data=[SimpleNamespace(b64_json=base64.b64encode(expected).decode())]
        )
        with (
            patch.object(
                openai_service,
                "_download_headshot",
                AsyncMock(return_value=(b"reference", "image/png")),
            ),
            patch.object(
                openai_service.client.images,
                "edit",
                AsyncMock(return_value=response),
            ) as edit,
        ):
            actual = await openai_service.generate_thumbnail(
                "A useful thumbnail brief",
                "A clean editorial style",
                "https://res.cloudinary.com/demo/headshot.png",
            )

        self.assertEqual(actual, expected)
        self.assertEqual(
            edit.call_args.kwargs["model"], openai_service.OPENAI_IMAGE_MODEL
        )
        self.assertNotIn("response_format", edit.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
