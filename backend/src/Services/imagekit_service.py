import cloudinary
import cloudinary.uploader
from Configs.env import (
    # CLOUDINARY_URL,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_CLOUD_NAME,
)

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
)


def upload_file(
    file_bytes: bytes, file_name: str, folder: str, content_type: str = "image/png"
) -> str:
    """Upload a file to Cloudinary and return the CDN URL."""
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=folder,
        public_id=file_name,
        overwrite=True,
        resource_type="image",
    )
    return result["secure_url"]  # always use secure_url, not url


def get_variants(base_url: str):
    """Returns 3 size variant URLs using Cloudinary transformations."""
    if not base_url:
        return None
    return {
        "youtube": base_url.replace(
            "/upload/", "/upload/w_1280,h_720,c_fill,g_auto,q_auto,f_auto/"
        ),
        "shorts": base_url.replace(
            "/upload/", "/upload/w_1080,h_1920,c_fill,g_auto,q_auto,f_auto/"
        ),
        "square": base_url.replace(
            "/upload/", "/upload/w_1080,h_1080,c_fill,g_auto,q_auto,f_auto/"
        ),
    }
