import asyncio
import logging
from sqlmodel import Session, select
from Configs.sql import engine
from Models.models import Job, Thumbnail
from Services.openai_service import generate_thumbnail
from Services.imagekit_service import upload_file


logger = logging.getLogger(__name__)

STYLES = {
    "bold_dramatic": (
        "Create a bold, dramatic YouTube thumbnail with high contrast, "
        "cinematic lighting, dark moody background, and powerful composition. "
        ""
        "The person's face should be prominent with a dramatic expression."
    ),
    "clean_minimal": (
        "Create a clean, minimal YouTube thumbnail with bright lighting, "
        "white/light background, modern professional aesthetic, plenty of "
        "whitespace, and sharp clean composition. The person should look "
        "approachable and professional."
    ),
    "vibrant_energetic": (
        "Create a vibrant, energetic YouTube thumbnail with colorful gradients, "
        "dynamic angles, eye-catching pop-art style colors, and energetic "
        "composition. The person should have an excited or engaging expression."
    ),
}

STYLE_ORDER = ["bold_dramatic", "clean_minimal", "vibrant_energetic"]
INTERRUPTED_ERROR = "Generation was interrupted before it finished"


def _fail_thumbnail(thumbnail_id: str, message: str) -> None:
    with Session(engine) as session:
        thumbnail = session.get(Thumbnail, thumbnail_id)
        if not thumbnail:
            return
        thumbnail.status = "failed"
        thumbnail.error_message = message[:2000]
        session.add(thumbnail)
        session.commit()


def recover_interrupted_jobs() -> None:
    """Make persisted states honest after a process restart or old worker crash."""
    with Session(engine) as session:
        jobs = session.exec(select(Job)).all()
        changed = False
        for job in jobs:
            thumbnails = session.exec(
                select(Thumbnail).where(Thumbnail.job_id == job.id)
            ).all()
            non_terminal = [
                thumbnail
                for thumbnail in thumbnails
                if thumbnail.status in {"pending", "generating"}
            ]
            if not non_terminal:
                continue

            for thumbnail in non_terminal:
                thumbnail.status = "failed"
                thumbnail.error_message = INTERRUPTED_ERROR
                session.add(thumbnail)

            job.status = (
                "completed"
                if any(thumbnail.status == "uploaded" for thumbnail in thumbnails)
                else "failed"
            )
            session.add(job)
            changed = True

        if changed:
            session.commit()
            logger.warning("Recovered interrupted thumbnail generation records")


async def generate_one_thumbnail(
    thumbnail_id: str, prompt: str, headshot_url: str
) -> bool:
    """
    Generate and upload a single thumbnail using AI.

    Generates a single base thumbnail via OpenAI, uploads it to ImageKit,
    and updates the Thumbnail row status in DB.
    ImageKit then derives a Shorts and square variant from this base image.

    Args:
        thumbnail_id: ID of the Thumbnail row to process.
        prompt: User-provided description for the thumbnail.
        headshot_url: URL of the user's headshot to incorporate.
    """
    try:
        with Session(engine) as session:
            thumbnail = session.get(Thumbnail, thumbnail_id)
            if not thumbnail:
                logger.error("Thumbnail %s not found", thumbnail_id)
                return False

            thumbnail.status = "generating"
            thumbnail.error_message = None
            style_name = thumbnail.style_name
            job_id = thumbnail.job_id
            session.add(thumbnail)
            session.commit()

        style_prompt = STYLES.get(style_name)
        if not style_prompt:
            message = f"Unknown style: {style_name}"
            logger.error(message)
            _fail_thumbnail(thumbnail_id, message)
            return False

        try:
            image_bytes = await generate_thumbnail(
                prompt=prompt,
                style_prompt=style_prompt,
                headshot_url=headshot_url,
            )
        except Exception as exc:
            logger.exception("Generation failed for thumbnail %s", thumbnail_id)
            _fail_thumbnail(
                thumbnail_id, "Image generation failed. Please try again."
            )
            return False

        try:
            url = upload_file(
                file_bytes=image_bytes,
                file_name=thumbnail_id,
                folder=f"thumbnails/{job_id}",
            )
        except Exception as exc:
            logger.exception("Upload failed for thumbnail %s", thumbnail_id)
            _fail_thumbnail(
                thumbnail_id, "Generated image upload failed. Please try again."
            )
            return False

        with Session(engine) as session:
            thumbnail = session.get(Thumbnail, thumbnail_id)
            if not thumbnail:
                logger.error(
                    "Thumbnail %s disappeared before upload completed", thumbnail_id
                )
                return False
            thumbnail.imagekit_url = url
            thumbnail.status = "uploaded"
            thumbnail.error_message = None
            session.add(thumbnail)
            session.commit()

        logger.info("Thumbnail %s generated and uploaded successfully", thumbnail_id)
        return True
    except Exception as exc:
        logger.exception("Unexpected thumbnail worker failure for %s", thumbnail_id)
        try:
            _fail_thumbnail(
                thumbnail_id, "Unexpected worker failure. Please try again."
            )
        except Exception:
            logger.exception("Could not persist failure for thumbnail %s", thumbnail_id)
        return False


async def process_job(job_id: str):
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            logger.error("Job %s not found", job_id)
            return

        job.status = "processing"
        prompt = job.prompt
        headshot_url = job.headshot_url
        session.add(job)
        session.commit()

        thumbnails = session.exec(
            select(Thumbnail).where(Thumbnail.job_id == job_id)
        ).all()

        if not thumbnails:
            logger.error("No thumbnails found for job %s", job_id)
            job.status = "failed"
            session.add(job)
            session.commit()
            return

        thumbnail_ids = [thumbnail.id for thumbnail in thumbnails]

    tasks = [
        generate_one_thumbnail(
            headshot_url=headshot_url,
            prompt=prompt,
            thumbnail_id=thumbnail_id,
        )
        for thumbnail_id in thumbnail_ids
    ]
    await asyncio.gather(*tasks)

    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            logger.error("Job %s disappeared while processing", job_id)
            return
        thumbnails = session.exec(
            select(Thumbnail).where(Thumbnail.job_id == job_id)
        ).all()
        for thumbnail in thumbnails:
            if thumbnail.status in {"pending", "generating"}:
                thumbnail.status = "failed"
                thumbnail.error_message = "Worker finished without a terminal result"
                session.add(thumbnail)

        job.status = (
            "completed"
            if any(thumbnail.status == "uploaded" for thumbnail in thumbnails)
            else "failed"
        )
        session.add(job)
        session.commit()
        logger.info("Job %s finished with status: %s", job_id, job.status)
