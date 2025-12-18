import requests
import json

# API 설정
BASE_URL = "http://127.0.0.1:5002"

def test_health():
    """헬스체크 테스트"""
    print("=" * 60)
    print("🔍 Testing /health endpoint...")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_analyze(diary_text, mood=None):
    """일기 분석 테스트"""
    print("\n" + "=" * 60)
    print("📝 Testing /analyze endpoint...")
    print("=" * 60)
    
    data = {
        "date": "2024-01-15",
        "diaryText": diary_text
    }
    
    if mood:
        data["selfReportedMood"] = mood
    
    print(f"📤 Request Data:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(
            f"{BASE_URL}/analyze",
            json=data,
            timeout=30
        )
        
        print(f"\n📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Analysis Result:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return True
        else:
            print(f"\n❌ Error Response:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out (30s)")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("\n🚀 Starting API Tests...\n")
    
    # 1. 헬스체크
    if not test_health():
        print("\n⚠️ Server is not responding. Please check if it's running:")
        print("   python main.py")
        return
    
    # 2. 샘플 일기 테스트
    test_cases = [
        {
            "mood": "불안함",
            "text": "오늘 발표가 너무 긴장됐다. 떨리고 말도 잘 안 나왔다. 계속 실수할까봐 걱정됐다."
        },
        {
            "mood": "행복함",
            "text": "오늘 프로젝트가 성공적으로 마무리됐다. 팀원들과 축하 파티도 했고 정말 뿌듯했다."
        },
        {
            "mood": None,
            "text": "아무것도 하기 싫다. 삶이 무의미하게 느껴진다."
        }
    ]
    
    success_count = 0
    for i, case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}/{len(test_cases)}")
        print(f"{'='*60}")
        
        if test_analyze(case["text"], case["mood"]):
            success_count += 1
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    print(f"✅ Passed: {success_count}/{len(test_cases)}")
    print(f"❌ Failed: {len(test_cases) - success_count}/{len(test_cases)}")
    print("=" * 60)

if __name__ == "__main__":
    main()