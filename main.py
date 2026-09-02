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
        print(f"Discord Response Status: {res.status_code}")
    except Exception as e:
        print(f"Discord 발송 오류: {e}")


def check_jobs():
    target_keywords = ["전문군무", "전문경력", "경력경쟁"]

    tz_kst = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(tz_kst)
    yesterday_kst = now_kst - datetime.timedelta(days=1)
    target_date_str = yesterday_kst.strftime("%Y-%m-%d")

    base_url = "https://www.gojobs.go.kr/apmList.do"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.gojobs.go.kr/apmList.do?menuNo=401&mngrMenuYn=N&selMenuNo=400&upperMenuNo=&wd=1360",
    }

    params = {
        "menuNo": "401",
        "mngrMenuYn": "N",
        "selMenuNo": "400",
        "wd": "1360",
    }

    payload = {
        "pageIndex": "1",
        "menuNo": "401",
        "mngrMenuYn": "N",
        "selMenuNo": "400",
        "wd": "1360",
    }

    scraped_jobs = []
    matched_jobs = []

    try:
        res = requests.post(
            base_url, params=params, data=payload, headers=headers, timeout=10
        )
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

            href = title_elem.get("href", "")
            seq_match = re.search(r"\d+", href)
            seq = seq_match.group() if seq_match else ""
            link = (
                f"https://www.gojobs.go.kr/apmView.do?apmSeq={seq}&menuNo=401&mngrMenuYn=N&selMenuNo=400&upperMenuNo=&wd=1360"
                if seq
                else base_url
            )

            scraped_jobs.append(f"• {title} ({row_text[-10:] if len(row_text)>=10 else row_text})")

            # 키워드 및 어제 날짜 확인
            if any(kw in title for kw in target_keywords):
                if target_date_str in row_text:
                    matched_jobs.append({"title": title, "link": link})

    except Exception as e:
        print(f"Error: {e}")

    # 디스코드 전송 (매칭 결과가 없어도 무조건 보고서 메시지 전송)
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
            "title": "📢 [국방부 군무원] 신규 채용공고 등록 알림",
            "description": f"**기준 등록일:** `{target_date_str}`\n신규 공고가 감지되었습니다!",
            "color": 3447003,
            "fields": fields,
            "timestamp": now_kst.isoformat(),
        }
    else:
        sample_list = "\n".join(scraped_jobs[:5]) if scraped_jobs else "수집된 공고 없음"
        embed_data = {
            "title": "🔔 [국방부 군무원] 모니터링 실행 완료",
            "description": (
                f"**기준 등록일(어제):** `{target_date_str}`\n"
                f"**상태:** 조건 키워드(`전문군무`, `전문경력`, `경력경쟁`)에 맞는 신규 공고가 없습니다.\n\n"
                f"**현재 사이트 상위 공고 목록:**\n{sample_list}"
            ),
            "color": 15105570,
            "timestamp": now_kst.isoformat(),
        }

    send_discord(embed_data)


if __name__ == "__main__":
    check_jobs()
