import sys, os, json, re
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
  for scheme in ["dark", "light"]:
    b, page, errors, log, db = open_app(p, scheme)
    page.locator('[data-act="openset"]').first.tap(); page.wait_for_timeout(500)
    page.locator('.srow [data-act="keyfor"]').first.tap(); page.wait_for_timeout(400)
    check(page.locator(".joinrow").count() == 1, "key sheet offers joining with the next song")
    page.screenshot(path=OUT + "/m-%s-01-sheet.png" % scheme)
    page.locator(".joinrow").tap(); page.wait_for_timeout(300)
    check(page.locator(".joinrow.on").count() == 1, "toggle turns on")
    page.locator('[data-act="closekey"]').first.tap(); page.wait_for_timeout(500)
    page.wait_for_timeout(1500)
    sid = db["setlists"]["l1"]["data"]
    check(sid.get("joins") and list(sid["joins"].values()) == [1], "join is saved to the server (%s)" % sid.get("joins"))
    check(page.locator(".srow.ja").count() == 1 and page.locator(".srow.jb").count() == 1, "setlist marks the joined pair")
    page.screenshot(path=OUT + "/m-%s-02-setlist.png" % scheme)
    # stage
    page.locator('.cta[data-act="playfrom"]').tap(); page.wait_for_timeout(1500)
    page.screenshot(path=OUT + "/m-%s-03-stage.png" % scheme)
    top = page.inner_text(".st-top")
    check(page.locator("#stChart.combo .chart").count() == 2, "stage shows both songs on one page")
    check("1–2/3" in top, "counter shows 1–2/3 (%s)" % top.replace("\n", " "))
    fits = page.evaluate("(()=>{const a=document.getElementById('stArea').getBoundingClientRect(),c=document.getElementById('stChart').getBoundingClientRect();return [c.top>=a.top-1,c.bottom<=a.bottom+1,c.right<=a.right+1,c.left>=a.left-1]})()")
    check(all(fits), "combined chart fits the screen %s" % fits)
    check("tovább:" in page.inner_text("#stChart"), "divider names the next song")
    page.locator('.st-zone[data-act="next"]').tap(); page.wait_for_timeout(900)
    top = page.inner_text(".st-top")
    check(re.search(r"\b3/3", top) and page.locator("#stChart.combo").count() == 0, "next goes to song 3 (%s)" % top.replace("\n", " "))
    page.locator('.st-zone[data-act="prev"]').tap(); page.wait_for_timeout(900)
    check("1–2/3" in page.inner_text(".st-top"), "prev goes back to the joined page")
    # key sheet tabs: change the second song's key
    page.locator('[data-act="stagekey"]').tap(); page.wait_for_timeout(400)
    check(page.locator(".ktabs button").count() == 2, "stage key sheet has a tab per song")
    page.locator(".ktabs button").nth(1).tap(); page.wait_for_timeout(300)
    page.screenshot(path=OUT + "/m-%s-04-keytabs.png" % scheme)
    page.locator('.kopt[data-v="F"]').tap(); page.locator('[data-act="stagedone"]').tap(); page.wait_for_timeout(900)
    kb = page.inner_text(".skey")
    check(kb.endswith("F"), "second song key changes on its own (%s)" % kb)
    page.screenshot(path=OUT + "/m-%s-05-after.png" % scheme)
    pk = page.inner_text(".peek")
    check("Anthem" in pk and "6" in pk, "peek shows the next song and its first line (%s)" % pk.replace("\n", " "))
    page.locator(".peek").tap(); page.wait_for_timeout(900)
    check(re.search(r"\b3/3", page.inner_text(".st-top")) is not None, "tapping the peek turns to the next song")
    check(not errors, "no console errors %s" % errors)
    b.close()
srv.shutdown()
print("PROBLEMS:", json.dumps([x for x in problems if x], ensure_ascii=False))
