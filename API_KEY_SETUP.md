# Gemini API 키 설정 방법

## 방법 1: 환경 변수 설정 (권장)

### Windows (PowerShell)
```powershell
$env:GEMINI_API_KEY="여기에_API_키_입력"
```

### Windows (CMD)
```cmd
set GEMINI_API_KEY=여기에_API_키_입력
```

### Linux/Mac
```bash
export GEMINI_API_KEY="여기에_API_키_입력"
```

## 방법 2: emotion.py 파일에서 직접 설정

`emotion.py` 파일의 7번째 줄을 수정하세요:

```python
# 기존
genai.configure(api_key=os.getenv("GEMINI_API_KEY") or "YOUR_API_KEY")

# 수정 후
genai.configure(api_key="여기에_API_키_입력")
```

## API 키 발급 방법

1. [Google AI Studio](https://makersuite.google.com/app/apikey)에 접속
2. "Create API Key" 버튼 클릭
3. 생성된 API 키를 복사하여 위 방법 중 하나로 설정

## 참고

- API 키가 설정되지 않으면 간단한 키워드 기반 분석이 수행됩니다.
- 정확한 AI 분석을 위해서는 Gemini API 키 설정이 필요합니다.


