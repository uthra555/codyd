import datetime
import os
import re
from bs4 import BeautifulSoup
import requests


def send_discord(content_text, embed_data=None):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    # Webhook URL이 없을 경우 로그 출력
    if not webhook_url:
        print(
            "CRITICAL ERROR: DISCORD_WEBHOOK_URL이 Settings Secrets에 설정되지 않았습니다."
        )
        return False

    payload = {"username": "국방부 채용 알림봇", "content": content_text}
    if embed_data:
        payload["embeds"] = [embed_data]

    try:
        res = requests.post(webhook_url, json=payload, timeout=10)
        print(f"Discord API 응답 코드: {res.status_code}")
        return res.status_code in [200, 204]
    except Exception as e:
        print(f"Discord 전송 실패 예외: {e}")
        return False


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
    error_log = ""

    try:
        # 직접 요청 진행
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
        error_log = f"사이트 접속 중 오류 발생: {e}"

    # 디스코드 무조건 발송 처리
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
            "description": f"**등록일:** `{target_date_str}`\n조건에 부합하는 신규 공고가 감지되었습니다!",
            "color": 3447003,
            "fields": fields,
            "timestamp": now_kst.isoformat(),
        }
        send_discord("✅ **신규 공고 수신 성공!**", embed_data)
    else:
        sample_list = (
            "\n".join([f"• {t}" for t in scraped_titles[:5]])
            if scraped_titles
            else "공고 목록 수집 불가"
        )
        if error_log:
            sample_list += f"\n\n⚠️ {error_log}"

        embed_data = {
            "title": "🔔 [국방부 군무원] 모니터링 실행 보고",
            "description": (
                f"**기준 등록일(어제):** `{target_date_str}`\n\n"
                f"**현재 게시판 상위 공고 제목 (최대 5개):**\n{sample_list}"
            ),
            "color": 65280,
            "timestamp": now_kst.isoformat(),
        }
        send_discord("ℹ️ **모니터링 실행 결과**", embed_data)


if __name__ == "__main__":
    check_jobs()
