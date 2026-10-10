import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, open_app
from playwright.sync_api import sync_playwright
problems = []
def check(c, m):
    print(("ok: " if c else "FAIL: ") + m)
    if not c: problems.append(m)
srv = serve()
with sync_playwright() as p:
    b, page, errors, log, db = open_app(p, "light")
    page.locator('[data-act="tab"][data-v="songs"]').tap(); page.wait_for_timeout(300)
    page.locator('#songList [data-act="opensong"]').first.tap(); page.wait_for_timeout(500)
    s = page.context.new_cdp_session(page)
    s.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 6, "y": 500}]})
    for i in range(1, 6):
        page.wait_for_timeout(20); s.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": 6 + i * 25, "y": 500}]})
    page.wait_for_timeout(100)
    shifted = page.evaluate("getComputedStyle(document.getElementById('app')).transform")
    check(shifted != "none", f"back-swipe moves the page ({shifted})")
    # leave the app mid-swipe: no touchend, the page is hidden and shown again
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    page.wait_for_timeout(200)
    t = page.evaluate("getComputedStyle(document.getElementById('app')).transform")
    check(t == "none" and page.locator(".under").count() == 0, f"after leaving mid-swipe the page is back in place ({t}, under={page.locator('.under').count()})")
    page.locator('[data-act="back"]').tap(); page.wait_for_timeout(500)
    check(page.evaluate("getComputedStyle(document.getElementById('app')).transform") == "none", "next screen is not shifted")
    check(not errors, f"no console errors {errors}")
    b.close()
srv.shutdown()
print("PROBLEMS:", problems)
