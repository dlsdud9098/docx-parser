<div align="center">

# 📄 docx-parser

**DOCX 파일을 마크다운으로 변환하고, 이미지 추출 및 Vision AI 분석까지**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Coverage](https://img.shields.io/badge/Coverage-84%25-yellowgreen.svg)](.)
[![Tests](https://img.shields.io/badge/Tests-691%20passed-brightgreen.svg)](.)
[![LangChain](https://img.shields.io/badge/LangChain-Compatible-orange.svg)](https://langchain.com/)

[설치](#-설치) •
[기본 사용법](#-기본-사용법) •
[Vision AI](#-vision-이미지-자동-설명) •
[LangChain 연동](#-langchain--llamaindex-연동) •
[API Reference](#-api-reference)

</div>

---

## ✨ 특징

| 기능               | 설명                                                       |
| ------------------ | ---------------------------------------------------------- |
| 🖼️ **이미지 추출** | DOCX 내 모든 이미지를 번호별로 추출                        |
| 🔄 **포맷 변환**   | WDP, TMP, EMF 등 비표준 포맷을 PNG로 자동 변환             |
| 📍 **위치 보존**   | `[IMAGE_N]` placeholder로 이미지 위치 정확히 표시          |
| 📊 **메타데이터**  | 작성자, 제목, 페이지 수 등 DOCX 메타데이터 추출            |
| 🤖 **Vision AI**   | OpenAI, Anthropic, Google, Transformers로 이미지 자동 설명 |
| 📋 **테이블 요약** | OpenAI, Claude, Gemini, Cerebras로 테이블 LLM 자동 요약    |
| 🔗 **LangChain**   | `BaseLoader` 인터페이스 완벽 호환                          |

---

## 📦 설치

```bash
pip install git+https://github.com/dlsdud9098/docx-parser.git
```

---

## 🚀 기본 사용법

```python
from docx_parser import parse_docx

result = parse_docx("document.docx", output_dir="output")

print(result.content)      # 마크다운 텍스트 ([IMAGE_N] 포함)
print(result.images)       # {1: Path("output/images/001_image.png"), ...}
print(result.image_count)  # 이미지 개수
print(result.metadata)     # DOCX 메타데이터
```

### 자동 저장

```python
# 마크다운으로 자동 저장
result = parse_docx("document.docx", output_dir="output", save_file=True)
# → output/document/document.md, output/document/images/

# JSON으로 저장
result = parse_docx("document.docx", output_dir="output",
                    output_format="json", save_file=True)
# → output/document/document.json
```

| output_format | 저장 파일         |
| ------------- | ----------------- |
| `"markdown"`  | `{filename}.md`   |
| `"text"`      | `{filename}.txt`  |
| `"json"`      | `{filename}.json` |

---

## 🖼️ 이미지 포맷 변환

DOCX 내부의 비표준 이미지 포맷을 자동으로 PNG로 변환합니다.

| 원본 포맷      | 설명                           | 변환            | 요구사항       |
| -------------- | ------------------------------ | --------------- | -------------- |
| WDP / HDP      | Windows Media Photo (JPEG XR)  | → PNG           | `libjxr-tools` |
| TMP            | 임시 파일 (매직 바이트로 감지) | → 원본 또는 PNG | -              |
| EMF / WMF      | Windows Metafile               | → PNG           | `PIL`          |
| PNG, JPEG, GIF | 표준 웹 포맷                   | 변환 없음       | -              |

```bash
# WDP 변환을 위한 의존성 설치 (Ubuntu/Debian)
sudo apt install libjxr-tools
```

```python
# 기본: 자동 변환 (convert_images=True)
result = parse_docx("document.docx", output_dir="output")

# 변환 비활성화
result = parse_docx("document.docx", output_dir="output", convert_images=False)
```

---

## 🤖 Vision: 이미지 자동 설명

### 지원 Provider

| Provider          | 모델                     | 환경변수            |
| ----------------- | ------------------------ | ------------------- |
| **openai**        | gpt-4o, gpt-4o-mini      | `OPENAI_API_KEY`    |
| **anthropic**     | claude-sonnet-4-20250514 | `ANTHROPIC_API_KEY` |
| **gemini/google** | gemini-1.5-flash         | `GOOGLE_API_KEY`    |
| **transformers**  | LLaVA, Qwen-VL 등 (로컬) | -                   |

> **Note**: Cerebras는 텍스트 전용 모델만 제공하므로 Vision(이미지 설명)에는 사용할 수 없습니다. 테이블 요약에만 사용 가능합니다.

### 기본 사용 (간편 방식)

```python
from docx_parser import parse_docx

# Gemini로 이미지 설명 (환경변수: GOOGLE_API_KEY)
result = parse_docx("document.docx", "output",
    auto_describe_images="gemini"
)

# OpenAI로 이미지 설명 (환경변수: OPENAI_API_KEY)
result = parse_docx("document.docx", "output",
    auto_describe_images="openai"
)

# [IMAGE_1] → [IMAGE_1: 회사 로고 이미지...](path) 자동 치환
print(result.content)
```

### Fallback (여러 Provider 순차 시도)

```python
# gemini 실패 → openai → anthropic 순서로 시도
result = parse_docx("document.docx", "output",
    auto_describe_images=["gemini", "openai", "anthropic"]
)
```

### 이미지별 프롬프트

```python
result = parse_docx("document.docx", "output",
    auto_describe_images="gemini",
    image_prompts={
        1: "이 기술 도면을 상세히 분석해주세요.",
        2: "이 사진을 간단히 설명해주세요.",
        3: "이 차트의 트렌드를 분석해주세요.",
    }
)
```

### 고급 사용 (VisionProvider 직접 생성)

```python
from docx_parser import parse_docx
from docx_parser.vision import create_vision_provider

provider = create_vision_provider("openai", model="gpt-4o", max_tokens=500)

result = parse_docx("document.docx", "output",
    vision_provider=provider,
    auto_describe_images=True
)
```

### 로컬 모델 (GPU) - 간편 방식

```python
# 기본 설정 (LLaVA, FP16)
result = parse_docx("document.docx", "output",
    auto_describe_images="transformers"
)

# 4bit 양자화 (VRAM 절약)
result = parse_docx("document.docx", "output",
    auto_describe_images="transformers",
    vision_load_in_4bit=True,
    vision_batch_size=2
)

# 다른 모델 사용
result = parse_docx("document.docx", "output",
    auto_describe_images="transformers",
    vision_model="Qwen/Qwen2-VL-7B-Instruct",
    vision_load_in_4bit=True
)
```

### 로컬 모델 (GPU) - 고급 설정

```python
from docx_parser.vision import create_vision_provider

provider = create_vision_provider("transformers",
    model="llava-hf/llava-v1.6-mistral-7b-hf",
    load_in_4bit=True,
    batch_size=4,
)

result = parse_docx("document.docx", "output",
    vision_provider=provider,
    auto_describe_images=True
)
```

| VRAM  | 권장 설정                                       |
| ----- | ----------------------------------------------- |
| 8GB   | `vision_load_in_4bit=True, vision_batch_size=1` |
| 16GB  | `vision_load_in_4bit=True, vision_batch_size=4` |
| 24GB+ | `vision_batch_size=8`                           |

---

## 🔄 기존 마크다운에 이미지 설명 추가

테이블 요약만 먼저 수행한 뒤, **나중에 이미지 분석을 추가**할 수 있습니다. 기존 테이블 요약은 그대로 유지됩니다.

```python
from docx_parser import update_markdown_with_images

# 기본 사용법
update_markdown_with_images(
    "document.docx",                      # 원본 DOCX
    "output/document/document.md",        # 기존 마크다운 파일
    vision_provider="openai"              # Vision AI 제공자
)

# 폴백 순서 지정 (gemini 실패 시 openai 시도)
update_markdown_with_images(
    "document.docx",
    "output/document/document.md",
    vision_provider=["gemini", "openai"]
)

# 저장 없이 결과만 확인
updated = update_markdown_with_images(
    "document.docx",
    "output/document/document.md",
    save=False
)
```

**동작 방식:**

| 단계 | 설명                                                   |
| ---- | ------------------------------------------------------ |
| 1    | 기존 MD 파일에서 `[IMAGE_N]` 플레이스홀더 탐색         |
| 2    | 원본 DOCX에서 이미지 정보만 추출 (테이블 재분석 안 함) |
| 3    | Vision AI로 이미지 설명 생성                           |
| 4    | `[IMAGE_N]` → `[IMAGE_N: 설명](경로)` 교체             |

> 이미 설명이 있는 `[IMAGE_N: ...]` 형태는 건너뜁니다.

---

## 📋 테이블 추출 및 LLM 요약

테이블을 별도 파일로 추출하고, **RAG 검색에 최적화된 메타 설명**을 LLM으로 생성합니다.

### 요약 결과 형식

```
1. 표의 주제: 학술위원회 구성원 목록
2. 컬럼 구성: 이름, 소속, 학과/전공
3. 주요 키워드: 박세호, 세브란스병원, 김성배, 서울아산병원, 이정언, 삼성서울병원...
```

- **표의 주제**: 테이블이 무엇에 대한 것인지
- **컬럼 구성**: 어떤 열로 구성되어 있는지
- **주요 키워드**: 고유명사, 기관명, 인명, 날짜 등 검색에 사용될 핵심 단어

### 기본 사용

```python
from docx_parser import parse_docx

# 테이블 추출 + Cerebras로 요약
result = parse_docx(
    "document.docx",
    output_dir="output",
    extract_tables=True,
    auto_summarize_tables="cerebras",  # "openai", "claude", "gemini" 가능
)

# 결과
print(result.tables_list)          # List[TableInfo] - 테이블 정보
print(result.table_descriptions)   # {1: "요약1", 2: "요약2", ...}
print(result.content)              # [TABLE_N: 요약](path) 형태로 치환됨
```

### 지원 Provider

| Provider          | 모델                    | 환경변수 (단수/복수 모두 지원)             |
| ----------------- | ----------------------- | ------------------------------------------ |
| **openai**        | gpt-4o-mini             | `OPENAI_API_KEY` / `OPENAI_API_KEYS`       |
| **claude**        | claude-3-5-haiku-latest | `ANTHROPIC_API_KEY` / `ANTHROPIC_API_KEYS` |
| **gemini/google** | gemini-2.0-flash        | `GOOGLE_API_KEY` / `GOOGLE_API_KEYS`       |
| **cerebras**      | llama-3.3-70b           | `CEREBRAS_API_KEY` / `CEREBRAS_API_KEYS`   |

> `.env` 파일이 있으면 자동으로 로드됩니다 (`python-dotenv` 필요)

### Fallback (여러 Provider 순차 시도)

```python
# cerebras 실패 → openai → claude 순서로 시도
result = parse_docx(
    "document.docx",
    output_dir="output",
    extract_tables=True,
    auto_summarize_tables=["cerebras", "openai", "claude"],
)
```

### 멀티 API 키 (자동 병렬 처리)

```bash
# 환경변수에 쉼표로 구분하여 여러 키 설정
export CEREBRAS_API_KEY="key1,key2,key3"
```

```python
from docx_parser.summarizer import CerebrasSummarizer

# 파라미터로 직접 전달
summarizer = CerebrasSummarizer(api_key=["key1", "key2", "key3"])

# 또는 쉼표로 구분된 문자열
summarizer = CerebrasSummarizer(api_key="key1,key2,key3")
```

**동작 방식:**

- **키 1개**: 순차 처리 (delay 적용)
- **키 2개 이상**: 자동 병렬 처리 (키 개수만큼 동시 실행)

Rate limit 회피에 효과적입니다.

### 출력 구조

```
output/
└── document/                # 문서별 폴더
    ├── document.md
    ├── images/
    │   ├── 001_image.png
    │   └── ...
    └── tables/              # extract_tables=True
        ├── 001_table.json   # 또는 .md, .html
        ├── 002_table.json
        └── ...
```

---

## 📊 메타데이터 추출

```python
result = parse_docx("document.docx")

# 코어 메타데이터
print(result.metadata.core.creator)    # 작성자
print(result.metadata.core.title)      # 제목
print(result.metadata.core.created)    # 생성일

# 앱 메타데이터
print(result.metadata.app.pages)       # 페이지 수
print(result.metadata.app.words)       # 단어 수

# 연도 (파일명에서 자동 추출 또는 직접 지정)
print(result.metadata.to_dict()['year'])  # 2022 (파일명: "GBCC 2022_결과보고서.docx")
```

### 연도 자동 추출

파일명에서 `20XX` 패턴을 자동으로 추출하여 `year` 필드에 저장합니다.

```python
# 자동 추출: "GBCC 2022_결과보고서.docx" → year: 2022
result = parse_docx("GBCC 2022_결과보고서.docx")
print(result.metadata.to_dict()['year'])  # 2022

# 사용자 직접 지정 (우선순위 높음)
result = parse_docx("report.docx", year=2023)
print(result.metadata.to_dict()['year'])  # 2023

# LangChain 메타데이터에서도 사용 가능
docs = result.to_langchain_documents()
print(docs[0].metadata['year'])  # 2023
```

---

## 📑 헤더 자동 감지 (Hierarchy Mode)

DOCX 문서의 제목/섹션 구조를 자동으로 마크다운 헤더(`#`, `##`, `###`)로 변환합니다.

### 기본 모드

```python
# 폰트 크기 기반 (큰 폰트 → 상위 헤더)
result = parse_docx("document.docx", hierarchy_mode="font_size")

# Word 스타일 기반 (Heading 1, Heading 2 등)
result = parse_docx("document.docx", hierarchy_mode="style")

# 자동 (스타일 우선, 폰트 폴백)
result = parse_docx("document.docx", hierarchy_mode="auto")
```

### 🆕 Pattern 모드 (커스텀 패턴)

텍스트 패턴으로 헤더를 감지합니다. LangChain의 `MarkdownHeaderTextSplitter`와 함께 사용하기 좋습니다.

```python
from docx_parser import parse_docx

# 커스텀 헤더 패턴: (패턴 예시, 헤더레벨)
heading_patterns = [
    ("I. ", 1),     # I. II. III. IV. → H1
    ("1. ", 2),     # 1. 2. 3. 4. → H2
    ("1) ", 3),     # 1) 2) 3) 4) → H3
    ("(1) ", 4),    # (1) (2) (3) → H4
]

result = parse_docx(
    "document.docx",
    output_dir="output",
    hierarchy_mode="pattern",
    heading_patterns=heading_patterns,
    save_file=True
)

# 결과: "I. 개요" → "# I. 개요"
#       "1. 등록" → "## 1. 등록"
#       "1) 행사개요" → "### 1) 행사개요"
```

**지원 패턴:**

| 입력 예시 | 매칭 대상       | 설명          |
| --------- | --------------- | ------------- |
| `"I. "`   | I. II. III. IV. | 로마숫자      |
| `"Ⅰ. "`   | Ⅰ. Ⅱ. Ⅲ.        | 전각 로마숫자 |
| `"1. "`   | 1. 2. 3. 10.    | 숫자+점       |
| `"1) "`   | 1) 2) 3)        | 숫자+괄호     |
| `"(1) "`  | (1) (2) (3)     | 괄호+숫자     |
| `"A. "`   | A. B. C.        | 대문자+점     |
| `"a) "`   | a) b) c)        | 소문자+괄호   |
| `"가. "`  | 가. 나. 다.     | 한글+점       |

### LangChain과 함께 사용

```python
from docx_parser import parse_docx
from langchain_text_splitters import MarkdownHeaderTextSplitter

# 1. Pattern 모드로 파싱
result = parse_docx("document.docx", hierarchy_mode="pattern",
                    heading_patterns=[("^\\d+\\. ", 1), ("^\\d+\\) ", 2)])

# 2. 헤더 기준 분할
headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]
splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
chunks = splitter.split_text(result.markdown_content)

for chunk in chunks:
    print(chunk.metadata)  # {'Header 1': '1. 등록', 'Header 2': '1) 개요'}
```

| hierarchy_mode | 설명                     | 사용 시점                       |
| -------------- | ------------------------ | ------------------------------- |
| `"none"`       | 헤더 감지 안 함 (기본값) | 원본 그대로 필요할 때           |
| `"font_size"`  | 폰트 크기 기반           | 일반적인 문서                   |
| `"style"`      | Word 스타일 기반         | 스타일이 정확히 적용된 문서     |
| `"auto"`       | 스타일 → 폰트 폴백       | 다양한 문서                     |
| `"pattern"`    | 커스텀 텍스트 패턴       | 보고서, 계약서 등 정형화된 문서 |

---

## 🔗 LangChain / LlamaIndex 연동

### Document 변환

```python
from docx_parser import parse_docx

result = parse_docx("document.docx", output_dir="output")

# LangChain
docs = result.to_langchain_documents()

# LlamaIndex
docs = result.to_llama_index_documents()

# Vision 설명 포함
docs = result.to_langchain_documents(described=True, provider=provider)
```

### 텍스트 분할

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

result = parse_docx("document.docx")
docs = result.to_langchain_documents()

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(docs)
```

### 벡터 스토어

```python
from llama_index.core import VectorStoreIndex

result = parse_docx("document.docx")
docs = result.to_llama_index_documents()

index = VectorStoreIndex.from_documents(docs)
response = index.as_query_engine().query("문서의 주요 내용은?")
```

### Loader 클래스

```python
from docx_parser import DocxDirectLoader
from docx_parser.langchain_loader import DocxDirectoryLoader

# 단일 파일
loader = DocxDirectLoader("document.docx", output_dir="output")
docs = loader.load()

# 디렉토리 전체
loader = DocxDirectoryLoader("documents/", output_dir="output")
docs = loader.load()
```

---

## 📁 출력 구조

```
output/
└── document/                    # 문서별 폴더
    ├── document.md              # output_format="markdown"
    ├── document.json            # output_format="json"
    ├── document.txt             # output_format="text"
    ├── images/
    │   ├── 001_image1.png
    │   ├── 002_image2.png
    │   └── ...
    └── tables/                  # extract_tables=True
        ├── 001_table.md
        ├── 002_table.md
        └── ...
```

### 플레이스홀더 형식

이미지와 테이블 모두 경로가 포함된 링크 형식으로 출력됩니다:

```markdown
# 이미지 (경로 포함)

[IMAGE_1](output/document/images/001_image.png)

# 이미지 + Vision AI 설명

[IMAGE_1: 차트 이미지입니다](output/document/images/001_image.png)

# 테이블 (경로 + RAG 검색용 요약)

[TABLE_1: 1. 표의 주제: 학술위원회 구성원 목록 2. 컬럼 구성: 이름, 소속, 학과/전공 3. 주요 키워드: 박세호, 세브란스병원, 김성배, 서울아산병원...](output/document/tables/001_table.md)
```

---

## 📖 API Reference

### parse_docx()

```python
def parse_docx(
    docx_path: str | Path | List[str] | List[Path],
    output_dir: Optional[str | Path] = None,
    extract_images: bool = True,
    output_format: str = "markdown",      # "markdown", "text", "json"
    table_format: str = "markdown",       # "markdown", "html", "json", "text"
    extract_metadata: bool = True,
    hierarchy_mode: str = "none",         # "none", "auto", "style", "font_size", "pattern"
    heading_patterns: Optional[List[Tuple[str, int]]] = None,  # pattern 모드용
    vision_provider: Optional[VisionProvider] = None,  # 직접 provider 전달 (고급)
    auto_describe_images: str | List[str] | bool = False,  # "openai", "anthropic", "gemini", "transformers"
    image_prompts: Optional[Dict[int, str]] = None,
    save_file: bool = False,
    convert_images: bool = True,
    extract_tables: bool = False,         # 테이블 별도 파일로 추출
    auto_summarize_tables: str | List[str] | bool = False,  # "openai", "claude", "gemini", "google", "cerebras"
    summarizer_max_tokens: int = 200,     # 테이블 요약 최대 토큰 (키워드 추출 포함 시 300+ 권장)
    vision_max_tokens: int = 300,         # 이미지 설명 최대 토큰
    vision_model: Optional[str] = None,   # Vision 모델 ID (예: "gpt-4o-mini", "llava-hf/...")
    vision_load_in_4bit: bool = False,    # Transformers 4bit 양자화
    vision_load_in_8bit: bool = False,    # Transformers 8bit 양자화
    vision_batch_size: int = 4,           # Transformers 배치 크기
    year: Optional[int] = None,           # 문서 연도 (미지정 시 파일명에서 자동 추출)
) -> ParseResult | List[ParseResult]
```

### update_markdown_with_images()

```python
def update_markdown_with_images(
    docx_path: str | Path,                # 원본 DOCX 파일 경로
    markdown_path: str | Path,            # 업데이트할 마크다운 파일 경로
    vision_provider: str | List[str] | VisionProvider = "openai",
    image_prompts: Optional[Dict[int, str]] = None,
    vision_max_tokens: int = 300,
    vision_model: Optional[str] = None,
    save: bool = True,                    # True면 파일 덮어쓰기
) -> str                                  # 업데이트된 마크다운 내용
```

### ParseResult

```python
result.content             # 콘텐츠 (markdown/text: str, json: List[block])
result.text_content        # 순수 텍스트 (항상 str)
result.markdown_content    # 마크다운 (항상 str)
result.images              # {num: Path} 이미지 경로
result.image_count         # 이미지 개수
result.metadata            # DocxMetadata
result.images_list         # List[ImageInfo]
result.image_descriptions  # {num: str} Vision 설명
result.tables_list         # List[TableInfo] 테이블 정보
result.table_descriptions  # {num: str} LLM 요약

# 저장 메서드
result.save_markdown(path)
result.save_text(path)
result.save_json(path)

# Vision 메서드
result.describe_images(provider, image_prompts=None)
result.get_described_content(provider=None)

# 테이블 메서드
result.describe_tables(summarizer=None)
result.replace_table_placeholders(descriptions=None)

# Framework 변환
result.to_langchain_documents(described=False, provider=None)
result.to_llama_index_documents(described=False, provider=None)
result.to_langchain_metadata()
```

### output_format="json" 블록 구조

`output_format="json"`일 때 `result.content`는 블록 리스트로 반환됩니다.

```python
result = parse_docx("document.docx", output_format="json")

# result.content 예시:
[
    {"type": "heading", "level": 1, "content": "문서 제목"},
    {"type": "paragraph", "content": "일반 텍스트 내용입니다."},
    {"type": "image", "index": 1},
    {"type": "table", "headers": ["이름", "나이"], "rows": [["홍길동", "30"]], "metadata": {...}},
    {"type": "paragraph", "content": "또 다른 텍스트."}
]
```

| 블록 타입   | 필드                                               |
| ----------- | -------------------------------------------------- |
| `paragraph` | `content`                                          |
| `heading`   | `level`, `content`                                 |
| `table`     | `headers`, `rows`, `metadata`                      |
| `image`     | `index`, `path`(optional), `description`(optional) |

---

## 🏗️ 아키텍처

모듈화된 프로세서 기반 아키텍처로 확장성과 테스트 용이성을 제공합니다.

```
docx_parser/
├── parser.py           # 오케스트레이션
├── processors/         # 핵심 처리 로직
│   ├── table.py        # 테이블 파싱 (vMerge, gridSpan 지원)
│   ├── content.py      # 콘텐츠 파싱 (마크다운/JSON 변환)
│   ├── style.py        # 스타일 및 폰트 분석
│   ├── metadata.py     # 메타데이터 추출
│   └── image.py        # 이미지 추출 및 변환
├── strategies/         # 헤딩 감지 전략 (Strategy Pattern)
│   ├── style.py        # Word 스타일 기반
│   ├── font_size.py    # 폰트 크기 기반
│   └── pattern.py      # 커스텀 패턴 기반
├── formatters/         # 출력 포맷터
│   ├── markdown.py     # 마크다운 변환
│   ├── html.py         # HTML 변환
│   └── json_formatter.py
├── vision/             # Vision AI 통합
│   ├── openai.py       # OpenAI GPT-4o
│   ├── anthropic.py    # Claude
│   ├── google.py       # Gemini
│   └── transformers.py # 로컬 모델 (LLaVA 등)
├── summarizer/         # 테이블 LLM 요약
│   ├── openai.py       # OpenAI gpt-4o-mini
│   ├── claude.py       # Anthropic Claude
│   ├── gemini.py       # Google Gemini
│   └── cerebras.py     # Cerebras Llama
└── models/             # 데이터 모델
```

---

## 📄 License

MIT License
