import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, open_app
from playwright.sync_api import sync_playwright
OUT = os.path.dirname(__file__) + "/shots"
problems = []
def check(c, m):
    print(("ok: " if c else "FAIL: ") + m)
    if not c: problems.append(m)
srv = serve()
with sync_playwright() as p:
    b, page, errors, log, db = open_app(p, "light", logged_in=False)
    reqs = []
    page.on("request", lambda r: reqs.append(r.url) if "supabase" in r.url else None)
    page.screenshot(path=OUT + "/g-01-login.png")
    page.locator('[data-act="guest"]').tap(); page.wait_for_timeout(1500)
    page.screenshot(path=OUT + "/g-02-home.png")
    check("Vendég mód" in page.inner_text("body"), "guest home shows guest status")
    page.wait_for_timeout(7000)
    nc = page.evaluate("(()=>{const s=JSON.parse(localStorage.getItem('szk-guest-store-v1'));return Object.values(s.songs).filter(r=>r.data.cover).length})()")
    check(nc >= 2, "guest songs start getting covers right after login (%d)" % nc)
    page.locator('[data-act="tab"][data-v="songs"]').tap(); page.wait_for_timeout(300)
    n = page.locator("#songList .row").count()
    check(n == 88, "guest starts with the song library (%d)" % n)
    # guest edits stay local
    page.locator('.fab').tap(); page.wait_for_timeout(400)
    page.fill("#f-title", "Vendég dal"); page.fill("#f-body", "Verse: 1 4 5")
    page.locator('[data-act="saveedit"]').tap(); page.wait_for_timeout(2000)
    check(page.locator(".h1.song").inner_text() == "Vendég dal", "guest can add a song")
    check(not any(s["data"].get("title") == "Vendég dal" for s in db["songs"].values()), "guest song never reaches the owner's server")
    check(not reqs, "guest mode makes no server calls (%s)" % reqs[:2])
    # survives reload
    page.reload(); page.wait_for_timeout(1500)
    page.locator('[data-act="tab"][data-v="songs"]').tap(); page.fill("#q", "Vendég"); page.wait_for_timeout(300)
    check(page.locator("#songList .row").count() == 1, "guest library survives reload")
    # logout -> login screen, owner store untouched
    page.locator('[data-act="tab"][data-v="sets"]').tap(); page.wait_for_timeout(300)
    page.locator('[data-act="logout"]').tap(); page.wait_for_timeout(200)
    page.locator('[data-act="dologout"]').tap(); page.wait_for_timeout(600)
    check(page.locator("#loginForm").count() == 1, "guest logout returns to login")
    # real login afterwards sees the owner's data, not the guest song
    page.fill("#l-email", "test@example.com"); page.fill("#l-pw", "pw")
    page.locator('button[form="loginForm"]').tap(); page.wait_for_timeout(2500)
    page.locator('[data-act="tab"][data-v="songs"]').tap(); page.fill("#q", "Vendég"); page.wait_for_timeout(300)
    check(page.locator("#songList .row").count() == 0, "owner account does not see the guest song")
    check(not errors, "no console errors %s" % errors)
    b.close()
srv.shutdown()
print("PROBLEMS:", json.dumps(problems, ensure_ascii=False))
