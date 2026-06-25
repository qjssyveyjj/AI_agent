import base64
import binascii
import io

from PIL import Image

from app.config import settings


def _strip_data_url(data: str) -> tuple[str, str | None]:
    """拆分 data URL，返回 (纯 base64 字符串, mime)。普通 base64 原样返回。"""
    if data.startswith("data:"):
        header, _, payload = data.partition(",")
        mime = header[5:].split(";")[0] or None
        return payload, mime
    return data, None


def preprocess_image_to_data_url(raw: str) -> str:
    """
    接收前端传来的图片（data URL 或纯 base64），统一为压缩后的 JPEG data URL。
    - 长边缩放到 IMAGE_MAX_EDGE
    - 转 JPEG，质量 IMAGE_JPEG_QUALITY
    解析失败时按原样回退为 data URL（避免阻断流程）。
    """
    payload, _ = _strip_data_url(raw)
    try:
        image_bytes = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        return raw if raw.startswith("data:") else f"data:image/jpeg;base64,{payload}"

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            if img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")

            max_edge = settings.image_max_edge
            w, h = img.size
            longest = max(w, h)
            if longest > max_edge:
                scale = max_edge / longest
                img = img.resize((int(w * scale), int(h * scale)))

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=settings.image_jpeg_quality)
            encoded = base64.b64encode(buf.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        return raw if raw.startswith("data:") else f"data:image/jpeg;base64,{payload}"
