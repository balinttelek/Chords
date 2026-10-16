import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import harness
from harness import serve, open_app
from playwright.sync_api import sync_playwright
problems = []
def check(c, m):
    print(("ok: " if c else "FAIL: ") + m)
    if not c: problems.append(m)
real = harness.make_db
def db2():
    d = real(); d["setlists"]["l1"]["data"]["songIds"] = list(d["songs"])[:15]; return d
harness.make_db = db2
srv = serve()
with sync_playwright() as p:
    b, page, errors, log, db = open_app(p, "light")
    page.locator('[data-act="openset"]').first.tap(); page.wait_for_timeout(600)
    ids0 = db["setlists"]["l1"]["data"]["songIds"]
    page.evaluate("window.scrollTo(0,document.body.scrollHeight)"); page.wait_for_timeout(300)
    last = page.locator(".srow").last
    last_title = last.locator(".t1").inner_text()
    g = last.locator(".grip").bounding_box()
    s = page.context.new_cdp_session(page)
    x, y = g["x"] + g["width"] / 2, g["y"] + g["height"] / 2
    T = lambda t, pts: s.send("Input.dispatchTouchEvent", {"type": t, "touchPoints": pts})
    T("touchStart", [{"x": x, "y": y}])
    steps = 20
    for i in range(1, steps + 1):
        page.wait_for_timeout(16); T("touchMove", [{"x": x, "y": y + (60 - y) * i / steps}])
    for _ in range(150):
        page.wait_for_timeout(16); T("touchMove", [{"x": x, "y": 60}])
    sy = page.evaluate("scrollY")
    check(sy < 5, "holding near the top scrolls the list up (scrollY %s)" % sy)
    T("touchMove", [{"x": x, "y": 200}]); page.wait_for_timeout(100)
    T("touchEnd", []); page.wait_for_timeout(2500)
    first = page.locator(".srow").first.locator(".t1").inner_text()
    check(first == last_title, "last song dragged to the top in one move (%s -> first: %s)" % (last_title, first))
    # and back down: first row to the bottom
    page.evaluate("window.scrollTo(0,0)"); page.wait_for_timeout(300)
    top = page.locator(".srow").first; tt = top.locator(".t1").inner_text(); g = top.locator(".grip").bounding_box()
    x, y = g["x"] + g["width"] / 2, g["y"] + g["height"] / 2
    T("touchStart", [{"x": x, "y": y}])
    for i in range(1, 21):
        page.wait_for_timeout(16); T("touchMove", [{"x": x, "y": y + (790 - y) * i / 20}])
    for _ in range(150):
        page.wait_for_timeout(16); T("touchMove", [{"x": x, "y": 790}])
    T("touchEnd", []); page.wait_for_timeout(2500)
    lastt = page.locator(".srow").last.locator(".t1").inner_text()
    check(lastt == tt, "first song dragged to the bottom in one move (%s -> last: %s)" % (tt, lastt))
    check(not errors, "no console errors %s" % errors)
    b.close()
srv.shutdown()
print("PROBLEMS:", json.dumps(problems, ensure_ascii=False))
