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


async def generate_one_thumbnail(thumbnail_id: str, prompt: str, headshot_url: str):
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
    with Session(engine) as session:
        # 1. Thumbnail not found
        thumbnail = session.get(Thumbnail, thumbnail_id)
        if not thumbnail:
            logger.error(f"Thumbnail {thumbnail_id} not found")
            return

        thumbnail.status = "generating"
        style_name = thumbnail.style_name
        job_id = thumbnail.job_id
        session.commit()

        style_prompt = STYLES.get(style_name)
        if not style_prompt:
            logger.error(f"Unknown style: {style_name}")
            thumbnail.status = "failed"
            thumbnail.error = f"Unknown style: {style_name}"
            session.commit()
            return

        # 2. AI generation failed
        try:
            image_byte = await generate_thumbnail(
                prompt=prompt, style_prompt=style_prompt, headshot_url=headshot_url
            )
        except Exception as e:
            logger.error(f"Generation failed for {thumbnail_id}: {e}")
            thumbnail.status = "failed"
            thumbnail.error = str(e)
            session.commit()
            return

        # 3. Upload failed
        try:
            file_name = f"{thumbnail_id}.png"
            folder_path = f"thumbnails/{job_id}/"
            url = upload_file(
                file_bytes=image_byte, file_name=file_name, folder=folder_path
            )
        except Exception as e:
            logger.error(f"Upload failed for {thumbnail_id}: {e}")
            thumbnail.status = "failed"
            thumbnail.error = str(e)
            session.commit()
            return

        # 4. All good
        thumbnail.imagekit_url = url
        thumbnail.status = "uploaded"
        session.commit()
        logger.info(f"Thumbnail {thumbnail_id} generated and uploaded successfully")


async def process_job(job_id: str):
    # make job as processing
    # find all thumbnails for this job
    # start one worker for each thumbnail
    # wait for all workers to finish
    # mark job as completed / failed job
    with Session(engine) as session:
        # 1. Job not found
        job = session.get(Job, job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = "processing"
        prompt = job.prompt
        headshot_url = job.headshot_url
        session.commit()

        thumbnails = job.thumbnails

        # 2. No thumbnails found
        if not thumbnails:
            logger.error(f"No thumbnails found for job {job_id}")
            job.status = "failed"
            session.commit()
            return

        thumbnails_ids = [t.id for t in thumbnails]
        tasks = [
            generate_one_thumbnail(
                headshot_url=headshot_url,
                prompt=prompt,
                thumbnail_id=tid,
            )
            for tid in thumbnails_ids
        ]

        # 3. Unexpected worker crash
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(
                f"Unexpected error during thumbnail generation for job {job_id}: {e}"
            )
            job.status = "failed"
            session.commit()
            return

        session.refresh(job)

        thumbnails = job.thumbnails
        all_failed = all(t.status == "failed" for t in thumbnails)
        job.status = "failed" if all_failed else "completed"
        session.commit()
        logger.info(f"Job {job_id} finished with status: {job.status}")
        print(f"Job {job_id} finished with status: {job.status}")
