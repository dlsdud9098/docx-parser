<div align="center">

# 📄 docx-parser

**DOCX 파일을 마크다운으로 변환하고, 이미지 추출 및 Vision AI 분석까지**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
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
# → output/document.md, output/images/document/

# JSON으로 저장
result = parse_docx("document.docx", output_dir="output",
                    output_format="json", save_file=True)
# → output/document.json
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

| Provider         | 모델                     |
| ---------------- | ------------------------ |
| **OpenAI**       | gpt-4o, gpt-4o-mini      |
| **Anthropic**    | claude-sonnet-4-20250514 |
| **Google**       | gemini-1.5-flash         |
| **Transformers** | LLaVA, Qwen-VL 등 (로컬) |

### 기본 사용

```python
from docx_parser import parse_docx
from docx_parser.vision import create_vision_provider

provider = create_vision_provider("openai")

result = parse_docx("document.docx", "output",
    vision_provider=provider,
    auto_describe_images=True
)

# [IMAGE_1] → [Image: 회사 로고 이미지...] 자동 치환
print(result.content)
```

### 이미지별 프롬프트

```python
result = parse_docx("document.docx", "output",
    image_prompts={
        1: "이 기술 도면을 상세히 분석해주세요.",
        2: "이 사진을 간단히 설명해주세요.",
        3: "이 차트의 트렌드를 분석해주세요.",
    },
    vision_provider=provider,
    auto_describe_images=True
)
```

### 로컬 모델 (GPU)

```python
provider = create_vision_provider("transformers",
    model_id="llava-hf/llava-v1.6-mistral-7b-hf",
    load_in_4bit=True,
    batch_size=4,
)
```

| VRAM  | 권장 batch_size |
| ----- | --------------- |
| 8GB   | 2               |
| 16GB  | 4               |
| 24GB+ | 8               |

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
├── document.md           # output_format="markdown"
├── document.json         # output_format="json"
├── document.txt          # output_format="text"
└── images/
    └── document/
        ├── 001_image1.png
        ├── 002_image2.png
        └── ...
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
    vision_provider: Optional[VisionProvider] = None,
    auto_describe_images: bool = False,
    image_prompts: Optional[Dict[int, str]] = None,
    save_file: bool = False,
    convert_images: bool = True,
    convert_circled_numbers: bool = True, # ①②③ -> 1. 2. 3.
) -> ParseResult | List[ParseResult]
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

# 저장 메서드
result.save_markdown(path)
result.save_text(path)
result.save_json(path)

# Vision 메서드
result.describe_images(provider, image_prompts=None)
result.get_described_content(provider=None)

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

## 📄 License

MIT License
