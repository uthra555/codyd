import datetime
import os
import re
from bs4 import BeautifulSoup
import requests


def send_discord(embed_data):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL이 설정되지 않았습니다.")
        return

    payload = {
        "username": "국방부 채용 알림봇",
        "avatar_url": "https://www.gojobs.go.kr/images/common/logo.gif",
        "embeds": [embed_data],
    }

    try:
        res = requests.post(webhook_url, json=payload, timeout=10)
        print(f"Discord 전송 결과: {res.status_code}")
    except Exception as e:
        print(f"Discord 발송 오류: {e}")


def check_jobs():
    # 감시할 키워드 목록
    target_keywords = ["전문군무", "전문경력", "경력경쟁"]

    # 한국 시간(KST) 기준 날짜 설정
    tz_kst = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(tz_kst)
    yesterday_kst = now_kst - datetime.timedelta(days=1)
    target_date_str = yesterday_kst.strftime("%Y-%m-%d")

    target_url = "https://www.gojobs.go.kr/apmList.do?menuNo=401&mngrMenuYn=N&selMenuNo=400&upperMenuNo=&wd=1360"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.gojobs.go.kr/main.do",
    }

    matched_jobs = []

    try:
        res = requests.get(target_url, headers=headers, timeout=15)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            if len(cols) < 2:
                continue

            title_elem = row.find("a")
            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            row_text = " ".join([c.get_text(strip=True) for c in cols])

            # 키워드 포함 여부 및 작성일(어제) 확인
            if any(kw in title for kw in target_keywords):
                if target_date_str in row_text:
                    href = title_elem.get("href", "")
                    seq_match = re.search(r"\d+", href)
                    seq = seq_match.group() if seq_match else ""

                    link = (
                        f"https://www.gojobs.go.kr/apmView.do?apmSeq={seq}&menuNo=401&mngrMenuYn=N&selMenuNo=400&upperMenuNo=&wd=1360"
                        if seq
                        else target_url
                    )

                    if not any(j["title"] == title for j in matched_jobs):
                        matched_jobs.append({"title": title, "link": link})

    except Exception as e:
        print(f"수집 중 오류 발생: {e}")

    # 조건에 부합하는 신규 공고가 있을 때만 디스코드 발송
    if matched_jobs:
        fields = [
            {
                "name": f"📌 {job['title']}",
                "value": f"[👉 채용공고 바로가기]({job['link']})",
                "inline": False,
            }
            for job in matched_jobs
        ]
        embed_data = {
            "title": "📢 [국방부 군무원] 신규 채용공고 알림",
            "description": f"**등록일:** `{target_date_str}`\n설정한 조건에 부합하는 신규 공고가 등록되었습니다.",
            "color": 3447003,
            "fields": fields,
            "timestamp": now_kst.isoformat(),
        }
        send_discord(embed_data)
    else:
        print("신규 조건 공고가 없어 알림을 보내지 않았습니다.")


if __name__ == "__main__":
    check_jobs()
