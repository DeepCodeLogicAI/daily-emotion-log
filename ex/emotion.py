# emotion.py
import google.generativeai as genai
import json
import os

# 🔐 API KEY (env 파일 써도 되고, 일단은 직접 써도 됨)
genai.configure(api_key=os.getenv("GEMINI_API_KEY") or "YOUR_API_KEY")


class EmotionAnalyzer:
    def __init__(self, content: str):
        self.content = content
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def analyze(self):
        prompt = f"""
너는 따뜻하고 전문적인 심리 상담사야.
아래 일기를 읽고 반드시 JSON 형식으로만 분석 결과를 출력해.

일기:
{self.content}

출력 형식(JSON):
{{
  "psychologicalState": "심리 상태 한 문장 요약",
  "mood": "기분 (예: 평온함, 우울함, 기쁨 등)",
  "reason": "이렇게 느낀 이유",
  "advice": "따뜻한 위로와 조언"
}}
"""

        response = self.model.generate_content(prompt)

        try:
            # Gemini가 ```json ``` 감싸서 줄 수도 있어서 처리
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]

            return json.loads(text)

        except Exception as e:
            print("Emotion analysis error:", e)
            return {
                "psychologicalState": "분석 실패",
                "mood": "알 수 없음",
                "reason": "일기 내용이 짧거나 분석이 어려웠어요.",
                "advice": "오늘도 충분히 잘 해냈어요 🌷"
            }
