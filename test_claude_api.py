import requests
from config import CLAUDE_API_KEY

# Claude API 테스트
def test_claude_api():
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    # 간단한 테스트 요청
    payload = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 100,
        "messages": [
            {"role": "user", "content": "Hello, can you translate '안녕하세요' to English?"}
        ]
    }
    
    try:
        print("Claude API 테스트 중...")
        res = requests.post(url, json=payload, headers=headers)
        print(f"상태 코드: {res.status_code}")
        print(f"응답 헤더: {dict(res.headers)}")
        
        data = res.json()
        print(f"응답 데이터: {data}")
        
        if "content" in data:
            print("✅ API 정상 작동")
            return True
        else:
            print("❌ API 응답 구조 문제")
            return False
            
    except Exception as e:
        print(f"❌ API 요청 오류: {e}")
        return False

if __name__ == "__main__":
    test_claude_api()