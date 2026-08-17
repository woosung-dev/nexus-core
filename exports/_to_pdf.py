# 로컬 HTTP 로 서빙 중인 HTML 보고서를 headless Chrome 으로 PDF 변환
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1]
OUT = sys.argv[2]

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(channel="chrome")
    except Exception:
        browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, wait_until="networkidle")
    page.wait_for_timeout(2500)  # Chart.js 렌더/애니메이션 완료 대기
    page.pdf(
        path=OUT,
        format="A4",
        print_background=True,
        margin={"top": "14mm", "bottom": "14mm", "left": "10mm", "right": "10mm"},
        scale=0.62,
    )
    browser.close()
print("PDF 저장:", OUT)
