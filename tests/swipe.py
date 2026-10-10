import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, open_app
from playwright.sync_api import sync_playwright
def touch_drag(page, x0, y0, x1, y1, steps=12, dt=16):
    s = page.context.new_cdp_session(page)
    s.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0}]})
    for i in range(1, steps + 1):
        page.wait_for_timeout(dt)
        s.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + (x1 - x0) * i / steps, "y": y0 + (y1 - y0) * i / steps}]})
    s.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
srv = serve()
with sync_playwright() as p:
    b, page, errors, log, db = open_app(p, "light")
    page.locator('[data-act="openset"]').first.tap(); page.wait_for_timeout(600)
    n0 = page.locator(".srow").count()
    r = page.locator(".srow").first.bounding_box(); y = r["y"] + r["height"] / 2
    touch_drag(page, r["x"] + r["width"] - 60, y, r["x"] + r["width"] - 340, y)
    page.wait_for_timeout(900)
    print("swipe remove:", n0, "->", page.locator(".srow").count())
    # stage: swipe from the very left edge to previous song, and right-to-left to next
    page.locator('.cta[data-act="playfrom"]').tap(); page.wait_for_timeout(1500)
    import re
    I = lambda: re.search(r"(\d+)/\d+", page.inner_text(".st-top")).group(1)
    print("stage start", I())
    touch_drag(page, 380, 500, 80, 500); page.wait_for_timeout(900); print("after swipe left (next):", I(), "stage open:", page.locator("#stage").count())
    touch_drag(page, 4, 500, 330, 500); page.wait_for_timeout(900); print("after edge swipe right (prev):", I(), "stage open:", page.locator("#stage").count())
    touch_drag(page, 8, 520, 9, 520, steps=1); page.wait_for_timeout(900); print("edge tap on first song:", I(), "stage open:", page.locator("#stage").count())
    print("errors", errors)
    b.close()
srv.shutdown()
