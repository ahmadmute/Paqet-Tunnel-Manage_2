#!/usr/bin/env python3
"""
Paqet - Decoy website on port 443
Serves a fake corporate/portal page so DPI or scanners see a normal site.
Python 3 stdlib only. Run as root: python3 paqet-decoy.py [--port 443] [--bind 0.0.0.0]
"""
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

DEFAULT_PORT = 443
DEFAULT_BIND = "0.0.0.0"

FAKE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Secure Portal – Enterprise Access</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Inter', system-ui, sans-serif; background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%); color: #e2e8f0; min-height: 100vh; line-height: 1.6; }
    .header { background: rgba(30, 41, 59, 0.95); border-bottom: 1px solid #334155; padding: 16px 32px; display: flex; align-items: center; justify-content: space-between; }
    .header h1 { font-size: 1.25rem; font-weight: 700; color: #f8fafc; }
    .header nav { display: flex; gap: 24px; }
    .header a { color: #94a3b8; text-decoration: none; font-size: 0.9375rem; }
    .header a:hover { color: #3b82f6; }
    .hero { max-width: 800px; margin: 0 auto; padding: 80px 24px 60px; text-align: center; }
    .hero h2 { font-size: 2rem; font-weight: 700; color: #f8fafc; margin-bottom: 16px; letter-spacing: -0.02em; }
    .hero p { font-size: 1.125rem; color: #94a3b8; margin-bottom: 32px; }
    .cta { display: inline-block; padding: 14px 28px; background: linear-gradient(180deg, #3b82f6, #2563eb); color: #fff; text-decoration: none; border-radius: 10px; font-weight: 600; font-size: 1rem; }
    .cta:hover { background: linear-gradient(180deg, #60a5fa, #3b82f6); }
    .features { max-width: 900px; margin: 0 auto; padding: 40px 24px 60px; display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 24px; }
    .feature { background: rgba(30, 41, 59, 0.6); border: 1px solid #334155; border-radius: 12px; padding: 24px; }
    .feature h3 { font-size: 1rem; font-weight: 600; color: #f1f5f9; margin-bottom: 8px; }
    .feature p { font-size: 0.875rem; color: #94a3b8; }
    .footer { text-align: center; padding: 32px; font-size: 0.8125rem; color: #64748b; border-top: 1px solid #334155; }
  </style>
</head>
<body>
  <header class="header">
    <h1>Secure Portal</h1>
    <nav><a href="/">Home</a><a href="/login">Sign in</a><a href="/">Support</a></nav>
  </header>
  <section class="hero">
    <h2>Enterprise-grade secure access</h2>
    <p>Connect to your organization's resources safely and reliably.</p>
    <a href="/login" class="cta">Sign in</a>
  </section>
  <section class="features">
    <div class="feature"><h3>Secure access</h3><p>Encrypted connections for all services.</p></div>
    <div class="feature"><h3>24/7 availability</h3><p>Always-on infrastructure.</p></div>
    <div class="feature"><h3>Compliance ready</h3><p>Built for enterprise requirements.</p></div>
  </section>
  <footer class="footer">&copy; 2026 Secure Portal. All rights reserved.</footer>
</body>
</html>
"""

FAKE_LOGIN_HTML = """<!DOCTYPE html>
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
    .logo h1 { font-size: 1.5rem; font-weight: 700; color: #f8fafc; }
    .logo p { font-size: 0.875rem; color: #94a3b8; margin-top: 6px; }
    label { display: block; font-size: 0.875rem; font-weight: 500; color: #cbd5e1; margin-bottom: 8px; }
    input { width: 100%; padding: 12px 16px; border: 1px solid #475569; border-radius: 10px; background: #0f172a; color: #f1f5f9; font-size: 1rem; margin-bottom: 18px; outline: none; }
    .btn { width: 100%; padding: 14px; background: linear-gradient(180deg, #3b82f6, #2563eb); color: #fff; border: none; border-radius: 10px; font-size: 1rem; font-weight: 600; cursor: pointer; }
    .btn:hover { background: linear-gradient(180deg, #60a5fa, #3b82f6); }
    .foot { text-align: center; margin-top: 24px; font-size: 0.75rem; color: #64748b; }
    .foot a { color: #3b82f6; text-decoration: none; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="logo">
        <h1>Secure Portal</h1>
        <p>Sign in to access your account</p>
      </div>
      <form method="get" action="#">
        <label for="u">Username</label>
        <input type="text" id="u" name="username" placeholder="Enter username">
        <label for="p">Password</label>
        <input type="password" id="p" name="password" placeholder="Enter password">
        <button type="submit" class="btn">Sign in</button>
      </form>
    </div>
    <p class="foot"><a href="/">Back to home</a></p>
  </div>
</body>
</html>
"""


class DecoyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/" or path == "/index.html" or path.startswith("/?"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(FAKE_HTML.encode("utf-8"))
        elif path == "/login":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(FAKE_LOGIN_HTML.encode("utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(FAKE_HTML.encode("utf-8"))


def main():
    port = DEFAULT_PORT
    bind = DEFAULT_BIND
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--port" and i + 2 < len(sys.argv):
            port = int(sys.argv[i + 2])
        elif arg == "--bind" and i + 2 < len(sys.argv):
            bind = sys.argv[i + 2]

    if port < 1024 and os.geteuid() != 0:
        print("Run as root to bind to port {}".format(port), file=sys.stderr)
        sys.exit(1)

    try:
        server = HTTPServer((bind, port), DecoyHandler)
    except OSError as e:
        if "Address already in use" in str(e) or e.errno == 98:
            print("Port {} is already in use. Stop the other service or use another port.".format(port), file=sys.stderr)
        else:
            print("Error: {}".format(e), file=sys.stderr)
        sys.exit(1)

    print("Decoy website: http://{}:{}/ (Ctrl+C to stop)".format(bind, port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
