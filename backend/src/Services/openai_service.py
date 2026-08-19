from openai import AsyncOpenAI
import base64
import io

import httpx

from Configs.env import (
    ALLOWED_HEADSHOT_HOSTS,
    MAX_UPLOAD_SIZE_MB,
    OPENAI_API_KEY,
    OPENAI_IMAGE_MODEL,
    OPENAI_IMAGE_QUALITY,
)


client = AsyncOpenAI(api_key=OPENAI_API_KEY)
MAX_REFERENCE_IMAGE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


async def _download_headshot(headshot_url: str) -> tuple[bytes, str]:
    parsed_url = httpx.URL(headshot_url)
    if (
        parsed_url.scheme not in {"http", "https"}
        or parsed_url.host not in ALLOWED_HEADSHOT_HOSTS
    ):
        raise ValueError("Headshot URL is not from an allowed image host")

    contents = bytearray()
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as http_client:
        async with http_client.stream("GET", headshot_url) as response:
            response.raise_for_status()
            if response.url.host not in ALLOWED_HEADSHOT_HOSTS:
                raise ValueError("Headshot redirected to an untrusted image host")
            content_type = (
                response.headers.get("content-type", "").split(";", 1)[0].lower()
            )
            if content_type not in ALLOWED_IMAGE_TYPES:
                raise ValueError("Headshot URL did not return a supported image")
            async for chunk in response.aiter_bytes():
                contents.extend(chunk)
                if len(contents) > MAX_REFERENCE_IMAGE_BYTES:
                    raise ValueError(
                        f"Headshot must be {MAX_UPLOAD_SIZE_MB} MB or smaller"
                    )

    if not contents:
        raise ValueError("Headshot URL returned an empty image")
    return bytes(contents), content_type


async def generate_thumbnail(prompt: str, style_prompt: str, headshot_url) -> bytes:
    """Create a thumbnail by editing the supplied reference headshot."""
    full_prompt = f"""{style_prompt} \n\n User request: {prompt}\n\n
    Important : The generated thumbnail MUST prominently feature the person shown in the provided reference headshot photo. Keep their likeness accurate.
    """

    image_bytes, content_type = await _download_headshot(headshot_url)
    image_file = io.BytesIO(image_bytes)
    extension = content_type.removeprefix("image/").replace("jpeg", "jpg")
    image_file.name = f"headshot.{extension}"

    response = await client.images.edit(
        model=OPENAI_IMAGE_MODEL,
        image=image_file,
        prompt=full_prompt,
        size="1536x1024",
        quality=OPENAI_IMAGE_QUALITY,
    )
    if response.data and response.data[0].b64_json:
        return base64.b64decode(response.data[0].b64_json)
    raise RuntimeError("OpenAI returned no generated image")
