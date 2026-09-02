import datetime
import os
import re
from bs4 import BeautifulSoup
import requests


def send_discord(embed_data):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("디스코드 웹훅 URL이 설정되지 않았습니다.")
        return

    payload = {
        "username": "국방부 채용 알림봇",
        "avatar_url": "https://www.gojobs.go.kr/images/common/logo.gif",
        "embeds": [embed_data],
    }

    res = requests.post(webhook_url, json=payload)
    if res.status_code in [200, 204]:
        print("디스코드 메시지 전송 성공!")
    else:
        print(f"디스코드 전송 실패: {res.status_code}, {res.text}")


def check_jobs():
    # 감지 대상 키워드 (제목 중간 포함 시에도 검출)
    target_keywords = ["전문군무", "전문경력", "경력경쟁"]

    # 한국 표준시(KST, UTC+9) 설정
    tz_kst = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(tz_kst)

    # 어제 날짜 구하기 (YYYY-MM-DD 포맷: 예 '2026-09-01')
    yesterday_kst = now_kst - datetime.timedelta(days=1)
    target_date_str = yesterday_kst.strftime("%Y-%m-%d")

    found_jobs = []
    base_url = "https://www.gojobs.go.kr/apmList.do"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    print(
        f"수집 시작 (기준 어제 날짜: {target_date_str}, 키워드: {target_keywords})"
    )

    # 1페이지부터 10페이지까지 순회
    for page in range(1, 11):
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
                row_text = row.get_text()

                # 1. 키워드 포함 검사 (제목 중간 포함 가능)
                if any(kw in title for kw in target_keywords):
                    # 2. 어제 날짜(YYYY-MM-DD) 등록 여부 검사
                    if target_date_str in row_text:
                        href = title_elem.get("href", "")
                        seq_match = re.search(r"\d+", href)

                        if seq_match:
                            seq = seq_match.group()
                            link = f"https://www.gojobs.go.kr/apmView.do?apmSeq={seq}"
                        else:
                            link = base_url

                        found_jobs.append({"title": title, "link": link})
        except Exception as e:
            print(f"{page}페이지 수집 중 에러 발생: {e}")

    # 디스코드 임베드 알림 전송
    if found_jobs:
        fields = []
        for job in found_jobs:
            fields.append(
                {
                    "name": f"📌 {job['title']}",
                    "value": f"[👉 해당 채용공고 바로가기]({job['link']})",
                    "inline": False,
                }
            )

        embed_data = {
            "title": "📢 [국방부 군무원] 신규 채용공고 알림",
            "description": f"**등록일:** `{target_date_str}`\n어제 등록된 신규 공고 검색 결과입니다.",
            "color": 3447003,  # 블루 컬러
            "fields": fields,
            "footer": {"text": "국방부 군무원 채용관리 자동 모니터링"},
            "timestamp": now_kst.isoformat(),
        }
        send_discord(embed_data)
        print(f"총 {len(found_jobs)}건의 공고 알림 전송 완료!")
    else:
        print(f"{target_date_str} 날짜의 해당 키워드 공고가 없습니다.")


if __name__ == "__main__":
    check_jobs()
