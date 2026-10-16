import sys, os, json, re
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
    d = real(); d["songs"]["mts"] = {"id": "mts", "data": {"title": "Mighty to Save", "artist": "", "key": "A", "bpm": "", "notes": "", "body": ""}, "updated_at": harness.now(), "deleted": False}
    d["setlists"]["l1"]["data"]["songIds"].insert(1, "mts"); return d
harness.make_db = db2
srv = serve()
with sync_playwright() as p:
    b, page, errors, log, db = open_app(p, "light")
    page.evaluate("navigator.clipboard.readText=async()=>'Mighty to Save\\nVerse: 1 5 6 4\\nChorus: 4 1 5 6'")
    page.locator('[data-act="openset"]').first.tap(); page.wait_for_timeout(500)
    page.locator('.cta[data-act="playfrom"]').tap(); page.wait_for_timeout(1200)
    page.locator('.st-zone[data-act="next"]').tap(); page.wait_for_timeout(900)
    top = page.inner_text(".st-top")
    check("Mighty" in top and page.locator(".st-add").count() == 1, "empty song on stage offers Kotta hozzáadása (%s)" % top.replace("\n", " "))
    page.screenshot(path=os.path.dirname(__file__) + "/shots/stage-empty.png")
    page.locator(".st-add").tap(); page.wait_for_timeout(500)
    check(page.locator("#f-body").count() == 1 and page.locator(".impbtn").count() == 2, "opens the editor with import buttons")
    page.locator('[data-act="paste"]').tap(); page.wait_for_timeout(400)
    page.locator('[data-act="saveedit"]').tap(); page.wait_for_timeout(1200)
    top = page.inner_text(".st-top") if page.locator(".st-top").count() else ""
    check(page.locator("#stage").count() == 1 and "Mighty" in top, "save returns to the same song on stage (%s)" % top.replace("\n", " "))
    check(page.locator("#stChart").count() == 1 and page.locator(".st-add").count() == 0, "chart now shows on stage")
    page.screenshot(path=os.path.dirname(__file__) + "/shots/stage-after-add.png")
    # cancel path
    page.locator('.st-zone[data-act="next"]').tap(); page.wait_for_timeout(900)
    page.locator('[data-act="exitstage"]').tap(); page.wait_for_timeout(600)
    check(page.locator(".srow").count() > 0, "Kész still leaves the stage to the setlist")
    check(not errors, "no console errors %s" % errors)
    b.close()
srv.shutdown()
print("PROBLEMS:", json.dumps(problems, ensure_ascii=False))
