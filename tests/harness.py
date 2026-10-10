import os
"""Run the Chords app in an iPhone-sized headless Chromium with a fake Supabase and Apple search.
Usage: python3 harness.py <scenario-module-function-name>  (scenarios defined in flows.py)"""
import json, re, time, threading, http.server, socketserver, functools, sys, os, datetime
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PORT = 8765

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve():
    h = functools.partial(Quiet, directory=ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", PORT), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

def now(): return datetime.datetime.utcnow().isoformat() + "Z"

def make_db():
    seed = json.load(open(ROOT + "/songs-seed.json"))
    songs = {}
    for s in seed:
        sid = s.pop("id"); songs[sid] = {"id": sid, "data": s, "updated_at": now(), "deleted": False}
    ids = list(songs)
    setlists = {"l1": {"id": "l1", "data": {"name": "Vasárnap, október 11.", "date": "2026-10-11", "songIds": [ids[0], "echoes", ids[2]], "keys": {"echoes": "D"}, "updatedAt": 1}, "updated_at": now(), "deleted": False}}
    return {"songs": songs, "setlists": setlists}

def itunes_payload(term):
    t = term.lower()
    res = []
    for i in range(4):
        res.append({"trackName": term.split(" ")[0].title() + (" (Live)" if i % 2 else ""), "artistName": "Artist %d" % i,
                    "collectionName": "Album %d %s" % (i, "Look to You" if "look" in t and i == 2 else ""), "collectionId": 100 + i,
                    "artworkUrl100": "http://127.0.0.1:%d/icons/icon-192.png?a=%d&/100x100bb.jpg" % (PORT, i)})
    return res

def install_routes(page, db, log):
    def supa(route):
        req = route.request; u = urlparse(req.url); path = u.path
        if path.startswith("/auth/v1/token"):
            return route.fulfill(json={"access_token": "t", "refresh_token": "r", "expires_in": 3600, "user": {"id": "u1", "email": "test@example.com"}})
        m = re.match(r"/rest/v1/(songs|setlists)", path)
        if m:
            coll = m.group(1)
            if req.method == "POST":
                for r in json.loads(req.post_data or "[]"):
                    db[coll][r["id"]] = {"id": r["id"], "data": r["data"], "updated_at": r["updated_at"], "deleted": r["deleted"]}
                log.append(("upsert", coll, len(json.loads(req.post_data or "[]"))))
                return route.fulfill(status=201, body="")
            return route.fulfill(json=list(db[coll].values()))
        return route.fulfill(status=404, body="")
    page.route(re.compile(r"https://[a-z0-9]+\.supabase\.co/.*"), supa)
    def itunes(route):
        q = parse_qs(urlparse(route.request.url).query)
        cb = q.get("callback", ["cb"])[0]; term = q.get("term", [""])[0]
        body = "%s(%s);" % (cb, json.dumps({"resultCount": 4, "results": itunes_payload(term)}))
        route.fulfill(status=200, content_type="text/javascript", body=body)
    page.route(re.compile(r"https://itunes\.apple\.com/.*"), itunes)
    page.route(re.compile(r"https://fonts\.(googleapis|gstatic)\.com/.*"), lambda r: r.fulfill(status=200, content_type="text/css", body=""))
    page.route(re.compile(r"https://cdn\.jsdelivr\.net/.*"), lambda r: r.abort())

def open_app(p, scheme="light", logged_in=True):
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 428, "height": 926}, device_scale_factor=2, is_mobile=True, has_touch=True,
                        color_scheme=scheme, service_workers="block",
                        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
    page = ctx.new_page()
    errors, log = [], []
    page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    page.on("console", lambda m: errors.append("console." + m.type + ": " + m.text) if m.type in ("error",) else None)
    db = make_db()
    install_routes(page, db, log)
    if logged_in:
        page.add_init_script("""try{localStorage.setItem('szk-auth-v1',JSON.stringify({access_token:'t',refresh_token:'r',expires_at:Date.now()+3600e3,user_id:'u1',email:'test@example.com'}))}catch(e){}""")
    page.goto("http://127.0.0.1:%d/index.html" % PORT)
    page.wait_for_timeout(1500)
    return b, page, errors, log, db
