import datetime
import os
import re
from bs4 import BeautifulSoup
import requests


def send_discord(embed_data):
    """디스코드 임베드(Embed) 형태로 예쁘게 전송하는 함수"""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("디스코드 웹훅 URL이 설정되지 않았습니다.")
        return

    payload = {
        "username": "국방부 채용 알림봇",
        "avatar_url": "https://www.gojobs.go.kr/images/common/logo.gif",  # 로고 이미지
        "embeds": [embed_data],
    }

    res = requests.post(webhook_url, json=payload)
    if res.status_code in [200, 204]:
        print("디스코드 메시지 전송 성공!")
    else:
        print(f"디스코드 전송 실패: {res.status_code}, {res.text}")


def check_jobs():
    target_keywords = ["전문군무", "전문경력", "경력경쟁"]

    # 한국 시간(KST) 기준 어제 날짜 구하기
    tz_kst = datetime.timezone(datetime.timedelta(hours=9))
    yesterday = datetime.datetime.now(tz_kst) - datetime.timedelta(days=1)
    yesterday_str1 = yesterday.strftime("%Y-%m-%d")
    yesterday_str2 = yesterday.strftime("%Y.%m.%d")

    found_jobs = []
    base_url = "https://www.gojobs.go.kr/apmList.do"

    print(f"수집 시작 (기준 어제 날짜: {yesterday_str1})")

    # 1페이지부터 10페이지까지 순회
    for page in range(1, 11):
        payload = {"pageIndex": str(page), "s_apmMenuSeq": "2"}
        try:
            res = requests.post(base_url, data=payload, timeout=10)
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

                # 키워드 검사 (전문군무 OR 전문경력)
                if any(kw in title for kw in target_keywords):
                    # 어제 날짜로 등록된 공고인지 확인
                    if (
                        yesterday_str1 in row_text
                        or yesterday_str2 in row_text
                    ):
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

    # 디스코드 임베드 카드 형태의 알림 작성
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
            "title": f"📢 [국방부 군무원] 신규 채용공고 알림",
            "description": f"**등록일:** `{yesterday_str1}`\n어제 등록된 조건('전문군무', '전문경력') 검색 결과입니다.",
            "color": 3447003,  # 디스코드 블루 컬러
            "fields": fields,
            "footer": {
                "text": "국방부 군무원 채용관리 자동 모니터링 시스템"
            },
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        send_discord(embed_data)
    else:
        print("조건에 맞는 어제자 신규 공고가 없습니다.")


if __name__ == "__main__":
    check_jobs()
