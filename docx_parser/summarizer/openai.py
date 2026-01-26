"""
OpenAI API table summarizer.
"""

from typing import Optional, Union, List, TYPE_CHECKING
import os

from .base import TableSummarizer

if TYPE_CHECKING:
    from ..models.table import TableInfo


class OpenAISummarizer(TableSummarizer):
    """OpenAI API를 사용한 테이블 요약

    Example:
        # 단일 키
        summarizer = OpenAISummarizer(api_key="key1")

        # 여러 키 (rate limit 시 자동 전환)
        summarizer = OpenAISummarizer(api_key=["key1", "key2", "key3"])

        # 환경변수에서 쉼표로 구분 (OPENAI_API_KEY=key1,key2,key3)
        summarizer = OpenAISummarizer()
    """

    def __init__(
        self,
        api_key: Optional[Union[str, List[str]]] = None,
        model: Optional[str] = None,
        prompt: Optional[str] = None,
        max_tokens: int = 150,
        language: str = "ko",
    ):
        """
        Args:
            api_key: OpenAI API 키 (단일 또는 리스트, 쉼표 구분 문자열도 가능)
                     없으면 OPENAI_API_KEY 환경변수 사용
            model: 모델명 (기본: gpt-4o-mini)
            prompt: 커스텀 프롬프트
            max_tokens: 최대 토큰 수
            language: 응답 언어
        """
        super().__init__(model=model, prompt=prompt, max_tokens=max_tokens, language=language)

        # Parse API keys (OPENAI_API_KEY 또는 OPENAI_API_KEYS 지원)
        env_value = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEYS")
        self._api_keys = self._parse_api_keys(api_key, env_value)

        if not self._api_keys:
            raise ValueError(
                "OpenAI API key required. "
                "Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        self._client = None

    @property
    def default_model(self) -> str:
        return "gpt-4o-mini"

    @property
    def provider_name(self) -> str:
        return "openai"

    def _reset_client(self) -> None:
        """클라이언트 재생성"""
        self._client = None

    @property
    def client(self):
        """Lazy initialization of OpenAI client"""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "openai package required. "
                    "Install with: pip install openai"
                )

            self._client = OpenAI(api_key=self._get_current_key())
        return self._client

    def _call_api(
        self,
        table: "TableInfo",
        prompt: Optional[str] = None,
    ) -> str:
        """테이블 요약 생성 (실제 API 호출)

        Args:
            table: TableInfo 객체
            prompt: 커스텀 프롬프트

        Returns:
            테이블 요약 텍스트
        """
        table_content = self._format_table_content(table)

        system_prompt = prompt or self.prompt
        user_message = f"""다음 테이블을 요약해주세요:

{table_content}

요약:"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=self.max_tokens,
            temperature=0.3,
        )

        return response.choices[0].message.content.strip()
