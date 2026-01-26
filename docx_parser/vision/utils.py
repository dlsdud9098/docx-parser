"""
Common utilities for vision providers.
"""

import base64
import mimetypes
import io
from pathlib import Path
from typing import Union


def encode_image_base64(image: Union[Path, bytes, io.BytesIO]) -> str:
    """이미지를 Base64로 인코딩

    Args:
        image: 이미지 파일 경로, bytes, 또는 BytesIO 객체

    Returns:
        Base64 인코딩된 문자열
    """
    if isinstance(image, bytes):
        return base64.standard_b64encode(image).decode("utf-8")
    elif isinstance(image, io.BytesIO):
        return base64.standard_b64encode(image.getvalue()).decode("utf-8")
    else:
        with open(image, "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8")


def get_image_mime_type(image: Union[Path, bytes, io.BytesIO], filename: str = None) -> str:
    """이미지 MIME 타입 추출

    Args:
        image: 이미지 파일 경로, bytes, 또는 BytesIO 객체
        filename: bytes인 경우 파일명 (확장자 추출용)

    Returns:
        MIME 타입 문자열 (예: 'image/png')
    """
    # bytes인 경우 magic number로 타입 추정
    if isinstance(image, (bytes, io.BytesIO)):
        data = image if isinstance(image, bytes) else image.getvalue()
        # Magic number 기반 타입 추정
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            return "image/png"
        elif data[:3] == b'\xff\xd8\xff':
            return "image/jpeg"
        elif data[:6] in (b'GIF87a', b'GIF89a'):
            return "image/gif"
        elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            return "image/webp"
        elif data[:2] == b'BM':
            return "image/bmp"
        # filename으로 추정 시도
        if filename:
            ext = Path(filename).suffix.lower()
            mime_map = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".gif": "image/gif",
                ".webp": "image/webp", ".bmp": "image/bmp",
            }
            if ext in mime_map:
                return mime_map[ext]
        return "image/png"  # 기본값

    # Path인 경우
    mime_type, _ = mimetypes.guess_type(str(image))
    if not mime_type:
        ext = image.suffix.lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
        }
        mime_type = mime_map.get(ext, "image/png")

    return mime_type


def encode_image_data_uri(image: Union[Path, bytes, io.BytesIO], filename: str = None) -> str:
    """이미지를 data URI 형식으로 인코딩 (OpenAI용)

    Args:
        image: 이미지 파일 경로, bytes, 또는 BytesIO 객체
        filename: bytes인 경우 파일명 (확장자 추출용)

    Returns:
        data:image/type;base64,... 형식 문자열
    """
    mime_type = get_image_mime_type(image, filename)
    base64_data = encode_image_base64(image)
    return f"data:{mime_type};base64,{base64_data}"


def get_image_info(image: Union[Path, bytes, io.BytesIO], filename: str = None) -> tuple[str, str]:
    """이미지 Base64와 MIME 타입 반환 (Anthropic용)

    Args:
        image: 이미지 파일 경로, bytes, 또는 BytesIO 객체
        filename: bytes인 경우 파일명 (확장자 추출용)

    Returns:
        (base64_data, mime_type) 튜플
    """
    return encode_image_base64(image), get_image_mime_type(image, filename)
