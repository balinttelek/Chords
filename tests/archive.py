import sys, os, json, datetime
sys.path.insert(0, os.path.dirname(__file__))
import harness
from harness import serve, open_app
from playwright.sync_api import sync_playwright
problems = []
def check(c, m):
    print(("ok: " if c else "FAIL: ") + m)
    if not c: problems.append(m)
real = harness.make_db
today = datetime.date.today()
def db2():
    d = real()
    ids = list(d["songs"])
    def mk(i, name, date, **kw): d["setlists"][i] = {"id": i, "data": {"name": name, "date": date, "songIds": ids[:3], "updatedAt": 1, **kw}, "updated_at": harness.now(), "deleted": False}
    d["setlists"].clear()
    mk("up", "Jövő vasárnap", (today + datetime.timedelta(days=7)).isoformat())
    mk("td", "Ma", today.isoformat())
    mk("p1", "Múlt hét", (today - datetime.timedelta(days=7)).isoformat())
    mk("p2", "Két hete", (today - datetime.timedelta(days=14)).isoformat())
    return d
harness.make_db = db2
srv = serve()
with sync_playwright() as p:
    b, page, errors, log, db = open_app(p, "light")
    page.wait_for_timeout(1500)
    names = page.locator(".glist.sets .t1").all_inner_texts()
    check(names == ["Ma", "Jövő vasárnap"], "home shows today and upcoming only (%s)" % names)
    check("2 korábbi alkalom" in page.inner_text(".archrow"), "archive row counts past occasions")
    page.screenshot(path=os.path.dirname(__file__) + "/shots/arch-home.png")
    page.locator(".archrow").tap(); page.wait_for_timeout(500)
    an = page.locator(".glist.sets .t1").all_inner_texts()
    check(an == ["Múlt hét", "Két hete"], "archive lists past ones, latest first (%s)" % an)
    page.screenshot(path=os.path.dirname(__file__) + "/shots/arch-list.png")
    page.locator('[data-act="openset"]').first.tap(); page.wait_for_timeout(500)
    check(page.locator(".srow").count() == 3, "an archived setlist opens normally")
    check("Visszaállítás" in page.inner_text(".archbtn"), "it offers restore")
    page.go_back(); page.wait_for_timeout(500)
    check(page.locator("h1").inner_text() == "Archívum", "back returns to the archive")
    # restore one, archive one by hand
    page.locator('[data-act="openset"]').first.tap(); page.wait_for_timeout(400)
    page.locator(".archbtn").tap(); page.wait_for_timeout(400)
    page.go_back(); page.wait_for_timeout(400); page.go_back(); page.wait_for_timeout(500)
    names = page.locator(".glist.sets .t1").all_inner_texts()
    check("Múlt hét" in names, "restored setlist is back on the home list (%s)" % names)
    page.locator('[data-act="openset"]', has_text="Ma").first.tap(); page.wait_for_timeout(400)
    page.locator(".archbtn").tap(); page.wait_for_timeout(400); page.go_back(); page.wait_for_timeout(500)
    names2 = page.locator(".glist.sets .t1").all_inner_texts()
    check(len(names2) == len(names) - 1, "archiving by hand moves it off the home list (%s)" % names2)
    page.wait_for_timeout(2000)
    check(db["setlists"]["p1"]["data"].get("archived") is False, "restore syncs")
    check(not errors, "no console errors %s" % errors)
    b.close()
srv.shutdown()
print("PROBLEMS:", json.dumps(problems, ensure_ascii=False))
