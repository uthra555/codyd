import datetime
import os
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import requests


MAX_ATTEMPTS = 3


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


def send_error_alert(error_message):
    embed_data = {
        "title": "⚠️ [국방부 군무원] 채용공고 수집 실패",
        "description": (
            f"{MAX_ATTEMPTS}회 시도했지만 채용공고 페이지를 불러오지 못했습니다.\n"
            "사이트 접속 문제일 수 있으니 확인이 필요합니다.\n\n"
            f"**오류 내용:**\n```{error_message}```"
        ),
        "color": 15158332,
        "timestamp": datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=9))
        ).isoformat(),
    }
    send_discord(embed_data)


def extract_rows(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for row in soup.find_all("tr"):
        cols = row.find_all(["td", "th"])
        if len(cols) < 2:
            continue
        title_elem = row.find("a")
        if not title_elem:
            continue
        title = title_elem.get_text(strip=True)
        row_text = " ".join([c.get_text(strip=True) for c in cols])
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", row_text)
        reg_date = date_match.group() if date_match else None
        rows.append(
            {
                "title": title,
                "row_text": row_text,
                "reg_date": reg_date,
                "href": title_elem.get("href", ""),
            }
        )
    return rows


def fetch_job_rows(target_url, oldest_target_date, max_pages):
    """페이지 1부터 순회하며 행을 모은다. 등록일이 오래된 페이지가 나오면 조기 종료."""
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            all_rows = []
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

                page.goto(
                    "https://www.gojobs.go.kr/main.do",
                    timeout=60000,
                    wait_until="domcontentloaded",
                )
                page.goto(target_url, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_selector("table", timeout=30000)

                for page_num in range(1, max_pages + 1):
                    if page_num > 1:
                        with page.expect_navigation(timeout=30000):
                            page.evaluate(f"fn_egov_link_page({page_num})")
                        page.wait_for_selector("table", timeout=30000)

                    rows = extract_rows(page.content())
                    if not rows:
                        break
                    all_rows.extend(rows)

                    oldest_on_page = min(
                        (r["reg_date"] for r in rows if r["reg_date"]), default=None
                    )
                    if oldest_on_page and oldest_on_page < oldest_target_date:
                        # 등록일 내림차순 정렬이므로 다음 페이지는 전부 더 오래됨
                        break

                browser.close()

            return all_rows
        except Exception as e:
            last_error = e
            print(f"[시도 {attempt}/{MAX_ATTEMPTS}] 페이지 로딩 실패: {e}")

    raise RuntimeError(str(last_error))


def check_jobs():
    # 필터 키워드 설정
    include_keywords = ["전문군무", "전문경력", "경력경쟁"]
    exclude_keyword = "합격자"

    # 한국 시간(KST) 기준 날짜 계산: 매일 오전 9시 실행 시 '어제 날짜' 추출
    # LOOKBACK_DAYS(기본 1)로 조회 기간을 늘릴 수 있음 (테스트/수동 실행용)
    tz_kst = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(tz_kst)
    lookback_days = int(os.environ.get("LOOKBACK_DAYS", "1") or "1")
    start_offset_days = int(os.environ.get("START_OFFSET_DAYS", "1") or "1")
    target_dates = [
        (now_kst - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(start_offset_days, start_offset_days + lookback_days)
    ]
    oldest_target_date = target_dates[-1]
    date_range_label = (
        target_dates[0] if lookback_days == 1 else f"{target_dates[-1]} ~ {target_dates[0]}"
    )

    # 조회 기간이 며칠 안 되면 페이지도 조금만, 길면 조금 더 넉넉히 순회 (성능/안전 상한)
    max_pages = min(30, lookback_days * 3 + 2)

    target_url = "https://www.gojobs.go.kr/apmList.do?menuNo=401&mngrMenuYn=N&selMenuNo=400&upperMenuNo=&wd=1360"

    matched_jobs = []

    try:
        rows = fetch_job_rows(target_url, oldest_target_date, max_pages)
    except Exception as e:
        print(f"수집 중 오류 발생: {e}")
        send_error_alert(str(e))
        return

    print(f"총 {len(rows)}개 공고 행 수집 완료 (최대 {max_pages}페이지 순회)")

    for row in rows:
        title = row["title"]
        row_text = row["row_text"]

        # 1. 조회 대상 기간(target_dates)에 올라온 공고인지 확인 (등록일 비교)
        matched_date = next((d for d in target_dates if d in row_text), None)
        if matched_date is None:
            continue

        # 2. 제외 키워드('합격자')가 포함되어 있으면 스킵
        if exclude_keyword in title:
            continue

        # 3. 포함 키워드('전문군무', '전문경력', '경력경쟁') 중 하나라도 포함 시 수집
        if any(kw in title for kw in include_keywords):
            href = row["href"]
            seq_matches = re.findall(r"\d+", href)
            seq = seq_matches[-1] if seq_matches else ""

            link = (
                f"https://www.gojobs.go.kr/apmView.do?apmSeq={seq}&menuNo=401&mngrMenuYn=N&selMenuNo=400&upperMenuNo=&wd=1360"
                if seq
                else target_url
            )

            if not any(j["title"] == title for j in matched_jobs):
                matched_jobs.append(
                    {"title": title, "link": link, "date": matched_date}
                )

    # 조건에 맞는 공고가 있을 때만 디스코드 알림 발송
    if matched_jobs:
        fields = [
            {
                "name": f"📌 {job['title']}",
                "value": f"[👉 채용공고 바로가기]({job['link']}) (등록일: {job['date']})",
                "inline": False,
            }
            for job in matched_jobs
        ]
        embed_data = {
            "title": "📢 [국방부 군무원] 신규 채용공고 알림",
            "description": (
                f"**조회 기간:** `{date_range_label}`\n"
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
            f"[{date_range_label}] 조건 부합 공고가 없어 알림을 전송하지 않았습니다."
        )


if __name__ == "__main__":
    check_jobs()
