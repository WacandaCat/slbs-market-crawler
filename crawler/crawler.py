# -*- coding: utf-8 -*-
"""
SLBS 캐릭터 마켓 레이더 - 네이버쇼핑 수집기
============================================
실행: run_crawler.bat 더블클릭 (또는 python crawler.py)

동작 순서
 1. Supabase에서 수집 키워드 목록(crawl_keywords)과 캐릭터 사전(character_dict)을 불러옴
 2. 키워드별로 네이버쇼핑 검색 결과를 페이지 순회하며 수집 (리뷰순)
 3. 별점/리뷰/구매/찜/등록일 파싱 → 판매개월수·point 계산 → 캐릭터 매칭
 4. 결과를 Supabase(crawl_runs, crawl_items)에 업로드
 5. 백업용 CSV도 로컬에 저장 (output/ 폴더, 엑셀에서 바로 열림)

기존 노트북 대비 수정 사항
 - pagingIndex 고정 버그 수정 (페이지가 실제로 넘어감)
 - 상품명 기준 중복 제거
 - 구매/찜 수의 쉼표(1,234) 파싱 처리
 - 등록일 없는 상품 안전 처리, 판매개월수 최소 1 (0 나눗셈 방지)
 - 캐릭터 매칭을 긴 단어부터 시도 (예: '곰돌이푸'가 '곰'보다 먼저 매칭)
 - pandas/numpy/openpyxl 의존성 제거. Windows 앱 제어 정책이 이 패키지들의
   컴파일된 DLL을 차단하는 경우가 있어, 백업을 표준 csv 모듈로 저장한다.
 - 네이버 차단 페이지를 감지하면 즉시 중단한다. 계속 요청하면 차단이 길어진다.
 - 페이지 간격을 랜덤하게 두어 요청 속도를 낮춘다.
 - 수집 회차 기록은 실제로 상품을 모은 뒤에 만든다 (빈 회차가 남지 않음)
"""

import csv
import os
import random
import re
import sys
import time
from datetime import datetime, date
from urllib.parse import quote

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By

try:
    import config
except ImportError:
    print("[오류] config.py 파일이 없습니다.")
    print("       config.example.py를 복사해서 config.py로 저장한 뒤")
    print("       Supabase 주소와 키를 채워 넣어 주세요.")
    sys.exit(1)

# ------------------------------------------------------------
# 설정
# ------------------------------------------------------------
ITEMS_PER_KEYWORD = getattr(config, "ITEMS_PER_KEYWORD", 500)  # 키워드당 목표 수집 개수
ITEMS_PER_PAGE = 20
SCROLL_DEPTH = 3                                    # 페이지당 스크롤 횟수 (지연 로딩 대응)
PAGE_WAIT = getattr(config, "PAGE_WAIT", (6, 11))   # 페이지 로드 후 대기(초) 최소~최대
SCROLL_WAIT = (2, 4)                                # 스크롤 후 대기(초) 최소~최대
BETWEEN_PAGES = getattr(config, "BETWEEN_PAGES", (4, 9))  # 다음 페이지로 넘어가기 전 추가 대기

# 네이버가 차단 페이지를 내려줄 때 나타나는 문구
BLOCK_MARKERS = (
    "접속이 일시적으로 제한",
    "비정상적인 접근",
    "쇼핑 서비스 접속이",
    "일시적으로 제한되었습니다",
)

SB_URL = config.SUPABASE_URL.rstrip("/")
SB_HEADERS = {
    "apikey": config.SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
}

FIELDS = [
    "crawled_at", "keyword", "product_name", "rating", "reviews", "purchases",
    "wishes", "reg_date", "months_on_sale", "point", "character_name",
]


class NaverBlocked(Exception):
    """네이버가 접속을 제한했을 때"""


def nap(span):
    time.sleep(random.uniform(*span))


# ------------------------------------------------------------
# Supabase 통신
# ------------------------------------------------------------
def sb_select(table, params=None):
    r = requests.get(f"{SB_URL}/rest/v1/{table}", headers=SB_HEADERS, params=params or {})
    r.raise_for_status()
    return r.json()


def sb_insert(table, rows, returning=False):
    headers = dict(SB_HEADERS)
    headers["Prefer"] = "return=representation" if returning else "return=minimal"
    r = requests.post(f"{SB_URL}/rest/v1/{table}", headers=headers, json=rows)
    r.raise_for_status()
    return r.json() if returning else None


def sb_update(table, match_params, patch):
    r = requests.patch(f"{SB_URL}/rest/v1/{table}", headers=SB_HEADERS,
                       params=match_params, json=patch)
    r.raise_for_status()


def load_keywords():
    rows = sb_select("crawl_keywords", {
        "select": "keyword",
        "is_active": "eq.true",
        "order": "sort_order.asc",
    })
    keywords = [r["keyword"] for r in rows]
    if not keywords:
        keywords = getattr(config, "FALLBACK_KEYWORDS", ["캐릭터 케이스"])
        print(f"[안내] DB에 활성 키워드가 없어 기본 키워드를 사용합니다: {keywords}")
    return keywords


def load_character_dict():
    rows = sb_select("character_dict", {"select": "token,character_name"})
    # 긴 토큰부터 매칭해야 '곰돌이푸'가 '곰'보다 먼저 잡힘
    return sorted(
        [(r["token"], r["character_name"]) for r in rows],
        key=lambda x: len(x[0]),
        reverse=True,
    )


# ------------------------------------------------------------
# 파싱 로직
# ------------------------------------------------------------
def parse_sales_info(info):
    """'판매정보' 텍스트에서 별점/리뷰/구매/찜/등록일을 추출"""
    rating = re.search(r"별점\n([\d.]+)", info)
    rating = float(rating.group(1)) if rating else None

    reviews = re.search(r"리뷰\n?\(?([\d,]+)\)?", info)
    reviews = int(reviews.group(1).replace(",", "")) if reviews else None

    purchases = re.search(r"구매\s*([\d,]+)", info)
    purchases = int(purchases.group(1).replace(",", "")) if purchases else 0

    wishes = re.search(r"찜\s*([\d,]+)", info)
    wishes = int(wishes.group(1).replace(",", "")) if wishes else 0

    reg = re.search(r"등록일\s*(\d{4}\.\d{2})", info)
    reg = reg.group(1) if reg else None

    return rating, reviews, purchases, wishes, reg


def months_since(reg_date_str):
    """등록일(YYYY.MM) 기준 판매개월수. 없거나 이번 달이면 최소 1."""
    if not reg_date_str:
        return None
    try:
        reg = datetime.strptime(reg_date_str, "%Y.%m")
    except ValueError:
        return None
    now = datetime.now()
    months = (now.year - reg.year) * 12 + (now.month - reg.month)
    return max(months, 1)


def match_character(product_name, char_dict_sorted):
    for token, name in char_dict_sorted:
        if token in product_name:
            return name
    return "기타"


# ------------------------------------------------------------
# 크롬 실행
# ------------------------------------------------------------
def make_driver():
    """
    셀레니움 4는 크롬드라이버를 스스로 내려받는다(Selenium Manager).
    실패할 때만 webdriver-manager로 한 번 더 시도한다.
    """
    try:
        return webdriver.Chrome()
    except Exception as e:
        print(f"[안내] 크롬 자동 실행 1차 시도 실패: {type(e).__name__}")
        try:
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            return webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        except Exception as e2:
            print("\n[오류] 크롬을 실행하지 못했습니다.")
            print(f"       원인: {type(e2).__name__}: {e2}")
            print("       크롬 브라우저가 설치되어 있는지 확인해 주세요.")
            sys.exit(1)


def page_text(driver):
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        return ""


def check_blocked(driver):
    text = page_text(driver)
    if any(m in text for m in BLOCK_MARKERS):
        raise NaverBlocked(text.strip()[:200])


# ------------------------------------------------------------
# 크롤링
# ------------------------------------------------------------
def crawl_keyword(driver, keyword, target_count):
    encoded = quote(keyword)
    total_pages = (target_count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    collected = []
    seen_names = set()

    for page in range(1, total_pages + 1):
        url = (
            "https://search.shopping.naver.com/search/all"
            f"?query={encoded}&pagingIndex={page}&pagingSize={ITEMS_PER_PAGE}"
            "&productSet=total&sort=review&viewType=list"
        )
        driver.get(url)
        nap(PAGE_WAIT)

        # 차단 페이지면 더 두드리지 말고 즉시 중단
        check_blocked(driver)

        for _ in range(SCROLL_DEPTH):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            nap(SCROLL_WAIT)

        page_found = 0
        misses = 0
        for i in range(1, ITEMS_PER_PAGE + 1):
            sel = (
                "#content > div.style_content__xWg5l > div.basicList_list_basis__uNBZx"
                f" > div > div:nth-child({i}) > div > div.product_info_area__xxCTi"
            )
            try:
                title = driver.find_element(
                    By.CSS_SELECTOR, f"{sel} > div.product_title__Mmw2K").text
                amt = driver.find_element(
                    By.CSS_SELECTOR, f"{sel} > div.product_etc_box__ElfVA").text
            except Exception:
                misses += 1
                continue

            if not title or title in seen_names:
                continue
            seen_names.add(title)
            collected.append((title, amt))
            page_found += 1

        if misses:
            print(f"  [{keyword}] {page}페이지: {misses}개 항목을 읽지 못했습니다.")
        print(f"  [{keyword}] {page}/{total_pages}페이지: 신규 {page_found}개 "
              f"(누적 {len(collected)}개)")

        # 첫 페이지부터 하나도 못 읽으면 차단이 아니라 구조 변경일 수 있다
        if page == 1 and page_found == 0:
            print(f"\n  [{keyword}] 첫 페이지에서 상품을 하나도 찾지 못했습니다.")
            print("  네이버 페이지 구조가 바뀌었을 수 있습니다.")
            print("  check_page.bat 을 실행해 구조를 조사해 주세요.")
            break
        if page_found == 0 and page > 1:
            print(f"  [{keyword}] 더 이상 새 상품이 없어 조기 종료합니다.")
            break
        if len(collected) >= target_count:
            break

        nap(BETWEEN_PAGES)

    return collected


def build_rows(keyword, raw_items, char_dict_sorted, run_id):
    today = date.today().isoformat()
    rows = []
    for title, amt in raw_items:
        rating, reviews, purchases, wishes, reg = parse_sales_info(amt)
        months = months_since(reg)
        point = None
        if reviews is not None and months:
            point = round(reviews / months, 4)
        rows.append({
            "run_id": run_id,
            "crawled_at": today,
            "keyword": keyword,
            "product_name": title,
            "rating": rating,
            "reviews": reviews,
            "purchases": purchases,
            "wishes": wishes,
            "reg_date": reg,
            "months_on_sale": months,
            "point": point,
            "character_name": match_character(title, char_dict_sorted),
        })
    return rows


def save_backup(rows):
    """엑셀에서 바로 열리는 CSV로 저장 (BOM 포함 UTF-8이라 한글이 깨지지 않음)"""
    os.makedirs("output", exist_ok=True)
    path = f"output/crawl_{datetime.now():%Y%m%d_%H%M}.csv"
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def print_blocked_notice(detail):
    print("\n" + "=" * 50)
    print("네이버가 접속을 일시적으로 제한했습니다.")
    print("=" * 50)
    print("수집을 중단합니다. 계속 시도하면 제한이 더 길어집니다.\n")
    print("  - 보통 몇 시간 뒤 자동으로 풀립니다. 시간을 두고 다시 실행해 주세요.")
    print("  - 다시 할 때는 config.py 의 ITEMS_PER_KEYWORD 를 100~200 정도로")
    print("    줄이면 요청이 적어져 제한에 걸릴 확률이 낮아집니다.")
    print("  - VPN을 쓰고 계시면 끄고 시도해 보세요.\n")
    if detail:
        print("네이버 안내 문구:")
        print("  " + detail.replace("\n", "\n  "))
    print("=" * 50)


# ------------------------------------------------------------
# 메인
# ------------------------------------------------------------
def main():
    print("=" * 50)
    print("SLBS 캐릭터 마켓 레이더 - 수집 시작")
    print("=" * 50)

    keywords = load_keywords()
    char_dict_sorted = load_character_dict()
    print(f"수집 키워드 {len(keywords)}개: {keywords}")
    print(f"캐릭터 사전 {len(char_dict_sorted)}개 토큰 로드 완료\n")

    driver = make_driver()
    harvest = []          # (키워드, 원본항목들)
    blocked = None
    try:
        for keyword in keywords:
            print(f"\n>> '{keyword}' 수집 중...")
            try:
                raw = crawl_keyword(driver, keyword, ITEMS_PER_KEYWORD)
            except NaverBlocked as e:
                blocked = str(e)
                break
            harvest.append((keyword, raw))
    finally:
        driver.quit()

    total_raw = sum(len(raw) for _, raw in harvest)

    if blocked and total_raw == 0:
        print_blocked_notice(blocked)
        sys.exit(1)

    if total_raw == 0:
        print("\n[경고] 수집된 상품이 없습니다.")
        print("       check_page.bat 을 실행해 페이지 구조를 조사해 주세요.")
        print("       (수집 회차는 기록하지 않았습니다)")
        sys.exit(1)

    if blocked:
        print("\n[안내] 중간에 접속 제한이 걸려 일부만 수집했습니다.")
        print(f"       지금까지 모은 {total_raw:,}건은 정상 저장합니다.")

    # 실제로 모은 게 있을 때만 수집 회차를 기록한다
    run = sb_insert("crawl_runs",
                    {"keywords": [k for k, _ in harvest], "item_count": 0},
                    returning=True)[0]
    run_id = run["id"]

    all_rows = []
    for keyword, raw in harvest:
        all_rows.extend(build_rows(keyword, raw, char_dict_sorted, run_id))

    print(f"\n총 {len(all_rows):,}건 업로드 중...")
    for i in range(0, len(all_rows), 500):
        sb_insert("crawl_items", all_rows[i:i + 500])
    sb_update("crawl_runs", {"id": f"eq.{run_id}"}, {"item_count": len(all_rows)})

    backup = save_backup(all_rows)

    classified = sum(1 for r in all_rows if r["character_name"] != "기타")
    print("\n" + "=" * 50)
    print("수집 완료")
    print(f"  - 총 상품 수: {len(all_rows):,}건")
    print(f"  - 캐릭터 분류: {classified:,}건 / 미분류 {len(all_rows) - classified:,}건")
    print(f"  - 로컬 백업: {backup}")
    print("  - 대시보드에서 바로 확인할 수 있습니다.")
    print("=" * 50)

    if blocked:
        print_blocked_notice(blocked)


if __name__ == "__main__":
    main()
