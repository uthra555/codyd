import datetime
import os
import re
from bs4 import BeautifulSoup
import requests


def send_discord(embed_data):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL 미설정")
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
    target_keywords = ["전문군무", "전문경력", "경력경쟁"]

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

    scraped_titles = []
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

            if title and len(title) > 2:
                scraped_titles.append(title)

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

    # 디스코드 메시지 전송
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
            "description": f"**등록일:** `{target_date_str}`\n설정한 조건에 부합하는 신규 공고가 감지되었습니다!",
            "color": 3447003,
            "fields": fields,
            "timestamp": now_kst.isoformat(),
        }
    else:
        sample_list = (
            "\n".join([f"• {t}" for t in scraped_titles[:5]])
            if scraped_titles
            else "공고 목록을 정상적으로 불러왔으나 표시할 항목이 없습니다."
        )
        embed_data = {
            "title": "🔔 [국방부 군무원] 일일 모니터링 정상 작동 보고",
            "description": (
                f"**조회 일자 기준(어제):** `{target_date_str}`\n"
                f"**상태:** 조건 키워드(`전문군무`, `전문경력`, `경력경쟁`)의 신규 등록 공고가 없습니다.\n\n"
                f"**현재 게시판 최신 공고 목록 (수집 정상 확인용):**\n{sample_list}"
            ),
            "color": 65280,
            "timestamp": now_kst.isoformat(),
        }

    send_discord(embed_data)


if __name__ == "__main__":
    check_jobs()
