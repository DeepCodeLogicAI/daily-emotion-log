# gemini_client.py
import os
import json
import re
from typing import Any, Dict, List

from dotenv import load_dotenv
from json_repair import repair_json
import google.generativeai as genai

from schemas import DiaryEntryIn

# .env 로드 (OS 환경변수보다 우선 적용)
load_dotenv(override=True)

# API Key
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
if not GEMINI_API_KEY or len(GEMINI_API_KEY) < 20:
    raise RuntimeError("GEMINI_API_KEY가 .env에 없거나 유효하지 않습니다.")

genai.configure(api_key=GEMINI_API_KEY)

# ✅ 모델명은 강제로 고정 (환경변수/OS 충돌 방지)
MODEL_NAME = "models/gemini-2.5-flash"

# 허용 라벨 (schemas.py와 동일)
ALLOWED_LABELS = [
    "기쁨", "슬픔", "분노", "불안", "두려움", "혐오", "놀람", "평온",
    "피로", "외로움", "죄책감", "무기력", "만족", "답답함"
]

SYSTEM = """당신은 감정 분석 및 일상적 자기관리 코치 AI입니다.
- 진단/치료/의학적 판단을 하지 마세요.
- 출력은 JSON 하나만 반환하세요(설명/코드블록 금지).
- Rationale는 일기에서 직접 추출 가능한 키워드/짧은 문구만(해석 추가 금지).
- Suggestions는 최대 3개.
- 자해/자살/극단적 표현이 명확할 때만 RiskFlag 설정.
"""

SCHEMA = f"""반드시 다음 스키마의 JSON 하나만 출력하세요.
- PrimaryEmotion.label 및 SecondaryEmotions[].label 은 반드시 다음 중 하나여야 함:
  {ALLOWED_LABELS}

{{
  "PrimaryEmotion":{{"label":"...","confidence":0.0-1.0}},
  "SecondaryEmotions":[{{"label":"...","confidence":0.0-1.0}}],
  "Valence":-1.0-1.0,
  "Arousal":0.0-1.0,
  "Intensity":0-100,
  "Summary":"1~3문장",
  "Rationale":["키워드/문구"],
  "Suggestions":["최대 3개"],
  "RiskFlag": null 또는 {{"level":"low|medium|high","message":"안내 문구"}}
}}
"""

# 라벨 정규화(모델이 "행복/우울/긴장/스트레스" 같은 걸 내놔도 허용 라벨로 매핑)
LABEL_MAP = {
    # 기쁨/만족
    "행복": "기쁨", "즐거움": "기쁨", "기대": "기쁨", "뿌듯": "만족", "성취": "만족",
    # 슬픔/무기력
    "우울": "슬픔", "허무": "무기력", "상실감": "슬픔",
    # 불안/두려움
    "긴장": "불안", "초조": "불안", "걱정": "불안", "스트레스": "불안",
    "공포": "두려움",
    # 분노/답답함
    "짜증": "분노", "화남": "분노", "분개": "분노", "억울": "분노",
    "답답": "답답함", "갑갑": "답답함",
    # 평온
    "안정": "평온", "차분": "평온", "편안": "평온",
    # 피로/외로움/죄책감
    "지침": "피로", "피곤": "피로",
    "고립": "외로움",
    "후회": "죄책감",
    # 놀람/혐오
    "충격": "놀람",
}

def _clamp_float(x: Any, lo: float, hi: float, default: float) -> float:
    try:
        v = float(x)
        if v < lo:
            return lo
        if v > hi:
            return hi
        return v
    except Exception:
        return default

def _clamp_int(x: Any, lo: int, hi: int, default: int) -> int:
    try:
        v = int(float(x))
        if v < lo:
            return lo
        if v > hi:
            return hi
        return v
    except Exception:
        return default

def _normalize_label(label: Any) -> str:
    s = str(label or "").strip()
    if not s:
        return "평온"
    if s in ALLOWED_LABELS:
        return s
    if s in LABEL_MAP:
        return LABEL_MAP[s]
    for k, v in LABEL_MAP.items():
        if k in s:
            return v
    return "평온"

def _extract_json(text: str) -> Dict[str, Any]:
    """
    1) 코드블록 제거
    2) '{'부터 시작하는 JSON 후보 문자열 추출
    3) json.loads 시도 → 실패하면 json_repair로 복구 후 다시 파싱
    """
    t = (text or "").strip()

    if "```json" in t:
        t = t.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in t:
        t = t.split("```", 1)[1].split("```", 1)[0].strip()

    s = t.find("{")
    if s == -1:
        raise ValueError(f"모델이 JSON을 반환하지 않았습니다. raw={t[:300]}")

    candidate = t[s:]

    # 정상 파싱 먼저 시도
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # 흔한 trailing comma 제거(가벼운 보정)
        candidate2 = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            return json.loads(candidate2)
        except json.JSONDecodeError:
            # json-repair로 복구
            repaired = repair_json(candidate2)
            return json.loads(repaired)

def _ensure_schema(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    모델이 키를 빼먹거나 타입이 흔들려도 AnalysisResult에 맞추기 위한 보정
    """
    out: Dict[str, Any] = {}

    pe = d.get("PrimaryEmotion") or d.get("primaryEmotion") or d.get("primary_emotion") or {}
    se = d.get("SecondaryEmotions") or d.get("secondaryEmotions") or d.get("secondary_emotions") or []

    out["PrimaryEmotion"] = {
        "label": _normalize_label(pe.get("label") if isinstance(pe, dict) else None),
        "confidence": _clamp_float(pe.get("confidence") if isinstance(pe, dict) else None, 0.0, 1.0, 0.7),
    }

    sec_list: List[Dict[str, Any]] = []
    if isinstance(se, list):
        for item in se[:5]:
            if isinstance(item, dict):
                sec_list.append({
                    "label": _normalize_label(item.get("label")),
                    "confidence": _clamp_float(item.get("confidence"), 0.0, 1.0, 0.5),
                })
    out["SecondaryEmotions"] = sec_list

    out["Valence"] = _clamp_float(d.get("Valence"), -1.0, 1.0, 0.0)
    out["Arousal"] = _clamp_float(d.get("Arousal"), 0.0, 1.0, 0.5)
    out["Intensity"] = _clamp_int(d.get("Intensity"), 0, 100, 50)

    summary = d.get("Summary")
    out["Summary"] = str(summary).strip() if summary else "오늘의 감정 상태를 요약할 수 없습니다."

    rationale = d.get("Rationale")
    out["Rationale"] = [str(x).strip() for x in rationale] if isinstance(rationale, list) else []

    suggestions = d.get("Suggestions")
    out["Suggestions"] = [str(x).strip() for x in suggestions][:3] if isinstance(suggestions, list) else []

    rf = d.get("RiskFlag")
    if rf is None:
        out["RiskFlag"] = None
    elif isinstance(rf, dict):
        level = rf.get("level")
        msg = rf.get("message")
        if level in ("low", "medium", "high") and msg:
            out["RiskFlag"] = {"level": level, "message": str(msg)}
        else:
            out["RiskFlag"] = None
    else:
        out["RiskFlag"] = None

    return out

def analyze(entry: DiaryEntryIn) -> Dict[str, Any]:
    prompt = f"""[시스템]
{SYSTEM}

[입력]
Date: {entry.date}
SelfReportedMood: {entry.selfReportedMood or "N/A"}
DiaryText:
{entry.diaryText}

[출력]
{SCHEMA}
""".strip()

    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config={
            "temperature": 0.1,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 2048,
            "response_mime_type": "application/json",
        },
    )

    try:
        resp = model.generate_content(prompt)

        # ✅ 더 안전한 텍스트 추출: parts를 모두 합침
        parts_text = ""
        try:
            cand = resp.candidates[0]
            for p in cand.content.parts:
                if hasattr(p, "text") and p.text:
                    parts_text += p.text
        except Exception:
            parts_text = getattr(resp, "text", "") or ""

        raw = _extract_json(parts_text)
        return _ensure_schema(raw)

    except Exception as e:
        raise RuntimeError(f"Gemini 요청 실패: {str(e)}")