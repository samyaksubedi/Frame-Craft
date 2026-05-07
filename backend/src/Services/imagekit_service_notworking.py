# from imagekitio import ImageKit
# # from Configs.env import IMAGEKIT_PRIVATE_KEY, IMAGEKIT_PUBLIC_KEY, IMAGEKIT_URL_ENDPOINT


# imagekit = ImageKit(private_key=IMAGEKIT_PRIVATE_KEY)


# def upload_file(
#     file_bytes: bytes, file_name: str, folder: str, content_type: str = "image/png"
# ) -> str:
#     """Upload a file to ImageKit and return the CDN URL."""
#     result = imagekit.files.upload(
#         file=file_bytes,
#         file_name=file_name,
#         folder=folder,
#         is_private_file=False,
#         use_unique_file_name=True,
#     )
#     # print("result.url →", result.url)
#     # print("full result →", result)
#     # return result.thumbnail_url
#     # return result.url

#     # Manually construct URL using your endpoint + file_path
#     return f"{IMAGEKIT_URL_ENDPOINT}/{result.file_path.lstrip('/')}"


# def get_variants(base_url: str):
#     """Returns 3 sizes variant URL's using imagekit transformations."""
#     return {
#         "youtube": f"{base_url}?tr=w-1280,h-720,c-maintain_ratio,fo-auto",
#         "shorts": f"{base_url}?tr=w-1080,h-1920,c-maintain_ratio,fo-auto",
#         "square": f"{base_url}?tr=w-1080,h-1080,c-maintain_ratio,fo-auto",
#     }
