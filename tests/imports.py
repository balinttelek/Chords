import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import harness
from harness import serve, open_app, make_db
from playwright.sync_api import sync_playwright
NEW = {"same-god","tuz-altal-felel","tuz-altal-felel-2","mi-mossa-le","alive","boldly-i-approach","gyozelmunk-hangja","yahweh","szuksegem-van-rad","you","open-the-eyes-of-my-heart","olthatatlan-lang","i-speak-jesus","god-i-look-to-you","praise","do-it-again","huseges-isten","megtart-kegyelmed"}
problems = []
def check(c, m):
    print(("ok: " if c else "FAIL: ") + m)
    if not c: problems.append(m)
def old_db():
    db = make_db()
    for i in NEW: db["songs"].pop(i, None)
    return db
harness.make_db, real = old_db, harness.make_db
srv = serve()
with sync_playwright() as p:
    b, page, errors, log, db = open_app(p)
    page.wait_for_timeout(3500)
    check(NEW <= set(db["songs"]), "all new songs reach the server (%d)" % len(NEW & set(db["songs"])))
    page.locator('[data-act="tab"][data-v="songs"]').tap(); page.fill("#q", "boldly"); page.wait_for_timeout(300)
    page.locator('#songList [data-act="opensong"]').first.tap(); page.wait_for_timeout(500)
    page.screenshot(path=os.path.dirname(__file__) + "/shots/imp-boldly.png")
    check("Bridge/Refrain" in page.inner_text("body"), "imported chart renders")
    # delete one, reload: it must not come back
    db["songs"]["praise"]["deleted"] = True
    page.evaluate("(()=>{const s=JSON.parse(localStorage.getItem('szk-store-v2'));s.songs.praise.deleted=true;localStorage.setItem('szk-store-v2',JSON.stringify(s))})()")
    page.reload(); page.wait_for_timeout(3000)
    check(db["songs"]["praise"]["deleted"], "a deleted imported song stays deleted")
    check(not errors, "no console errors %s" % errors)
    b.close()
    # fresh empty account: seed gets everything once
    harness.make_db = lambda: {"songs": {}, "setlists": {}}
    b, page, errors, log, db = open_app(p); page.wait_for_timeout(3500)
    check(len(db["songs"]) == 88, "empty account seeds all 88 songs (%d)" % len(db["songs"]))
    b.close()
srv.shutdown()
print("PROBLEMS:", json.dumps(problems, ensure_ascii=False))
