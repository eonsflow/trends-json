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
    return keywords[:20]  # 최대 20개까지

def fetch_google_trends():
    # 샘플 고정 (향후 Google Trends 연동 가능)
    return ["환율", "손흥민", "디아블로 출시", "전세사기", "청년도약계좌", "청년 취업지원금", "테슬라 주가", "넷플릭스 해지", "카리나", "청약 일정", "아이폰16", "로또 당첨"]

def merge_keywords():
    naver = fetch_naver_trends()
    google = fetch_google_trends()
    combined = naver + google
    deduped = []
    seen = set()
    for kw in combined:
        if kw not in seen:
            deduped.append(kw)
            seen.add(kw)
    return deduped[:20]

def enrich_keywords(keywords):
    from random import choice, randint
    difficulty = ["하", "중", "상"]
    related = [["재난", "기상청"], ["넷플릭스", "구독"], ["청년", "지원금"], ["아이폰", "출시일"], ["EPL", "득점왕"]]
    channels = ["이슈", "실생활", "정책", "경제", "엔터", "스포츠"]

    enriched = []
    for kw in keywords:
        enriched.append({
            "keyword": kw,
            "volume": randint(12000, 60000),
            "difficulty": choice(difficulty),
            "related": ", ".join(choice(related)),
            "channel": choice(channels)
        })
    return enriched

def save_to_json(keywords):
    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trends": keywords
    }
    with open("trends.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    try:
        keywords = merge_keywords()
        enriched = enrich_keywords(keywords)
        save_to_json(enriched)
        print(f"✅ {len(enriched)}개 키워드 저장 완료 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
