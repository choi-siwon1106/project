### main.py

from __future__ import annotations

import os
import base64
import json
import re
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

_MODEL = "gpt-4o-mini"


def _load_image_api_key() -> str | None:
    """image_api_key를 환경변수에서 읽어온다. 우선순위: IMAGE_API_KEY > OPENAI_API_KEY"""
    return os.environ.get("IMAGE_API_KEY") or os.environ.get("OPENAI_API_KEY")


def _extract_json(text: str):
    """LLM 응답 텍스트에서 JSON 부분만 뽑아낸다.

    모델이 코드블록(```json ... ```)이나 앞뒤 설명을 붙여서 응답하는 경우를
    대비해, 텍스트 안에서 JSON으로 보이는 부분만 추출해 파싱한다.
    """
    cleaned = text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    start_candidates = [i for i in (cleaned.find("["), cleaned.find("{")) if i != -1]
    if not start_candidates:
        raise ValueError("응답에서 JSON을 찾을 수 없습니다.")
    start = min(start_candidates)

    end_candidates = [i for i in (cleaned.rfind("]"), cleaned.rfind("}")) if i != -1]
    end = max(end_candidates) + 1

    return json.loads(cleaned[start:end])


def _build_brief_context(brand_brief: dict) -> str:
    """brand_brief 딕셔너리를 프롬프트에 넣기 좋은 텍스트로 정리한다."""
    industry = brand_brief.get("industry", "")
    target = brand_brief.get("target", "")
    keywords = ", ".join(brand_brief.get("keywords", []))
    tone = brand_brief.get("tone", "")
    competitors = ", ".join(brand_brief.get("competitors", []))
    notes = brand_brief.get("notes", "")

    lines = [
        f"업종: {industry}",
        f"타겟 고객: {target}",
        f"키워드: {keywords}",
    ]
    if tone:
        lines.append(f"톤앤매너: {tone}")
    if competitors:
        lines.append(f"경쟁사: {competitors}")
    if notes:
        lines.append(f"추가 요청사항: {notes}")

    return "\n".join(lines)


def load_brief(brief_path: str) -> dict:
    with open(brief_path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_naming(brand_brief: dict) -> list[dict]:
    """브랜드 브리프를 받아 네이밍 후보 리스트(naming_candidates)를 생성한다.

    반환 형식 (실패 시 빈 리스트):
        [{"name_kr": "...", "name_en": "...", "name_meaning": "..."}, ...]
    """
    context = _build_brief_context(brand_brief)

    prompt = f"""당신은 브랜드 네이밍 전문가입니다. 아래 브랜드 브리프를 참고해서
브랜드명 후보를 한글로 3개, 영어로 3개 만들어주세요.

[브랜드 브리프]
{context}

[요청 사항]
- 경쟁사(예: {", ".join(brand_brief.get("competitors", []))})와 겹치지 않는 이름일 것
- 브리프의 톤앤매너와 키워드를 반영할 것
- 너무 흔하거나 일반적인 단어 조합은 피할 것
- 각 후보는 한글명, 영문명, 이름의 의미/유래를 함께 제시할 것

반드시 아래 JSON 형식으로만 응답하세요. 다른 설명, 인사말, 코드블록 표시는 넣지 마세요.
[
  {{"name_kr": "한글 브랜드명", "name_en": "영문 브랜드명", "name_meaning": "이름의 의미와 유래 (1~2문장)"}},
  ...
]"""

    try:
        raw_response = client.chat.completions.create(
            model=_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        ).choices[0].message.content
        naming_candidates = _extract_json(raw_response)
    except Exception as e:
        error_message = f"[generate_naming] 오류 발생: {e}"
        print(error_message)
        naming_candidates = []

    return naming_candidates


def generate_slogans(brand_brief: dict) -> list[str]:
    """브랜드 브리프를 받아 슬로건 3개(slogans)를 생성한다.

    반환 형식 (실패 시 빈 리스트):
        ["슬로건1", "슬로건2", "슬로건3"]
    """
    context = _build_brief_context(brand_brief)

    prompt = f"""당신은 카피라이터입니다. 아래 브랜드 브리프를 참고해서
슬로건을 정확히 3개 만들어주세요.

[브랜드 브리프]
{context}

[요청 사항]
- 각 슬로건은 한국어로, 15자 내외의 짧고 강렬한 문구일 것
- 브리프의 톤앤매너("{brand_brief.get("tone", "")}")를 반영할 것
- 다이어트/체중 감량 목적이 아니라 "바쁜 일상 속에서도 나를 위해 제대로 챙긴다"는
  메시지에 초점을 맞출 것 (추가 요청사항 참고)
- 직부한 표현("건강한 하루", "당신을 위한") 대신 구체적이고 입체적인 표현일 것

반드시 아래 JSON 형식으로만 응답하세요. 다른 설명, 인사말, 코드블록 표시는 넣지 마세요.
["슬로건1", "슬로건2", "슬로건3"]"""

    try:
        raw_response = client.chat.completions.create(
            model=_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        ).choices[0].message.content
        slogans = _extract_json(raw_response)
    except Exception as e:
        error_message = f"[generate_slogans] 오류 발생: {e}"
        print(error_message)
        slogans = []

    return slogans


def generate_differentiation(brand_brief: dict) -> dict:
    """브랜드 브리프의 경쟁사(competitors)를 분석해 차별화 포인트를 제안한다.

    반환 형식 (실패 시 빈 dict):
        {
          "competitor_analysis": [{"competitor": "...", "positioning": "..."}, ...],
          "differentiation_points": ["...", "...", "..."]
        }
    """
    context = _build_brief_context(brand_brief)
    competitors = brand_brief.get("competitors", [])

    prompt = f"""당신은 브랜드 전략 컨설턴트입니다. 아래 브랜드 브리프와 경쟁사 목록을 분석해서
경쟁사별 포지셔닝과 이 브랜드만의 차별화 포인트를 제안해주세요.

[브랜드 브리프]
{context}

[경쟁사]
{", ".join(competitors) if competitors else "없음"}

[요청 사항]
- 각 경쟁사의 예상 포지셔닝(강점/약점)을 1~2문장으로 분석할 것
- 브리프의 톤앤매너와 키워드, 추가 요청사항을 반영해 이 브랜드만의 차별화 포인트를 3개 제안할 것
- 다이어트/체중 감량이 아니라 브리프에 명시된 실제 맥락에 초점을 맞출 것

반드시 아래 JSON 형식으로만 응답하세요. 다른 설명, 인사말, 코드블록 표시는 넣지 마세요.
{{
  "competitor_analysis": [
    {{"competitor": "경쟁사명", "positioning": "예상 포지셔닝(강점/약점)"}}
  ],
  "differentiation_points": ["차별화 포인트1", "차별화 포인트2", "차별화 포인트3"]
}}"""

    try:
        raw_response = client.chat.completions.create(
            model=_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        ).choices[0].message.content
        differentiation = _extract_json(raw_response)
    except Exception as e:
        error_message = f"[generate_differentiation] 오류 발생: {e}"
        print(error_message)
        differentiation = {}

    return differentiation


def generate_story(brand_brief: dict) -> str:
    prompt = f"""
    당신은 브랜드 스토리텔러입니다. 아래 브리프를 참고해 브랜드 스토리를 작성해주세요.
 
    업종: {brand_brief['industry']}
    타겟: {brand_brief['target']}
    키워드: {', '.join(brand_brief['keywords'])}
    톤앤매너: {brand_brief.get('tone', '')}
    경쟁사: {', '.join(brand_brief.get('competitors', []))}
    참고사항: {brand_brief.get('notes', '')}

    주의사항:
    다이어트/체중감량이 아니라 "바쁜 일상 속 자기관리"가 동기입니다.
    "저칼로리", "살 빠지는" 같은 워딩은 금지.
    "대충 때우는 배달음식"과 대비되는 "스스로를 위한 제대로 된 한 끼" 느낌을 담으세요.

    200~300자 분량의 브랜드 스토리 텍스트만 출력하세요. 다른 설명 없이 스토리 본문만.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        brand_story = response.choices[0].message.content.strip()
        return brand_story
    except Exception as e:
        error_message = f"generate_story 실패: {e}"
        print(error_message)
        return ""


def generate_color_palette(brand_brief: dict) -> dict:
    prompt = f"""
    아래 브랜드 브리프에 어울리는 컬러 팔레트를 만들어주세요.
    
    업종: {brand_brief['industry']}
    타겟: {brand_brief['target']}
    키워드: {', '.join(brand_brief['keywords'])}
    톤앤매너: {brand_brief.get('tone', '')}

    신선함, 건강함, 신뢰감을 주는 컬러로 선정하세요. 자극적인 레드/네온 계열은 피하세요.
    
    아래 JSON 형식으로만 응답하세요:
    {{
    "main_color": "#XXXXXX",
    "sub_colors": ["#XXXXXX", "#XXXXXX"]
    }}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        color_palette = json.loads(response.choices[0].message.content)
        return color_palette
    except Exception as e:
        error_message = f"generate_color_palette 실패: {e}"
        print(error_message)
        return {"main_color": "#CCCCCC", "sub_colors": ["#EEEEEE", "#AAAAAA"]}


def save_color_palette_image(color_palette: dict, output_dir: str) -> str | None:
    """
    color_palette 예: {"main_color": "#2E7D32", "sub_colors": ["#81C784", "#E8F5E9"]}
    matplotlib으로 컬러 스와치를 그려 output_dir/color_palette.png 로 저장한다.

    반환: color_palette_path (실패 시 None. 실패해도 프로그램은 계속 진행)
    """
    try:
        main_color = color_palette.get("main_color")
        sub_colors = color_palette.get("sub_colors", [])

        if not main_color:
            raise ValueError("color_palette에 'main_color' 값이 없습니다.")

        swatches = [("Main", main_color)] + [
            (f"Sub {i + 1}", hex_code) for i, hex_code in enumerate(sub_colors)
        ]

        fig, ax = plt.subplots(figsize=(2.2 * len(swatches), 3))

        for i, (label, hex_code) in enumerate(swatches):
            ax.add_patch(patches.Rectangle((i, 0), 1, 1, facecolor=hex_code, edgecolor="#DDDDDD"))
            ax.text(i + 0.5, 1.12, label, ha="center", va="bottom", fontsize=12, fontweight="bold")
            ax.text(i + 0.5, -0.12, hex_code.upper(), ha="center", va="top", fontsize=10, family="monospace")

        ax.set_xlim(0, len(swatches))
        ax.set_ylim(-0.35, 1.35)
        ax.axis("off")
        fig.tight_layout()

        os.makedirs(output_dir, exist_ok=True)
        color_palette_path = os.path.join(output_dir, "color_palette.png")
        fig.savefig(color_palette_path, dpi=150)
        plt.close(fig)

        print(f"  - 저장: {color_palette_path}")
        return color_palette_path

    except Exception as e:
        error_message = f"[컬러 팔레트 시각화 실패] {e}"
        print(error_message)
        return None


def _build_logo_prompt(brand_brief: dict, color_palette: dict, brand_name: str = "") -> str:
    """brand_brief + color_palette(+ brand_name) -> 이미지 생성 API용 logo_prompt로 변환."""
    industry = brand_brief.get("industry", "")
    keywords = ", ".join(brand_brief.get("keywords", []))
    tone = brand_brief.get("tone", "")
    main_color = color_palette.get("main_color", "")
    sub_colors = ", ".join(color_palette.get("sub_colors", []))

    if brand_name:
        name_line = f"Brand name: {brand_name}. "
        text_instruction = (
            f"Include the brand name '{brand_name}' as clean, legible typography "
            "integrated into the logo (wordmark or lettermark combined with a simple icon). "
        )
    else:
        name_line = ""
        text_instruction = "Flat design, simple geometric shape, no text or letters. "

    return (
        f"A minimalist, modern vector logo for a '{industry}' brand. "
        f"{name_line}"
        f"Brand keywords: {keywords}. Brand tone: {tone}. "
        f"Primary brand color: {main_color}. Secondary colors: {sub_colors}. "
        f"{text_instruction}"
        "Flat design, centered on a plain white background, professional brand identity style."
    )


def generate_logo(
    brand_brief: dict,
    color_palette: dict,
    naming_candidates: list[dict] | None = None,
    output_dir: str = "./output",
    logo_count: int | None = None,
) -> list[str]:
    """
    이미지 생성 API(gpt-image-1)로 로고 시안을 생성해 PNG로 저장한다.
    naming_candidates가 있으면 브랜드명 후보 개수만큼(기본 3개) 로고를 생성해
    후보마다 하나씩 이름을 로고에 반영한다.

    반환: logo_paths (실패 시 빈 리스트. 실패해도 프로그램은 계속 진행)
    """
    logo_paths: list[str] = []

    if logo_count is None:
        logo_count = len(naming_candidates) if naming_candidates else 2

    image_api_key = _load_image_api_key()
    if not image_api_key:
        print("[안내] 이미지 생성 API 키가 없습니다. 환경변수 IMAGE_API_KEY(또는 OPENAI_API_KEY)를 설정하세요.")
        return logo_paths

    image_client = OpenAI(api_key=image_api_key)
    os.makedirs(output_dir, exist_ok=True)

    # 기본은 gpt-image-1. 조직 인증(Organization Verification) 문제로 막히는 경우
    # 코드를 고치지 않고도 환경변수만 바꿔서 dall-e-3로 즉시 전환할 수 있게 한다.
    image_model = os.environ.get("IMAGE_MODEL", "gpt-image-1")

    for i in range(logo_count):
        try:
            # 로고마다 네이밍 후보를 하나씩 돌아가며 프롬프트에 반영한다.
            candidate = (
                naming_candidates[i % len(naming_candidates)] if naming_candidates else None
            )
            brand_name = candidate.get("name_en", "") if candidate else ""
            logo_prompt = _build_logo_prompt(brand_brief, color_palette, brand_name)

            request_kwargs = dict(
                model=image_model,
                prompt=logo_prompt,
                size="1024x1024",
                n=1,
            )
            if image_model.startswith("dall-e"):
                # dall-e-2/3는 response_format을 명시해야 b64_json으로 받을 수 있다.
                request_kwargs["response_format"] = "b64_json"
            else:
                # gpt-image 계열은 기본적으로 base64(b64_json)로 응답한다.
                request_kwargs["quality"] = "medium"

            response = image_client.images.generate(**request_kwargs)
            image_base64 = response.data[0].b64_json
            image_bytes = base64.b64decode(image_base64)

            logo_path = os.path.join(output_dir, f"logo_{i + 1:02d}.png")
            with open(logo_path, "wb") as f:
                f.write(image_bytes)

            print(f"  - 저장: {logo_path}")
            logo_paths.append(logo_path)

        except Exception as e:
            error_message = f"[로고 시안 {i + 1} 생성 실패] {e}"
            print(error_message)
            if "organization" in str(e).lower() or "verif" in str(e).lower():
                print(
                    "    힌트: gpt-image-1은 OpenAI 조직 인증이 필요할 수 있습니다. "
                    "환경변수 IMAGE_MODEL=dall-e-3 로 설정하면 대체 모델로 시도합니다."
                )
            continue  # 한 장 실패해도 다음 로고 생성 계속 진행

    return logo_paths


def save_result(brand_result: dict, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    result_json_path = os.path.join(output_dir, "brand_result.json")

    with open(result_json_path, "w", encoding="utf-8") as f:
        json.dump(brand_result, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장 완료: {result_json_path}")
    return result_json_path


def main():
    print("🎨 AI 브랜드 아이덴티티 생성기")

    brief_path = input("브리프 파일 경로를 입력하세요: ")
    output_dir = input("출력 폴더 경로를 입력하세요 (엔터 시 ./output): ") or "./output"

    brand_brief = load_brief(brief_path)

    print("[1/6] 브랜드 네이밍 생성 중...")
    naming_candidates = generate_naming(brand_brief)

    print("[2/6] 슬로건 생성 중...")
    slogans = generate_slogans(brand_brief)

    print("[3/6] 경쟁사 분석 및 차별화 포인트 도출 중...")
    differentiation = generate_differentiation(brand_brief)

    print("[4/6] 브랜드 스토리 생성 중...")
    brand_story = generate_story(brand_brief)

    print("[5/6] 컬러 팔레트 생성 중...")
    color_palette = generate_color_palette(brand_brief)
    color_palette_path = save_color_palette_image(color_palette, output_dir)

    print("[6/6] 로고 시안 생성 중...")
    logo_paths = generate_logo(brand_brief, color_palette, naming_candidates, output_dir)

    brand_result = {
        "brief": brand_brief,
        "naming_candidates": naming_candidates,
        "slogans": slogans,
        "differentiation": differentiation,
        "brand_story": brand_story,
        "color_palette": color_palette,
        "logo_paths": logo_paths,
    }
    result_json_path = save_result(brand_result, output_dir)

    print(f"✅ 완료! {output_dir} 폴더를 확인하세요.")


if __name__ == "__main__":
    main()