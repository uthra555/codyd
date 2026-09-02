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
    target_keywords = ["전문군무", "전문경력", "경력경쟁"]

    # 한국 시간(KST) 기준 날짜 구하기
    tz_kst = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(tz_kst)
    yesterday = now - datetime.timedelta(days=1)

    # 다양한 날짜 포맷 대응 (2026-09-01, 2026.09.01, 09-01, 09.01 등)
    date_patterns = [
        yesterday.strftime("%Y-%m-%d"),
        yesterday.strftime("%Y.%m.%d"),
        yesterday.strftime("%m-%d"),
        yesterday.strftime("%m.%d"),
    ]

    found_jobs = []
    base_url = "https://www.gojobs.go.kr/apmList.do"

    # User-Agent 설정 (브라우저 접근으로 위장)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    print(
        f"수집 시작 (기준 어제 날짜 패턴: {date_patterns}, 키워드: {target_keywords})"
    )

    for page in range(1, 11):
        payload = {"pageIndex": str(page), "s_apmMenuSeq": "2"}
        try:
            res = requests.post(
                base_url, data=payload, headers=headers, timeout=10
            )
            soup = BeautifulSoup(res.text, "html.parser")

            rows = soup.select("table tbody tr")
            for row in rows:
                row_text = row.get_text()

                # 제목 요소 찾기
                title_elem = row.select_one("a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)

                # 1. 키워드 검사
                if any(kw in title for kw in target_keywords):
                    # 2. 날짜 검사 (행 전체 텍스트에 어제 날짜 패턴이 있는지)
                    if any(dp in row_text for dp in date_patterns):
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

    # 결과 전송 (공고가 없더라도 테스트 확인용 메시지를 디스코드로 발송)
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
            "description": f"**기준 날짜:** `{date_patterns[0]}`\n조건에 맞는 신규 공고를 찾았습니다!",
            "color": 3447003,
            "fields": fields,
            "footer": {"text": "국방부 군무원 채용관리 자동 모니터링"},
            "timestamp": now.isoformat(),
        }
    else:
        # 공고가 없을 때도 디스코드 연결 테스트 겸 확인 알림을 보냅니다.
        embed_data = {
            "title": "🔍 [국방부 군무원] 모니터링 정기 점검",
            "description": (
                f"**점검 시각:** `{now.strftime('%Y-%m-%d %H:%M:%S')}`\n"
                f"사이트 탐색을 완료했으나 어제 날짜(`{date_patterns[0]}`) 기준 "
                f"키워드(`{', '.join(target_keywords)}`)에 매칭되는 신규 공고가 없습니다."
            ),
            "color": 15105570,  # 주황색
            "footer": {"text": "정상 작동 중"},
            "timestamp": now.isoformat(),
        }

    send_discord(embed_data)


if __name__ == "__main__":
    check_jobs()
