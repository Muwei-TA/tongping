"""Bounded, normalized image storage; downloads repeat post authorization."""
from io import BytesIO
import warnings
from PIL import Image, UnidentifiedImageError
from .clubs import require_member
from .content import get_post
from .db import transaction
from .errors import DomainError, new_id, require

MAX_UPLOAD = 5 * 1024 * 1024
MAX_PIXELS = 16_000_000


def normalize(raw):
    require(0 < len(raw) <= MAX_UPLOAD, 413, "IMAGE_TOO_LARGE", "图片须在 5 MB 以内")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as image:
                require(image.format in ("PNG", "JPEG", "WEBP"), 422, "INVALID_IMAGE", "仅支持 PNG、JPEG、WebP")
                require(image.width * image.height <= MAX_PIXELS, 422, "INVALID_IMAGE", "图片像素过大")
                image.load()
                image.thumbnail((2400, 2400))
                clean = image.convert("RGB")
                clean.info.clear()
                output = BytesIO()
                clean.save(output, format="PNG")
                require(output.tell() <= 20 * 1024 * 1024, 413, "IMAGE_TOO_LARGE", "图片解码后过大")
                return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombWarning, Image.DecompressionBombError, ValueError):
        raise DomainError(422, "INVALID_IMAGE", "图片无法解码，请重新选择") from None


def upload(db, club_id, actor, raw):
    require_member(db, club_id, actor)
    data = normalize(raw)
    with transaction(db):
        require_member(db, club_id, actor)
        mid = new_id()
        db.execute("INSERT INTO media VALUES(?,?,?,?,?)", (mid, club_id, actor, data, "image/png"))
    return {"id": mid, "content_type": "image/png"}


def download(db, media_id, actor):
    row = db.execute("SELECT * FROM media WHERE id=?", (media_id,)).fetchone()
    require(row is not None, 404, "NOT_FOUND", "图片不存在")
    require_member(db, row["club_id"], actor)
    post = db.execute("SELECT id FROM posts WHERE media_id=?", (media_id,)).fetchone()
    if post:
        get_post(db, post["id"], actor)
    else:
        require(row["author_id"] == actor, 404, "NOT_FOUND", "图片未发布")
    return row["data"], row["content_type"]
