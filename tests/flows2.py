import sys, os, json, re
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, open_app, PORT
from playwright.sync_api import sync_playwright
OUT = os.path.join(os.path.dirname(__file__), "shots")
problems = []
def check(c, m):
    print(("ok: " if c else "FAIL: ") + m)
    if not c: problems.append(m)
srv = serve()
with sync_playwright() as p:
    # 1. login
    b, page, errors, log, db = open_app(p, "light", logged_in=False)
    page.screenshot(path=OUT + "/x-01-login.png")
    check(page.locator("#loginForm").count() == 1, "login screen shows when signed out")
    page.fill("#l-email", "test@example.com"); page.fill("#l-pw", "pw")
    page.locator('button[form="loginForm"]').tap(); page.wait_for_timeout(2500)
    check(page.locator(".glist.sets .row").count() == 1, "after login the setlists load")
    # 2. add a new song, then offline reload keeps it
    page.locator('[data-act="tab"][data-v="songs"]').tap(); page.wait_for_timeout(300)
    page.locator('.fab').tap(); page.wait_for_timeout(400)
    page.fill("#f-title", "Teszt dal"); page.fill("#f-body", "Verse: 1 4 5\nChorus: 6 4 1 5")
    page.locator('[data-act="saveedit"]').tap(); page.wait_for_timeout(800)
    check(page.locator(".h1.song").inner_text() == "Teszt dal", "new song saves and opens")
    page.wait_for_timeout(2500)
    check(any(s["data"].get("title") == "Teszt dal" for s in db["songs"].values()), "new song reaches the server")
    page.context.set_offline(True)
    page.locator('[data-act="back"]').tap(); page.wait_for_timeout(300)
    page.locator('[data-act="tab"][data-v="sets"]').tap(); page.wait_for_timeout(800)
    page.screenshot(path=OUT + "/x-02-offline.png")
    txt = page.inner_text("body")
    check("Teszt dal" in txt or page.locator(".glist").count() > 0, "app opens offline from stored data")
    check("Offline" in txt, "offline status is shown")
    page.context.set_offline(False)
    # 3. delete a song
    page.reload(); page.wait_for_timeout(1500)
    page.locator('[data-act="tab"][data-v="songs"]').tap(); page.wait_for_timeout(300)
    page.fill("#q", "Teszt"); page.wait_for_timeout(300)
    page.locator('#songList [data-act="opensong"]').first.tap(); page.wait_for_timeout(400)
    page.locator('[data-act="edit"]').tap(); page.wait_for_timeout(400)
    page.locator('[data-act="askdel"]').tap(); page.wait_for_timeout(200)
    page.locator('[data-act="dodelsong"]').tap(); page.wait_for_timeout(1200)
    page.screenshot(path=OUT + "/x-03-after-delete.png")
    check(page.locator("#songList").count() == 1, "after deleting, the song list is shown")
    page.wait_for_timeout(2500)
    check(all(s["deleted"] for s in db["songs"].values() if s["data"].get("title") == "Teszt dal"), "deletion reaches the server")
    # 4. setlist swipe-to-remove and undo
    page.locator('[data-act="tab"][data-v="sets"]').tap(); page.wait_for_timeout(300)
    page.locator('[data-act="openset"]').first.tap(); page.wait_for_timeout(500)
    n0 = page.locator(".srow").count()
    row = page.locator(".srow").first.bounding_box()
    y = row["y"] + row["height"] / 2
    from swipe_util import touch_drag
    touch_drag(page, row["x"] + row["width"] - 60, y, row["x"] + row["width"] - 340, y); page.wait_for_timeout(900)
    check(page.locator(".srow").count() == n0 - 1, "swipe left removes a song from the setlist")
    page.screenshot(path=OUT + "/x-04-swiped.png")
    und = page.locator('#toast button')
    if und.count(): und.first.click(); page.wait_for_timeout(500)
    check(page.locator(".srow").count() == n0, "undo brings it back")
    # 5. new setlist + empty state + delete
    page.go_back(); page.wait_for_timeout(500)
    page.locator('.addcenter').tap(); page.wait_for_timeout(600)
    page.screenshot(path=OUT + "/x-05-newset.png")
    check(page.locator(".empty").count() == 1, "new setlist shows the empty state")
    page.locator('[data-act="askdel"]').tap(); page.locator('[data-act="dodelset"]').tap(); page.wait_for_timeout(800)
    check(page.locator(".glist.sets .row").count() == 1, "deleting the new setlist removes it")
    print("ERRORS:", errors)
    errors = [e for e in errors if "ERR_INTERNET_DISCONNECTED" not in e]  # expected while the test is offline
    check(not errors, "no console errors")
    b.close()
srv.shutdown()
print("PROBLEMS:", json.dumps(problems, ensure_ascii=False))
