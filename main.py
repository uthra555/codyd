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
        "username": "국방부 채용 진단봇",
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

    scraped_rows = []

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

            row_text = " | ".join([c.get_text(strip=True) for c in cols])
            if len(row_text) > 5:
                scraped_rows.append(row_text)

    except Exception as e:
        scraped_rows.append(f"수집 에러: {e}")

    # 디스코드 보고서 생성 (상위 7개 항목 출력)
    preview_text = "\n".join([f"• `{r}`" for r in scraped_rows[:7]])

    embed_data = {
        "title": "🔍 [진단 알림] 1페이지 파싱 결과 확인",
        "description": (
            f"**오늘 날짜(KST):** `{now_kst.strftime('%Y-%m-%d')}`\n"
            f"**어제 날짜(KST):** `{target_date_str}`\n\n"
            f"**사이트에서 실제 읽어온 공고 목록 (상위 7개):**\n{preview_text}"
        ),
        "color": 3447003,
        "timestamp": now_kst.isoformat(),
    }

    send_discord(embed_data)


if __name__ == "__main__":
    check_jobs()
