"""
OpenAI Vision Provider (GPT-4o, GPT-4o-mini).
"""

import os
from pathlib import Path
from typing import Optional

from .base import VisionProvider
from .exceptions import ProviderNotInstalledError, APIKeyNotFoundError, RateLimitError
from .utils import encode_image_data_uri


class OpenAIVisionProvider(VisionProvider):
    """OpenAI GPT-4o Vision Provider

    Example:
        provider = OpenAIVisionProvider(api_key="sk-...")
        description = provider.describe_image(Path("image.png"))

        # 환경변수 사용
        # export OPENAI_API_KEY=sk-...
        provider = OpenAIVisionProvider()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        prompt: Optional[str] = None,
        max_tokens: int = 300,
        language: str = "ko",
        detail: str = "auto",
    ):
        """
        Args:
            api_key: OpenAI API 키 (없으면 OPENAI_API_KEY 환경변수 사용)
            model: 사용할 모델 (gpt-4o, gpt-4o-mini 등)
            prompt: 커스텀 프롬프트 (없으면 기본 프롬프트 사용)
            max_tokens: 최대 토큰 수
            language: 응답 언어 ("ko", "en", "ja")
            detail: 이미지 해상도 설정 ("low", "high", "auto")
        """
        try:
            import openai
            self._openai = openai
        except ImportError:
            raise ProviderNotInstalledError("OpenAI", "openai")

        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise APIKeyNotFoundError("OpenAI", "OPENAI_API_KEY")

        self.detail = detail
        self.client = openai.OpenAI(api_key=self.api_key)

        super().__init__(model=model, prompt=prompt, max_tokens=max_tokens, language=language)

    @property
    def default_model(self) -> str:
        return "gpt-4o"

    @property
    def provider_name(self) -> str:
        return "openai"

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
        data_uri = self._encode_image(image_path)
        use_prompt = prompt if prompt is not None else self.prompt

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": use_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": data_uri,
                                    "detail": self.detail
                                }
                            }
                        ]
                    }
                ]
            )
            return response.choices[0].message.content

        except self._openai.RateLimitError as e:
            raise RateLimitError("OpenAI") from e

    def _encode_image(self, image_path: Path) -> str:
        return encode_image_data_uri(image_path)
