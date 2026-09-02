import datetime
import os
import re
from bs4 import BeautifulSoup
import requests


def send_discord(embed_data):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return

    payload = {
        "username": "국방부 채용 알림봇",
        "avatar_url": "https://www.gojobs.go.kr/images/common/logo.gif",
        "embeds": [embed_data],
    }
    requests.post(webhook_url, json=payload)


def check_jobs():
    target_keywords = ["전문군무", "전문경력", "경력경쟁"]

    tz_kst = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(tz_kst)
    yesterday_kst = now_kst - datetime.timedelta(days=1)

    # 파악 가능한 여러 날짜 형태 준비
    date_format_1 = yesterday_kst.strftime("%Y-%m-%d")  # 2026-09-01
    date_format_2 = yesterday_kst.strftime("%Y.%m.%d")  # 2026.09.01
    date_format_3 = yesterday_kst.strftime("%m-%d")  # 09-01

    base_url = "https://www.gojobs.go.kr/apmList.do"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    recent_samples = []
    matched_jobs = []

    for page in range(1, 4):
        payload = {"pageIndex": str(page), "s_apmMenuSeq": "2"}
        try:
            res = requests.post(
                base_url, data=payload, headers=headers, timeout=10
            )
            soup = BeautifulSoup(res.text, "html.parser")

            rows = soup.select("table tbody tr")
            for row in rows:
                cols = row.select("td")
                if len(cols) < 2:
                    continue

                title_elem = row.select_one("a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                full_row_str = " | ".join(
                    [c.get_text(strip=True) for c in cols]
                )

                # 상위 5개 공고 원본 형태 기록
                if len(recent_samples) < 5:
                    recent_samples.append(full_row_str)

                # 키워드 확인
                if any(kw in title for kw in target_keywords):
                    # 날짜 형식 중 하나라도 걸리는지 확인
                    if any(
                        df in full_row_str
                        for df in [date_format_1, date_format_2, date_format_3]
                    ):
                        href = title_elem.get("href", "")
                        seq_match = re.search(r"\d+", href)
                        seq = seq_match.group() if seq_match else ""
                        link = (
                            f"https://www.gojobs.go.kr/apmView.do?apmSeq={seq}"
                            if seq
                            else base_url
                        )
                        matched_jobs.append({"title": title, "link": link})
        except Exception as e:
            print(f"Error: {e}")

    # 디스코드 보고서 작성
    if matched_jobs:
        fields = [
            {
                "name": f"📌 {j['title']}",
                "value": f"[👉 바로가기]({j['link']})",
                "inline": False,
            }
            for j in matched_jobs
        ]
        embed_data = {
            "title": "🎉 [국방부 군무원] 신규 공고를 찾았습니다!",
            "description": f"**기준 날짜:** `{date_format_1}`",
            "color": 3066993,
            "fields": fields,
        }
    else:
        sample_text = "\n".join([f"• `{s}`" for s in recent_samples])
        embed_data = {
            "title": "🔍 [진단 결과] 매칭된 공고가 없습니다.",
            "description": (
                f"**프로그램이 계산한 어제 날짜:** `{date_format_1}`\n\n"
                f"**실제 웹사이트에서 읽어온 상위 공고 목록:**\n{sample_text}\n\n"
                "위 목록의 날짜 표기와 어제 날짜가 일치하는지 확인해 주세요!"
            ),
            "color": 15105570,
        }

    send_discord(embed_data)


if __name__ == "__main__":
    check_jobs()
