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

    # 이미지 인코딩
    from docx_parser.vision import ImageEncoder
    encoder = ImageEncoder()
    encoded = encoder.encode(Path("image.png"))

    # 재시도 데코레이터
    from docx_parser.vision import with_retry, retry_on_rate_limit

    @retry_on_rate_limit(max_retries=3)
    def call_api():
        return provider.describe_image(image)
"""

from typing import Optional, Literal

from .base import VisionProvider, ImageDescription
from .encoder import (
    ImageEncoder,
    EncodedImage,
    encode_image_base64,
    encode_image_data_uri,
    get_image_info,
    get_image_mime_type,
)
from .exceptions import (
    VisionError,
    ProviderNotInstalledError,
    APIKeyNotFoundError,
    ImageProcessingError,
    RateLimitError,
)
from .retry import (
    RetryConfig,
    RetryHandler,
    with_retry,
    retry_on_rate_limit,
    calculate_delay,
)

ProviderType = Literal["openai", "anthropic", "google", "gemini", "transformers"]


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

        # Google Gemini (both "google" and "gemini" work)
        provider = create_vision_provider("gemini", model="gemini-1.5-flash")
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

    elif provider in ("google", "gemini"):
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
            f"Supported: openai, anthropic, google, gemini, transformers"
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
    # Encoder
    "ImageEncoder",
    "EncodedImage",
    "encode_image_base64",
    "encode_image_data_uri",
    "get_image_info",
    "get_image_mime_type",
    # Retry
    "RetryConfig",
    "RetryHandler",
    "with_retry",
    "retry_on_rate_limit",
    "calculate_delay",
    # Exceptions
    "VisionError",
    "ProviderNotInstalledError",
    "APIKeyNotFoundError",
    "ImageProcessingError",
    "RateLimitError",
]
