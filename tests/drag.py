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
    # give a setlist song a long title so truncation matters
    page.locator('[data-act="openset"]').first.tap(); page.wait_for_timeout(600)
    page.locator('[data-act="picker"]').tap(); page.wait_for_timeout(400)
    page.fill("#pq", "bemegyek"); page.wait_for_timeout(300)
    page.locator('#pickList [data-act="pick"]').first.tap(); page.wait_for_timeout(300)
    page.go_back(); page.wait_for_timeout(500)
    rows = page.locator(".srow")
    LONG = rows.count() - 1
    w0 = [rows.nth(i).bounding_box()["width"] for i in range(rows.count())]
    g = page.locator(".srow .grip").nth(LONG).bounding_box()
    s = page.context.new_cdp_session(page)
    x, y = g["x"] + g["width"] / 2, g["y"] + g["height"] / 2
    s.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    for i in range(1, 8):
        page.wait_for_timeout(30); s.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y + i * 6}]})
    page.wait_for_timeout(100)
    dragging = page.locator(".srow.dragging")
    check(dragging.count() == 1, "grip drag lifts the row")
    wd = dragging.bounding_box()["width"] if dragging.count() else 0
    check(abs(wd - w0[LONG]) < 1, f"lifted row keeps its width ({w0[LONG]} -> {wd})")
    page.screenshot(path=os.path.join(os.path.dirname(__file__), "shots", "drag.png"))
    s.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []}); page.wait_for_timeout(500)
    check(not errors, "no console errors")
    b.close()
srv.shutdown()
print("PROBLEMS:", problems)
