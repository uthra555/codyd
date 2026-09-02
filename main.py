import datetime
import os
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
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
    # 필터 키워드 설정
    include_keywords = ["전문군무", "전문경력", "경력경쟁"]
    exclude_keyword = "합격자"

    # 한국 시간(KST) 기준 날짜 계산: 매일 오전 9시 실행 시 '어제 날짜' 추출
    tz_kst = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(tz_kst)
    yesterday_kst = now_kst - datetime.timedelta(days=1)
    target_date_str = yesterday_kst.strftime("%Y-%m-%d")

    target_url = "https://www.gojobs.go.kr/apmList.do?menuNo=401&mngrMenuYn=N&selMenuNo=400&upperMenuNo=&wd=1360"

    matched_jobs = []

    try:
        # Playwright를 사용하여 브라우저 렌더링 수집
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()

            page.goto("https://www.gojobs.go.kr/main.do", timeout=30000)
            page.goto(target_url, timeout=30000)
            page.wait_for_selector("table", timeout=15000)

            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")

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

            # 1. '어제 올라온 공고'인지 확인 (등록일 비교)
            if target_date_str not in row_text:
                continue

            # 2. 제외 키워드('합격자')가 포함되어 있으면 스킵
            if exclude_keyword in title:
                continue

            # 3. 포함 키워드('전문군무', '전문경력', '경력경쟁') 중 하나라도 포함 시 수집
            if any(kw in title for kw in include_keywords):
                href = title_elem.get("href", "")
                seq_match = re.search(r"\d+", href)
                seq = seq_match.group() if seq_match else ""

                link = (
                    f"https://www.gojobs.go.kr/apmView.do?apmSeq={seq}&menuNo=401&mngrMenuYn=N&selMenuNo=400&upperMenuNo=&wd=1360"
                    if seq
                    else target_url
                )

                if not any(j["title"] == title for j in matched_jobs):
                    matched_jobs.append(
                        {"title": title, "link": link, "date": target_date_str}
                    )

    except Exception as e:
        print(f"수집 중 오류 발생: {e}")

    # 어제 등록된 조건에 맞는 공고가 있을 때만 디스코드 알림 발송
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
            "title": "📢 [국방부 군무원] 어제 등록된 신규 채용공고 알림",
            "description": (
                f"**등록일:** `{target_date_str}`\n"
                "**포함 키워드:** `전문군무`, `전문경력`, `경력경쟁`\n"
                "**제외 키워드:** `합격자` 제외 완료\n\n"
                "조건에 부합하는 신규 공고가 감지되었습니다!"
            ),
            "color": 3447003,
            "fields": fields,
            "timestamp": now_kst.isoformat(),
        }
        send_discord(embed_data)
    else:
        print(
            f"[{target_date_str}] 어제 등록된 조건 부합 공고가 없어 알림을 전송하지 않았습니다."
        )


if __name__ == "__main__":
    check_jobs()
