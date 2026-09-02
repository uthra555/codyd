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

    target_url = "https://www.gojobs.go.kr/apmList.do?menuNo=401&mngrMenuYn=N&selMenuNo=400&upperMenuNo=&wd=1360"

    # 세션 객체 생성 (쿠키 및 브라우저 환경 유지)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            ),
            "Referer": "https://www.gojobs.go.kr/main.do",
        }
    )

    scraped_jobs = []
    matched_jobs = []

    try:
        # 1차: 메인 페이지 접속으로 세션 쿠키 수집
        session.get("https://www.gojobs.go.kr/main.do", timeout=10)

        # 2차: 타깃 게시판 페이지 접속
        res = session.get(target_url, timeout=15)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        # 테이블 행 추출
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
                scraped_jobs.append(f"• {title}")

            # 키워드 및 날짜 확인
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
        print(f"수집 작업 중 에러 발생: {e}")

    # 디스코드 메시지 무조건 전송 (결과 유무 파악용)
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
            "description": f"**등록일:** `{target_date_str}`\n조건에 부합하는 신규 공고가 발견되었습니다!",
            "color": 3447003,
            "fields": fields,
            "timestamp": now_kst.isoformat(),
        }
    else:
        sample_list = (
            "\n".join(scraped_jobs[:5])
            if scraped_jobs
            else "공고 목록 수집 실패 (사이트 세션 차단 가능성)"
        )
        embed_data = {
            "title": "🔔 [국방부 군무원] 모니터링 실행 보고",
            "description": (
                f"**접속 주소:** `{target_url}`\n"
                f"**기준 등록일(어제):** `{target_date_str}`\n\n"
                f"**현재 게시판 상위 공고 목록 (최대 5개):**\n{sample_list}"
            ),
            "color": 65280,
            "timestamp": now_kst.isoformat(),
        }

    send_discord(embed_data)


if __name__ == "__main__":
    check_jobs()
