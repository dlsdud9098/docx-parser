"""
Vision providers for multimodal image description.

Example:
    from docx_parser.vision import create_vision_provider

    # 팩토리 함수 사용
    provider = create_vision_provider("openai", api_key="sk-...")

    # 또는 직접 클래스 사용
    from docx_parser.vision import OpenAIVisionProvider
    provider = OpenAIVisionProvider(api_key="sk-...")

    # 이미지 설명 생성
    description = provider.describe_image(Path("image.png"))
"""

from typing import Optional, Literal

from .base import VisionProvider, ImageDescription
from .exceptions import (
    VisionError,
    ProviderNotInstalledError,
    APIKeyNotFoundError,
    ImageProcessingError,
    RateLimitError,
)

ProviderType = Literal["openai", "anthropic", "google", "transformers"]


def create_vision_provider(
    provider: ProviderType,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> VisionProvider:
    """Vision Provider 팩토리 함수

    Args:
        provider: 제공자 타입
            - API: "openai", "anthropic", "google"
            - 로컬: "transformers"
        api_key: API 키 (API provider만)
        model: 모델명 (기본값 사용 시 None)
        **kwargs: 제공자별 추가 옵션

    Returns:
        VisionProvider 인스턴스

    Raises:
        ValueError: 알 수 없는 provider
        ProviderNotInstalledError: 패키지 미설치
        APIKeyNotFoundError: API 키 없음

    Example:
        # OpenAI
        provider = create_vision_provider("openai", model="gpt-4o")

        # Anthropic
        provider = create_vision_provider("anthropic", model="claude-sonnet-4-20250514")

        # Google Gemini
        provider = create_vision_provider("google", model="gemini-1.5-flash")

        # Hugging Face Transformers (로컬)
        provider = create_vision_provider("transformers",
            model="llava-hf/llava-v1.6-mistral-7b-hf",
            load_in_4bit=True
        )

        # Transformers with batch processing
        provider = create_vision_provider("transformers",
            model="llava-hf/llava-v1.6-mistral-7b-hf",
            load_in_4bit=True,
            batch_size=8  # 배치 크기 (기본: 4, GPU 메모리에 따라 조절)
        )
    """
    if provider == "openai":
        from .openai import OpenAIVisionProvider
        return OpenAIVisionProvider(api_key=api_key, model=model, **kwargs)

    elif provider == "anthropic":
        from .anthropic import AnthropicVisionProvider
        return AnthropicVisionProvider(api_key=api_key, model=model, **kwargs)

    elif provider == "google":
        from .google import GeminiVisionProvider
        return GeminiVisionProvider(api_key=api_key, model=model, **kwargs)

    elif provider == "transformers":
        from .transformers import TransformersVisionProvider
        model_id = model or kwargs.pop("model_id", None)
        if not model_id:
            model_id = "llava-hf/llava-v1.6-mistral-7b-hf"
        return TransformersVisionProvider(model_id=model_id, **kwargs)

    else:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Supported: openai, anthropic, google, transformers"
        )


# Lazy imports for individual providers
def __getattr__(name: str):
    if name == "OpenAIVisionProvider":
        from .openai import OpenAIVisionProvider
        return OpenAIVisionProvider
    elif name == "AnthropicVisionProvider":
        from .anthropic import AnthropicVisionProvider
        return AnthropicVisionProvider
    elif name == "GeminiVisionProvider":
        from .google import GeminiVisionProvider
        return GeminiVisionProvider
    elif name == "TransformersVisionProvider":
        from .transformers import TransformersVisionProvider
        return TransformersVisionProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Base classes
    "VisionProvider",
    "ImageDescription",
    # Factory
    "create_vision_provider",
    "ProviderType",
    # API Providers (lazy loaded)
    "OpenAIVisionProvider",
    "AnthropicVisionProvider",
    "GeminiVisionProvider",
    # Local Providers (lazy loaded)
    "TransformersVisionProvider",
    # Exceptions
    "VisionError",
    "ProviderNotInstalledError",
    "APIKeyNotFoundError",
    "ImageProcessingError",
    "RateLimitError",
]
