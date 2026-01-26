"""
Base class for table summarizers.
"""

import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.table import TableInfo


class TableSummarizer(ABC):
    """테이블 요약 제공자 추상 클래스

    Example:
        # 단일 API 키
        summarizer = CerebrasSummarizer(api_key="key1")

        # 여러 API 키 (rate limit 시 자동 전환)
        summarizer = CerebrasSummarizer(api_key=["key1", "key2", "key3"])

        # 환경변수에서 쉼표로 구분 (CEREBRAS_API_KEY=key1,key2,key3)
        summarizer = CerebrasSummarizer()
    """

    def __init__(
        self,
        model: Optional[str] = None,
        prompt: Optional[str] = None,
        max_tokens: int = 150,
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

        # Multi API key support
        self._api_keys: List[str] = []
        self._current_key_index: int = 0

    def _parse_api_keys(self, api_key: Optional[Union[str, List[str]]], env_value: Optional[str]) -> List[str]:
        """API 키 파싱 (리스트, 쉼표 구분 문자열, 환경변수 모두 지원)

        Args:
            api_key: 파라미터로 전달된 API 키
            env_value: 환경변수에서 가져온 값

        Returns:
            API 키 리스트
        """
        if api_key:
            if isinstance(api_key, list):
                return [k.strip() for k in api_key if k.strip()]
            else:
                # 쉼표로 구분된 문자열 지원
                return [k.strip() for k in api_key.split(",") if k.strip()]

        if env_value:
            return [k.strip() for k in env_value.split(",") if k.strip()]

        return []

    def _get_current_key(self) -> str:
        """현재 사용할 API 키 반환"""
        if not self._api_keys:
            raise ValueError(f"No API keys available for {self.provider_name}")
        return self._api_keys[self._current_key_index]

    def _rotate_key(self) -> bool:
        """다음 API 키로 전환

        Returns:
            True: 다음 키로 전환 성공
            False: 더 이상 키가 없음
        """
        if self._current_key_index < len(self._api_keys) - 1:
            self._current_key_index += 1
            self._reset_client()
            return True
        return False

    def _reset_client(self) -> None:
        """클라이언트 재생성 (서브클래스에서 구현)"""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """기본 모델명"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """제공자 이름 (예: 'cerebras', 'openai')"""
        pass

    @abstractmethod
    def _call_api(self, table: "TableInfo", prompt: Optional[str] = None) -> str:
        """실제 API 호출 (서브클래스에서 구현)

        Args:
            table: TableInfo 객체
            prompt: 커스텀 프롬프트

        Returns:
            테이블 요약 텍스트
        """
        pass

    def summarize_table(
        self,
        table: "TableInfo",
        prompt: Optional[str] = None,
    ) -> str:
        """단일 테이블 요약 생성 (API 키 자동 전환 지원)

        Args:
            table: TableInfo 객체
            prompt: 커스텀 프롬프트 (None이면 self.prompt 사용)

        Returns:
            테이블 요약 텍스트
        """
        last_error = None
        attempts = 0
        max_attempts = len(self._api_keys)

        while attempts < max_attempts:
            try:
                return self._call_api(table, prompt)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Rate limit 또는 인증 에러인 경우 다음 키로 시도
                if any(keyword in error_str for keyword in ["rate", "limit", "429", "quota", "unauthorized", "401"]):
                    if self._rotate_key():
                        attempts += 1
                        continue

                # 다른 에러는 그냥 raise
                raise

        # 모든 키 실패
        raise last_error or Exception(f"All {max_attempts} API keys failed")

    def summarize_tables(
        self,
        tables: List["TableInfo"],
        table_prompts: Optional[Dict[int, str]] = None,
        delay: float = 0.5,
    ) -> Dict[int, str]:
        """여러 테이블 요약 생성

        Args:
            tables: TableInfo 리스트
            table_prompts: {테이블_인덱스: 프롬프트} 매핑 (선택)
            delay: 요청 간 대기 시간 (초, 기본: 0.5) - 순차 처리 시만 사용

        Returns:
            {테이블_인덱스: 요약} 딕셔너리

        Note:
            API 키가 여러 개 등록되어 있으면 자동으로 병렬 처리합니다.
            - 키 1개: 순차 처리 (delay 적용)
            - 키 2개 이상: 병렬 처리 (키 개수만큼 동시 실행)
        """
        # API 키가 여러 개면 자동으로 병렬 처리
        if len(self._api_keys) > 1:
            return self._summarize_tables_parallel(tables, table_prompts)

        # 순차 처리
        result = {}
        for i, table in enumerate(tables):
            try:
                prompt = table_prompts.get(table.index) if table_prompts else None
                summary = self.summarize_table(table, prompt=prompt)
                result[table.index] = summary
            except Exception as e:
                result[table.index] = f"[테이블 요약 실패: {str(e)}]"

            # 마지막 요청이 아니면 딜레이
            if delay > 0 and i < len(tables) - 1:
                time.sleep(delay)
        return result

    def _summarize_tables_parallel(
        self,
        tables: List["TableInfo"],
        table_prompts: Optional[Dict[int, str]] = None,
    ) -> Dict[int, str]:
        """여러 API 키로 병렬 처리

        각 API 키마다 별도 summarizer 인스턴스를 생성하고
        ThreadPoolExecutor로 동시 처리합니다.
        """
        from . import create_table_summarizer

        num_keys = len(self._api_keys)
        max_workers = min(num_keys, len(tables))

        # 각 API 키별로 summarizer 생성
        summarizers = []
        for key in self._api_keys:
            summarizer = create_table_summarizer(
                provider=self.provider_name,
                api_key=key,
                model=self.model,
                max_tokens=self.max_tokens,
                language=self.language,
            )
            summarizers.append(summarizer)

        result = {}

        def process_table(args):
            idx, table, summarizer_idx = args
            summarizer = summarizers[summarizer_idx % num_keys]
            prompt = table_prompts.get(table.index) if table_prompts else None
            try:
                summary = summarizer._call_api(table, prompt)
                return table.index, summary
            except Exception as e:
                return table.index, f"[테이블 요약 실패: {str(e)}]"

        # 테이블을 API 키별로 분배
        tasks = [(i, table, i) for i, table in enumerate(tables)]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_table, task) for task in tasks]
            for future in as_completed(futures):
                table_index, summary = future.result()
                result[table_index] = summary

        return result

    def _get_default_prompt(self, language: str) -> str:
        """언어별 기본 프롬프트"""
        prompts = {
            "ko": "이 테이블의 내용을 한 문장으로 간결하게 요약해주세요. 테이블의 주제와 핵심 데이터를 포함해야 합니다.",
            "en": "Summarize this table in one concise sentence. Include the topic and key data of the table.",
            "ja": "このテーブルの内容を一文で簡潔に要約してください。テーブルの主題と重要なデータを含めてください。",
            "zh": "请用一句话简洁地总结这个表格。包括表格的主题和关键数据。",
        }
        return prompts.get(language, prompts["en"])

    def _format_table_content(self, table: "TableInfo") -> str:
        """테이블 내용을 LLM에 전달할 형식으로 변환 (메모리 데이터 사용)"""
        # TableInfo에 rows 데이터가 있으면 직접 사용 (파일 I/O 없음)
        if table.headers or table.rows:
            return table.to_text(max_rows=10)

        # rows가 없으면 기본 정보만
        info = f"테이블 ({table.row_count}행 x {table.col_count}열)"
        if table.headers:
            info += f"\n헤더: {', '.join(table.headers)}"
        return info
