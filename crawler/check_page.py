# -*- coding: utf-8 -*-
"""
네이버쇼핑 페이지 구조 진단기
==============================
수집이 0건일 때 실행한다. 실제 페이지를 열어 구조를 조사하고
같은 폴더에 page_report.json 을 남긴다. 그 파일을 보고 선택자를 고친다.

실행: check_page.bat 더블클릭
"""

import json
import re
import sys
import time
from collections import Counter
from urllib.parse import quote

from selenium import webdriver
from selenium.webdriver.common.by import By

KEYWORD = "캐릭터 케이스"
URL = (
    "https://search.shopping.naver.com/search/all"
    f"?query={quote(KEYWORD)}&pagingIndex=1&pagingSize=20"
    "&productSet=total&sort=review&viewType=list"
)

# 상품 카드를 찾을 때 시도해 볼 후보들. 해시가 붙는 클래스명이라 부분일치로 찾는다.
CANDIDATES = [
    "div[class*='product_info_area']",
    "div[class*='product_title']",
    "div[class*='product_etc']",
    "div[class*='basicList_list_basis']",
    "div[class*='basicList_item']",
    "li[class*='basicList_item']",
    "div[class*='adProduct_info']",
    "div[class*='product_item']",
    "li[class*='product_item']",
    "a[class*='product_link']",
    "div[class*='superSavingProduct']",
    "[data-shp-contents-type='chnl_prod']",
    "#composite-card-list",
    "#content",
]


def make_driver():
    try:
        return webdriver.Chrome()
    except Exception:
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()))


def class_prefix_census(html):
    """'product_title__aBc12' 같은 클래스에서 해시 앞부분만 세어 컴포넌트 이름을 찾는다."""
    tokens = []
    for chunk in re.findall(r'class="([^"]*)"', html):
        tokens.extend(chunk.split())
    counter = Counter()
    for t in tokens:
        m = re.match(r"^([A-Za-z][\w]*?)__[\w-]+$", t)
        if m:
            counter[m.group(1)] += 1
    return counter.most_common(60)


def find_embedded_json(html):
    """__NEXT_DATA__ 등 페이지에 박힌 JSON에서 상품 배열이 있는 경로를 찾는다."""
    out = {}
    m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    out["has_next_data"] = bool(m)
    if not m:
        return out
    try:
        data = json.loads(m.group(1))
    except Exception as e:
        out["parse_error"] = f"{type(e).__name__}: {e}"
        return out

    hits = []
    marker_keys = {"reviewCount", "productTitle", "purchaseCnt", "keepCnt", "openDate"}

    def walk(node, path, depth):
        if len(hits) >= 6 or depth > 12:
            return
        if isinstance(node, dict):
            keys = set(node.keys())
            if marker_keys & keys:
                hits.append({"path": path, "keys": sorted(keys)[:45]})
                return
            for k, v in node.items():
                walk(v, f"{path}.{k}", depth + 1)
        elif isinstance(node, list):
            for i, v in enumerate(node[:2]):
                walk(v, f"{path}[{i}]", depth + 1)

    walk(data, "$", 0)
    out["product_like_paths"] = hits
    return out


def main():
    print("네이버쇼핑 페이지를 열어 구조를 조사합니다. 크롬 창을 닫지 마세요.\n")
    driver = make_driver()
    report = {"requested_url": URL}
    try:
        driver.get(URL)
        time.sleep(8)
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)

        html = driver.page_source
        report["final_url"] = driver.current_url
        report["page_title"] = driver.title
        report["html_length"] = len(html)

        try:
            body = driver.find_element(By.TAG_NAME, "body").text
            report["body_text_head"] = body[:1200]
            report["body_text_length"] = len(body)
        except Exception as e:
            report["body_text_error"] = f"{type(e).__name__}: {e}"

        report["class_prefixes"] = class_prefix_census(html)
        report["embedded_json"] = find_embedded_json(html)

        counts = {}
        for sel in CANDIDATES:
            try:
                counts[sel] = len(driver.find_elements(By.CSS_SELECTOR, sel))
            except Exception:
                counts[sel] = -1
        report["selector_counts"] = counts

        # 상품 카드로 보이는 요소 하나의 실제 HTML을 떠서 남긴다
        samples = []
        for sel in ["div[class*='product_title']", "a[class*='product_link']",
                    "div[class*='product_info_area']", "div[class*='basicList_item']"]:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if not els:
                continue
            el = els[0]
            try:
                card = driver.execute_script(
                    "var e=arguments[0];for(var i=0;i<4&&e.parentElement;i++)e=e.parentElement;return e.outerHTML;",
                    el)
            except Exception:
                card = el.get_attribute("outerHTML")
            samples.append({"matched_selector": sel, "outer_html": (card or "")[:6000]})
            break
        report["sample_cards"] = samples

    except Exception as e:
        report["fatal_error"] = f"{type(e).__name__}: {e}"
    finally:
        driver.quit()

    with open("page_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    print("=" * 50)
    print("조사 완료 — page_report.json 을 만들었습니다.")
    print(f"  페이지 제목: {report.get('page_title')}")
    print(f"  최종 주소  : {report.get('final_url')}")
    hits = {k: v for k, v in report.get("selector_counts", {}).items() if v > 0}
    print(f"  찾은 요소  : {hits if hits else '없음'}")
    print("\n이 창을 닫고, Claude 에게 '진단 끝났어' 라고 알려주세요.")
    print("=" * 50)


if __name__ == "__main__":
    main()
