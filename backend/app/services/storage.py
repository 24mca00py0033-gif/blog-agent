"""Image storage: Cloudinary when configured, local disk (static/) otherwise."""
import shutil
from pathlib import Path

from ..config import get_settings

STATIC_ROOT = Path(__file__).resolve().parents[2] / "static"
STATIC_ROOT.mkdir(parents=True, exist_ok=True)


def _cloudinary():
    s = get_settings()
    if not (s.cloudinary_cloud_name and s.cloudinary_api_key and s.cloudinary_api_secret):
        return None
    import cloudinary

    cloudinary.config(
        cloud_name=s.cloudinary_cloud_name,
        api_key=s.cloudinary_api_key,
        api_secret=s.cloudinary_api_secret,
        secure=True,
    )
    return cloudinary


def upload_image(data: bytes, folder: str, public_id: str, ext: str = "png") -> str:
    """Returns a URL (absolute for Cloudinary, /static/... for the local fallback)."""
    cld = _cloudinary()
    if cld:
        import cloudinary.uploader

        res = cloudinary.uploader.upload(
            data, folder=folder, public_id=public_id, overwrite=True, resource_type="image"
        )
        return res["secure_url"]
    path = STATIC_ROOT / folder / f"{public_id}.{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"/static/{folder}/{public_id}.{ext}"


def delete_folder(folder: str) -> None:
    cld = _cloudinary()
    if cld:
        try:
            import cloudinary.api

            cloudinary.api.delete_resources_by_prefix(f"{folder}/")
            cloudinary.api.delete_folder(folder)
        except Exception:
            pass  # never block a delete on storage cleanup
    else:
        shutil.rmtree(STATIC_ROOT / folder, ignore_errors=True)
