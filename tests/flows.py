import sys, json, os
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, open_app
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(__file__), "shots")
os.makedirs(OUT, exist_ok=True)
problems = []
def check(cond, msg):
    if not cond: problems.append(msg); print("FAIL:", msg)
    else: print("ok:", msg)

def shot(page, name): page.screenshot(path=f"{OUT}/{name}.png")

def tap(page, sel):
    page.locator(sel).first.tap(); page.wait_for_timeout(350)

srv = serve()
with sync_playwright() as p:
    for scheme in ["light", "dark"]:
        b, page, errors, log, db = open_app(p, scheme)
        page.wait_for_timeout(1500)
        shot(page, f"{scheme}-01-home")
        check(page.locator(".glist.sets .row").count() == 1, f"[{scheme}] home lists 1 setlist")
        # overflow check on every screen
        def no_hscroll(tag):
            w = page.evaluate("document.documentElement.scrollWidth - innerWidth")
            check(w <= 0, f"[{scheme}] no horizontal overflow on {tag} (got {w})")
        no_hscroll("home")
        # songs tab
        tap(page, '[data-act="tab"][data-v="songs"]'); shot(page, f"{scheme}-02-songs")
        check(page.locator("#songList .row").count() >= 60, f"[{scheme}] song list has the seeded songs")
        no_hscroll("songs")
        page.fill("#q", "echo"); page.wait_for_timeout(300); shot(page, f"{scheme}-03-search")
        check(page.locator("#songList .row").count() == 1, f"[{scheme}] search 'echo' finds one song")
        rw = page.evaluate("[...document.querySelectorAll('#songList .row')].map(r=>r.getBoundingClientRect().right - r.parentElement.getBoundingClientRect().right)")
        check(all(x <= 0.5 for x in rw), f"[{scheme}] search rows fit their card")
        page.fill("#q", ""); page.wait_for_timeout(200)
        # open song
        tap(page, '#songList [data-act="opensong"]'); shot(page, f"{scheme}-04-song")
        check(page.locator(".h1.song").count() == 1, f"[{scheme}] song page opens")
        # edit + cover picker
        tap(page, '[data-act="edit"]'); shot(page, f"{scheme}-05-edit")
        check(page.locator("#f-title").count() == 1, f"[{scheme}] edit opens")
        tap(page, '[data-act="coverpick"]'); page.wait_for_selector(".citem",timeout=8000); shot(page, f"{scheme}-06-coverpick")
        check(page.locator(".citem").count() > 0, f"[{scheme}] cover picker shows results")
        page.fill("#cq", "look to you"); page.wait_for_timeout(600); page.wait_for_selector(".citem",timeout=8000)
        check(page.locator(".citem").count() > 0, f"[{scheme}] cover picker re-search works")
        tap(page, '.citem >> nth=2'); page.wait_for_timeout(400); shot(page, f"{scheme}-07-edit-after-cover")
        check("Artist 2" == page.input_value("#f-artist"), f"[{scheme}] picking a cover fills artist")
        title_before = page.input_value("#f-title")
        tap(page, '[data-act="saveedit"]'); page.wait_for_timeout(600)
        rec = [s for s in db["songs"].values() if s["data"].get("title") == title_before]
        page.wait_for_timeout(2500)
        rec = [s for s in db["songs"].values() if s["data"].get("title") == title_before]
        check(rec and rec[0]["data"].get("coverQ") == "manual" and rec[0]["data"].get("body"), f"[{scheme}] saved song keeps body and manual cover")
        # back to home, open setlist
        page.go_back(); page.wait_for_timeout(500)
        tap(page, '[data-act="tab"][data-v="sets"]')
        tap(page, '[data-act="openset"]'); shot(page, f"{scheme}-08-setlist")
        check(page.locator(".srow").count() == 3, f"[{scheme}] setlist shows 3 songs")
        no_hscroll("setlist")
        # picker
        tap(page, '[data-act="picker"]'); shot(page, f"{scheme}-09-picker")
        cw = page.evaluate("(()=>{const c=document.querySelector('#pickList .check');const r=c.getBoundingClientRect();return [r.right,innerWidth]})()")
        check(cw[0] <= cw[1], f"[{scheme}] picker checkmark visible ({cw})")
        page.fill("#pq", "agnus"); page.wait_for_timeout(300)
        n_before = len(db["setlists"]["l1"]["data"]["songIds"])
        tap(page, '#pickList [data-act="pick"]')
        sel = page.evaluate("(()=>{const i=document.activeElement;return i&&i.id==='pq'?[i.selectionStart,i.selectionEnd,i.value.length]:null})()")
        check(sel and sel[0] == 0 and sel[1] == sel[2], f"[{scheme}] search text selected after pick ({sel})")
        page.go_back(); page.wait_for_timeout(500)
        # key sheet on setlist
        tap(page, '.srow [data-act="keyfor"] >> nth=0'); shot(page, f"{scheme}-10-keysheet")
        tap(page, '.kopt >> nth=4'); page.wait_for_timeout(600)
        check(page.locator(".ksheet").count() == 0, f"[{scheme}] setlist key sheet closes after pick")
        # stage
        tap(page, '.cta[data-act="playfrom"]'); page.wait_for_timeout(1200); shot(page, f"{scheme}-11-stage")
        check(page.locator("#stChart").count() == 1, f"[{scheme}] stage opens")
        fits = page.evaluate("(()=>{const a=document.getElementById('stArea').getBoundingClientRect(),c=document.getElementById('stChart').getBoundingClientRect();return [c.top>=a.top-1,c.bottom<=a.bottom+1,c.right<=a.right+1]})()")
        check(all(fits), f"[{scheme}] stage chart fits its area {fits}")
        # stage key: select then Kész
        tap(page, '[data-act="stagekey"]'); tap(page, '.kopt >> nth=0')
        check(page.locator(".ksheet").count() == 1, f"[{scheme}] stage key sheet stays open after a tap")
        sub = page.inner_text("#skSub")
        idxk = int(__import__("re").search(r"(\d+)/\d+", page.inner_text(".st-top")).group(1))
        page.locator('[data-act="stagedone"]').tap(); page.wait_for_timeout(120)
        page.locator('[data-act="next"]').tap(); page.wait_for_timeout(700); shot(page, f"{scheme}-12-stage-key")
        check(int(__import__("re").search(r"(\d+)/\d+", page.inner_text(".st-top")).group(1)) == idxk, f"[{scheme}] stray tap right after Kész doesn't turn the page")
        check("C" in page.inner_text(".skey"), f"[{scheme}] Kész applies the stage key (button shows {page.inner_text('.skey')}, sub '{sub}')")
        # immediate tap on next zone right after closing is ignored
        import re as _re
        IDX=lambda: int(_re.search(r"(\d+)/\d+", page.inner_text(".st-top")).group(1))
        idx0 = IDX()
        page.wait_for_timeout(500)
        page.locator('[data-act="next"]').tap(); page.wait_for_timeout(800)
        check(IDX() == idx0 + 1, f"[{scheme}] next tap turns the page later")
        # back gesture keeps stage
        page.go_back(); page.wait_for_timeout(500)
        check(page.locator("#stage").count() == 1, f"[{scheme}] browser back keeps the stage open")
        # stage library
        tap(page, '[data-act="stagelib"]'); page.wait_for_timeout(400); shot(page, f"{scheme}-13-stagelib")
        check(page.locator("#libList .row").count() > 10, f"[{scheme}] stage song search lists songs")
        page.go_back(); page.wait_for_timeout(400)
        # letters + light toggles
        tap(page, '[data-act="letters"]'); page.wait_for_timeout(400); shot(page, f"{scheme}-14-letters")
        tap(page, '[data-act="letters"]'); page.wait_for_timeout(300)
        # exit
        tap(page, '[data-act="exitstage"]'); page.wait_for_timeout(600)
        check(page.locator(".srow").count() > 0 and page.locator("#stage").count() == 0, f"[{scheme}] Kész leaves the stage to the setlist")
        bg = page.evaluate("getComputedStyle(document.documentElement).backgroundColor")
        shot(page, f"{scheme}-15-after-stage")
        print("ERRORS:", json.dumps(errors, ensure_ascii=False, indent=1))
        check(not errors, f"[{scheme}] no console errors")
        b.close()
srv.shutdown()
print("\nPROBLEMS:", json.dumps(problems, ensure_ascii=False, indent=1))
