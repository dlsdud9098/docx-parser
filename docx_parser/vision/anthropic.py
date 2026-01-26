"""
Anthropic Claude Vision Provider.
"""

import os
from pathlib import Path
from typing import Optional

from .base import VisionProvider
from .exceptions import ProviderNotInstalledError, APIKeyNotFoundError, RateLimitError
from .utils import get_image_info


class AnthropicVisionProvider(VisionProvider):
    """Anthropic Claude Vision Provider

    Example:
        provider = AnthropicVisionProvider(api_key="sk-ant-...")
        description = provider.describe_image(Path("image.png"))

        # 환경변수 사용
        # export ANTHROPIC_API_KEY=sk-ant-...
        provider = AnthropicVisionProvider()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        prompt: Optional[str] = None,
        max_tokens: int = 300,
        language: str = "ko",
    ):
        """
        Args:
            api_key: Anthropic API 키 (없으면 ANTHROPIC_API_KEY 환경변수 사용)
            model: 사용할 모델 (claude-sonnet-4-20250514, claude-3-opus-20240229 등)
            prompt: 커스텀 프롬프트
            max_tokens: 최대 토큰 수
            language: 응답 언어
        """
        try:
            import anthropic
            self._anthropic = anthropic
        except ImportError:
            raise ProviderNotInstalledError("Anthropic", "anthropic")

        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise APIKeyNotFoundError("Anthropic", "ANTHROPIC_API_KEY")

        self.client = anthropic.Anthropic(api_key=self.api_key)

        super().__init__(model=model, prompt=prompt, max_tokens=max_tokens, language=language)

    @property
    def default_model(self) -> str:
        return "claude-sonnet-4-20250514"

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def describe_image(
        self,
        image_path: Path,
        prompt: Optional[str] = None,
    ) -> str:
        """이미지 설명 생성

        Args:
            image_path: 이미지 파일 경로
            prompt: 커스텀 프롬프트 (None이면 self.prompt 사용)
        """
        base64_data, media_type = get_image_info(image_path)
        use_prompt = prompt if prompt is not None else self.prompt

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_data,
                                }
                            },
                            {
                                "type": "text",
                                "text": use_prompt
                            }
                        ]
                    }
                ]
            )
            return response.content[0].text

        except self._anthropic.RateLimitError as e:
            raise RateLimitError("Anthropic") from e

    def _encode_image(self, image_path: Path) -> str:
        base64_data, _ = get_image_info(image_path)
        return base64_data
