import json
import requests
from bs4 import BeautifulSoup

def fetch_naver_trends():
    url = "https://datalab.naver.com/keyword/realtimeList.naver?where=main"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    keywords = [span.text.strip() for span in soup.select(".item_title")]
    return keywords[:5]

def save_to_json(keywords):
    data = {"trends": keywords}
    with open("trends.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    try:
        keywords = fetch_naver_trends()
        save_to_json(keywords)
    except Exception as e:
        print(f"❌ 오류 발생: {e}")