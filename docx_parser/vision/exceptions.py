"""
Vision provider exceptions.
"""

from typing import Optional


class VisionError(Exception):
    """Vision 처리 관련 기본 예외"""
    pass


class ProviderNotInstalledError(VisionError):
    """필요한 패키지가 설치되지 않은 경우"""
    def __init__(self, provider: str, package: str):
        self.provider = provider
        self.package = package
        super().__init__(
            f"{provider} provider requires '{package}' package. "
            f"Install with: pip install docx-parser[{provider.lower()}]"
        )


class APIKeyNotFoundError(VisionError):
    """API 키가 없는 경우"""
    def __init__(self, provider: str, env_var: str):
        self.provider = provider
        self.env_var = env_var
        super().__init__(
            f"{provider} API key not found. "
            f"Set {env_var} environment variable or pass api_key parameter."
        )


class ImageProcessingError(VisionError):
    """이미지 처리 실패"""
    def __init__(self, image_path: str, reason: str):
        self.image_path = image_path
        self.reason = reason
        super().__init__(f"Failed to process image '{image_path}': {reason}")


class RateLimitError(VisionError):
    """API 레이트 리밋"""
    def __init__(self, provider: str, retry_after: Optional[int] = None):
        self.provider = provider
        self.retry_after = retry_after
        msg = f"{provider} API rate limit exceeded."
        if retry_after:
            msg += f" Retry after {retry_after} seconds."
        super().__init__(msg)
