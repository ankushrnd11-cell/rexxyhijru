import os
import time
import threading
import urllib.parse
import requests
import json
from flask import Flask, jsonify
from instagrapi import Client  # [web:16]
import logging
from werkzeug.serving import WSGIRequestHandler


SESSIONID_1 = os.getenv("SESSIONID_1", "")
SESSIONID_2 = os.getenv("SESSIONID_2", "")
SESSIONID_3 = os.getenv("SESSIONID_3", "")
SESSIONID_4 = os.getenv("SESSIONID_4", "")
SESSIONID_5 = os.getenv("SESSIONID_5", "")
SESSIONID_6 = os.getenv("SESSIONID_6", "")
GROUP_IDS = os.getenv("GROUP_IDS", "")  
MESSAGE_TEXT = os.getenv("MESSAGE_TEXT", "Hello 👋")
SELF_URL = os.getenv("SELF_URL", "")
NC_TITLES_RAW = os.getenv("NC_TITLES", "") 
SPAM_START_OFFSET = int(os.getenv("SPAM_START_OFFSET", "1"))
SPAM_GAP_BETWEEN_ACCOUNTS = int(os.getenv("SPAM_GAP_BETWEEN_ACCOUNTS", "6"))
NC_START_OFFSET = int(os.getenv("NC_START_OFFSET", "1"))
NC_ACC_GAP = int(os.getenv("NC_ACC_GAP", "30"))

MSG_REFRESH_DELAY = int(os.getenv("MSG_REFRESH_DELAY", "1"))
BURST_COUNT = int(os.getenv("BURST_COUNT", "1"))
SELF_PING_INTERVAL = int(os.getenv("SELF_PING_INTERVAL", "60"))
COOLDOWN_ON_ERROR = int(os.getenv("COOLDOWN_ON_ERROR", "300"))
DOC_ID = os.getenv("DOC_ID", "29088580780787855")
CSRF_TOKEN = os.getenv("CSRF_TOKEN", "")

app = Flask(__name__)

log = logging.getLogger("werkzeug")
log.disabled = True
app.logger.disabled = True

WSGIRequestHandler.log_request = lambda *args, **kwargs: None
WSGIRequestHandler.log = lambda *args, **kwargs: None

MAX_SESSION_LOGS = 200
session_logs = {
    "acc1": [],
    "acc2": [],
    "acc3": [],
    "acc4": [],
    "acc5": [],
    "acc6": [],
    "system": []
}
logs_lock = threading.Lock()
START_TIME = time.time()
account_status = {}
USERS = []

from collections import defaultdict
logs_ui = defaultdict(list)

def _push_log(session, msg):
    if session not in session_logs:
        session = "system"
    with logs_lock:
        session_logs[session].append(msg)
        if len(session_logs[session]) > MAX_SESSION_LOGS:
            session_logs[session].pop(0)


def log(msg, session="system"):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    _push_log(session, msg)

def ui_log(user, message):
    if user not in USERS:
        USERS.append(user)

    logs_ui[user].append(message)

    if len(logs_ui[user]) > 35:
        logs_ui[user].pop(0)

@app.route("/health")
def health():
    return jsonify({"status": "ok", "message": "Bot process alive"})

def summarize(lines):
    rev = list(reversed(lines))
    last_login = next((l for l in rev if "Logged in" in l), None)
    last_send_ok = next((l for l in rev if "✅" in l and "sent to" in l), None)
    last_send_err = next((l for l in rev if "Send failed" in l or "⚠ send failed" in l), None)
    last_title_ok = next((l for l in rev if "changed title" in l and "📝" in l), None)
    last_title_err = next((l for l in rev if "Title change" in l or "GraphQL title" in l), None)
    return {
        "last_login": last_login,
        "last_send_ok": last_send_ok,
        "last_send_error": last_send_err,
        "last_title_ok": last_title_ok,
        "last_title_error": last_title_err,
    }

@app.route("/status")
def status():
    with logs_lock:
        acc1_logs = session_logs["acc1"][-80:]
        acc2_logs = session_logs["acc2"][-80:]
        acc3_logs = session_logs["acc3"][-80:]
        acc4_logs = session_logs["acc4"][-80:]
        acc5_logs = session_logs["acc5"][-80:]
        acc6_logs = session_logs["acc6"][-80:]   
        system_last = session_logs["system"][-5:]

    return jsonify({
        "ok": True,
        "acc1": summarize(acc1_logs),
        "acc2": summarize(acc2_logs),
        "acc3": summarize(acc3_logs),
        "acc4": summarize(acc4_logs),
        "acc5": summarize(acc5_logs),
        "acc6": summarize(acc6_logs),
        "system_last": system_last
    })


@app.route("/dashboard")
def dashboard():
    runtime = int(time.time() - START_TIME)

    h = runtime // 3600
    m = (runtime % 3600) // 60
    s = runtime % 60

    runtime_text = f"{h:02}:{m:02}:{s:02}"

    html = f"""
<!DOCTYPE html>
<html>
<head>

<title>SINISTERS ⚡ SX⁷</title>

<meta http-equiv="refresh" content="2">

<style>

body{{
background:#efefef;
font-family:Arial,sans-serif;
margin:0;
padding:35px;
color:#111;
}}

.header{{
background:white;
border:2px solid #111;
border-radius:12px;
padding:20px;
text-align:center;
margin-bottom:25px;
}}

.title{{
font-size:34px;
font-weight:bold;
}}

.runtime{{
margin-top:10px;
font-size:20px;
}}

.container{{
display:flex;
flex-wrap:wrap;
gap:20px;
}}

.box{{
background:white;
border:2px solid #111;
border-radius:12px;
width:320px;
height:520px;
padding:15px;
overflow-y:auto;
box-sizing:border-box;
}}

.username{{
font-size:22px;
font-weight:bold;
border-bottom:2px solid #111;
padding-bottom:8px;
margin-bottom:8px;
}}

.status{{
font-size:18px;
margin-bottom:15px;
}}

.log{{
padding:4px 0;
font-size:15px;
word-break:break-word;
}}

</style>

</head>

<body>

<div class="header">

<div class="title">
SINISTERS ⚡ SX⁷
</div>

<div class="runtime">
RUNTIME ⏳ {runtime_text}
</div>

</div>

<div class="container">
"""

    for user in USERS:

        html += f"""

<div class="box">

<div class="username">{user}</div>

<div class="status">
{account_status.get(user,"❌ INACTIVE")}
</div>

"""

        for line in logs_ui[user][-35:]:

            html += f'<div class="log">{line}</div>'

        html += "</div>"

    html += """

</div>

<script>

document.querySelectorAll('.box').forEach(function(b){

b.scrollTop=b.scrollHeight;

});

</script>

</body>

</html>

"""

    return html


def decode_session(session):
    if not session:
        return session
    try:
        return urllib.parse.unquote(session)
    except Exception:
        return session
    

def parse_session(raw):
    if not raw:
        return None

    raw = raw.strip()

    if "|" not in raw:
        return None

    username, sessionid = raw.split("|", 1)

    return {
        "username": username.strip(),
        "sessionid": decode_session(sessionid.strip())
    }


def login_session(session_id, name_hint=""):
    session_id = decode_session(session_id)
    try:
        cl = Client()
        cl.login_by_sessionid(session_id)  # [web:16]
        uname = getattr(cl, "username", None) or name_hint or "unknown"
        log(f"✅ Logged in {uname}", session=name_hint or "system")
        return cl
    except Exception as e:
        log(f"❌ Login failed ({name_hint}): {e}", session=name_hint or "system")
        return None

def safe_send_message(cl, gid, msg, acc_name):
    try:
        cl.direct_send(msg, thread_ids=[int(gid)])  # [web:16]
        ui_log(acc_name, f"📨 SENT - {gid}")
        return True
    except Exception as e:
        ui_log(acc_name, "❌ SENT FAILED")
        return False

def safe_change_title_direct(cl, gid, new_title, acc_name):
    try:
        tt = cl.direct_thread(int(gid))  # [web:16]
        try:
            tt.update_title(new_title)
            return True
        except Exception:
            pass

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "X-CSRFToken": CSRF_TOKEN,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://www.instagram.com/direct/t/{gid}/",
        }
        cookies = {"csrftoken": CSRF_TOKEN}
        try:
            cl.private.headers.update(headers)
            cl.private.cookies.update(cookies)
            variables = {"thread_fbid": gid, "new_title": new_title}
            payload = {"doc_id": DOC_ID, "variables": json.dumps(variables)}
            resp = cl.private.post("https://www.instagram.com/api/graphql/", data=payload, timeout=10)
            try:
                result = resp.json()
                if "errors" in result:
                    return False
                ui_log(acc_name, f"⚡ {new_title}")
                return True
            except Exception as e:
                return False
        except Exception as e:
            return False
    except Exception as e:
        return False

# --------- Loops ----------
def spam_loop(accounts, groups, message_delay):
    if not groups:
        log("⚠ No groups for messaging loop.", session="system")
        return

    time.sleep(SPAM_START_OFFSET)

    idx = 0
    n = len(accounts)

    while True:
        acc = accounts[idx]
        acc_name = acc["name"]

        try:
            # cooldown check
            if acc.get("cooldown_until", 0) > time.time():
                log(f"⏳ {acc_name} cooling down", session=acc_name)
            elif not acc["active"] or not acc["client"]:
                log(f"⏭ {acc_name} inactive, skipping message slot", session=acc_name)
            else:
                cl = acc["client"]
                for gid in groups:
                    for _ in range(BURST_COUNT):
                        ok = safe_send_message(cl, gid, MESSAGE_TEXT, acc_name)
                        if not ok:
                            log(f"⛔ {acc_name} failed, applying cooldown for message loop", session=acc_name)
                            acc["cooldown_until"] = time.time() + COOLDOWN_ON_ERROR
                            break
                        time.sleep(MSG_REFRESH_DELAY)

                    if acc.get("cooldown_until", 0) > time.time():
                        break

                    time.sleep(0.5)

        except Exception as e:
            log(f"❌ Exception in {acc_name} message loop: {e}", session=acc_name)
            acc["cooldown_until"] = time.time() + COOLDOWN_ON_ERROR

        time.sleep(message_delay)
        idx = (idx + 1) % n


def parse_nc_titles():
    """
    Returns a list of 4 titles, one per account.
    If NC_TITLES_RAW has fewer than 4, it pads with MESSAGE_TEXT[:40].
    """
    base = [t.strip() for t in NC_TITLES_RAW.split(",") if t.strip()]
    default_title = MESSAGE_TEXT[:40] or "NC"
    while len(base) < 6:
        base.append(default_title)
    return base[:6]

def nc_loop(accounts, groups, titles_map, rename_delay):
    if not groups:
        log("⚠ No groups for title loop.", session="system")
        return

    per_account_titles = parse_nc_titles()
    log(f"NC titles per account: {per_account_titles}", session="system")

    time.sleep(NC_START_OFFSET)

    idx = 0
    n = len(accounts)

    while True:
        acc = accounts[idx]
        acc_name = acc["name"]
        account_title = per_account_titles[idx]

        try:
            # cooldown check
            if acc.get("cooldown_until", 0) > time.time():
                log(f"⏳ {acc_name} cooling down", session=acc_name)
            elif not acc["active"] or not acc["client"]:
                log(f"⏭ {acc_name} inactive, skipping nc slot", session=acc_name)
            else:
                cl = acc["client"]
                for gid in groups:
                    titles = titles_map.get(str(gid)) or titles_map.get(int(gid)) or [account_title]
                    t = titles[0]

                    ok = safe_change_title_direct(cl, gid, t, acc_name)
                    if not ok:
                        log(f"⛔ {acc_name} failed, applying cooldown for nc loop", session=acc_name)
                        acc["cooldown_until"] = time.time() + COOLDOWN_ON_ERROR
                        break

                    time.sleep(1)

        except Exception as e:
            log(f"❌ Exception in {acc_name} nc loop: {e}", session=acc_name)
            acc["cooldown_until"] = time.time() + COOLDOWN_ON_ERROR

        time.sleep(rename_delay)
        idx = (idx + 1) % n


def self_ping_loop():
    while True:
        if SELF_URL:
            try:
                requests.get(SELF_URL, timeout=10)
                log("🔁 Self ping successful", session="system")
            except Exception as e:
                log(f"⚠ Self ping failed: {e}", session="system")
        time.sleep(SELF_PING_INTERVAL)

def start_bot():
    log(
        "STARTUP: "
        f"SESSIONID_1={repr(SESSIONID_1)}, "
        f"SESSIONID_2={repr(SESSIONID_2)}, "
        f"SESSIONID_3={repr(SESSIONID_3)}, "
        f"SESSIONID_4={repr(SESSIONID_4)}, "
        f"SESSIONID_5={repr(SESSIONID_5)}, "
        f"SESSIONID_6={repr(SESSIONID_6)}, "
        f"GROUP_IDS={repr(GROUP_IDS)}, MESSAGE_TEXT={repr(MESSAGE_TEXT)}, "
        f"NC_TITLES={repr(NC_TITLES_RAW)}",
        session="system"
    )

    session_entries = [
        parse_session(SESSIONID_1),
        parse_session(SESSIONID_2),
        parse_session(SESSIONID_3),
        parse_session(SESSIONID_4),
        parse_session(SESSIONID_5),
        parse_session(SESSIONID_6),
    ]

    session_entries = [x for x in session_entries if x]

    groups = [g.strip() for g in GROUP_IDS.split(",") if g.strip()]
    if not groups:
        log("❌ GROUP_IDS is empty or invalid", session="system")
        return

    titles_map = {}
    raw_titles = os.getenv("GROUP_TITLES", "")
    if raw_titles:
        try:
            titles_map = json.loads(raw_titles)
        except Exception as e:
            log(f"⚠ GROUP_TITLES JSON parse error: {e}. Using fallback titles.", session="system")

    accounts = []
    for i, entry in enumerate(session_entries, 1):
        acc_name = entry["username"]

        log(f"🔐 Logging in account {i}...", session="system")
        cl = login_session(entry["sessionid"], acc_name)
        if cl:
            if acc_name not in USERS:
                USERS.append(acc_name)
                
            account_status[acc_name] = "✔ ACTIVE"
            accounts.append({"name": acc_name, "username": entry["username"], "client": cl, "active": True, "status": "✔ ACTIVE", "cooldown_until": 0})
        else:
            if acc_name not in USERS:
                USERS.append(acc_name)
                
            account_status[acc_name] = "❌ INACTIVE"
            log(f"⚠ {acc_name} login failed, keeping slot inactive", session=acc_name)
            accounts.append({"name": acc_name, "username": entry["username"], "client": None, "active": False, "status": "❌ INACTIVE", "cooldown_until": 0})


    # if ALL six are really inactive (no client), no point starting loops
    if not any(a["client"] for a in accounts):
        log("❌ No accounts logged in, aborting.", session="system")
        return

    active_accounts = sum(1 for a in accounts if a["client"])

    MESSAGE_DELAY = 45 / active_accounts
    RENAME_DELAY = 180 / active_accounts

    try:
        t1 = threading.Thread(target=spam_loop, args=(accounts, groups, MESSAGE_DELAY), daemon=True)
        t1.start()
        log(
            "▶ Started spam loop with 6 slots "
            f"({SPAM_START_OFFSET}s start, {SPAM_GAP_BETWEEN_ACCOUNTS}s gap between slots)",
            session="system"
        )
    except Exception as e:
        log(f"❌ Failed to start spam loop thread: {e}", session="system")

    try:
        t2 = threading.Thread(target=nc_loop, args=(accounts, groups, titles_map, RENAME_DELAY), daemon=True)
        t2.start()
        log(
            "▶ Started nc loop with 6 slots "
            f"({NC_START_OFFSET}s start, {NC_ACC_GAP}s gap between slots)",
            session="system"
        )
    except Exception as e:
        log(f"❌ Failed to start nc loop thread: {e}", session="system")

    try:
        t3 = threading.Thread(target=self_ping_loop, daemon=True)
        t3.start()
    except Exception as e:
        log(f"⚠ Failed to start self-ping thread: {e}", session="system")


def run_bot_once():
    try:
        threading.Thread(target=start_bot, daemon=True).start()
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ Failed to start bot (import-time): {e}", flush=True)

run_bot_once()
# -------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )
