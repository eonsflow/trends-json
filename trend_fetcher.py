import os
import json
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

# ── 네이버 데이터랩 검색어 트렌드 API 설정 ───────────────────────────────
# 키는 코드에 넣지 않고 환경변수(GitHub Secrets)에서 읽는다.
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"
DATALAB_MAX_GROUPS = 5          # 한 번에 보낼 수 있는 키워드 그룹 최대 5개
DATALAB_TREND_DAYS = 30         # 검색량 추이 조회 기간(일)
DATALAB_TIME_UNIT = "date"      # date | week | month


def fetch_naver_trends():
    """네이버 실시간 검색어(서비스 종료됨) — 남아있으면 긁고, 없으면 빈 리스트."""
    url = "https://datalab.naver.com/keyword/realtimeList.naver?where=main"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        keywords = [span.text.strip() for span in soup.select(".item_title")]
        return keywords[:20]
    except Exception as e:
        print(f"⚠️ 실시간 검색어 수집 실패: {e}")
        return []


def fetch_google_trends():
    # 샘플 고정 (향후 Google Trends 연동 가능)
    return ["환율", "손흥민", "디아블로 출시", "전세사기", "청년도약계좌", "청년 취업지원금",
            "테슬라 주가", "넷플릭스 해지", "카리나", "청약 일정", "아이폰16", "로또 당첨"]


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


# ── 데이터랩 검색량 추이 ─────────────────────────────────────────────────
def _datalab_request(keyword_groups, start_date, end_date):
    """키워드 그룹(<=5개) 한 배치를 데이터랩 API로 조회."""
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        "Content-Type": "application/json",
    }
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": DATALAB_TIME_UNIT,
        "keywordGroups": [
            {"groupName": kw, "keywords": [kw]} for kw in keyword_groups
        ],
    }
    res = requests.post(DATALAB_URL, headers=headers,
                        data=json.dumps(body), timeout=15)
    res.raise_for_status()
    return res.json()


def fetch_datalab_trends(keywords):
    """
    키워드별 검색량 추이를 데이터랩에서 가져온다.
    반환: { 키워드: {"trend": [{"date","ratio"}...], "volume": 최근_상대비율} }
    데이터랩 ratio는 각 요청 내 최댓값을 100으로 하는 상대값이다.
    """
    if not (NAVER_CLIENT_ID and NAVER_CLIENT_SECRET):
        print("⚠️ NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 미설정 — 데이터랩 건너뜀")
        return {}

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=DATALAB_TREND_DAYS)).strftime("%Y-%m-%d")

    result = {}
    # 키워드를 5개씩(그룹 최대치) 나눠 배치 호출
    for i in range(0, len(keywords), DATALAB_MAX_GROUPS):
        batch = keywords[i:i + DATALAB_MAX_GROUPS]
        try:
            data = _datalab_request(batch, start_date, end_date)
        except Exception as e:
            print(f"⚠️ 데이터랩 조회 실패({batch}): {e}")
            continue

        for entry in data.get("results", []):
            kw = entry.get("title")
            points = [
                {"date": p["period"], "ratio": p["ratio"]}
                for p in entry.get("data", [])
            ]
            latest = points[-1]["ratio"] if points else 0
            result[kw] = {"trend": points, "volume": round(latest, 1)}

        time.sleep(0.3)  # API 부하 완화

    return result


def enrich_keywords(keywords):
    from random import choice, randint
    difficulty = ["하", "중", "상"]
    related = [["재난", "기상청"], ["넷플릭스", "구독"], ["청년", "지원금"],
               ["아이폰", "출시일"], ["EPL", "득점왕"]]
    channels = ["이슈", "실생활", "정책", "경제", "엔터", "스포츠"]

    datalab = fetch_datalab_trends(keywords)

    enriched = []
    for kw in keywords:
        info = datalab.get(kw)
        if info:
            volume = info["volume"]          # 데이터랩 최근 검색량(상대비율)
            trend = info["trend"]            # 검색량 추이 시계열
        else:
            volume = randint(12000, 60000)   # 데이터랩 미연동/실패 시 폴백
            trend = []

        enriched.append({
            "keyword": kw,
            "volume": volume,
            "trend": trend,
            "difficulty": choice(difficulty),
            "related": ", ".join(choice(related)),
            "channel": choice(channels),
        })
    return enriched


def save_to_json(keywords):
    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trend_unit": DATALAB_TIME_UNIT,
        "trends": keywords,
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
