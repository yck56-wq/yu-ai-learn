from io import BytesIO
from pathlib import Path
from uuid import uuid4
import re

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError

from ..config import settings

MAX_BYTES = 5 * 1024 * 1024


def store_avatar(content):
    if len(content) > MAX_BYTES:
        raise HTTPException(413, '头像不能超过 5 MB')
    try:
        with Image.open(BytesIO(content)) as source:
            if source.format not in ('PNG', 'JPEG', 'WEBP') or source.width * source.height > 20_000_000:
                raise HTTPException(422, '请选择尺寸合适的 JPG、PNG 或 WebP 图片')
            source.load()
            image = ImageOps.exif_transpose(source).convert('RGBA')
            image.thumbnail((512, 512), Image.Resampling.LANCZOS)
            image.info.clear()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, '图片无法读取，请重新选择头像') from None
    directory = Path(settings.avatar_storage_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (uuid4().hex + '.png')
    image.save(path, format='PNG')
    return path


def avatar_path(filename):
    if not re.fullmatch(r'[0-9a-f]{32}\.png', filename):
        raise HTTPException(404, '头像不存在')
    path = Path(settings.avatar_storage_dir) / filename
    if not path.is_file():
        raise HTTPException(404, '头像不存在')
    return path
