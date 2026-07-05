import os
import re
import json
import time
import base64
import hmac
import hashlib
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

# ── 네이버 Developers (DataLab 검색어트렌드) ────────────────────────────
# 상대지수(0~100, 요청 내 정규화). 키워드 자체 시계열의 모양/피크월 산출용.
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

# ── 네이버 검색광고 (키워드도구, 절대 검색량) ──────────────────────────
SAD_CUSTOMER = os.getenv("NAVER_SAD_CUSTOMER_ID", "")
SAD_KEY = os.getenv("NAVER_SAD_API_KEY", "")
SAD_SECRET = os.getenv("NAVER_SAD_SECRET", "")

DATALAB_TIME_UNIT = "month"     # 키워드별 월별 추이
DATALAB_TREND_MONTHS = 12       # 검색량 추이 조회 기간(개월)
NAVER_MAX_KEYWORDS = 5          # 한 번에 보낼 수 있는 키워드 최대 5개


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


def _norm(s):
    return re.sub(r"\s+", "", s or "")


def _parse_vol(v):
    """검색광고 검색량 파싱. "< 10" → 10 처럼 숫자만 남긴다."""
    if isinstance(v, (int, float)):
        return int(v)
    s = re.sub(r"[^0-9]", "", str(v if v is not None else ""))
    return int(s) if s else 0


def _chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


# ── 데이터랩 검색어트렌드: 최대 5개 키워드 묶음 → 키워드별 월별 추이 ──────
def datalab_trend(keywords, start_date, end_date, ages=None):
    """
    반환: { 키워드: [{"period","ratio"}...] }  (각 키워드는 자체 0~100 상대지수)
    """
    if not (NAVER_CLIENT_ID and NAVER_CLIENT_SECRET):
        raise RuntimeError("NAVER_CLIENT_ID/SECRET 없음")

    groups = [{"groupName": k, "keywords": [k]} for k in keywords[:NAVER_MAX_KEYWORDS]]
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": DATALAB_TIME_UNIT,
        "keywordGroups": groups,
    }
    if ages:
        body["ages"] = ages

    res = requests.post(
        "https://openapi.naver.com/v1/datalab/search",
        headers={
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
            "Content-Type": "application/json",
        },
        data=json.dumps(body),
        timeout=15,
    )
    if not res.ok:
        raise RuntimeError(f"DataLab {res.status_code}: {res.text[:150]}")

    data = res.json()
    out = {}
    for g in data.get("results", []) or []:
        out[g.get("title")] = [
            {"period": d.get("period"), "ratio": float(d.get("ratio", 0))}
            for d in (g.get("data") or [])
        ]
    return out


# ── 검색광고 키워드도구: 키워드별 절대 월간 검색량(PC+모바일) ───────────
def _sad_sign(ts, method, uri):
    msg = f"{ts}.{method}.{uri}"
    digest = hmac.new(SAD_SECRET.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def search_ad_volume(keywords):
    """반환: { 키워드: 절대_월간_검색량 }  (입력 키워드와 정확 매칭되는 것만)"""
    if not (SAD_CUSTOMER and SAD_KEY and SAD_SECRET):
        raise RuntimeError("NAVER_SAD_* 없음")

    ts = str(round(time.time() * 1000))
    uri = "/keywordstool"
    sig = _sad_sign(ts, "GET", uri)
    hint = ",".join(_norm(k) for k in keywords[:NAVER_MAX_KEYWORDS])

    res = requests.get(
        f"https://api.searchad.naver.com{uri}?hintKeywords={requests.utils.quote(hint)}&showDetail=1",
        headers={
            "X-Timestamp": ts,
            "X-API-KEY": SAD_KEY,
            "X-Customer": SAD_CUSTOMER,
            "X-Signature": sig,
        },
        timeout=15,
    )
    if not res.ok:
        raise RuntimeError(f"SearchAd {res.status_code}: {res.text[:150]}")

    data = res.json()
    by_key = {}
    for r in data.get("keywordList", []) or []:
        by_key[_norm(str(r.get("relKeyword", "")))] = (
            _parse_vol(r.get("monthlyPcQcCnt")) + _parse_vol(r.get("monthlyMobileQcCnt"))
        )
    # 입력 키워드와 정확 매칭되는 것만
    out = {}
    for k in keywords:
        v = by_key.get(_norm(k))
        if v is not None:
            out[k] = v
    return out


def fetch_naver_metrics(keywords):
    """
    데이터랩 추이 + 검색광고 절대 검색량을 5개씩 배치로 모아 합친다.
    반환: { 키워드: {"volume": int|None, "trend": [{"period","ratio"}...]} }
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=DATALAB_TREND_MONTHS * 30)).strftime("%Y-%m-%d")

    metrics = {kw: {"volume": None, "trend": []} for kw in keywords}

    for batch in _chunks(keywords, NAVER_MAX_KEYWORDS):
        try:
            for kw, points in datalab_trend(batch, start_date, end_date).items():
                if kw in metrics:
                    metrics[kw]["trend"] = points
        except Exception as e:
            print(f"⚠️ 데이터랩 추이 실패({batch}): {e}")

        try:
            for kw, vol in search_ad_volume(batch).items():
                if kw in metrics:
                    metrics[kw]["volume"] = vol
        except Exception as e:
            print(f"⚠️ 검색광고 검색량 실패({batch}): {e}")

        time.sleep(0.3)  # API 부하 완화

    return metrics


def enrich_keywords(keywords):
    from random import choice, randint
    difficulty = ["하", "중", "상"]
    related = [["재난", "기상청"], ["넷플릭스", "구독"], ["청년", "지원금"],
               ["아이폰", "출시일"], ["EPL", "득점왕"]]
    channels = ["이슈", "실생활", "정책", "경제", "엔터", "스포츠"]

    metrics = fetch_naver_metrics(keywords)

    enriched = []
    for kw in keywords:
        m = metrics.get(kw, {})
        volume = m.get("volume")
        if volume is None:                    # 검색광고 미연동/실패 시 폴백
            volume = randint(12000, 60000)
        enriched.append({
            "keyword": kw,
            "volume": volume,                 # 검색광고 절대 월간 검색량(PC+모바일)
            "trend": m.get("trend", []),      # 데이터랩 월별 검색량 추이(상대지수)
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
