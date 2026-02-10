#!/usr/bin/env python3
"""
Paqet Tunnel Manager - Web Dashboard
Login at /login (looks like normal site for DPI). Dashboard at /dashboard.
Python 3 stdlib only. Run as root: python3 paqet-dashboard.py [--port 8880] [--bind 0.0.0.0]
"""
import hashlib
import json
import os
import secrets
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

CONFIG_DIR = os.environ.get("PAQET_CONFIG_DIR", "/etc/paqet")
DEFAULT_PORT = 8880
DEFAULT_BIND = "0.0.0.0"
COOKIE_NAME = "psid"
# Simple auth: any non-empty user + password "paqet" or "admin" works. Change if you want.
LOGIN_PASSWORD = os.environ.get("PAQET_DASHBOARD_PASS", "paqet")
SESSION_SECRET = secrets.token_hex(16)
SESSION_TOKEN = hashlib.sha256((SESSION_SECRET + "ok").encode()).hexdigest()[:32]


def run_cmd(cmd, timeout=10):
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "LANG": "C"}
        )
        return r.stdout or "", r.stderr or "", r.returncode
    except Exception as e:
        return "", str(e), -1


def get_services():
    out, _, _ = run_cmd(
        ["systemctl", "list-units", "--type=service", "--no-legend", "--no-pager",
         "paqet-*.service"]
    )
    services = []
    for line in out.strip().splitlines():
        parts = line.split()
        if len(parts) < 1:
            continue
        unit = parts[0]
        name = unit.replace("paqet-", "").replace(".service", "")
        active = "active" if len(parts) >= 3 and parts[2] == "active" else "inactive"
        services.append({"unit": unit, "name": name, "status": active})
    return services


def get_logs(unit, lines=100):
    out, err, code = run_cmd(
        ["journalctl", "-u", unit, "-n", str(lines), "--no-pager", "-o", "short-iso"]
    )
    return (out + err).strip() if (out or err) else "(no logs)"


def get_config(name):
    path = os.path.join(CONFIG_DIR, name + ".yaml")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return None


def get_all_configs():
    configs = []
    if not os.path.isdir(CONFIG_DIR):
        return configs
    for f in os.listdir(CONFIG_DIR):
        if f.endswith(".yaml"):
            configs.append(f.replace(".yaml", ""))
    return sorted(configs)


def valid_session(cookie_header):
    if not cookie_header:
        return False
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith(COOKIE_NAME + "="):
            val = part.split("=", 1)[1].strip().split(",")[0]
            return val == SESSION_TOKEN
    return False


def make_session_cookie():
    return "{}={}; Path=/; HttpOnly; SameSite=Lax".format(COOKIE_NAME, SESSION_TOKEN)


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_redirect(self, location, status=302):
        self.send_response(status)
        self.send_header("Location", location)
        self.end_headers()

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def send_html(self, html, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        qs = parse_qs(urlparse(self.path).query)
        cookie = self.headers.get("Cookie", "")

        if path == "/":
            self.send_redirect("/login")
            return
        if path == "/login":
            self.send_html(LOGIN_HTML)
            return
        if path == "/dashboard":
            if not valid_session(cookie):
                self.send_redirect("/login")
                return
            self.send_html(DASHBOARD_HTML)
            return
        if path == "/api/status":
            self.send_json({"services": get_services(), "configs": get_all_configs()})
            return
        if path == "/api/logs":
            unit = qs.get("service", ["paqet-default"])[0]
            if not unit.endswith(".service"):
                unit = "paqet-" + unit.replace("paqet-", "") + ".service"
            lines = int(qs.get("lines", [100])[0])
            logs = get_logs(unit, lines)
            self.send_json({"service": unit, "logs": logs})
            return
        if path == "/api/config":
            name = qs.get("name", [""])[0].strip() or qs.get("config", [""])[0].strip()
            if not name:
                self.send_json({"error": "missing name"}, 400)
                return
            content = get_config(name)
            if content is None:
                self.send_json({"error": "not found"}, 404)
                return
            self.send_json({"name": name, "content": content})
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        cookie = self.headers.get("Cookie", "")

        if path == "/login":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length else ""
            params = parse_qs(body)
            user = (params.get("username", [""])[0] or "").strip()
            pw = (params.get("password", [""])[0] or "").strip()
            if user and (pw == LOGIN_PASSWORD or pw == "admin" or not LOGIN_PASSWORD):
                self.send_response(302)
                self.send_header("Location", "/dashboard")
                self.send_header("Set-Cookie", make_session_cookie())
                self.end_headers()
            else:
                self.send_html(LOGIN_HTML.replace("<!-- error -->", "<p class='err'>Invalid credentials.</p>"), 200)
            return
        if path == "/api/restart":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8") if length else "{}"
                data = json.loads(body) if body else {}
                unit = data.get("service", "")
                if not unit:
                    self.send_json({"ok": False, "error": "missing service"}, 400)
                    return
                if not unit.endswith(".service"):
                    unit = "paqet-" + unit.replace("paqet-", "") + ".service"
                run_cmd(["systemctl", "restart", unit])
                self.send_json({"ok": True, "service": unit})
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return
        self.send_response(404)
        self.end_headers()


LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sign in – Secure Portal</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Inter', system-ui, sans-serif; min-height: 100vh; background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%); color: #e2e8f0; display: flex; align-items: center; justify-content: center; padding: 20px; }
    .wrap { width: 100%; max-width: 420px; }
    .card { background: rgba(30, 41, 59, 0.8); backdrop-filter: blur(12px); border: 1px solid rgba(71, 85, 105, 0.5); border-radius: 16px; padding: 40px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.4); }
    .logo { text-align: center; margin-bottom: 28px; }
    .logo h1 { font-size: 1.5rem; font-weight: 700; color: #f8fafc; letter-spacing: -0.02em; }
    .logo p { font-size: 0.875rem; color: #94a3b8; margin-top: 6px; }
    label { display: block; font-size: 0.875rem; font-weight: 500; color: #cbd5e1; margin-bottom: 8px; }
    input[type="text"], input[type="password"] { width: 100%; padding: 12px 16px; border: 1px solid #475569; border-radius: 10px; background: #0f172a; color: #f1f5f9; font-size: 1rem; margin-bottom: 18px; outline: none; }
    input:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2); }
    .btn { width: 100%; padding: 14px; background: linear-gradient(180deg, #3b82f6, #2563eb); color: #fff; border: none; border-radius: 10px; font-size: 1rem; font-weight: 600; cursor: pointer; }
    .btn:hover { background: linear-gradient(180deg, #60a5fa, #3b82f6); }
    .err { color: #f87171; font-size: 0.875rem; margin-bottom: 12px; text-align: center; }
    .foot { text-align: center; margin-top: 24px; font-size: 0.75rem; color: #64748b; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="logo">
        <h1>Secure Portal</h1>
        <p>Sign in to access your account</p>
      </div>
      <!-- error -->
      <form method="post" action="/login">
        <label for="u">Username</label>
        <input type="text" id="u" name="username" placeholder="Enter username" required autocomplete="username">
        <label for="p">Password</label>
        <input type="password" id="p" name="password" placeholder="Enter password" required autocomplete="current-password">
        <button type="submit" class="btn">Sign in</button>
      </form>
    </div>
    <p class="foot">&copy; 2026 Secure Portal. All rights reserved.</p>
  </div>
</body>
</html>
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dashboard – Secure Portal</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Inter', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
    .header { background: rgba(30, 41, 59, 0.95); border-bottom: 1px solid #334155; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
    .header h1 { font-size: 1.25rem; font-weight: 700; color: #f8fafc; }
    .header a { color: #94a3b8; text-decoration: none; font-size: 0.875rem; }
    .header a:hover { color: #3b82f6; }
    .main { max-width: 1100px; margin: 0 auto; padding: 24px; }
    .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 24px; margin-bottom: 24px; }
    .card h2 { font-size: 1rem; font-weight: 600; color: #f1f5f9; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
    .card h2::before { content: ''; width: 4px; height: 20px; background: #3b82f6; border-radius: 2px; }
    .status { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 10px; }
    .status.active { background: #22c55e; box-shadow: 0 0 8px #22c55e; }
    .status.inactive { background: #ef4444; box-shadow: 0 0 8px #ef4444; }
    .row { display: flex; align-items: center; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #334155; }
    .row:last-child { border-bottom: none; }
    .tabs { display: flex; gap: 8px; margin-bottom: 16px; }
    .tabs button { padding: 10px 18px; border: 1px solid #475569; background: #0f172a; color: #94a3b8; border-radius: 8px; cursor: pointer; font-size: 0.875rem; font-weight: 500; }
    .tabs button:hover { background: #1e293b; color: #e2e8f0; }
    .tabs button.active { background: #3b82f6; border-color: #3b82f6; color: #fff; }
    button.act { padding: 8px 14px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; cursor: pointer; font-size: 0.8125rem; font-weight: 500; }
    button.act:hover { background: #2563eb; }
    pre { background: #0f172a; padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 12px; line-height: 1.5; white-space: pre-wrap; color: #cbd5e1; border: 1px solid #334155; min-height: 200px; max-height: 400px; overflow-y: auto; }
    .meta { color: #64748b; font-size: 0.8125rem; margin-bottom: 12px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
    .meta select, .meta input { padding: 8px 12px; border: 1px solid #475569; border-radius: 6px; background: #0f172a; color: #e2e8f0; font-size: 0.875rem; }
    .footer { text-align: center; padding: 24px; font-size: 0.75rem; color: #64748b; border-top: 1px solid #334155; margin-top: 24px; }
  </style>
</head>
<body>
  <header class="header">
    <h1>Secure Portal – Dashboard</h1>
    <a href="/login">Sign out</a>
  </header>
  <main class="main">
    <div class="card">
      <h2>Services</h2>
      <div class="meta"><button class="act" onclick="refresh()">Refresh</button></div>
      <div id="serviceList">Loading…</div>
    </div>
    <div class="card">
      <h2>Logs &amp; Configuration</h2>
      <div class="tabs">
        <button class="active" onclick="showTab('logs')">Logs</button>
        <button onclick="showTab('config')">Configuration</button>
      </div>
      <div id="logsTab">
        <div class="meta">Service: <select id="logService"></select> Lines: <input type="number" id="logLines" value="100" min="10" max="500" style="width:70px"> <button class="act" onclick="loadLogs()">Load logs</button></div>
        <pre id="logOutput">Select a service and click Load logs.</pre>
      </div>
      <div id="configTab" style="display:none">
        <div class="meta">Config: <select id="configSelect"></select> <button class="act" onclick="loadConfig()">Load config</button></div>
        <pre id="configOutput">Select a config and click Load config.</pre>
      </div>
    </div>
  </main>
  <footer class="footer">&copy; 2026 Secure Portal. All rights reserved.</footer>

  <script>
    function refresh() {
      fetch('/api/status').then(function(r) { return r.json(); }).then(function(d) {
        var services = d.services || [];
        var list = document.getElementById('serviceList');
        list.innerHTML = services.length ? services.map(function(s) {
          var cls = s.status === 'active' ? 'active' : 'inactive';
          var u = s.unit.replace(/'/g, "\\'");
          return '<div class="row"><span><span class="status ' + cls + '"></span>' + s.unit + ' &ndash; ' + s.status + '</span><button class="act" onclick="restartService(\'' + u + '\')">Restart</button></div>';
        }).join('') : '<p style="color:#94a3b8">No services found.</p>';
        var logSel = document.getElementById('logService');
        logSel.innerHTML = services.map(function(s) { return '<option value="' + s.unit + '">' + s.unit + '</option>'; }).join('') || '<option>—</option>';
        return fetch('/api/status');
      }).then(function(r) { return r.json(); }).then(function(d) {
        var cfg = document.getElementById('configSelect');
        var names = d.configs || [];
        cfg.innerHTML = names.map(function(n) { return '<option value="' + n + '">' + n + '</option>'; }).join('') || '<option>—</option>';
      }).catch(function(e) { document.getElementById('serviceList').innerHTML = '<p style="color:#ef4444">Error: ' + e.message + '</p>'; });
    }
    function showTab(tab) {
      document.querySelectorAll('.tabs button').forEach(function(b) { b.classList.remove('active'); });
      event.target.classList.add('active');
      document.getElementById('logsTab').style.display = tab === 'logs' ? 'block' : 'none';
      document.getElementById('configTab').style.display = tab === 'config' ? 'block' : 'none';
    }
    function loadLogs() {
      var service = document.getElementById('logService').value;
      var lines = document.getElementById('logLines').value || 100;
      fetch('/api/logs?service=' + encodeURIComponent(service) + '&lines=' + lines).then(function(r) { return r.json(); }).then(function(d) {
        document.getElementById('logOutput').textContent = d.logs || '(empty)';
      }).catch(function(e) { document.getElementById('logOutput').textContent = 'Error: ' + e.message; });
    }
    function loadConfig() {
      var name = document.getElementById('configSelect').value;
      if (!name) return;
      fetch('/api/config?name=' + encodeURIComponent(name)).then(function(r) { return r.json(); }).then(function(d) {
        document.getElementById('configOutput').textContent = d.content || '(empty)';
      }).catch(function(e) { document.getElementById('configOutput').textContent = 'Error: ' + e.message; });
    }
    function restartService(unit) {
      fetch('/api/restart', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ service: unit }) })
        .then(function(r) { return r.json(); }).then(function(d) { if (d.ok) refresh(); else alert(d.error || 'Failed'); }).catch(function(e) { alert(e.message); });
    }
    refresh();
    setInterval(refresh, 10000);
  </script>
</body>
</html>
"""


def main():
    port = DEFAULT_PORT
    bind = DEFAULT_BIND
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--port" and i + 2 < len(sys.argv):
            port = int(sys.argv[i + 2])
        elif arg == "--bind" and i + 2 < len(sys.argv):
            bind = sys.argv[i + 2]

    if os.geteuid() != 0:
        print("Warning: Run as root to read systemd and /etc/paqet", file=sys.stderr)

    server = HTTPServer((bind, port), DashboardHandler)
    print("Paqet Dashboard: http://{}:{}/login (Ctrl+C to stop)".format(bind, port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    server.server_close()


if __name__ == "__main__":
    main()
