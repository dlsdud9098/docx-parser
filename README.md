# docx-parser

DOCX 파일을 파싱하여 이미지 추출, 메타데이터, 멀티모달 Vision 분석을 지원합니다.
LangChain과 완벽하게 호환됩니다.

## 설치

```bash
# 기본 설치
pip install -e .

# LangChain 지원
pip install -e ".[langchain]"

# LlamaIndex 지원
pip install -e ".[llama-index]"

# Vision API (OpenAI, Anthropic, Google)
pip install -e ".[vision]"

# 로컬 모델 (Transformers)
pip install -e ".[vision-local]"

# 전체 설치
pip install -e ".[all]"
```

## 특징

- **외부 의존성 없음**: 기본 기능은 순수 Python 표준 라이브러리만 사용
- **이미지 추출**: DOCX 내 모든 이미지를 번호별로 추출
- **이미지 자동 변환**: WDP, TMP, EMF 등 비표준 포맷을 PNG로 자동 변환
- **위치 보존**: `[IMAGE_N]` placeholder로 이미지 위치 정확히 표시
- **메타데이터 추출**: 작성자, 제목, 페이지 수 등 DOCX 메타데이터
- **멀티모달 Vision**: 6개 Provider로 이미지 자동 설명 생성
- **이미지별 프롬프트**: 도면, 차트, 사진 등 타입별 최적화 분석
- **마크다운 출력**: 표를 포함한 마크다운 형식 출력
- **LangChain 호환**: `BaseLoader` 인터페이스 구현

## 기본 사용법

```python
from docx_parser import parse_docx

result = parse_docx("document.docx", output_dir="output")

print(result.content)      # 마크다운 텍스트 ([IMAGE_N] 포함)
print(result.images)       # {1: Path("output/images/001_image.png"), ...}
print(result.image_count)  # 이미지 개수
print(result.metadata)     # DOCX 메타데이터
```

## 자동 저장 (save_file)

`output_dir`과 함께 `save_file=True`를 지정하면 `output_format`에 따라 파싱 결과가 자동으로 저장됩니다.

```python
from docx_parser import parse_docx

# 마크다운 자동 저장 (기본 output_format)
result = parse_docx("document.docx", output_dir="output", save_file=True)
# 저장됨: output/document.md, output/images/document/

# JSON으로 저장
result = parse_docx("report.docx", output_dir="output",
                    output_format="json", save_file=True)
# 저장됨: output/report.json, output/images/report/

# 이미지만 저장 (기본 동작)
result = parse_docx("document.docx", output_dir="output")
# 저장됨: output/images/document/ (이미지만)

# 배치 처리
results = parse_docx(["doc1.docx", "doc2.docx"],
                     output_dir="output", save_file=True)
# 저장됨: output/doc1.md, output/doc2.md
```

| output_format | 저장 파일         |
| ------------- | ----------------- |
| `"markdown"`  | `{filename}.md`   |
| `"text"`      | `{filename}.txt`  |
| `"json"`      | `{filename}.json` |

### 수동 저장 (기존 방식)

```python
result = parse_docx("document.docx", output_dir="output")

# 원하는 경로에 개별 저장
result.save_markdown("custom/path/document.md")
result.save_text("custom/path/document.txt")
result.save_json("custom/path/document.json")
```

## 이미지 포맷 변환

DOCX 내부의 비표준 이미지 포맷(WDP, TMP, EMF 등)을 자동으로 PNG로 변환합니다.

### 지원 포맷

| 원본 포맷      | 설명                                     | 변환                 |
| -------------- | ---------------------------------------- | -------------------- |
| WDP / HDP      | Windows Media Photo (JPEG XR 전신)       | → PNG                |
| TMP            | 임시 파일 (매직 바이트로 실제 포맷 감지) | → 원본 포맷 또는 PNG |
| EMF / WMF      | Windows Metafile (벡터 그래픽)           | → PNG                |
| PNG, JPEG, GIF | 표준 웹 포맷                             | 변환 없음            |

### 사용법

```python
from docx_parser import parse_docx

# 기본: 자동 변환 활성화 (convert_images=True)
result = parse_docx("document.docx", output_dir="output")
# WDP, TMP 등이 자동으로 PNG로 변환됨

# 변환 비활성화 (원본 그대로 저장)
result = parse_docx("document.docx", output_dir="output", convert_images=False)
```

> **참고**: 이미지 변환에는 PIL/Pillow가 필요합니다. `pip install Pillow`

## Vision: 이미지 자동 설명

### 지원 Provider

| Provider     | 모델                     | 설치                               |
| ------------ | ------------------------ | ---------------------------------- |
| OpenAI       | gpt-4o, gpt-4o-mini      | `pip install -e ".[openai]"`       |
| Anthropic    | claude-sonnet-4-20250514 | `pip install -e ".[anthropic]"`    |
| Google       | gemini-1.5-flash         | `pip install -e ".[google]"`       |
| Transformers | LLaVA, Qwen-VL 등        | `pip install -e ".[vision-local]"` |

### 기본 사용

```python
from docx_parser import parse_docx
from docx_parser.vision import create_vision_provider

# Provider 생성
provider = create_vision_provider("openai")  # 또는 "anthropic", "google", "transformers"

# 자동 이미지 설명
result = parse_docx("document.docx", "output",
    vision_provider=provider,
    auto_describe_images=True
)

# [IMAGE_1] → [Image: 회사 로고 이미지...] 자동 치환됨
print(result.content)
```

### 이미지별 프롬프트 (v0.3.3+)

이미지 타입에 따라 최적화된 프롬프트를 적용할 수 있습니다.

```python
from docx_parser import parse_docx
from docx_parser.vision import create_vision_provider

provider = create_vision_provider("openai")

# 이미지별 다른 프롬프트 적용
result = parse_docx("document.docx", "output",
    image_prompts={
        1: "이 기술 도면을 상세히 분석해주세요: 치수, 부품명, 구조...",
        2: "이 기념사진을 간단히 설명해주세요.",
        3: "이 차트의 트렌드와 핵심 수치를 분석해주세요.",
    },
    vision_provider=provider,
    auto_describe_images=True
)
```

#### 라벨 기반 프롬프트 매핑 (권장 패턴)

```python
# 프롬프트 사전 정의
MY_PROMPTS = {
    "도면": """이 기술 도면을 상세히 분석해주세요:
- 치수 및 규격 정보
- 부품명 및 구성요소
- 구조적 특징""",
    "사진": "이 사진의 주요 내용을 간단히 설명해주세요.",
    "차트": """이 차트를 분석해주세요:
- 차트 유형
- 주요 트렌드
- 핵심 수치""",
}

# 이미지별 라벨 지정
labels = ["도면", "사진", "차트"]
image_prompts = {i+1: MY_PROMPTS[lbl] for i, lbl in enumerate(labels)}

result = parse_docx("document.docx", "output",
    image_prompts=image_prompts,
    vision_provider=provider,
    auto_describe_images=True
)
```

### 로컬 모델 (Transformers)

GPU에서 로컬 실행:

```python
from docx_parser.vision import create_vision_provider

provider = create_vision_provider("transformers",
    model_id="llava-hf/llava-v1.6-mistral-7b-hf",
    load_in_4bit=True,  # 메모리 절약
    batch_size=4,       # GPU 메모리에 따라 조절
)

result = parse_docx("document.docx", "output",
    vision_provider=provider,
    auto_describe_images=True
)
```

**배치 크기 권장:**

- 8GB VRAM: `batch_size=2`
- 16GB VRAM: `batch_size=4` (기본)
- 24GB+ VRAM: `batch_size=8`

## 메타데이터 추출

```python
result = parse_docx("document.docx")

# 코어 메타데이터
print(result.metadata.core.creator)    # 작성자
print(result.metadata.core.title)      # 제목
print(result.metadata.core.created)    # 생성일

# 앱 메타데이터
print(result.metadata.app.pages)       # 페이지 수
print(result.metadata.app.words)       # 단어 수
print(result.metadata.app.application) # 작성 앱
```

## LangChain / LlamaIndex 연동

### ParseResult에서 직접 변환 (LlamaParse 스타일)

```python
from docx_parser import parse_docx

result = parse_docx("document.docx", output_dir="output")

# LangChain Document로 변환
docs = result.to_langchain_documents()
# [Document(page_content="...", metadata={...})]

# LlamaIndex Document로 변환
docs = result.to_llama_index_documents()
# [Document(text="...", metadata={...})]

# 이미지 설명이 포함된 버전
from docx_parser.vision import create_vision_provider
provider = create_vision_provider("openai")
docs = result.to_langchain_documents(described=True, provider=provider)
```

### 텍스트 분할 (LangChain)

```python
from docx_parser import parse_docx
from langchain_text_splitters import RecursiveCharacterTextSplitter

result = parse_docx("document.docx")
docs = result.to_langchain_documents()

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(docs)
```

### 벡터 스토어 (LlamaIndex)

```python
from docx_parser import parse_docx
from llama_index.core import VectorStoreIndex

result = parse_docx("document.docx")
docs = result.to_llama_index_documents()

index = VectorStoreIndex.from_documents(docs)
query_engine = index.as_query_engine()
response = query_engine.query("문서의 주요 내용은?")
```

### Loader 클래스 사용

```python
from docx_parser import DocxDirectLoader

# 단일 파일
loader = DocxDirectLoader("document.docx", output_dir="output")
docs = loader.load()

# 디렉토리 전체
from docx_parser.langchain_loader import DocxDirectoryLoader
loader = DocxDirectoryLoader("documents/", output_dir="output")
docs = loader.load()

# 벡터 스토어에 저장
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings())
```

## 출력 형식

```python
# 마크다운 (기본)
result = parse_docx("doc.docx", output_format="markdown")

# 플레인 텍스트
result = parse_docx("doc.docx", output_format="text")

# JSON
result = parse_docx("doc.docx", output_format="json")
```

## 표 형식

```python
# 마크다운 표 (기본)
result = parse_docx("doc.docx", table_format="markdown")

# HTML 표 (colspan/rowspan 지원)
result = parse_docx("doc.docx", table_format="html")

# JSON (병합 정보 보존)
result = parse_docx("doc.docx", table_format="json")
```

## 출력 구조

```python
# save_file=True 사용 시 (output_format에 따라 저장)
parse_docx("document.docx", output_dir="output", output_format="markdown", save_file=True)
```

```
output/
├── document.md              # output_format="markdown" 시
├── document.json            # output_format="json" 시
├── document.txt             # output_format="text" 시
└── images/
    └── document/
        ├── 001_image1.jpeg
        ├── 002_image2.png
        └── ...
```

## API Reference

### parse_docx()

```python
def parse_docx(
    docx_path: str | Path | List[str] | List[Path],
    output_dir: Optional[str | Path] = None,
    extract_images: bool = True,
    output_format: str = "markdown",  # "markdown", "text", "json"
    table_format: str = "markdown",   # "markdown", "html", "json", "text"
    extract_metadata: bool = True,
    hierarchy_mode: str = "none",     # "none", "auto", "style", "font_size"
    vision_provider: Optional[VisionProvider] = None,
    auto_describe_images: bool = False,
    image_prompts: Optional[Dict[int, str]] = None,
    save_file: bool = False,          # True면 output_format에 따라 저장
    convert_images: bool = True,      # WDP, TMP, EMF -> PNG 변환
) -> ParseResult | List[ParseResult]:
```

| 파라미터         | 설명                                                        |
| ---------------- | ----------------------------------------------------------- |
| `docx_path`      | DOCX 파일 경로 (단일 또는 리스트)                           |
| `output_dir`     | 이미지 및 문서 저장 디렉토리                                |
| `convert_images` | 비표준 이미지 포맷(WDP, TMP, EMF)을 PNG로 변환 (기본: True) |
| `save_file`      | True면 output_format에 따라 파일 자동 저장 (기본: False)    |

### ParseResult

```python
result.content          # 마크다운 콘텐츠
result.images           # {num: Path} 이미지 경로
result.image_count      # 이미지 개수
result.metadata         # DocxMetadata
result.images_list      # List[ImageInfo]
result.image_descriptions  # {num: str} 설명

# 저장 메서드
result.save_markdown(path)
result.save_text(path)
result.save_json(path)

# Vision 메서드
result.describe_images(provider, image_prompts=None)
result.get_described_content(provider=None)

# LangChain/LlamaIndex 변환 (v0.3.4+)
result.to_langchain_documents(described=False, provider=None)  # List[Document]
result.to_llama_index_documents(described=False, provider=None)  # List[Document]
result.to_langchain_metadata()  # Dict[str, Any]
```

## License

MIT
