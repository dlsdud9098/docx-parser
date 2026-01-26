"""
Table summarizers for LLM-based table summarization.

Example:
    from docx_parser.summarizer import create_table_summarizer

    # OpenAI
    summarizer = create_table_summarizer("openai")

    # Claude
    summarizer = create_table_summarizer("claude")

    # Gemini
    summarizer = create_table_summarizer("gemini")

    # Cerebras
    summarizer = create_table_summarizer("cerebras")

    # 테이블 요약 생성
    summary = summarizer.summarize_table(table_info)
"""

from typing import Optional, Literal

from .base import TableSummarizer

SummarizerType = Literal["openai", "claude", "gemini", "cerebras"]


def create_table_summarizer(
    provider: SummarizerType = "openai",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> TableSummarizer:
    """Table Summarizer 팩토리 함수

    Args:
        provider: 제공자 타입 ("openai", "claude", "gemini", "cerebras")
        api_key: API 키 (없으면 환경변수 사용)
        model: 모델명 (기본값 사용 시 None)
        **kwargs: 제공자별 추가 옵션

    Returns:
        TableSummarizer 인스턴스

    Example:
        # OpenAI (기본)
        summarizer = create_table_summarizer("openai")

        # Claude
        summarizer = create_table_summarizer("claude")

        # Gemini
        summarizer = create_table_summarizer("gemini")

        # Cerebras
        summarizer = create_table_summarizer("cerebras")

        # 커스텀 모델
        summarizer = create_table_summarizer(
            "openai",
            model="gpt-4o",
            language="ko"
        )
    """
    if provider == "openai":
        from .openai import OpenAISummarizer
        return OpenAISummarizer(api_key=api_key, model=model, **kwargs)

    elif provider == "claude":
        from .claude import ClaudeSummarizer
        return ClaudeSummarizer(api_key=api_key, model=model, **kwargs)

    elif provider == "gemini":
        from .gemini import GeminiSummarizer
        return GeminiSummarizer(api_key=api_key, model=model, **kwargs)

    elif provider == "cerebras":
        from .cerebras import CerebrasSummarizer
        return CerebrasSummarizer(api_key=api_key, model=model, **kwargs)

    else:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Supported: openai, claude, gemini, cerebras"
        )


# Lazy imports for individual providers
def __getattr__(name: str):
    if name == "OpenAISummarizer":
        from .openai import OpenAISummarizer
        return OpenAISummarizer
    if name == "ClaudeSummarizer":
        from .claude import ClaudeSummarizer
        return ClaudeSummarizer
    if name == "GeminiSummarizer":
        from .gemini import GeminiSummarizer
        return GeminiSummarizer
    if name == "CerebrasSummarizer":
        from .cerebras import CerebrasSummarizer
        return CerebrasSummarizer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Base classes
    "TableSummarizer",
    # Factory
    "create_table_summarizer",
    "SummarizerType",
    # Providers (lazy loaded)
    "OpenAISummarizer",
    "ClaudeSummarizer",
    "GeminiSummarizer",
    "CerebrasSummarizer",
]
