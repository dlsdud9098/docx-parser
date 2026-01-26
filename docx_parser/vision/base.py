"""
Base class for vision providers.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Union, TYPE_CHECKING
from dataclasses import dataclass
import io

if TYPE_CHECKING:
    from ..parser import ImageInfo


@dataclass
class ImageDescription:
    """이미지 설명 결과"""
    index: int
    description: str
    confidence: Optional[float] = None
    tokens_used: Optional[int] = None


class VisionProvider(ABC):
    """멀티모달 이미지 설명 제공자 추상 클래스

    Example:
        provider = OpenAIVisionProvider(api_key="sk-...")
        description = provider.describe_image(Path("image.png"))
    """

    def __init__(
        self,
        model: Optional[str] = None,
        prompt: Optional[str] = None,
        max_tokens: int = 300,
        language: str = "ko",
    ):
        """
        Args:
            model: 사용할 모델명 (기본값은 각 Provider별로 다름)
            prompt: 커스텀 프롬프트 (없으면 기본 프롬프트 사용)
            max_tokens: 최대 토큰 수
            language: 응답 언어 ("ko", "en", "ja")
        """
        self.model = model or self.default_model
        self.prompt = prompt or self._get_default_prompt(language)
        self.max_tokens = max_tokens
        self.language = language

    @property
    @abstractmethod
    def default_model(self) -> str:
        """기본 모델명"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """제공자 이름 (예: 'openai', 'anthropic')"""
        pass

    @abstractmethod
    def describe_image(
        self,
        image: Union[Path, bytes, "io.BytesIO"],
        prompt: Optional[str] = None,
    ) -> str:
        """단일 이미지 설명 생성

        Args:
            image: 이미지 파일 경로 또는 바이너리 데이터
            prompt: 커스텀 프롬프트 (None이면 self.prompt 사용)

        Returns:
            이미지 설명 텍스트
        """
        pass

    def describe_images(
        self,
        images: List["ImageInfo"],
        image_prompts: Optional[Dict[int, str]] = None,
    ) -> Dict[int, str]:
        """여러 이미지 설명 생성 (기본: 순차 처리)

        Args:
            images: ImageInfo 리스트 (path 또는 data 필드 사용)
            image_prompts: {이미지_인덱스: 프롬프트} 매핑 (선택)
                - 특정 이미지에 커스텀 프롬프트 적용
                - 지정되지 않은 이미지는 기본 프롬프트(self.prompt) 사용

        Returns:
            {이미지_인덱스: 설명} 딕셔너리

        Example:
            # 이미지별 다른 프롬프트 적용
            descriptions = provider.describe_images(images, {
                1: "이 도면을 상세히 분석해주세요...",
                2: "이 사진을 간단히 설명해주세요.",
            })
        """
        result = {}
        for img in images:
            try:
                # 해당 이미지의 커스텀 프롬프트 조회
                prompt = image_prompts.get(img.index) if image_prompts else None

                # path가 있으면 path 사용, 없으면 data 사용
                if img.path:
                    description = self.describe_image(Path(img.path), prompt=prompt)
                elif img.data:
                    description = self.describe_image(img.data, prompt=prompt)
                else:
                    continue  # path도 data도 없으면 스킵
                result[img.index] = description
            except Exception as e:
                # 개별 이미지 실패 시 에러 메시지로 대체
                result[img.index] = f"[이미지 처리 실패: {str(e)}]"
        return result

    @abstractmethod
    def _encode_image(self, image_path: Path) -> str:
        """이미지를 API 형식으로 인코딩"""
        pass

    def _get_default_prompt(self, language: str) -> str:
        """언어별 기본 프롬프트"""
        prompts = {
            "ko": "이 이미지를 간결하게 설명해주세요. 문서 컨텍스트에서 이해할 수 있도록 핵심 내용만 설명합니다.",
            "en": "Describe this image concisely. Focus on the key content for document context.",
            "ja": "この画像を簡潔に説明してください。文書コンテキストで理解できるように、重要な内容のみを説明します。",
            "zh": "请简洁地描述这张图片。专注于文档上下文中的关键内容。",
        }
        return prompts.get(language, prompts["en"])
