# DOCX 파서 계층 구조(Heading) 지원 기능 구현 계획

## 요약

DOCX 파일의 font size 정보를 분석하여 자동으로 마크다운 heading(`#`, `##`, `###`)을 생성하는 기능 추가.

**핵심 알고리즘**: 가장 많이 사용된 font size를 본문으로 간주, 그보다 큰 크기만 heading으로 인식.

---

## 수정 파일

| 파일                              | 변경 내용                                              |
| --------------------------------- | ------------------------------------------------------ |
| `docx_parser/parser.py`           | HierarchyMode enum, StyleInfo dataclass, 5개 새 메서드 |
| `docx_parser/langchain_loader.py` | hierarchy 파라미터 전달                                |
| `docx_parser/__init__.py`         | 새 타입 export                                         |

---

## 1. 새 타입 추가 (parser.py)

### HierarchyMode Enum

```python
class HierarchyMode(str, Enum):
    """How to detect heading hierarchy"""
    NONE = "none"            # 기본값: heading 감지 안함
    AUTO = "auto"            # style 우선, font_size 폴백
    STYLE = "style"          # styles.xml outlineLevel만 사용
    FONT_SIZE = "font_size"  # font size만 사용
```

### StyleInfo Dataclass

```python
@dataclass
class StyleInfo:
    """Style information from styles.xml"""
    style_id: str
    name: Optional[str] = None
    outline_level: Optional[int] = None  # 0=H1, 1=H2, ...
    font_size: Optional[int] = None      # half-points
```

---

## 2. 새 메서드 (5개)

### 2.1 `_load_styles_info()`

styles.xml 파싱하여 스타일별 outline_level, font_size 추출

### 2.2 `_collect_font_sizes()`

문서 전체 paragraph의 font size 수집 (Set)

### 2.3 `_get_most_common_font_size()`

**핵심**: 가장 많이 사용된 font size 찾기 (= 본문 크기)

```python
def _get_most_common_font_size(self, doc_xml: str, styles: Dict) -> Optional[int]:
    """가장 빈번한 font size를 본문 크기로 판단"""
    from collections import Counter
    sizes = []
    for para in root.findall('.//w:p', ns):
        size = self._get_paragraph_font_size(para, styles)
        if size:
            sizes.append(size)
    if not sizes:
        return None
    counter = Counter(sizes)
    return counter.most_common(1)[0][0]
```

### 2.4 `_build_font_size_hierarchy()`

**본문 크기보다 큰 것만** heading level 매핑

```python
def _build_font_size_hierarchy(
    self,
    font_sizes: Set[int],
    body_font_size: int
) -> Dict[int, int]:
    """
    본문 크기보다 큰 font size만 heading으로 매핑

    Example:
        font_sizes = {48, 36, 28, 24, 20}
        body_font_size = 24 (가장 빈번)

        heading candidates = {48, 36, 28} (24보다 큰 것)
        sorted = [48, 36, 28]

        Result: {48: 1, 36: 2, 28: 3}
        (24, 20은 본문이므로 heading 아님)
    """
    larger_sizes = [s for s in font_sizes if s > body_font_size]
    sorted_sizes = sorted(larger_sizes, reverse=True)

    hierarchy = {}
    for level, size in enumerate(sorted_sizes[:self.max_heading_level], start=1):
        hierarchy[size] = level

    return hierarchy
```

### 2.5 `_get_paragraph_font_size()`

단일 paragraph의 대표 font size 추출 (우선순위: run → paragraph → style)

### 2.6 `_get_heading_level()`

hierarchy_mode에 따라 heading level 결정

---

## 3. 기존 메서드 수정

### `__init__()` - 새 파라미터 추가

```python
def __init__(
    self,
    # ... 기존 파라미터 ...
    hierarchy_mode: HierarchyMode | str = HierarchyMode.NONE,  # 기본값: none
    max_heading_level: int = 6,
):
```

### `parse()` - 계층 분석 로직 추가

```python
def parse(self, docx_path, output_dir=None):
    with zipfile.ZipFile(docx_path) as z:
        # ... 기존 코드 ...

        if self.hierarchy_mode != HierarchyMode.NONE:
            styles = self._load_styles_info(z)
            doc_xml = z.read("word/document.xml").decode('utf-8')

            if self.hierarchy_mode in (HierarchyMode.AUTO, HierarchyMode.FONT_SIZE):
                font_sizes = self._collect_font_sizes(doc_xml, styles)
                body_size = self._get_most_common_font_size(doc_xml, styles)
                font_size_hierarchy = self._build_font_size_hierarchy(font_sizes, body_size)
```

### `_parse_paragraph()` - heading markup 생성

```python
def _parse_paragraph(self, elem, rid_to_num, styles=None, font_size_hierarchy=None):
    # ... 텍스트 추출 ...

    heading_level = self._get_heading_level(elem, styles, font_size_hierarchy)

    if heading_level and text.strip():
        return "#" * heading_level + " " + text

    return text
```

---

## 4. LangChain Loader 수정

`DocxDirectLoader`, `DocxDirectoryLoader`에 새 파라미터 전달:

```python
def __init__(
    self,
    # ... 기존 ...
    hierarchy_mode: HierarchyMode | str = HierarchyMode.NONE,
    max_heading_level: int = 6,
):
```

---

## 5. 사용 예시

```python
from docx_parser import parse_docx, HierarchyMode

# 기본 (heading 감지 안함)
result = parse_docx("document.docx")
# 출력: "개요\n\n개최 배경 및 목적\n\n..."

# font size 기반 heading 감지
result = parse_docx("document.docx", hierarchy_mode="font_size")
# 출력: "# 개요\n\n## 개최 배경 및 목적\n\n..."

# auto 모드 (style 우선, font_size 폴백)
result = parse_docx("document.docx", hierarchy_mode="auto")

# heading depth 제한
result = parse_docx("document.docx", hierarchy_mode="font_size", max_heading_level=3)
```

---

## 6. 알고리즘 예시

**입력 문서**:

```
Paragraph 1: font_size=48 "GBCC 2025 결과보고서"
Paragraph 2: font_size=36 "Ⅰ. 개요"
Paragraph 3: font_size=24 "GBCC는 유방암 인식을 넓히고..."
Paragraph 4: font_size=36 "Ⅱ. 개최 현황"
Paragraph 5: font_size=28 "1. 참가자 현황"
Paragraph 6: font_size=24 "총 5,631명이 참가했다..."
```

**처리 과정**:

1. Font size 수집: {48, 36, 28, 24}
2. 가장 빈번한 크기: 24 (본문)
3. 24보다 큰 크기: {48, 36, 28}
4. Heading 매핑: {48: 1, 36: 2, 28: 3}

**출력**:

```markdown
# GBCC 2025 결과보고서

## Ⅰ. 개요

GBCC는 유방암 인식을 넓히고...

## Ⅱ. 개최 현황

### 1. 참가자 현황

총 5,631명이 참가했다...
```

---

## 7. 검증 방법

### 테스트 1: 기본 동작 유지

```python
result = parse_docx("GBCC 2025_결과보고서_내부용_F.docx")
assert "#" not in result.content[:100]  # heading markup 없어야 함
```

### 테스트 2: font_size 모드

```python
result = parse_docx(
    "GBCC 2025_결과보고서_내부용_F.docx",
    hierarchy_mode="font_size"
)
# 첫 몇 줄에 # 또는 ## 있어야 함
assert result.content.startswith("#") or "## " in result.content[:500]
```

### 테스트 3: 본문보다 작은 크기는 heading 아님

```python
# 24pt 본문, 20pt 캡션 → 캡션은 heading 아님
```

### 테스트 4: LangChain 통합

```python
from docx_parser import DocxDirectLoader, HierarchyMode
loader = DocxDirectLoader("doc.docx", hierarchy_mode=HierarchyMode.FONT_SIZE)
docs = loader.load()
assert "# " in docs[0].page_content or "## " in docs[0].page_content
```

---

## 8. 구현 순서

1. `HierarchyMode` enum, `StyleInfo` dataclass 추가
2. `_load_styles_info()` 구현
3. `_collect_font_sizes()`, `_get_most_common_font_size()` 구현
4. `_build_font_size_hierarchy()` 구현
5. `_get_paragraph_font_size()`, `_get_heading_level()` 구현
6. `__init__()`, `parse()`, `_parse_content()`, `_parse_paragraph()` 수정
7. `parse_docx()` 함수 수정
8. `langchain_loader.py` 수정
9. `__init__.py` export 추가
10. 테스트 실행
