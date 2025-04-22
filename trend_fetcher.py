import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def fetch_naver_trends():
    url = "https://datalab.naver.com/keyword/realtimeList.naver?where=main"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    return [span.text.strip() for span in soup.select(".item_title")]

def fetch_google_trends():
    url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=KR"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "xml")
    return [item.find("title").text.strip() for item in soup.find_all("item")]

def merge_keywords(naver, google, max_count=20):
    both = [kw for kw in naver if kw in google]
    only_naver = [kw for kw in naver if kw not in google]
    only_google = [kw for kw in google if kw not in naver]
    return (both + only_naver + only_google)[:max_count]

def enrich_keywords(keywords):
    enriched = []
    for kw in keywords:
        enriched.append({
            "keyword": kw,
            "volume": 10000 + len(kw) * 1000,
            "difficulty": "중",
            "related": "연관어1, 연관어2",
            "channel": "이슈/일상"
        })
    return enriched

def save_to_json(keywords):
    data = {"trends": keywords}
    with open("trends.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    try:
        naver = fetch_naver_trends()
        google = fetch_google_trends()
        merged = merge_keywords(naver, google)
        enriched = enrich_keywords(merged)
        save_to_json(enriched)
        print(f"✅ {len(enriched)}개 키워드 저장 완료 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
