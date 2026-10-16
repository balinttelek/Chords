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
    b, page, errors, log, db = open_app(p, "light")
    page.locator('[data-act="tab"][data-v="songs"]').tap(); page.fill("#q", "irgalma"); page.wait_for_timeout(300)
    page.locator('#songList [data-act="opensong"]').first.tap(); page.wait_for_timeout(400)
    page.locator('[data-act="edit"]').tap(); page.wait_for_timeout(400)
    check(page.locator("#f-alt").count() == 1, "editor has a second title field")
    page.fill("#f-alt", "Mercy"); page.screenshot(path=os.path.dirname(__file__) + "/shots/alt-edit.png")
    page.locator('[data-act="saveedit"]').tap(); page.wait_for_timeout(2500)
    check(page.inner_text(".alt") == "Mercy", "song page shows the other title")
    page.screenshot(path=os.path.dirname(__file__) + "/shots/alt-song.png")
    check(any(s["data"].get("alt") == "Mercy" for s in db["songs"].values()), "second title syncs")
    page.locator('[data-act="back"]').tap(); page.wait_for_timeout(400)
    page.fill("#q", "mercy"); page.wait_for_timeout(300)
    titles = page.locator("#songList .row .t1").all_inner_texts()
    check(any("Irgalma" in t for t in titles), "search finds the song by its other title (%s)" % titles)
    check(not errors, "no console errors %s" % errors)
    b.close()
srv.shutdown()
print("PROBLEMS:", json.dumps(problems, ensure_ascii=False))
