# 브랜드 아이덴티티 생성기 (main.py)

브랜드 브리프(업종·타겟·키워드)를 입력하면 AI가 브랜드 네이밍, 슬로건, 경쟁사 차별화 포인트,
스토리, 컬러 팔레트, 로고 시안까지 자동 생성하는 CLI 프로그램입니다.

- **최종 업데이트**: 2026-08-22

---

## 1. 팀 구성 및 역할

네 명이 기능별로 나눠 개발했고, `main.py`에 병합해 **현재는 `main.py` 단일 파일**로 전체 파이프라인이 동작합니다.

| 담당 | 원래 파일 | 주요 함수 | 상태 |
|---|---|---|---|
| 팀장 — 통합/입력 | `main.py` | `load_brief`, `save_result`, 전체 실행 흐름 | 완료 |
| 팀원1 — 네이밍·카피 | `naming.py` → 병합 | `generate_naming`, `generate_slogans` | 완료 |
| 팀원2 — 스토리·컬러 | `content.py` → 병합 | `generate_story`, `generate_color_palette` | 완료 |
| 팀원3 — 비주얼 | `visual.py` → 병합 | `save_color_palette_image`, `generate_logo` | 완료 |
| 보너스 — 차별화 분석 | `main.py`에 직접 추가 | `generate_differentiation` | 완료 |

---

## 2. 폴더 구조

```
brand-generator/
├── main.py            # 전체 파이프라인 (병합 완료)
├── brief.json
├── .env                  # OPENAI_API_KEY, (선택) IMAGE_API_KEY, IMAGE_MODEL
└── output/
    ├── color_palette.png
    ├── logo_01.png
    ├── logo_02.png
    ├── logo_03.png
    ├── logo_04.png
    ├── logo_05.png
    ├── logo_06.png
    └── brand_result.json
```

> `naming.py` / `content.py` / `visual.py`는 개별 개발·테스트용이었고, 통합 결과물은
> `main.py` 하나로 병합되어 있습니다. 별도 파일을 import하지 않으므로 파일 위치 제약은 없습니다.

---

## 3. 사용한 브랜드 브리프

```json
{
  "industry": "밀키트",
  "target": "매일 대충 때우는 식사에 지쳐서, 바쁘더라도 제대로 챙겨 먹고 싶은 직장인",
  "keywords": ["간편함", "건강", "균형영양", "신선함", "시간절약"],
  "tone": "활기차고 신뢰감 있는, 실용적이면서 세련된",
  "competitors": ["프레시지", "마이셰프", "테이스티나인"],
  "notes": "다이어트나 헬스 목적이 아니라, 바쁜 와중에도 나 자신을 제대로 챙기고 싶은 마음에 초점. 대충 배달음식으로 때우는 것과 대비되는 '스스로를 위한 한 끼'라는 느낌을 전달하고 싶음."
}
```

모든 생성 함수(`generate_naming`, `generate_slogans`, `generate_differentiation`, `generate_story`,
`generate_color_palette`, `generate_logo`)의 프롬프트가 이 브리프의
**"다이어트 아님, 스스로를 위한 한 끼"** 톤을 명시적으로 반영합니다.

---

## 4. 모듈별 상세

### 4.1 네이밍·카피 — `generate_naming`, `generate_slogans`

```python
generate_naming(brand_brief) -> naming_candidates
# [{"name_kr": "...", "name_en": "...", "name_meaning": "..."}, ...] (한글 3개 + 영문 3개 요청)

generate_slogans(brand_brief) -> slogans
# ["슬로건1", "슬로건2", "슬로건3"]
```

- 모델: `gpt-4o-mini`
- 응답 후처리: `_extract_json()`으로 모델이 코드블록(```json)이나 설명을 덧붙여도 JSON만 안전하게 추출
- 경쟁사와 겹치지 않는 이름, 브리프 톤앤매너 반영을 프롬프트에 명시
- 실패 시 빈 리스트를 반환하고 다음 단계로 진행 (에러 메시지 출력)

### 4.2 경쟁사 차별화 분석 — `generate_differentiation` (보너스)

```python
generate_differentiation(brand_brief) -> differentiation
# {
#   "competitor_analysis": [{"competitor": "...", "positioning": "..."}, ...],
#   "differentiation_points": ["...", "...", "..."]
# }
```

- 브리프의 `competitors` 목록을 기반으로 경쟁사별 예상 포지셔닝과, 이 브랜드만의 차별화 포인트 3개를 생성
- 보너스 과제 "경쟁사 분석 추가" 항목을 구현한 함수이며, `main()` 파이프라인의 3단계로 통합됨

### 4.3 스토리·컬러 — `generate_story`, `generate_color_palette`

```python
generate_story(brand_brief) -> brand_story        # str, 200~300자
generate_color_palette(brand_brief) -> color_palette  # {"main_color": "#XXXXXX", "sub_colors": [...]}
```

- 모델: `gpt-4o-mini`
- `generate_color_palette`는 `response_format={"type": "json_object"}`로 JSON 파싱 안정성 확보
- 실패 시 `generate_color_palette`는 회색 계열 기본값(`#CCCCCC` 등)으로 대체해 파이프라인이 중단되지 않도록 처리

### 4.4 비주얼 — `save_color_palette_image`, `generate_logo`

```python
save_color_palette_image(color_palette, output_dir) -> color_palette_path

generate_logo(
    brand_brief,
    color_palette,
    naming_candidates=None,
    output_dir="./output",
    logo_count=None,
) -> logo_paths
```

- `save_color_palette_image`: matplotlib으로 메인/서브 컬러 스와치를 그려 `color_palette.png`로 저장
- `generate_logo`: 이미지 생성 API(기본 `gpt-image-1`)로 로고 시안을 생성
  - `naming_candidates`를 받으면 후보 개수만큼 로고를 생성하고, 로고마다 후보 브랜드명(`name_en`)을 프롬프트에 반영해 로고에 타이포그래피로 포함시킴
  - `naming_candidates`가 없으면 기본 2장 생성 (텍스트 없는 심볼 로고)
  - `IMAGE_MODEL` 환경변수로 `dall-e-3` 등 대체 모델 즉시 전환 가능 (조직 인증 이슈 대비)
  - 로고 1장 생성 실패해도 나머지는 계속 생성 (요구사항 9: 에러 처리)

---

## 5. 전체 함수 인터페이스 요약

코드에 정의된 함수는 총 13개(공개 함수 9개 + 내부 헬퍼 함수 4개)입니다.

**공개 함수 (9개)**

| 함수명 | 입력 | 출력 |
|---|---|---|
| `load_brief(brief_path)` | 브리프 파일 경로 | `brand_brief` |
| `generate_naming(brand_brief)` | 브리프 | `naming_candidates` |
| `generate_slogans(brand_brief)` | 브리프 | `slogans` |
| `generate_differentiation(brand_brief)` | 브리프 | `differentiation` |
| `generate_story(brand_brief)` | 브리프 | `brand_story` |
| `generate_color_palette(brand_brief)` | 브리프 | `color_palette` |
| `save_color_palette_image(color_palette, output_dir)` | 컬러 팔레트, 출력 폴더 | `color_palette_path` |
| `generate_logo(brand_brief, color_palette, naming_candidates, output_dir, logo_count)` | 브리프, 컬러 팔레트, 네이밍 후보(선택), 출력 폴더, 로고 개수(선택) | `logo_paths` |
| `save_result(brand_result, output_dir)` | 통합 결과, 출력 폴더 | `result_json_path` |

**내부 헬퍼 함수 (4개)**

| 함수명 | 입력 | 출력 | 역할 |
|---|---|---|---|
| `_load_image_api_key()` | 없음 | `image_api_key` | `IMAGE_API_KEY` > `OPENAI_API_KEY` 순으로 이미지 생성용 키 조회 |
| `_extract_json(text)` | LLM 응답 텍스트 | 파싱된 JSON(dict/list) | 코드블록·설명이 섞인 응답에서 JSON만 안전하게 추출 |
| `_build_brief_context(brand_brief)` | 브리프 | 프롬프트용 텍스트(str) | `brand_brief` 딕셔너리를 프롬프트에 넣기 좋은 문자열로 정리 |
| `_build_logo_prompt(brand_brief, color_palette, brand_name)` | 브리프, 컬러 팔레트, 브랜드명(선택) | `logo_prompt` | 이미지 생성 API에 넘길 로고 프롬프트 조립 (브랜드명 유무에 따라 텍스트 포함 여부 분기) |

---

## 6. 통합하면서 정리된 사항

기존에 파일별로 달랐던 부분들을 `main.py` 병합 과정에서 아래와 같이 정리했습니다.

1. **API 키 로딩 방식 통일**
   - `main.py` 최상단에서 `load_dotenv()`로 `.env`를 로드하고, 이후 모든 함수가 `os.environ.get("OPENAI_API_KEY")`를 공유
   - 이미지 생성용 키는 `_load_image_api_key()`로 분리 관리 (`IMAGE_API_KEY` > `OPENAI_API_KEY` 순서)

2. **`brief.json` 경로 처리**
   - `load_brief(brief_path)`는 전달받은 경로를 그대로 사용. `main()`에서 사용자가 입력한 경로를 그대로 넘기므로, 실행 위치(cwd) 기준 상대경로에 주의해서 입력할 것

3. **결과 파일명 충돌 이슈 해소**
   - 개별 모듈 파일이 사라지고 `main.py` 하나로 통합되었으므로, `output/brand_result.json`은 `save_result()`가 생성하는 최종 결과 하나만 존재

4. **파일 간 의존성 제거**
   - 더 이상 `content.py`가 `visual.py`를 import하는 구조가 아니라, 한 파일 안에 모든 함수가 있어 별도 폴더 배치 제약이 없음

5. **`generate_logo()` 인자 확정**
   - 최종 시그니처: `generate_logo(brand_brief, color_palette, naming_candidates=None, output_dir="./output", logo_count=None)`
   - `naming_candidates`를 넘기면 후보 수만큼, 안 넘기면 기본 2장 생성

---

## 7. 보너스 과제 진행 상황

| 항목 | 상태 | 비고 |
|---|---|---|
| 다국어 네이밍 지원 | 완료 | `generate_naming`이 `name_kr`/`name_en`을 함께 생성 |
| 경쟁사 분석 추가 | 완료 | `generate_differentiation()`으로 구현, `main()` 3단계에 통합 |

---

## 8. 실행 방법

```bash
# 1. 필요한 패키지 설치
pip install matplotlib openai python-dotenv

# 2. API 키 설정 (.env 파일)
# .env 파일 예시
OPENAI_API_KEY=sk-...
# (선택) 이미지 생성용 키를 텍스트용과 분리하고 싶다면
IMAGE_API_KEY=sk-...
# (선택) gpt-image-1 대신 다른 이미지 모델 사용 시
IMAGE_MODEL=dall-e-3

# 3. 실행
python main.py
```

실행하면 브리프 파일 경로와 출력 폴더 경로를 입력받아, 네이밍 → 슬로건 → 경쟁사 차별화 분석 →
브랜드 스토리 → 컬러 팔레트(+ 시각화) → 로고 시안 순으로 총 6단계를 진행하고
`output/brand_result.json`에 텍스트 결과 전체를 저장합니다.
