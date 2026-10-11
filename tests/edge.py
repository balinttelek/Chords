import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, open_app
from playwright.sync_api import sync_playwright
problems = []
def check(c, m):
    print(("ok: " if c else "FAIL: ") + m)
    if not c: problems.append(m)
srv = serve()
with sync_playwright() as p:
    b, page, errors, log, db = open_app(p, "dark")
    s = page.context.new_cdp_session(page)
    T = lambda typ, pts: s.send("Input.dispatchTouchEvent", {"type": typ, "touchPoints": pts})
    page.locator('[data-act="openset"]').first.tap(); page.wait_for_timeout(600)
    cta0 = page.locator(".cta").bounding_box()["y"]
    # edge touchstart must be cancelled (that is what stops iOS's own back swipe)
    page.evaluate("window.__dp=null;document.addEventListener('touchstart',e=>{setTimeout(()=>window.__dp=e.defaultPrevented)},{capture:false})")
    T("touchStart", [{"x": 6, "y": 500}])
    for i in range(1, 8):
        page.wait_for_timeout(16); T("touchMove", [{"x": 6 + i * 20, "y": 500}])
    page.wait_for_timeout(50)
    check(page.evaluate("window.__dp") is True, "edge touchstart is cancelled")
    cta1 = page.locator(".cta").bounding_box()["y"]
    ov = page.evaluate("document.documentElement.scrollWidth-innerWidth")
    check(ov <= 0, "page does not get wider mid-swipe (iOS would zoom out) (%s)" % ov)
    check(abs(cta1 - cta0) < 1, "Indítás stays at the same height mid-swipe (%s -> %s)" % (cta0, cta1))
    page.screenshot(path=os.path.dirname(__file__) + "/shots/edge-mid.png")
    for i in range(8, 16):
        page.wait_for_timeout(16); T("touchMove", [{"x": 6 + i * 20, "y": 500}])
    T("touchEnd", []); page.wait_for_timeout(700)
    check(page.locator(".glist.sets").count() == 1 and page.locator(".under").count() == 0, "edge swipe goes back to Setlistek")
    check(page.evaluate("[...document.querySelectorAll('[data-pin]')].length") == 0, "pins are cleared")
    # edge tap still taps
    page.locator('[data-act="openset"]').first.tap(); page.wait_for_timeout(600)
    page.evaluate("window.__clk=0;document.addEventListener('click',()=>window.__clk++)")
    T("touchStart", [{"x": 10, "y": 300}]); T("touchEnd", []); page.wait_for_timeout(300)
    check(page.evaluate("window.__clk") == 1, "a tap at the very edge still delivers one click")
    page.go_back(); page.wait_for_timeout(500)
    # edge vertical drag still scrolls a long page
    page.locator('[data-act="tab"][data-v="songs"]').tap(); page.wait_for_timeout(300)
    page.locator('#songList [data-act="opensong"]').first.tap(); page.wait_for_timeout(400)
    page.locator('[data-act="edit"]').tap(); page.wait_for_timeout(400)
    page.evaluate("window.scrollTo(0,0)")
    T("touchStart", [{"x": 8, "y": 700}])
    for i in range(1, 12):
        page.wait_for_timeout(16); T("touchMove", [{"x": 8, "y": 700 - i * 25}])
    T("touchEnd", []); page.wait_for_timeout(300)
    check(page.evaluate("scrollY") > 100, "a vertical drag from the edge still scrolls (%s)" % page.evaluate("scrollY"))
    check(not errors, "no console errors %s" % errors)
    b.close()
srv.shutdown()
print("PROBLEMS:", json.dumps(problems, ensure_ascii=False))
