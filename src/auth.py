import requests
import json

def get_access_token(base_url, app_key, app_secret):
    """
    App Key와 Secret을 사용하여 접속 토큰(Access Token)을 발급받습니다.
    토큰 유효기간(24시간) 문제를 해결하기 위해 실행 시마다 호출합니다.
    """
    url = f"{base_url}/oauth2/tokenP"
    
    headers = {
        "content-type": "application/json"
    }
    
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(body))
        response.raise_for_status()
        data = response.json()
        
        token = data.get("access_token")
        if not token:
            raise Exception("토큰 발급 응답에 access_token이 없습니다.")
            
        print("✅ [Auth] 새로운 접속 토큰 발급 완료")
        return token
        
    except Exception as e:
        print(f"❌ [Auth] 토큰 발급 실패: {e}")
        return None
