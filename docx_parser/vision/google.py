"""
Google Gemini Vision Provider.
"""

import os
from pathlib import Path
from typing import Optional

from .base import VisionProvider
from .exceptions import ProviderNotInstalledError, APIKeyNotFoundError
from .utils import encode_image_base64


class GeminiVisionProvider(VisionProvider):
    """Google Gemini Vision Provider

    Example:
        provider = GeminiVisionProvider(api_key="...")
        description = provider.describe_image(Path("image.png"))

        # 환경변수 사용
        # export GOOGLE_API_KEY=...
        provider = GeminiVisionProvider()
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
            api_key: Google API 키 (없으면 GOOGLE_API_KEY 환경변수 사용)
            model: 사용할 모델 (gemini-1.5-flash, gemini-1.5-pro 등)
            prompt: 커스텀 프롬프트
            max_tokens: 최대 토큰 수
            language: 응답 언어
        """
        try:
            import google.generativeai as genai
            self._genai = genai
        except ImportError:
            raise ProviderNotInstalledError("Google", "google-generativeai")

        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise APIKeyNotFoundError("Google", "GOOGLE_API_KEY")

        genai.configure(api_key=self.api_key)

        # model을 먼저 설정해야 super().__init__에서 사용 가능
        self._model_name = model or "gemini-1.5-flash"

        super().__init__(model=model, prompt=prompt, max_tokens=max_tokens, language=language)

        # 모델 인스턴스 생성
        self._model_instance = genai.GenerativeModel(self.model)

    @property
    def default_model(self) -> str:
        return "gemini-1.5-flash"

    @property
    def provider_name(self) -> str:
        return "google"

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
        # PIL Image 사용 시도
        try:
            from PIL import Image
            img = Image.open(image_path)
        except ImportError:
            # PIL 없으면 파일 직접 업로드
            img = self._genai.upload_file(str(image_path))

        use_prompt = prompt if prompt is not None else self.prompt

        response = self._model_instance.generate_content(
            [use_prompt, img],
            generation_config={"max_output_tokens": self.max_tokens}
        )

        return response.text

    def _encode_image(self, image_path: Path) -> str:
        return encode_image_base64(image_path)
