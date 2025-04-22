import json
import requests
from bs4 import BeautifulSoup

def get_google_trends():
    url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=KR"
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, "xml")
    return [item.title.text for item in soup.find_all("item")]

def get_naver_trends():
    url = "https://datalab.naver.com/keyword/realtimeList.naver"
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, "html.parser")
    return [span.text.strip() for span in soup.select("span.item_title")]

def main():
    google = get_google_trends()
    naver = get_naver_trends()
    trends = list(set(google) & set(naver))[:10]

    with open("trends.json", "w", encoding="utf-8") as f:
        json.dump({"trends": trends}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
