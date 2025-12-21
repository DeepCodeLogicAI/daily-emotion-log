# emotion.py
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 🔐 API KEY 설정
# 환경 변수에서 먼저 확인하고, 없으면 직접 설정된 키 사용
api_key = os.getenv("GEMINI_API_KEY")

if api_key and api_key != "YOUR_API_KEY":
    try:
        genai.configure(api_key=api_key)
        print(f"✅ Gemini API 키가 설정되었습니다. (키 길이: {len(api_key)})")
        
        # 사용 가능한 모델 목록 확인
        try:
            print("🔍 사용 가능한 모델 목록 확인 중...")
            models = genai.list_models()
            available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
            print(f"✅ 사용 가능한 모델: {available_models[:5]}")  # 처음 5개만 출력
        except Exception as list_e:
            print(f"⚠️ 모델 목록 확인 실패: {list_e}")
            
    except Exception as e:
        print(f"⚠️ API 키 설정 오류: {e}")
        api_key = None
else:
    print("⚠️ 경고: Gemini API 키가 설정되지 않았습니다!")
    api_key = None


class EmotionAnalyzer:
    def __init__(self, content: str):
        self.content = content
        self.api_key = api_key
        if self.api_key:
            # 사용 가능한 모델 목록에서 찾기
            try:
                models = genai.list_models()
                available_models = [m.name.replace('models/', '') for m in models 
                                   if 'generateContent' in m.supported_generation_methods]
                
                # 우선순위: flash 모델 우선, 없으면 pro 모델
                preferred_models = [m for m in available_models if 'flash' in m.lower()]
                if not preferred_models:
                    preferred_models = [m for m in available_models if 'pro' in m.lower()]
                
                if preferred_models:
                    model_name = preferred_models[0]
                    self.model = genai.GenerativeModel(model_name)
                    print(f"✅ Gemini 모델 초기화 성공 ({model_name})")
                else:
                    # 기본 모델 시도
                    model_names = ["gemini-pro", "models/gemini-pro"]
                    for model_name in model_names:
                        try:
                            self.model = genai.GenerativeModel(model_name)
                            print(f"✅ Gemini 모델 초기화 성공 ({model_name})")
                            break
                        except:
                            continue
                    
                    if not self.model:
                        print("❌ 사용 가능한 모델을 찾을 수 없습니다")
            except Exception as e:
                print(f"⚠️ 모델 목록 확인 실패, 기본 모델 시도: {e}")
                try:
                    self.model = genai.GenerativeModel("gemini-pro")
                    print("✅ Gemini 모델 초기화 성공 (gemini-pro - 기본)")
                except:
                    self.model = None
        else:
            self.model = None

    def analyze(self):
        # API 키가 없으면 간단한 분석 반환
        if not self.api_key or not self.model:
            print("⚠️ API 키가 없어 간단한 분석을 수행합니다.")
            print(f"API 키 상태: api_key={bool(self.api_key)}, model={bool(self.model)}")
            return self._simple_analysis()
        
        print(f"✅ API 키 확인됨, 모델 초기화 완료. 분석 시작...")
        
        # 간단한 프롬프트 - 참고 프로젝트 방식
        prompt = f"""Analyze the emotional tone of the following diary entry. Categorize it into exactly one of these categories: Happy, Neutral, Sad, Angry. Also provide a very short, supportive one-sentence summary of the mood in Korean.

Entry: "{self.content}"

Respond in JSON format only:
{{
  "mood": "Happy|Neutral|Sad|Angry",
  "summary": "한 줄 요약"
}}"""

        try:
            print("🔄 Gemini API 호출 중...")
            response = self.model.generate_content(prompt)
            print(f"Gemini 응답 원본: {response.text[:200]}...")  # 디버깅용
            
            # JSON 추출
            text = response.text.strip()
            
            # ```json 또는 ```로 감싸진 경우 제거
            if "```" in text:
                if "```json" in text:
                    text = text.split("```json")[1]
                elif "```" in text:
                    text = text.split("```")[1]
                if text.endswith("```"):
                    text = text.rsplit("```", 1)[0]
                text = text.strip()
            
            # JSON 객체 시작과 끝 찾기
            start_idx = text.find("{")
            end_idx = text.rfind("}")
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                text = text[start_idx:end_idx+1]
            
            # JSON 파싱
            result = json.loads(text)
            print(f"AI 분석 성공: {result}")
            
            # 필수 필드 확인
            if "mood" not in result:
                result["mood"] = "Neutral"
            if "summary" not in result:
                result["summary"] = "분석 결과를 가져올 수 없습니다."
            
            return result

        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            print(f"파싱 시도한 텍스트: {text[:500]}")
            # JSON 파싱 실패 시 기본값 반환
            return {
                "mood": "Neutral",
                "summary": "분석 결과를 파싱하는 중 오류가 발생했습니다."
            }
        except Exception as e:
            print(f"Emotion analysis error: {e}")
            print(f"에러 타입: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            
            # API 키 관련 오류인지 확인
            error_str = str(e).lower()
            error_type = type(e).__name__
            
            # 더 정확한 오류 메시지
            if "api" in error_str or "key" in error_str or "authentication" in error_str or "permission" in error_str:
                print(f"⚠️ API 키 인증 오류 감지: {error_str}")
                return {
                    "mood": "Neutral",
                    "summary":"일시적으로 감정 분석 기능을 사용할 수 없습니다. 잠시 후 다시 시도해 주세요."
                    # "summary": f"API 키 인증 오류가 발생했습니다. API 키를 확인해주세요. (오류: {error_str[:100]})"
                }
            
            # 네트워크 오류
            if "network" in error_str or "connection" in error_str or "timeout" in error_str:
                return {
                    "mood": "Neutral",
                    "summary": "네트워크 연결 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
                }
            
            return {
                "mood": "Neutral",
                "summary": f"분석 중 오류가 발생했습니다: {str(e)[:80]}"
            }
    
    def _simple_analysis(self):
        """API 키가 없을 때 간단한 키워드 기반 분석"""
        content_lower = self.content.lower()
        
        # 키워드 기반 감정 분석
        positive_words = ["좋", "행복", "기쁨", "즐거", "신나", "만족", "감사", "사랑"]
        negative_words = ["슬프", "우울", "힘들", "아픔", "화나", "짜증", "답답", "불안"]
        angry_words = ["화", "분노", "짜증", "불만", "답답", "화남"]
        
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        angry_count = sum(1 for word in angry_words if word in content_lower)
        
        if positive_count > negative_count and positive_count > 0:
            mood = "Happy"
            summary = "긍정적인 감정이 느껴집니다. 오늘도 좋은 하루였네요."
        elif angry_count > 0:
            mood = "Angry"
            summary = "불편한 감정이 느껴집니다. 자신을 돌보는 시간을 가져보세요."
        elif negative_count > 0:
            mood = "Sad"
            summary = "어려운 감정이 느껴집니다. 충분히 쉬어가도 괜찮아요."
        else:
            mood = "Neutral"
            summary = "차분한 상태입니다. 평온한 하루를 보내셨네요."
        
        return {
            "mood": mood,
            "summary": summary
        }
