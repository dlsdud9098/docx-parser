# DOCX Parser v0.3.2 테스트 계획서

> 작성일: 2026-01-25
> 버전: v0.3.2
> 총 테스트 케이스: 277개

---

## 목차

1. [개요](#1-개요)
2. [테스트 범위](#2-테스트-범위)
3. [테스트 케이스](#3-테스트-케이스)
   - [3.1 기본 파싱 테스트](#31-기본-파싱-테스트)
   - [3.2 이미지 처리 테스트](#32-이미지-처리-테스트)
   - [3.3 표 파싱 테스트](#33-표-파싱-테스트)
   - [3.4 특수문자 이스케이프 테스트](#34-특수문자-이스케이프-테스트)
   - [3.5 수직 병합 테스트](#35-수직-병합-테스트)
   - [3.6 수평 병합 테스트](#36-수평-병합-테스트)
   - [3.7 병합 조합 테스트](#37-병합-조합-테스트)
   - [3.8 Core 메타데이터 추출 테스트](#38-core-메타데이터-추출-테스트)
   - [3.9 App 메타데이터 추출 테스트](#39-app-메타데이터-추출-테스트)
   - [3.10 DocxMetadata 통합 테스트](#310-docxmetadata-통합-테스트)
   - [3.11 출력 형식 테스트](#311-출력-형식-테스트)
   - [3.12 텍스트 변환 테스트](#312-텍스트-변환-테스트)
   - [3.13 ParseResult 저장 메서드 테스트](#313-parseresult-저장-메서드-테스트)
   - [3.14 ParseResult 유틸리티 메서드 테스트](#314-parseresult-유틸리티-메서드-테스트)
   - [3.15 LangChain DocxDirectLoader 테스트](#315-langchain-docxdirectloader-테스트)
   - [3.16 LangChain DocxDirectoryLoader 테스트](#316-langchain-docxdirectoryloader-테스트)
   - [3.17 LangChain Import 테스트](#317-langchain-import-테스트)
   - [3.18 에러 처리 테스트](#318-에러-처리-테스트)
   - [3.19 엣지 케이스 테스트](#319-엣지-케이스-테스트)
   - [3.20 옵션 조합 테스트](#320-옵션-조합-테스트)
   - [3.21 성능 테스트](#321-성능-테스트)
   - [3.22 호환성 테스트](#322-호환성-테스트)
   - [3.23 계층 구조 (Heading) 테스트](#323-계층-구조-heading-테스트)
   - [3.24 Font Size 분석 테스트](#324-font-size-분석-테스트)
   - [3.25 Style 기반 Heading 테스트](#325-style-기반-heading-테스트)
   - [3.26 Vision 모듈 기본 테스트](#326-vision-모듈-기본-테스트)
   - [3.27 Transformers Provider 테스트](#327-transformers-provider-테스트)
   - [3.28 Vision 통합 테스트](#328-vision-통합-테스트)
   - [3.29 표 형식 (TableFormat) 테스트](#329-표-형식-tableformat-테스트)
   - [3.30 TableCell/TableData 클래스 테스트](#330-tablecelltabledata-클래스-테스트)
4. [테스트 요약](#4-테스트-요약)
5. [테스트 환경](#5-테스트-환경)

---

## 1. 개요

### 1.1 목적

이 문서는 `docx-parser` 패키지 v0.3.1의 모든 기능을 완전히 검증하기 위한 테스트 계획을 정의합니다.

### 1.2 대상 모듈

| 모듈                              | 설명                              |
| --------------------------------- | --------------------------------- |
| `docx_parser/parser.py`           | 핵심 파서 클래스 및 데이터 클래스 |
| `docx_parser/langchain_loader.py` | LangChain 호환 로더               |
| `docx_parser/vision/`             | 멀티모달 Vision 모듈              |
| `docx_parser/__init__.py`         | 패키지 초기화 및 export           |

### 1.3 주요 클래스

- `DocxParser`: 메인 파서 클래스
- `ParseResult`: 파싱 결과 데이터클래스
- `CoreMetadata`: Dublin Core 메타데이터
- `AppMetadata`: 애플리케이션 메타데이터
- `DocxMetadata`: 통합 메타데이터
- `ImageInfo`: 이미지 정보 (data 필드 포함)
- `StyleInfo`: 스타일 정보 (heading 감지용)
- `TableCell`: 표 셀 정보 (병합 정보 포함)
- `TableData`: 표 전체 데이터 구조
- `DocxDirectLoader`: 단일 파일 LangChain 로더
- `DocxDirectoryLoader`: 디렉토리 LangChain 로더
- `VisionProvider`: Vision 추상 클래스 (base)
- `TransformersProvider`: HuggingFace Transformers 기반 Vision

### 1.4 Enum 타입

- `VerticalMergeMode`: `repeat`, `empty`, `first`
- `HorizontalMergeMode`: `expand`, `single`, `repeat`
- `OutputFormat`: `markdown`, `text`, `json`
- `HierarchyMode`: `none`, `auto`, `style`, `font_size`
- `TableFormat`: `markdown`, `json`, `html`, `text`

---

## 2. 테스트 범위

### 2.1 기능 테스트 (Functional Testing)

- 텍스트 추출
- 이미지 추출 및 placeholder 치환
- 표 파싱 및 다양한 형식 변환 (markdown, json, html, text)
- 병합 셀 처리 (수직/수평) 및 병합 정보 보존
- 메타데이터 추출
- 출력 형식 변환
- 파일 저장
- LangChain 호환성
- Vision 이미지 설명 생성 (Transformers)

### 2.2 비기능 테스트 (Non-Functional Testing)

- 에러 처리
- 성능 (대용량 파일)
- 호환성 (다양한 DOCX 생성 도구)

---

## 3. 테스트 케이스

### 3.1 기본 파싱 테스트

**목적**: DocxParser의 기본 동작 검증

| ID     | 테스트 케이스          | 입력                  | 예상 결과                                                    | 우선순위 |
| ------ | ---------------------- | --------------------- | ------------------------------------------------------------ | -------- |
| TC-1.1 | 정상 DOCX 파일 파싱    | 유효한 .docx 파일     | ParseResult 반환, content 비어있지 않음                      | High     |
| TC-1.2 | DocxParser 기본 생성자 | 파라미터 없음         | 기본값 적용 (extract_images=True, output_format=MARKDOWN 등) | High     |
| TC-1.3 | parse_docx() 편의 함수 | 유효한 .docx 파일     | DocxParser.parse()와 동일한 결과                             | High     |
| TC-1.4 | output_dir 지정        | output_dir="./output" | 이미지 디렉토리 생성 (output/images/{stem}/)                 | High     |
| TC-1.5 | output_dir 미지정      | output_dir=None       | 이미지 미추출, images dict 비어있음                          | Medium   |

---

### 3.2 이미지 처리 테스트

**목적**: 이미지 추출 및 placeholder 치환 기능 검증

| ID      | 테스트 케이스                         | 입력                            | 예상 결과                                              | 우선순위 |
| ------- | ------------------------------------- | ------------------------------- | ------------------------------------------------------ | -------- |
| TC-2.1  | 이미지 포함 문서 파싱                 | 이미지 3개 포함 문서            | `[IMAGE_1]`, `[IMAGE_2]`, `[IMAGE_3]` placeholder 생성 | High     |
| TC-2.2  | 이미지 없는 문서 파싱                 | 텍스트만 있는 문서              | image_count=0, placeholder 없음                        | High     |
| TC-2.3  | 여러 이미지 순서                      | 이미지 10개 문서                | 1, 2, 3, ..., 10 순차 번호 부여                        | High     |
| TC-2.4  | extract_images=True + output_dir      | 이미지 문서 + 출력 경로         | 이미지 파일 저장, images dict에 Path 포함              | High     |
| TC-2.5  | extract_images=True + output_dir 없음 | 이미지 문서, output_dir=None    | 이미지 미저장, image_mapping만 채워짐                  | Medium   |
| TC-2.6  | extract_images=False                  | 이미지 문서                     | 이미지 미추출, placeholder만 content에 생성            | Medium   |
| TC-2.7  | 커스텀 placeholder                    | image_placeholder="(IMG:{num})" | `(IMG:1)`, `(IMG:2)` 형식 적용                         | Medium   |
| TC-2.8  | 이미지 저장 경로 확인                 | output_dir="./out"              | `out/images/{stem}/{num}_{name}` 경로                  | High     |
| TC-2.9  | ImageInfo 데이터 정확성               | 이미지 문서                     | index, name, path, original_name 모두 정확             | High     |
| TC-2.10 | 다양한 이미지 형식                    | PNG, JPEG, GIF, EMF 포함        | 모든 형식 정상 처리                                    | Medium   |
| TC-2.11 | 동일 이미지 중복 참조                 | 같은 이미지 2번 사용            | 동일 번호로 통합                                       | Low      |

---

### 3.3 표 파싱 테스트

**목적**: 표를 마크다운 형식으로 변환하는 기능 검증

| ID     | 테스트 케이스 | 입력              | 예상 결과                              | 우선순위 |
| ------ | ------------- | ----------------- | -------------------------------------- | -------- |
| TC-3.1 | 단순 표 (2x2) | 2행 2열 표        | 마크다운 테이블 형식 변환              | High     |
| TC-3.2 | 다중 행 표    | 10행 표           | 모든 행 포함                           | High     |
| TC-3.3 | 다중 열 표    | 5열 표            | 모든 열 포함                           | High     |
| TC-3.4 | 빈 셀 포함 표 | 일부 셀 비어있음  | 빈 문자열로 처리                       | Medium   |
| TC-3.5 | 헤더 구분선   | 일반 표           | 첫 행 아래 `\|---\|---\|` 형식         | High     |
| TC-3.6 | 불규칙 열 수  | 행마다 열 수 다름 | max_cols로 정규화, 부족한 열 빈 문자열 | Medium   |

---

### 3.4 특수문자 이스케이프 테스트

**목적**: 마크다운 표 셀 내 특수문자 이스케이프 검증

| ID     | 테스트 케이스   | 입력                    | 예상 결과                          | 우선순위 |
| ------ | --------------- | ----------------------- | ---------------------------------- | -------- |
| TC-4.1 | 파이프 문자     | 셀 내용: `a\|b`         | `a\\\|b`로 이스케이프              | High     |
| TC-4.2 | 백슬래시 문자   | 셀 내용: `a\\b`         | `a\\\\b`로 이스케이프              | High     |
| TC-4.3 | 별표 문자       | 셀 내용: `*bold*`       | `\\*bold\\*`로 이스케이프          | Medium   |
| TC-4.4 | 언더스코어 문자 | 셀 내용: `_italic_`     | `\\_italic\\_`로 이스케이프        | Medium   |
| TC-4.5 | 백틱 문자       | 셀 내용: `` `code` ``   | `` \\`code\\` ``로 이스케이프      | Medium   |
| TC-4.6 | 줄바꿈 문자     | 셀 내용: `line1\nline2` | `line1<br>line2`로 변환            | High     |
| TC-4.7 | 복합 특수문자   | 셀 내용: `a\|b*c_d`     | 모든 문자 올바른 순서로 이스케이프 | Medium   |

---

### 3.5 수직 병합 테스트

**목적**: vMerge 속성을 가진 셀의 처리 검증

| ID     | 테스트 케이스                    | 입력               | 예상 결과                       | 우선순위 |
| ------ | -------------------------------- | ------------------ | ------------------------------- | -------- |
| TC-5.1 | VerticalMergeMode.REPEAT         | 수직 병합 표       | 병합된 모든 셀에 값 반복        | High     |
| TC-5.2 | VerticalMergeMode.EMPTY          | 수직 병합 표       | 병합된 셀 비움 (빈 문자열)      | High     |
| TC-5.3 | VerticalMergeMode.FIRST_ONLY     | 수직 병합 표       | 첫 셀만 값, 나머지 비움         | High     |
| TC-5.4 | vMerge="restart" 처리            | restart 속성 포함  | 새 병합 시작점 정확히 인식      | High     |
| TC-5.5 | vMerge="continue" 처리           | continue 속성 포함 | 병합 계속 정확히 인식           | High     |
| TC-5.6 | 병합 없는 셀                     | vMerge 속성 없음   | 일반 처리, vmerge_values 초기화 | Medium   |
| TC-5.7 | vertical_merge="repeat" (문자열) | 문자열 파라미터    | VerticalMergeMode.REPEAT로 변환 | Medium   |

---

### 3.6 수평 병합 테스트

**목적**: gridSpan 속성을 가진 셀의 처리 검증

| ID     | 테스트 케이스                      | 입력            | 예상 결과                         | 우선순위 |
| ------ | ---------------------------------- | --------------- | --------------------------------- | -------- |
| TC-6.1 | HorizontalMergeMode.EXPAND         | gridSpan=3      | 원래 셀 + 빈 셀 2개 추가          | High     |
| TC-6.2 | HorizontalMergeMode.SINGLE         | gridSpan=3      | 단일 셀만 유지, span 무시         | High     |
| TC-6.3 | HorizontalMergeMode.REPEAT         | gridSpan=3      | 값을 3개 셀에 반복                | High     |
| TC-6.4 | gridSpan=2 처리                    | 2열 병합        | 모드에 따라 처리                  | High     |
| TC-6.5 | gridSpan=5 처리                    | 5열 병합        | 모드에 따라 처리                  | Medium   |
| TC-6.6 | horizontal_merge="expand" (문자열) | 문자열 파라미터 | HorizontalMergeMode.EXPAND로 변환 | Medium   |

---

### 3.7 병합 조합 테스트

**목적**: 수직/수평 병합 옵션 조합의 동작 검증

| ID     | 테스트 케이스   | Vertical   | Horizontal | 우선순위 |
| ------ | --------------- | ---------- | ---------- | -------- |
| TC-7.1 | REPEAT + EXPAND | REPEAT     | EXPAND     | High     |
| TC-7.2 | REPEAT + SINGLE | REPEAT     | SINGLE     | Medium   |
| TC-7.3 | REPEAT + REPEAT | REPEAT     | REPEAT     | Medium   |
| TC-7.4 | EMPTY + EXPAND  | EMPTY      | EXPAND     | Medium   |
| TC-7.5 | EMPTY + SINGLE  | EMPTY      | SINGLE     | Low      |
| TC-7.6 | EMPTY + REPEAT  | EMPTY      | REPEAT     | Low      |
| TC-7.7 | FIRST + EXPAND  | FIRST_ONLY | EXPAND     | Medium   |
| TC-7.8 | FIRST + SINGLE  | FIRST_ONLY | SINGLE     | Low      |
| TC-7.9 | FIRST + REPEAT  | FIRST_ONLY | REPEAT     | Low      |

---

### 3.8 Core 메타데이터 추출 테스트

**목적**: docProps/core.xml (Dublin Core) 메타데이터 추출 검증

| ID      | 테스트 케이스            | 입력                  | 예상 결과                                    | 우선순위 |
| ------- | ------------------------ | --------------------- | -------------------------------------------- | -------- |
| TC-8.1  | title 추출               | title 포함 문서       | CoreMetadata.title 정확히 추출               | High     |
| TC-8.2  | subject 추출             | subject 포함 문서     | CoreMetadata.subject 정확히 추출             | Medium   |
| TC-8.3  | creator 추출             | creator 포함 문서     | CoreMetadata.creator (author) 정확히 추출    | High     |
| TC-8.4  | keywords 추출            | keywords 포함 문서    | CoreMetadata.keywords 정확히 추출            | Medium   |
| TC-8.5  | description 추출         | description 포함 문서 | CoreMetadata.description 정확히 추출         | Low      |
| TC-8.6  | last_modified_by 추출    | 수정자 정보 포함      | CoreMetadata.last_modified_by 정확히 추출    | Medium   |
| TC-8.7  | revision 추출            | revision 포함 문서    | CoreMetadata.revision (int 타입) 정확히 추출 | Low      |
| TC-8.8  | created 추출             | 생성일 포함 문서      | ISO 8601 datetime 문자열                     | High     |
| TC-8.9  | modified 추출            | 수정일 포함 문서      | ISO 8601 datetime 문자열                     | High     |
| TC-8.10 | core.xml 없는 경우       | core.xml 미포함 DOCX  | 빈 CoreMetadata 반환 (에러 없음)             | High     |
| TC-8.11 | 특수문자 포함 메타데이터 | 한글, 특수문자 포함   | 정상 파싱                                    | Medium   |

---

### 3.9 App 메타데이터 추출 테스트

**목적**: docProps/app.xml (Application Properties) 메타데이터 추출 검증

| ID      | 테스트 케이스             | 입력                | 예상 결과                                             | 우선순위 |
| ------- | ------------------------- | ------------------- | ----------------------------------------------------- | -------- |
| TC-9.1  | Template 추출             | template 포함 문서  | AppMetadata.template 정확히 추출                      | Low      |
| TC-9.2  | TotalTime 추출            | 편집 시간 포함      | AppMetadata.total_time (int, 분 단위)                 | Low      |
| TC-9.3  | Pages 추출                | 페이지 수 포함      | AppMetadata.pages (int) 정확히 추출                   | High     |
| TC-9.4  | Words 추출                | 단어 수 포함        | AppMetadata.words (int) 정확히 추출                   | High     |
| TC-9.5  | Characters 추출           | 문자 수 포함        | AppMetadata.characters (int)                          | Medium   |
| TC-9.6  | CharactersWithSpaces 추출 | 공백 포함 문자 수   | AppMetadata.characters_with_spaces                    | Low      |
| TC-9.7  | Lines 추출                | 줄 수 포함          | AppMetadata.lines (int)                               | Low      |
| TC-9.8  | Paragraphs 추출           | 단락 수 포함        | AppMetadata.paragraphs (int)                          | Low      |
| TC-9.9  | Application 추출          | 애플리케이션 정보   | AppMetadata.application (예: "Microsoft Office Word") | Medium   |
| TC-9.10 | AppVersion 추출           | 버전 정보 포함      | AppMetadata.app_version                               | Low      |
| TC-9.11 | Company 추출              | 회사 정보 포함      | AppMetadata.company                                   | Low      |
| TC-9.12 | app.xml 없는 경우         | app.xml 미포함 DOCX | 빈 AppMetadata 반환 (에러 없음)                       | High     |
| TC-9.13 | 네임스페이스 있는 경우    | ep: 접두사 사용     | 정상 파싱                                             | Medium   |
| TC-9.14 | 네임스페이스 없는 경우    | 접두사 없는 태그    | 정상 파싱 (fallback)                                  | Medium   |

---

### 3.10 DocxMetadata 통합 테스트

**목적**: DocxMetadata 클래스 및 to_dict() 메서드 검증

| ID      | 테스트 케이스              | 입력                 | 예상 결과                   | 우선순위 |
| ------- | -------------------------- | -------------------- | --------------------------- | -------- |
| TC-10.1 | file_path 정확성           | 문서 파싱            | 절대 경로 저장              | High     |
| TC-10.2 | file_name 정확성           | 문서 파싱            | 파일명만 저장 (확장자 포함) | High     |
| TC-10.3 | file_size 정확성           | 문서 파싱            | 바이트 단위 정확한 크기     | Medium   |
| TC-10.4 | to_dict() 메서드           | 메타데이터 포함 문서 | flat dictionary 반환        | High     |
| TC-10.5 | to_dict() author 매핑      | creator="홍길동"     | `{"author": "홍길동"}`      | High     |
| TC-10.6 | to_dict() total_pages 매핑 | pages=100            | `{"total_pages": 100}`      | High     |
| TC-10.7 | to_dict() None 필드 제외   | 일부 필드 None       | None 값 dictionary에 미포함 | High     |
| TC-10.8 | extract_metadata=False     | 옵션 비활성화        | ParseResult.metadata=None   | Medium   |

---

### 3.11 출력 형식 테스트

**목적**: OutputFormat 옵션에 따른 출력 형식 검증

| ID      | 테스트 케이스                     | 입력                   | 예상 결과                                   | 우선순위 |
| ------- | --------------------------------- | ---------------------- | ------------------------------------------- | -------- |
| TC-11.1 | OutputFormat.MARKDOWN             | output_format=MARKDOWN | 마크다운 형식 content (표, 이스케이프 포함) | High     |
| TC-11.2 | OutputFormat.TEXT                 | output_format=TEXT     | 순수 텍스트 content (마크다운 제거)         | High     |
| TC-11.3 | OutputFormat.JSON                 | output_format=JSON     | JSON 직렬화 가능 content                    | High     |
| TC-11.4 | output_format="markdown" (문자열) | 문자열 파라미터        | OutputFormat.MARKDOWN으로 변환              | Medium   |
| TC-11.5 | output_format="text" (문자열)     | 문자열 파라미터        | OutputFormat.TEXT로 변환                    | Medium   |
| TC-11.6 | output_format="json" (문자열)     | 문자열 파라미터        | OutputFormat.JSON으로 변환                  | Medium   |
| TC-11.7 | text_content 항상 생성            | 모든 output_format     | ParseResult.text_content 항상 채워짐        | High     |

---

### 3.12 텍스트 변환 테스트

**목적**: \_to_text() 메서드의 마크다운→텍스트 변환 검증

| ID      | 테스트 케이스   | 입력             | 예상 결과      | 우선순위 |
| ------- | --------------- | ---------------- | -------------- | -------- |
| TC-12.1 | 파이프 제거     | `\| a \| b \|`   | `a  b`         | High     |
| TC-12.2 | 구분선 제거     | `\|---\|---\|`   | 빈 문자열      | High     |
| TC-12.3 | 이스케이프 복원 | `\\\|`           | `\|`           | High     |
| TC-12.4 | `<br>` 변환     | `line1<br>line2` | `line1\nline2` | High     |
| TC-12.5 | 공백 정규화     | `a    b`         | `a b`          | Medium   |
| TC-12.6 | 줄바꿈 정규화   | `a\n\n\n\nb`     | `a\n\nb`       | Medium   |

---

### 3.13 ParseResult 저장 메서드 테스트

**목적**: ParseResult의 파일 저장 기능 검증

| ID      | 테스트 케이스                 | 입력                   | 예상 결과                       | 우선순위 |
| ------- | ----------------------------- | ---------------------- | ------------------------------- | -------- |
| TC-13.1 | save_markdown()               | 출력 경로              | .md 파일 생성, 내용 정확        | High     |
| TC-13.2 | save_markdown() 경로 없음     | 존재하지 않는 디렉토리 | 디렉토리 자동 생성              | Medium   |
| TC-13.3 | save_text()                   | 출력 경로              | 텍스트 파일 생성                | High     |
| TC-13.4 | save_text() text_content 우선 | text_content 존재      | text_content 내용 저장          | High     |
| TC-13.5 | save_json()                   | 출력 경로              | JSON 파일 생성, 유효한 JSON     | High     |
| TC-13.6 | save_mapping()                | 출력 경로              | 매핑 파일 생성                  | Medium   |
| TC-13.7 | save_mapping() 형식           | 이미지 3개             | `[IMAGE_1] -> 001_img.png` 형식 | Medium   |

---

### 3.14 ParseResult 유틸리티 메서드 테스트

**목적**: ParseResult의 유틸리티 메서드 검증

| ID      | 테스트 케이스                     | 입력                 | 예상 결과                                           | 우선순위 |
| ------- | --------------------------------- | -------------------- | --------------------------------------------------- | -------- |
| TC-14.1 | get_image_path(N)                 | 존재하는 이미지 번호 | 올바른 Path 객체 반환                               | High     |
| TC-14.2 | get_image_path() 없는 번호        | 존재하지 않는 번호   | None 반환                                           | Medium   |
| TC-14.3 | replace_placeholders()            | {1: "로고 이미지"}   | `[IMAGE_1]` → `[Image: 로고 이미지]`                | High     |
| TC-14.4 | replace_placeholders() 형식       | 치환 실행            | `\n\n[Image: desc]\n\n` 형식                        | Medium   |
| TC-14.5 | to_json()                         | 파싱 결과            | 유효한 JSON 문자열 반환                             | High     |
| TC-14.6 | to_json() 필드                    | 파싱 결과            | content, image_count, images, source, metadata 포함 | High     |
| TC-14.7 | to_langchain_metadata()           | 파싱 결과            | LangChain 호환 dict 반환                            | High     |
| TC-14.8 | to_langchain_metadata() 필수 필드 | 파싱 결과            | source, page, file_type, image_count 포함           | High     |

---

### 3.15 LangChain DocxDirectLoader 테스트

**목적**: DocxDirectLoader 클래스 검증

| ID       | 테스트 케이스           | 입력               | 예상 결과                  | 우선순위 |
| -------- | ----------------------- | ------------------ | -------------------------- | -------- |
| TC-15.1  | 기본 load()             | 유효한 DOCX        | List[Document] 반환        | High     |
| TC-15.2  | Document 1개 반환       | 단일 문서          | len(docs) == 1             | High     |
| TC-15.3  | page_content 정확성     | 문서 로드          | ParseResult.content와 동일 | High     |
| TC-15.4  | metadata 포함           | 문서 로드          | 모든 메타데이터 포함       | High     |
| TC-15.5  | lazy_load()             | 유효한 DOCX        | Iterator[Document] 반환    | Medium   |
| TC-15.6  | output_dir 지정         | output_dir="./out" | metadata["image_dir"] 포함 | Medium   |
| TC-15.7  | 모든 생성자 옵션        | 각종 옵션          | 내부 파서에 정확히 전달    | High     |
| TC-15.8  | output_format="text"    | 텍스트 형식        | 텍스트 page_content        | Medium   |
| TC-15.9  | metadata["author"]      | creator 포함 문서  | author 키로 매핑           | High     |
| TC-15.10 | metadata["total_pages"] | pages 포함 문서    | total_pages 키로 매핑      | High     |
| TC-15.11 | metadata["images"]      | 이미지 포함 문서   | 이미지 목록 배열           | Medium   |

---

### 3.16 LangChain DocxDirectoryLoader 테스트

**목적**: DocxDirectoryLoader 클래스 검증

| ID      | 테스트 케이스       | 입력                   | 예상 결과                  | 우선순위 |
| ------- | ------------------- | ---------------------- | -------------------------- | -------- |
| TC-16.1 | 디렉토리 로드       | DOCX 3개 포함 디렉토리 | 3개 Document 반환          | High     |
| TC-16.2 | 기본 glob_pattern   | 기본값 사용            | `**/*.docx` 적용 (재귀)    | High     |
| TC-16.3 | 커스텀 glob_pattern | glob_pattern="\*.docx" | 현재 디렉토리만 (비재귀)   | Medium   |
| TC-16.4 | lazy_load()         | DOCX 디렉토리          | Iterator[Document] 반환    | Medium   |
| TC-16.5 | 빈 디렉토리         | DOCX 없는 디렉토리     | 빈 리스트 반환             | Medium   |
| TC-16.6 | 중첩 디렉토리       | 하위 폴더에 DOCX       | 재귀적으로 탐색            | Medium   |
| TC-16.7 | 모든 생성자 옵션    | 각종 옵션              | 각 DocxDirectLoader에 전달 | Medium   |

---

### 3.17 LangChain Import 테스트

**목적**: LangChain 의존성 처리 검증

| ID      | 테스트 케이스             | 입력                  | 예상 결과                                         | 우선순위 |
| ------- | ------------------------- | --------------------- | ------------------------------------------------- | -------- |
| TC-17.1 | langchain_core 설치됨     | langchain_core 패키지 | 정상 import (langchain_core.document_loaders)     | High     |
| TC-17.2 | langchain (legacy) 설치됨 | langchain 패키지만    | fallback import (langchain.document_loaders.base) | Medium   |
| TC-17.3 | 둘 다 없음                | LangChain 미설치      | ImportError with 설치 안내 메시지                 | High     |
| TC-17.4 | **all** 포함              | 패키지 import         | DocxDirectLoader, DocxDirectoryLoader 포함        | Medium   |

---

### 3.18 에러 처리 테스트

**목적**: 예외 상황 처리 검증

| ID      | 테스트 케이스          | 입력                    | 예상 결과                             | 우선순위 |
| ------- | ---------------------- | ----------------------- | ------------------------------------- | -------- |
| TC-18.1 | 존재하지 않는 파일     | 없는 경로               | FileNotFoundError 발생                | High     |
| TC-18.2 | 유효하지 않은 ZIP      | .txt 파일을 .docx로     | zipfile.BadZipFile 발생               | High     |
| TC-18.3 | word/document.xml 없음 | 불완전한 DOCX           | KeyError 발생                         | High     |
| TC-18.4 | 잘못된 XML 형식        | 손상된 document.xml     | xml.etree.ElementTree.ParseError 발생 | High     |
| TC-18.5 | 권한 없는 파일         | 읽기 권한 없음          | PermissionError 발생                  | Medium   |
| TC-18.6 | 잘못된 Enum 값         | output_format="invalid" | ValueError 발생                       | Medium   |
| TC-18.7 | 빈 DOCX 파일           | 콘텐츠 없는 DOCX        | 빈 content 반환 또는 적절한 에러      | Medium   |

---

### 3.19 엣지 케이스 테스트

**목적**: 경계 조건 및 특수 상황 처리 검증

| ID       | 테스트 케이스          | 입력                   | 예상 결과                              | 우선순위 |
| -------- | ---------------------- | ---------------------- | -------------------------------------- | -------- |
| TC-19.1  | 텍스트만 있는 문서     | 이미지/표 없음         | 정상 파싱, image_count=0               | High     |
| TC-19.2  | 이미지만 있는 문서     | 텍스트 없음            | placeholder만 포함                     | Medium   |
| TC-19.3  | 표만 있는 문서         | 텍스트/이미지 없음     | 마크다운 표만 포함                     | Medium   |
| TC-19.4  | 빈 표                  | 셀 없는 표             | 빈 문자열 또는 무시                    | Low      |
| TC-19.5  | 중첩 표                | 표 안의 표             | 내부 표도 처리 (또는 무시)             | Low      |
| TC-19.6  | 매우 긴 텍스트         | 100만 글자             | 메모리 정상, 정상 처리                 | Medium   |
| TC-19.7  | 특수 유니코드          | 한글, 이모지, 특수문자 | UTF-8 정상 처리                        | High     |
| TC-19.8  | 멀티 바이트 문자       | 중국어, 일본어         | UTF-8 인코딩 정상                      | Medium   |
| TC-19.9  | document.xml.rels 없음 | rels 파일 미포함       | 빈 rid_to_file, 이미지 없음 처리       | Medium   |
| TC-19.10 | 참조된 이미지 없음     | rId 있지만 파일 없음   | KeyError 무시 (pass), 해당 이미지 스킵 | Medium   |

---

### 3.20 옵션 조합 테스트

**목적**: 다양한 옵션 조합의 동작 검증

| ID      | 테스트 케이스            | extract_images | output_format          | 우선순위 |
| ------- | ------------------------ | -------------- | ---------------------- | -------- |
| TC-20.1 | 이미지 추출 + 마크다운   | True           | markdown               | High     |
| TC-20.2 | 이미지 추출 + 텍스트     | True           | text                   | Medium   |
| TC-20.3 | 이미지 추출 + JSON       | True           | json                   | Medium   |
| TC-20.4 | 이미지 미추출 + 마크다운 | False          | markdown               | Medium   |
| TC-20.5 | 이미지 미추출 + 텍스트   | False          | text                   | Low      |
| TC-20.6 | 이미지 미추출 + JSON     | False          | json                   | Low      |
| TC-20.7 | 메타데이터 추출 활성화   | -              | extract_metadata=True  | High     |
| TC-20.8 | 메타데이터 추출 비활성화 | -              | extract_metadata=False | Medium   |

---

### 3.21 성능 테스트

**목적**: 대용량 파일 및 리소스 사용량 검증

| ID      | 테스트 케이스        | 입력              | 예상 결과                   | 우선순위 |
| ------- | -------------------- | ----------------- | --------------------------- | -------- |
| TC-21.1 | 대용량 파일 (100MB+) | 100MB DOCX        | 정상 처리, 타임아웃 없음    | High     |
| TC-21.2 | 많은 이미지 (500+)   | 이미지 500개 문서 | 모든 이미지 처리, 번호 정확 | High     |
| TC-21.3 | 많은 표 (100+)       | 표 100개 문서     | 모든 표 마크다운 변환       | Medium   |
| TC-21.4 | 매우 큰 표 (1000행)  | 1000행 표         | 정상 처리, 메모리 정상      | Medium   |
| TC-21.5 | 메모리 사용량        | 대용량 파일       | 합리적 범위 내 메모리 사용  | Low      |

---

### 3.22 호환성 테스트

**목적**: 다양한 DOCX 생성 도구 호환성 검증

| ID      | 테스트 케이스           | 입력                 | 예상 결과 | 우선순위 |
| ------- | ----------------------- | -------------------- | --------- | -------- |
| TC-22.1 | MS Word 2007 DOCX       | Word 2007 생성 파일  | 정상 파싱 | Medium   |
| TC-22.2 | MS Word 2016 DOCX       | Word 2016 생성 파일  | 정상 파싱 | High     |
| TC-22.3 | MS Word 365 DOCX        | Word 365 생성 파일   | 정상 파싱 | High     |
| TC-22.4 | LibreOffice Writer DOCX | LibreOffice 내보내기 | 정상 파싱 | Medium   |
| TC-22.5 | Google Docs DOCX        | Google Docs 다운로드 | 정상 파싱 | Medium   |
| TC-22.6 | macOS Pages DOCX        | Pages 내보내기       | 정상 파싱 | Low      |

---

### 3.23 계층 구조 (Heading) 테스트

**목적**: HierarchyMode 옵션에 따른 마크다운 heading 생성 검증

| ID       | 테스트 케이스                             | 입력                       | 예상 결과                            | 우선순위 |
| -------- | ----------------------------------------- | -------------------------- | ------------------------------------ | -------- |
| TC-23.1  | HierarchyMode.NONE (기본값)               | hierarchy_mode="none"      | heading markup 없음, 기존 동작 유지  | High     |
| TC-23.2  | HierarchyMode.FONT_SIZE                   | hierarchy_mode="font_size" | font size 기반 `#`, `##`, `###` 생성 | High     |
| TC-23.3  | HierarchyMode.STYLE                       | hierarchy_mode="style"     | styles.xml outlineLevel 기반 heading | High     |
| TC-23.4  | HierarchyMode.AUTO                        | hierarchy_mode="auto"      | style 우선, font_size 폴백           | High     |
| TC-23.5  | hierarchy_mode="font_size" (문자열)       | 문자열 파라미터            | HierarchyMode.FONT_SIZE로 변환       | Medium   |
| TC-23.6  | max_heading_level=3                       | max_heading_level=3        | H1, H2, H3까지만 생성                | High     |
| TC-23.7  | max_heading_level=1                       | max_heading_level=1        | H1만 생성                            | Medium   |
| TC-23.8  | max_heading_level=6 (기본값)              | 기본값 사용                | H1~H6까지 생성 가능                  | High     |
| TC-23.9  | max_heading_level 범위 검증               | max_heading_level=10       | 6으로 클램프 (max 6)                 | Medium   |
| TC-23.10 | max_heading_level 범위 검증               | max_heading_level=0        | 1로 클램프 (min 1)                   | Medium   |
| TC-23.11 | 빈 paragraph에 heading 미적용             | 빈 텍스트 paragraph        | heading markup 없음                  | Medium   |
| TC-23.12 | LangChain loader에 hierarchy_mode 전달    | DocxDirectLoader 사용      | 내부 파서에 정확히 전달              | High     |
| TC-23.13 | LangChain loader에 max_heading_level 전달 | DocxDirectLoader 사용      | 내부 파서에 정확히 전달              | Medium   |

---

### 3.24 Font Size 분석 테스트

**목적**: font size 기반 heading 계층 결정 알고리즘 검증

| ID       | 테스트 케이스                     | 입력                          | 예상 결과                        | 우선순위 |
| -------- | --------------------------------- | ----------------------------- | -------------------------------- | -------- |
| TC-24.1  | 본문 크기 자동 감지               | 다양한 font size 문서         | 가장 빈번한 크기를 본문으로 인식 | High     |
| TC-24.2  | 본문보다 큰 크기만 heading        | 본문 9pt, 제목 14pt           | 14pt만 heading, 9pt는 본문       | High     |
| TC-24.3  | 본문보다 작은 크기는 heading 아님 | 본문 9pt, 캡션 7pt            | 7pt는 heading 아님               | High     |
| TC-24.4  | 여러 heading level 매핑           | 48pt, 36pt, 28pt, 24pt (본문) | 48pt→H1, 36pt→H2, 28pt→H3        | High     |
| TC-24.5  | font size 수집 정확성             | 복잡한 문서                   | 모든 paragraph의 font size 수집  | Medium   |
| TC-24.6  | run-level font size 우선          | run에 font size 지정          | paragraph/style보다 run 우선     | Medium   |
| TC-24.7  | paragraph-level font size         | pPr에 font size 지정          | style보다 paragraph 우선         | Medium   |
| TC-24.8  | style default font size           | style에만 font size           | style의 font size 사용           | Medium   |
| TC-24.9  | font size 없는 경우               | font size 정보 없음           | heading 아님으로 처리            | Medium   |
| TC-24.10 | half-points 단위 처리             | sz=48 (24pt)                  | 올바른 포인트 변환               | Low      |

---

### 3.25 Style 기반 Heading 테스트

**목적**: styles.xml의 outlineLevel을 활용한 heading 감지 검증

| ID       | 테스트 케이스                    | 입력                        | 예상 결과                       | 우선순위 |
| -------- | -------------------------------- | --------------------------- | ------------------------------- | -------- |
| TC-25.1  | outlineLevel=0 → H1              | Heading 1 스타일 적용       | `# ` prefix 생성                | High     |
| TC-25.2  | outlineLevel=1 → H2              | Heading 2 스타일 적용       | `## ` prefix 생성               | High     |
| TC-25.3  | outlineLevel=5 → H6              | Heading 6 스타일 적용       | `###### ` prefix 생성           | Medium   |
| TC-25.4  | styles.xml 로드                  | 유효한 DOCX                 | StyleInfo dict 정확히 생성      | High     |
| TC-25.5  | styles.xml 없는 경우             | styles.xml 미포함 DOCX      | 빈 styles dict, 에러 없음       | High     |
| TC-25.6  | custom style (outlineLevel 없음) | 일반 스타일                 | heading 아님으로 처리           | Medium   |
| TC-25.7  | AUTO 모드: style 우선            | style heading + font_size   | style의 heading level 사용      | High     |
| TC-25.8  | AUTO 모드: font_size 폴백        | custom style (heading 아님) | font_size 기반으로 폴백         | High     |
| TC-25.9  | StyleInfo.name 추출              | 스타일 이름 포함 문서       | StyleInfo.name 정확히 추출      | Low      |
| TC-25.10 | StyleInfo.font_size 추출         | 스타일에 font size 포함     | StyleInfo.font_size 정확히 추출 | Low      |

---

### 3.26 Vision 모듈 기본 테스트

**목적**: Vision 모듈의 기본 구조 및 팩토리 패턴 검증

| ID      | 테스트 케이스                          | 입력                               | 예상 결과                                   | 우선순위 |
| ------- | -------------------------------------- | ---------------------------------- | ------------------------------------------- | -------- |
| TC-26.1 | vision 모듈 import                     | `from docx_parser.vision import *` | VisionProvider, create_vision_provider 접근 | High     |
| TC-26.2 | VisionProvider 추상 클래스             | VisionProvider 직접 인스턴스화     | TypeError (추상 클래스)                     | High     |
| TC-26.3 | create_vision_provider("transformers") | transformers 타입 지정             | TransformersProvider 인스턴스 반환          | High     |
| TC-26.4 | create_vision_provider() 잘못된 타입   | provider_type="invalid"            | ValueError 발생                             | High     |
| TC-26.5 | VisionError 예외 클래스                | `from docx_parser.vision import *` | VisionError 접근 가능                       | Medium   |
| TC-26.6 | ProviderNotAvailableError              | 미설치 provider 사용 시도          | ProviderNotAvailableError 발생              | High     |
| TC-26.7 | ImageProcessingError                   | 잘못된 이미지 처리 시도            | ImageProcessingError 발생                   | Medium   |
| TC-26.8 | **all** export 확인                    | vision 모듈                        | 필수 클래스/함수 export 확인                | Medium   |

---

### 3.27 Transformers Provider 테스트

**목적**: HuggingFace Transformers 기반 VisionProvider 검증

| ID       | 테스트 케이스                  | 입력                                       | 예상 결과                                | 우선순위 |
| -------- | ------------------------------ | ------------------------------------------ | ---------------------------------------- | -------- |
| TC-27.1  | TransformersProvider 기본 생성 | 파라미터 없이 생성                         | 기본 모델로 인스턴스 생성                | High     |
| TC-27.2  | 커스텀 모델 지정               | model="llava-hf/llava-v1.6-mistral-7b-hf"  | 지정 모델로 초기화                       | High     |
| TC-27.3  | load_in_4bit=True              | 4bit 양자화 옵션                           | BitsAndBytes 4bit 로드                   | High     |
| TC-27.4  | load_in_8bit=True              | 8bit 양자화 옵션                           | BitsAndBytes 8bit 로드                   | Medium   |
| TC-27.5  | device_map="auto"              | 자동 디바이스 매핑                         | GPU 있으면 GPU, 없으면 CPU               | High     |
| TC-27.6  | device_map="cpu"               | CPU 강제                                   | CPU에서 실행                             | Medium   |
| TC-27.7  | torch_dtype 지정               | torch_dtype="float16"                      | 지정 dtype으로 로드                      | Medium   |
| TC-27.8  | describe() 메서드 - PIL Image  | PIL.Image 객체                             | 이미지 설명 문자열 반환                  | High     |
| TC-27.9  | describe() 메서드 - 파일 경로  | Path("/path/to/image.png")                 | 이미지 설명 문자열 반환                  | High     |
| TC-27.10 | describe() 메서드 - bytes      | 이미지 바이트 데이터                       | 이미지 설명 문자열 반환                  | Medium   |
| TC-27.11 | describe() 커스텀 prompt       | prompt="이 이미지를 한국어로 설명해주세요" | 커스텀 prompt 적용된 응답                | Medium   |
| TC-27.12 | describe() max_tokens          | max_tokens=100                             | 토큰 수 제한된 응답                      | Low      |
| TC-27.13 | describe() 빈 이미지           | 빈/손상된 이미지                           | ImageProcessingError 발생                | High     |
| TC-27.14 | transformers 미설치 시         | transformers 패키지 없음                   | ProviderNotAvailableError with 설치 안내 | High     |
| TC-27.15 | torch 미설치 시                | torch 패키지 없음                          | ProviderNotAvailableError with 설치 안내 | High     |
| TC-27.16 | batch_size 파라미터            | batch_size=8                               | self.batch_size=8 저장                   | High     |
| TC-27.17 | batch_size 기본값              | 파라미터 없이 생성                         | batch_size=4 (기본값)                    | High     |
| TC-27.18 | describe_images() 배치 처리    | 이미지 10개, batch_size=4                  | 3번의 배치 (4+4+2)로 처리                | High     |
| TC-27.19 | describe_images() 단일 이미지  | 이미지 1개                                 | 배치 아닌 단일 처리 (describe_image)     | Medium   |
| TC-27.20 | describe_images() 빈 리스트    | 이미지 0개                                 | 빈 딕셔너리 반환                         | Medium   |
| TC-27.21 | \_process_batch() 동작         | PIL Image 4개 + prompt                     | 4개 설명 리스트 반환                     | High     |
| TC-27.22 | 배치 처리 실패 시 폴백         | 배치 처리 중 에러 발생                     | 개별 처리로 자동 폴백                    | High     |
| TC-27.23 | 배치 이미지 로드 실패          | 일부 이미지 손상                           | 해당 이미지만 에러 메시지, 나머지 정상   | Medium   |
| TC-27.24 | batch_size=1 (배치 비활성화)   | batch_size=1                               | 실질적 단일 처리와 동일                  | Low      |
| TC-27.25 | 대량 이미지 배치 처리          | 이미지 50개, batch_size=8                  | 메모리 효율적 처리, 7번 배치             | Medium   |
| TC-27.26 | create_vision_provider + batch | batch_size=8 전달                          | TransformersProvider(batch_size=8) 생성  | High     |
| TC-27.27 | 배치 패딩 처리                 | 이미지 크기 다양                           | 패딩 적용, 모든 이미지 정상 처리         | Medium   |

---

### 3.28 Vision 통합 테스트

**목적**: parse_docx, ParseResult, LangChain과 Vision 통합 검증

| ID       | 테스트 케이스                             | 입력                                            | 예상 결과                           | 우선순위 |
| -------- | ----------------------------------------- | ----------------------------------------------- | ----------------------------------- | -------- |
| TC-28.1  | parse_docx() + vision_provider            | vision_provider=TransformersProvider()          | 이미지 설명 자동 생성               | High     |
| TC-28.2  | parse_docx() + auto_describe_images=True  | auto_describe_images=True                       | 모든 이미지에 대해 describe() 호출  | High     |
| TC-28.3  | parse_docx() + auto_describe_images=False | auto_describe_images=False                      | describe() 호출 안 함               | High     |
| TC-28.4  | ParseResult.image_descriptions 필드       | vision 파싱 결과                                | {1: "설명1", 2: "설명2"} 형태       | High     |
| TC-28.5  | ParseResult.describe_images() 수동 호출   | result.describe_images(provider)                | 이미지 설명 추가                    | High     |
| TC-28.6  | ParseResult.describe_images() 부분 호출   | result.describe_images(provider, indices=[1,3]) | 지정 이미지만 설명                  | Medium   |
| TC-28.7  | replace_placeholders() + vision           | descriptions={1: "로고"}                        | `[IMAGE_1]` → `[Image: 로고]` 치환  | High     |
| TC-28.8  | to_json() + image_descriptions            | vision 파싱 결과                                | JSON에 image_descriptions 포함      | Medium   |
| TC-28.9  | DocxDirectLoader + vision_provider        | DocxDirectLoader(vision_provider=provider)      | metadata["image_descriptions"] 포함 | High     |
| TC-28.10 | DocxDirectLoader + auto_describe_images   | auto_describe_images=True                       | 자동 설명 생성                      | High     |
| TC-28.11 | vision_provider 없이 auto_describe=True   | vision_provider=None, auto_describe_images=True | 에러 없이 무시 (설명 없음)          | Medium   |
| TC-28.12 | 이미지 없는 문서 + vision                 | 텍스트만 있는 문서                              | image_descriptions 빈 dict          | Medium   |
| TC-28.13 | output_dir 없이 Vision 동작               | output_dir=None + vision_provider               | ImageInfo.data로 설명 생성          | High     |
| TC-28.14 | bytes 기반 이미지 설명                    | ImageInfo.data에 bytes 저장된 상태              | describe_image(bytes) 정상 동작     | High     |
| TC-28.15 | path와 data 모두 있을 때                  | ImageInfo(path=..., data=...)                   | path 우선 사용                      | Medium   |
| TC-28.16 | Vision utils bytes 처리                   | encode_image_base64(bytes)                      | Base64 정상 인코딩                  | High     |
| TC-28.17 | Vision utils MIME 타입 추정               | get_image_mime_type(png_bytes)                  | "image/png" 반환 (magic number)     | High     |

---

### 3.29 표 형식 (TableFormat) 테스트

**목적**: TableFormat 옵션에 따른 표 출력 형식 검증

| ID       | 테스트 케이스                        | 입력                      | 예상 결과                                        | 우선순위 |
| -------- | ------------------------------------ | ------------------------- | ------------------------------------------------ | -------- |
| TC-29.1  | TableFormat.MARKDOWN (기본값)        | table_format="markdown"   | `\| col \| col \|` 마크다운 표 형식              | High     |
| TC-29.2  | TableFormat.JSON                     | table_format="json"       | `{"type": "table", "rows": [...]}` JSON 형식     | High     |
| TC-29.3  | TableFormat.HTML                     | table_format="html"       | `<table><tr><td>...</td></tr></table>` HTML 형식 | High     |
| TC-29.4  | TableFormat.TEXT                     | table_format="text"       | 탭 구분 텍스트 형식                              | High     |
| TC-29.5  | table_format="json" (문자열)         | 문자열 파라미터           | TableFormat.JSON으로 변환                        | Medium   |
| TC-29.6  | table_format="html" (문자열)         | 문자열 파라미터           | TableFormat.HTML로 변환                          | Medium   |
| TC-29.7  | JSON 형식 병합 정보 보존             | colspan=2, rowspan=3 포함 | JSON에 colspan, rowspan 정확히 포함              | High     |
| TC-29.8  | HTML 형식 colspan 속성               | colspan=2 포함 표         | `<td colspan="2">` 속성 생성                     | High     |
| TC-29.9  | HTML 형식 rowspan 속성               | rowspan=3 포함 표         | `<td rowspan="3">` 속성 생성                     | High     |
| TC-29.10 | HTML 형식 th 태그                    | 헤더 행 포함 표           | 첫 행 `<th>` 태그 사용                           | Medium   |
| TC-29.11 | TEXT 형식 탭 구분                    | 2열 표                    | 열 사이 탭(\t) 구분                              | High     |
| TC-29.12 | TEXT 형식 줄바꿈                     | 3행 표                    | 행 사이 줄바꿈(\n) 구분                          | High     |
| TC-29.13 | MARKDOWN + vertical_merge 조합       | table_format=md, v=repeat | 병합 모드와 함께 동작                            | High     |
| TC-29.14 | MARKDOWN + horizontal_merge 조합     | table_format=md, h=expand | 병합 모드와 함께 동작                            | High     |
| TC-29.15 | JSON 형식에서 병합 모드 무시         | table_format=json         | 원본 병합 정보 그대로 보존 (모드 무시)           | High     |
| TC-29.16 | HTML rowspan 스킵 처리               | rowspan=2 포함 표         | 다음 행에서 해당 셀 위치 스킵                    | High     |
| TC-29.17 | DocxParser.**init** table_format     | 생성자 파라미터           | self.table_format 정확히 설정                    | High     |
| TC-29.18 | parse_docx() table_format 전달       | 편의 함수 파라미터        | DocxParser에 정확히 전달                         | High     |
| TC-29.19 | LangChain loader에 table_format 전달 | DocxDirectLoader 사용     | 내부 파서에 정확히 전달                          | Medium   |
| TC-29.20 | 잘못된 table_format 값               | table_format="invalid"    | ValueError 발생                                  | Medium   |

---

### 3.30 TableCell/TableData 클래스 테스트

**목적**: TableCell, TableData 데이터클래스 검증

| ID       | 테스트 케이스                         | 입력                            | 예상 결과                             | 우선순위 |
| -------- | ------------------------------------- | ------------------------------- | ------------------------------------- | -------- |
| TC-30.1  | TableCell 기본 생성                   | TableCell(text="내용")          | colspan=1, rowspan=1, is_header=False | High     |
| TC-30.2  | TableCell colspan 설정                | TableCell(text="", colspan=3)   | colspan=3 저장                        | High     |
| TC-30.3  | TableCell rowspan 설정                | TableCell(text="", rowspan=2)   | rowspan=2 저장                        | High     |
| TC-30.4  | TableCell is_header 설정              | TableCell(text="", is_header=T) | is_header=True 저장                   | Medium   |
| TC-30.5  | TableCell is_merged_continuation      | is_merged_continuation=True     | 병합 연속 셀 표시                     | Medium   |
| TC-30.6  | TableCell.to_dict()                   | 셀 객체                         | {"text": "", "colspan": 2} 형식       | High     |
| TC-30.7  | TableCell.to_dict() colspan=1 제외    | colspan=1 (기본값)              | colspan 키 미포함 (1이면 생략)        | Medium   |
| TC-30.8  | TableCell.to_dict() rowspan=1 제외    | rowspan=1 (기본값)              | rowspan 키 미포함 (1이면 생략)        | Medium   |
| TC-30.9  | TableData 기본 생성                   | TableData(rows=[...])           | row_count, col_count 자동 계산        | High     |
| TC-30.10 | TableData.to_dict()                   | 표 데이터 객체                  | {"type": "table", "rows": [...]} 형식 | High     |
| TC-30.11 | TableData.to_dict() col_count         | 3열 표                          | col_count=3 포함                      | High     |
| TC-30.12 | TableData.to_dict() row_count         | 5행 표                          | row_count=5 포함                      | High     |
| TC-30.13 | \_parse_table_data() 정확성           | 복잡한 표                       | TableData 정확히 생성                 | High     |
| TC-30.14 | \_parse_table_data() 병합 추적        | vMerge restart/continue         | rowspan 정확히 계산                   | High     |
| TC-30.15 | \_parse_table_data() colspan 추적     | gridSpan 포함 표                | colspan 정확히 계산                   | High     |
| TC-30.16 | 빈 표 처리                            | 셀 없는 표                      | 빈 TableData 반환                     | Medium   |
| TC-30.17 | 다중 paragraph 셀                     | 셀 내 여러 paragraph            | 줄바꿈(\n)으로 연결                   | Medium   |
| TC-30.18 | ImageInfo.data 필드                   | 이미지 추출                     | bytes 데이터 저장                     | High     |
| TC-30.19 | ImageInfo.data + output_dir 없음      | output_dir=None                 | data 필드에 bytes 저장 (파일 없이)    | High     |
| TC-30.20 | ImageInfo.data + extract_images=False | extract_images=False            | data=None                             | Medium   |

---

## 4. 테스트 요약

| 카테고리                   | 테스트 케이스 수 | 우선순위 (High) |
| -------------------------- | ---------------- | --------------- |
| 3.1 기본 파싱              | 5                | 4               |
| 3.2 이미지 처리            | 11               | 6               |
| 3.3 표 파싱                | 6                | 4               |
| 3.4 특수문자 이스케이프    | 7                | 3               |
| 3.5 수직 병합              | 7                | 5               |
| 3.6 수평 병합              | 6                | 4               |
| 3.7 병합 조합              | 9                | 1               |
| 3.8 Core 메타데이터        | 11               | 5               |
| 3.9 App 메타데이터         | 14               | 3               |
| 3.10 DocxMetadata 통합     | 8                | 6               |
| 3.11 출력 형식             | 7                | 4               |
| 3.12 텍스트 변환           | 6                | 4               |
| 3.13 ParseResult 저장      | 7                | 4               |
| 3.14 ParseResult 유틸      | 8                | 6               |
| 3.15 DocxDirectLoader      | 11               | 7               |
| 3.16 DocxDirectoryLoader   | 7                | 2               |
| 3.17 LangChain Import      | 4                | 2               |
| 3.18 에러 처리             | 7                | 4               |
| 3.19 엣지 케이스           | 10               | 2               |
| 3.20 옵션 조합             | 8                | 2               |
| 3.21 성능 테스트           | 5                | 2               |
| 3.22 호환성 테스트         | 6                | 2               |
| 3.23 계층 구조 (Heading)   | 13               | 8               |
| 3.24 Font Size 분석        | 10               | 5               |
| 3.25 Style 기반 Heading    | 10               | 6               |
| 3.26 Vision 모듈 기본      | 8                | 5               |
| 3.27 Transformers 테스트   | 27               | 17              |
| 3.28 Vision 통합           | 17               | 12              |
| 3.29 표 형식 (TableFormat) | 20               | 14              |
| 3.30 TableCell/TableData   | 20               | 12              |
| **총계**                   | **277**          | **161**         |

---

## 5. 테스트 환경

### 5.1 필수 환경

```
Python: 3.10+
OS: Linux (Ubuntu 22.04+), macOS, Windows
```

### 5.2 테스트 도구

```
pytest >= 7.0
pytest-cov >= 4.0
```

### 5.3 선택적 의존성

```
langchain-core >= 0.1.0  # LangChain 테스트용
langchain >= 0.1.0       # Legacy LangChain 테스트용

# Vision 테스트용 (Transformers)
transformers >= 4.40.0
torch >= 2.0.0
accelerate >= 0.25.0
bitsandbytes >= 0.41.0  # 양자화 테스트용
Pillow >= 9.0.0
```

### 5.4 테스트 데이터

테스트에 필요한 DOCX 샘플 파일:

| 파일명               | 설명                              |
| -------------------- | --------------------------------- |
| `simple.docx`        | 텍스트만 포함                     |
| `with_images.docx`   | 이미지 포함 (PNG, JPEG)           |
| `with_tables.docx`   | 표 포함 (일반, 병합)              |
| `complex.docx`       | 텍스트 + 이미지 + 표              |
| `large.docx`         | 대용량 (100MB+)                   |
| `metadata.docx`      | 모든 메타데이터 포함              |
| `no_metadata.docx`   | 메타데이터 없음                   |
| `merged_cells.docx`  | 수직/수평 병합 셀                 |
| `special_chars.docx` | 특수문자 포함                     |
| `unicode.docx`       | 다국어 (한글, 중국어, 일본어)     |
| `headings.docx`      | Heading 스타일 적용 (H1~H6)       |
| `varied_fonts.docx`  | 다양한 font size (48pt~9pt)       |
| `no_styles.docx`     | styles.xml 없는 DOCX              |
| `vision_test.docx`   | 이미지 포함 (Vision 테스트용)     |
| `complex_table.docx` | 복잡한 병합 셀 표 (TableFormat용) |

---

## 변경 이력

| 버전 | 날짜       | 변경 내용                                               |
| ---- | ---------- | ------------------------------------------------------- |
| 1.0  | 2026-01-25 | 최초 작성 (v0.2.0)                                      |
| 1.1  | 2026-01-25 | v0.3.0 Heading 계층 구조 테스트 케이스 추가 (TC-23~25)  |
| 1.2  | 2026-01-25 | v0.3.0 Vision 테스트 케이스 추가 (TC-26~28, 25개)       |
| 1.3  | 2026-01-25 | v0.3.1 TableFormat 테스트 케이스 추가 (TC-29~30, 40개)  |
|      |            | - TableFormat enum (markdown, json, html, text)         |
|      |            | - TableCell, TableData 클래스                           |
|      |            | - ImageInfo.data 필드 (bytes 저장)                      |
| 1.4  | 2026-01-25 | v0.3.1 Vision bytes 지원 테스트 추가 (TC-28.13~17)      |
|      |            | - output_dir 없이 Vision 동작 지원                      |
|      |            | - VisionProvider.describe_image(bytes) 지원             |
|      |            | - Vision utils bytes 처리 함수                          |
| 1.5  | 2026-01-25 | v0.3.2 Transformers 배치 처리 테스트 추가 (TC-27.16~27) |
|      |            | - batch_size 파라미터 테스트                            |
|      |            | - describe_images() 배치 처리 동작 검증                 |
|      |            | - 배치 실패 시 폴백 처리 검증                           |
|      |            | - 대량 이미지 배치 처리 성능 테스트                     |
