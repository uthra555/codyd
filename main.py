import datetime
import os
import re
import sys
from bs4 import BeautifulSoup
import requests


def send_discord(embed_data):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL이 설정되지 않았습니다.")
        return False

    payload = {
        "username": "국방부 채용 알림봇",
        "avatar_url": "https://www.gojobs.go.kr/images/common/logo.gif",
        "embeds": [embed_data],
    }

    try:
        res = requests.post(webhook_url, json=payload, timeout=10)
        print(f"Discord Response: {res.status_code}")
        return res.status_code in [200, 204]
    except Exception as e:
        print(f"Discord 전송 실패: {e}")
        return False


def check_jobs():
    target_keywords = ["전문군무", "전문경력", "경력경쟁"]

    # KST (한국 시간) 기준
    tz_kst = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(tz_kst)

    # 어제 날짜 (YYYY-MM-DD)
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

    print(f"--- 모니터링 시작 (기준 날짜: {target_date_str}) ---")

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

                # 키워드 검사
                if any(kw in title for kw in target_keywords):
                    # 어제 날짜 검사
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
            print(f"{page}페이지 수집 중 예외 발생: {e}")

    # 결과 전송
    if found_jobs:
        fields = [
            {
                "name": f"📌 {job['title']}",
                "value": f"[👉 해당 채용공고 바로가기]({job['link']})",
                "inline": False,
            }
            for job in found_jobs
        ]

        embed_data = {
            "title": "📢 [국방부 군무원] 신규 채용공고 알림",
            "description": f"**등록일:** `{target_date_str}`\n어제 등록된 신규 공고가 발견되었습니다!",
            "color": 3447003,
            "fields": fields,
            "footer": {"text": "국방부 군무원 채용관리 자동 모니터링"},
            "timestamp": now_kst.isoformat(),
        }
        send_discord(embed_data)
    else:
        print(f"[{target_date_str}] 조건에 맞는 공고가 없습니다.")
        # 공고가 없더라도 정상 작동 확인을 위해 테스트용 알림 전송 (필요시 아래 3줄 주석 처리 가능)
        embed_data = {
            "title": "✅ [국방부 군무원] 모니터링 정상 작동 중",
            "description": f"기준 날짜(`{target_date_str}`)에 새로 올라온 공고가 없습니다.",
            "color": 65280,
            "timestamp": now_kst.isoformat(),
        }
        send_discord(embed_data)


if __name__ == "__main__":
    try:
        check_jobs()
    except Exception as err:
        print(f"최종 에러 발생: {err}")
        sys.exit(0)  # 에러가 나더라도 GitHub Actions가 실패로 처리하지 않게 방지
