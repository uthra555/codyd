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

    # 한국 표준시(KST, UTC+9) 기준 날짜 계산
    tz_kst = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(tz_kst)
    yesterday_kst = now_kst - datetime.timedelta(days=1)

    # 어제 날짜 (YYYY-MM-DD 포맷)
    target_date_str = yesterday_kst.strftime("%Y-%m-%d")

    found_jobs = []
    base_url = "https://www.gojobs.go.kr/apmList.do"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.gojobs.go.kr/apmList.do?menuNo=401&mngrMenuYn=N&selMenuNo=400&upperMenuNo=&wd=1360",
    }

    print(f"--- 탐색 시작 (기준 등록일: {target_date_str}) ---")

    # 1~10페이지 탐색
    for page in range(1, 11):
        # 전달해주신 URL의 파라미터와 폼 데이터를 정확하게 맞춤
        params = {
            "menuNo": "401",
            "mngrMenuYn": "N",
            "selMenuNo": "400",
            "wd": "1360",
        }

        payload = {
            "pageIndex": str(page),
            "menuNo": "401",
            "mngrMenuYn": "N",
            "selMenuNo": "400",
            "wd": "1360",
        }

        try:
            res = requests.post(
                base_url,
                params=params,
                data=payload,
                headers=headers,
                timeout=10,
            )
            soup = BeautifulSoup(res.text, "html.parser")

            # 테이블 내 모든 행(tr) 검색
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

                # 1. 제목에 키워드 포함 여부 검사
                if any(kw in title for kw in target_keywords):
                    # 2. 어제 날짜(YYYY-MM-DD) 매칭 검사
                    if target_date_str in row_text:
                        href = title_elem.get("href", "")
                        seq_match = re.search(r"\d+", href)

                        if seq_match:
                            seq = seq_match.group()
                            link = f"https://www.gojobs.go.kr/apmView.do?apmSeq={seq}&menuNo=401&mngrMenuYn=N&selMenuNo=400&upperMenuNo=&wd=1360"
                        else:
                            link = "https://www.gojobs.go.kr/apmList.do?menuNo=401&mngrMenuYn=N&selMenuNo=400&upperMenuNo=&wd=1360"

                        if not any(j["title"] == title for j in found_jobs):
                            found_jobs.append({"title": title, "link": link})
        except Exception as e:
            print(f"{page}페이지 파싱 중 예외 발생: {e}")

    # 신규 공고가 있는 경우에만 디스코드 발송
    if found_jobs:
        fields = [
            {
                "name": f"📌 {job['title']}",
                "value": f"[👉 채용공고 바로가기]({job['link']})",
                "inline": False,
            }
            for job in found_jobs
        ]

        embed_data = {
            "title": "📢 [국방부 군무원] 신규 채용공고 알림",
            "description": f"**등록일:** `{target_date_str}`\n조건에 부합하는 신규 공고가 등록되었습니다.",
            "color": 3447003,
            "fields": fields,
            "footer": {"text": "국방부 군무원 채용관리 자동 모니터링"},
            "timestamp": now_kst.isoformat(),
        }
        send_discord(embed_data)
        print(f"성공: {len(found_jobs)}건의 공고 알림 발송 완료")
    else:
        print(f"안내: [{target_date_str}] 자 신규 조건 공고가 없습니다.")


if __name__ == "__main__":
    check_jobs()
