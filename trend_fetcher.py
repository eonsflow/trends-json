import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def fetch_naver_trends():
    url = "https://datalab.naver.com/keyword/realtimeList.naver?where=main"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    keywords = [span.text.strip() for span in soup.select(".item_title")]
    
    enriched = []
    for kw in keywords[:20]:  # 🔥 최대 20개까지 추출
        enriched.append({
            "keyword": kw,
            "volume": 10000 + len(kw)*1000,       # 예시 검색량
            "difficulty": "중",                    # 예시 경쟁도
            "related": "연관어1, 연관어2",          # 예시 연관 키워드
            "channel": "이슈/일상"                  # 예시 추천 채널
        })

    return enriched

def save_to_json(keywords):
    data = {"trends": keywords}
    with open("trends.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    try:
        keywords = fetch_naver_trends()
        save_to_json(keywords)
        print(f"✅ {len(keywords)}개 키워드 저장 완료 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
