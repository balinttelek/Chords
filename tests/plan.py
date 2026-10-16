"""Planning Center screenshot -> setlist. Tesseract.js is replaced by the local tesseract CLI with the same settings."""
import sys, os, json, base64, subprocess, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, open_app
from playwright.sync_api import sync_playwright
UP = "/root/.claude/uploads/5e077ffb-0b47-5a17-a28b-64a8d5d5212e/"
IMGS = [UP + "19f86a2f-image.png", UP + "e4ace28d-image.jpg"]
problems = []
def check(c, m):
    print(("ok: " if c else "FAIL: ") + m)
    if not c: problems.append(m)
def ocr(dataurl, psm, wl):
    png = base64.b64decode(dataurl.split(",", 1)[1])
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f: f.write(png); fn = f.name
    args = ["tesseract", fn, "-", "--psm", str(psm or 3), "-l", "eng"]
    if wl: args += ["-c", "tessedit_char_whitelist=" + wl]
    text = subprocess.run(args, capture_output=True, text=True).stdout
    tsv = subprocess.run(args + ["tsv"], capture_output=True, text=True).stdout
    os.unlink(fn)
    return {"text": text, "tsv": tsv}
MOCK = """window.Tesseract={createWorker:async()=>{let P={};return {
  setParameters:async p=>{P={...P,...p}},
  recognize:async c=>({data:await window.__ocr(c.toDataURL('image/png'),P.tessedit_pageseg_mode||'',P.tessedit_char_whitelist||'')}),
  terminate:async()=>{}}}};"""
srv = serve()
with sync_playwright() as p:
    b, page, errors, log, db = open_app(p, "light")
    page.expose_function("__ocr", ocr)
    page.evaluate(MOCK)
    page.locator('[data-act="openset"]').first.tap(); page.wait_for_timeout(500)
    n0 = page.locator(".srow").count()
    page.set_input_files("#s-img", IMGS)
    page.wait_for_function("!document.querySelector('.ocrmsg')||!/felismerése/.test(document.querySelector('.ocrmsg').textContent)", timeout=120000)
    page.wait_for_timeout(500)
    msg = page.inner_text(".ocrmsg"); print("MSG:", msg)
    page.screenshot(path=os.path.dirname(__file__) + "/shots/plan-after.png", full_page=True)
    sl = [s for s in db["setlists"].values()][0]
    page.wait_for_timeout(2000)
    st = json.loads(page.evaluate("localStorage.getItem('szk-store-v2')"))
    set_ = list(st["setlists"].values())[0]["data"]
    titles = [st["songs"][i]["data"]["title"] for i in set_["songIds"]]
    keys = {st["songs"][i]["data"]["title"]: set_.get("keys", {}).get(i) or st["songs"][i]["data"]["key"] for i in set_["songIds"]}
    print("TITLES:", titles); print("KEYS:", keys)
    want = {"Let Go": "H", "Megváltott (Salvation Is Here)": "H", "Trust in God": "A", "Here again": "C", "Semmi más": "C", "Forrás": "G", "Reckless love": "E", "Mindenre elég": "A", "My Future Decided": "A"}
    from unicodedata import normalize as un
    n = lambda s: un("NFD", s.lower()).encode("ascii", "ignore").decode()
    for t, k in want.items():
        hit = [x for x in titles if n(t.split(" (")[0]) in n(x) or n(x) in n(t)]
        check(bool(hit), "found %s" % t)
        if hit: check(keys[hit[0]] == k, "%s key %s (got %s)" % (t, k, keys[hit[0]]))
    check(not any(n(x) in ("title", "hirdetesek", "predika") for x in titles), "non-songs skipped")
    # a chat message with a song list (not Planning Center)
    shot = os.path.dirname(__file__) + "/shots/chat-list.png"
    pg2 = b.new_page(viewport={"width": 390, "height": 600}, device_scale_factor=3)
    pg2.set_content("""<body style="margin:0;background:#e5ddd5;font:17px -apple-system,Helvetica,Arial">
    <div style="margin:60px 14px;background:#fff;border-radius:14px;padding:12px 14px;line-height:1.45;width:300px">
    Vasárnapi dalok:<br>1. Here Again - C<br>2. Trust In God (A)<br>G – Reckless Love<br>5) Goodness of God<br>- Who you say I am – Bb<br>Új dal ma: Mosolyfelhő – D<br>Köszi mindenkinek!</div></body>""")
    pg2.screenshot(path=shot); pg2.close()
    page.locator('[data-act="home"]').first.tap(); page.wait_for_timeout(400)
    page.locator('.addcenter').tap(); page.wait_for_timeout(600)
    page.set_input_files("#s-img", [shot])
    page.wait_for_function("document.querySelector('.ocrmsg')&&!/felismerése/.test(document.querySelector('.ocrmsg').textContent)", timeout=120000)
    page.wait_for_timeout(500); print("MSG2:", page.inner_text(".ocrmsg"))
    st = json.loads(page.evaluate("localStorage.getItem('szk-store-v2')"))
    sid = page.evaluate("ui=undefined") if False else None
    sets = sorted(st["setlists"].values(), key=lambda r: r["data"].get("updatedAt", 0))
    s2 = sets[-1]["data"]
    t2 = [(st["songs"][i]["data"]["title"], s2.get("keys", {}).get(i) or st["songs"][i]["data"]["key"]) for i in s2["songIds"]]
    print("CHAT:", t2)
    want2 = [("Here again", "C"), ("Trust in God", "A"), ("Reckless love", "G"), ("Goodness of God", None), ("Who you say i am", "A#"), ("Mosolyfelhő", "D")]
    for (t, k), got in zip(want2, t2 + [None] * 9):
        check(got and n(got[0]).startswith(n(t)[:7]) and (k is None or got[1] == k), "chat list: %s %s (got %s)" % (t, k, got))
    check(len(t2) == len(want2), "chat list: only the songs (%d)" % len(t2))
    check(not errors, "no console errors %s" % errors)
    b.close()
srv.shutdown()
print("PROBLEMS:", json.dumps(problems, ensure_ascii=False))
