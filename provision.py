# provision.py - WiFi AP mode provisioning
# Single-threaded captive portal: DNS + HTTP via select.poll()
# Tests credentials via STA while AP stays up (CYW43 supports both).

import network
import socket
import select
import time
import os

AP_SSID = "Cistern-Setup"
AP_PASSWORD = "cistern123"
CONFIG_FILE = "config.py"

SETUP_PAGE = (
    "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n"
    "<!DOCTYPE html><html><head>"
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    "<title>Cistern Setup</title><style>"
    "*{margin:0;padding:0;box-sizing:border-box}"
    "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
    "background:#0f172a;color:#e2e8f0;min-height:100vh;padding:20px}"
    ".wrap{max-width:400px;margin:0 auto}"
    ".card{background:#1e293b;border-radius:16px;padding:24px;margin-bottom:16px}"
    "h1{text-align:center;font-size:1.4rem;margin-bottom:20px;color:#38bdf8}"
    ".icon{text-align:center;font-size:2.5rem;margin-bottom:8px}"
    "label{display:block;margin-top:16px;font-size:.875rem;color:#94a3b8;font-weight:600}"
    "input{width:100%;padding:12px;margin-top:6px;border:1px solid #334155;border-radius:10px;"
    "font-size:16px;background:#0f172a;color:#e2e8f0;outline:none}"
    "input:focus{border-color:#38bdf8}"
    "button{width:100%;padding:14px;margin-top:24px;background:#38bdf8;color:#0f172a;"
    "border:none;border-radius:10px;font-size:1rem;font-weight:700;cursor:pointer}"
    "button:active{background:#0ea5e9}"
    ".msg{padding:12px;border-radius:10px;margin-bottom:16px;text-align:center;font-weight:600}"
    ".err{background:#7f1d1d;color:#fca5a5;border:1px solid #991b1b}"
    ".sub{text-align:center;margin-top:16px;font-size:.8rem;color:#64748b}"
    "</style></head><body><div class=wrap>"
    '<div class="icon">&#x1F4A7;</div>'
    "<h1>Cistern Setup</h1>"
    '<div class="card">'
    "__MSG__"
    '<form method="POST" action="http://192.168.4.1/save">'
    "<label>WiFi Network Name</label>"
    '<input name="ssid" value="__PREV_SSID__" placeholder="Your WiFi SSID" required>'
    "<label>WiFi Password</label>"
    '<input type="password" name="password" placeholder="Enter password" required>'
    '<button type="submit">Test &amp; Save</button>'
    "</form></div>"
    '<p class="sub">Cistern Monitor &middot; WiFi Setup</p>'
    "</div></body></html>"
)

TESTING_PAGE = (
    "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n"
    "<!DOCTYPE html><html><head>"
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<meta http-equiv="refresh" content="20;url=http://192.168.4.1/result">'
    "<title>Testing...</title><style>"
    "*{margin:0;padding:0;box-sizing:border-box}"
    "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
    "background:#0f172a;color:#e2e8f0;min-height:100vh;padding:20px}"
    ".wrap{max-width:400px;margin:0 auto;text-align:center}"
    ".card{background:#1e293b;border-radius:16px;padding:32px;margin-bottom:16px}"
    "h1{font-size:1.4rem;margin-bottom:20px;color:#38bdf8}"
    ".spin{font-size:3rem;animation:spin 1.5s linear infinite;display:inline-block;margin:16px 0}"
    "@keyframes spin{to{transform:rotate(360deg)}}"
    "p{margin:8px 0;color:#94a3b8}"
    "strong{color:#e2e8f0}"
    ".sub{font-size:.8rem;color:#64748b;margin-top:16px}"
    "</style></head><body><div class=wrap>"
    '<div class="card">'
    "<h1>Testing WiFi</h1>"
    '<p class="spin">&#x1F4A7;</p>'
    "<p>Connecting to <strong>__SSID__</strong></p>"
    "<p>This takes about 15 seconds...</p>"
    "</div>"
    '<p class="sub">Page will refresh automatically</p>'
    "</div></body></html>"
)

SUCCESS_PAGE = (
    "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n"
    "<!DOCTYPE html><html><head>"
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    "<title>Connected!</title><style>"
    "*{margin:0;padding:0;box-sizing:border-box}"
    "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
    "background:#0f172a;color:#e2e8f0;min-height:100vh;padding:20px}"
    ".wrap{max-width:400px;margin:0 auto;text-align:center}"
    ".card{background:#1e293b;border-radius:16px;padding:32px}"
    "h1{font-size:1.4rem;margin-bottom:12px;color:#4ade80}"
    ".icon{font-size:3rem;margin-bottom:16px}"
    "p{margin:8px 0;color:#94a3b8}"
    "strong{color:#e2e8f0}"
    "</style></head><body><div class=wrap>"
    '<div class="card">'
    '<div class="icon">&#x2705;</div>'
    "<h1>Connected!</h1>"
    "<p>Successfully connected to <strong>__SSID__</strong></p>"
    "<p>Credentials saved. Rebooting now...</p>"
    "</div></div></body></html>"
)


def has_config():
    try:
        from config import WIFI_SSID, WIFI_PASSWORD
        return bool(WIFI_SSID and WIFI_SSID != "your_wifi_name")
    except (ImportError, AttributeError):
        return False


def save_config(ssid, password):
    existing = {}
    try:
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, val = line.split('=', 1)
                    existing[key.strip()] = val.strip()
    except:
        pass

    existing['WIFI_SSID'] = '"{}"'.format(ssid.replace('"', '\\"'))
    existing['WIFI_PASSWORD'] = '"{}"'.format(password.replace('"', '\\"'))

    if 'OTA_BASE_URL' not in existing:
        existing['OTA_BASE_URL'] = '"https://raw.githubusercontent.com/bosmun0224/cistern/main/"'
    existing.pop('OTA_FILES', None)
    if 'FIREBASE_PROJECT_ID' not in existing:
        existing['FIREBASE_PROJECT_ID'] = '"cistern-blomquist"'
    if 'FIREBASE_API_KEY' not in existing:
        existing['FIREBASE_API_KEY'] = '"AIzaSyCMvUgbaUvekblMsrPx7Pg9sPrmgB4iPk4"'

    with open(CONFIG_FILE, 'w') as f:
        f.write("# config.py - Auto-generated by provisioning\n")
        for key, val in existing.items():
            f.write("{} = {}\n".format(key, val))
    print("Config saved: SSID=" + ssid)


def _url_decode(s):
    """Decode a URL-encoded string (handles + and all %XX sequences)."""
    s = s.replace('+', ' ')
    parts = s.split('%')
    decoded = parts[0]
    for part in parts[1:]:
        try:
            decoded += chr(int(part[:2], 16)) + part[2:]
        except (ValueError, IndexError):
            decoded += '%' + part
    return decoded


def parse_form(body):
    params = {}
    for pair in body.split('&'):
        if '=' in pair:
            key, val = pair.split('=', 1)
            params[key] = _url_decode(val)
    return params


def test_wifi(ssid, password, timeout=15):
    """Test WiFi credentials via STA interface (AP stays up). Returns (ok, reason)."""
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.connect(ssid, password)
    t = timeout
    while not sta.isconnected() and t > 0:
        time.sleep(1)
        t -= 1
    if sta.isconnected():
        ip = sta.ifconfig()[0]
        sta.disconnect()
        sta.active(False)
        return True, ip
    status = sta.status()
    reasons = {
        network.STAT_WRONG_PASSWORD: 'Wrong password',
        network.STAT_NO_AP_FOUND: 'Network not found — check the name',
        network.STAT_CONNECT_FAIL: 'Connection failed',
    }
    reason = reasons.get(status, 'Timed out ({}s)'.format(timeout))
    sta.disconnect()
    sta.active(False)
    return False, reason


def start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    time.sleep(0.5)
    ap.config(ssid=AP_SSID, password=AP_PASSWORD)
    print("AP started: " + ap.config('ssid'))
    print("IP: " + ap.ifconfig()[0])
    return ap


def _dns_reply(data, ip_bytes):
    """Build a DNS A-record response pointing all queries to our AP IP."""
    resp = data[:2] + b'\x81\x80'
    resp += b'\x00\x01\x00\x01\x00\x00\x00\x00'
    qend = 12
    while data[qend] != 0:
        qend += data[qend] + 1
    qend += 5
    resp += data[12:qend]
    resp += b'\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'
    resp += ip_bytes
    return resp


def run_server():
    """Single-threaded DNS + HTTP captive portal using select.poll().

    DNS redirects every domain lookup to the AP IP so phones/tablets
    auto-detect the captive portal and pop up the setup page.
    WiFi credentials are tested via STA while AP stays up.
    """
    from machine import Pin

    led = Pin('LED', Pin.OUT)
    ap = start_ap()
    ip = ap.ifconfig()[0]
    ip_bytes = bytes(int(b) for b in ip.split('.'))

    http = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    http.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    http.bind(('0.0.0.0', 80))
    http.listen(2)

    dns = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dns.bind(('0.0.0.0', 53))

    poller = select.poll()
    poller.register(http, select.POLLIN)
    poller.register(dns, select.POLLIN)

    print("Captive portal ready at http://" + ip)
    led.on()

    # State for credential testing
    pending_test = None   # (ssid, password) — queued after sending Testing page
    test_result = None    # (ok, ssid, detail) — filled after test completes
    last_password = ''    # remember for save_config after /result

    while True:
        # Run queued WiFi test (Testing page already sent to phone)
        if pending_test:
            ssid, password = pending_test
            last_password = password
            pending_test = None
            print("Testing WiFi: " + ssid)
            ok, detail = test_wifi(ssid, password)
            if ok:
                print("WiFi test OK: " + detail)
                test_result = (True, ssid, detail)
            else:
                print("WiFi test FAILED: " + detail)
                test_result = (False, ssid, detail)

        for sock, ev in poller.poll(1000):
            try:
                if sock is dns:
                    data, addr = dns.recvfrom(256)
                    if len(data) > 12:
                        dns.sendto(_dns_reply(data, ip_bytes), addr)

                elif sock is http:
                    conn, addr = http.accept()
                    try:
                        request = conn.recv(2048).decode()

                        if 'POST /save' in request:
                            if '\r\n\r\n' in request:
                                header_part, body = request.split('\r\n\r\n', 1)
                            else:
                                header_part = request
                                body = ''

                            content_length = 0
                            for line in header_part.split('\r\n'):
                                if line.lower().startswith('content-length:'):
                                    content_length = int(line.split(':')[1].strip())

                            while len(body) < content_length:
                                body += conn.recv(1024).decode()

                            print("POST body: " + body)
                            params = parse_form(body)
                            ssid = params.get('ssid', '')
                            password = params.get('password', '')

                            if ssid:
                                response = TESTING_PAGE.replace('__SSID__', ssid)
                                conn.sendall(response)
                                conn.close()
                                pending_test = (ssid, password)
                                test_result = None
                            else:
                                conn.sendall("HTTP/1.1 400 Bad Request\r\n\r\nMissing SSID")
                                conn.close()

                        elif 'GET /result' in request and test_result:
                            ok, ssid, detail = test_result
                            if ok:
                                save_config(ssid, last_password)
                                response = SUCCESS_PAGE.replace('__SSID__', ssid)
                                conn.sendall(response)
                                conn.close()
                                print("Credentials verified + saved, rebooting...")
                                time.sleep(2)
                                ap.active(False)
                                import machine
                                machine.reset()
                            else:
                                msg = '<div class="msg err">' + detail + '</div>'
                                page = SETUP_PAGE.replace('__MSG__', msg).replace('__PREV_SSID__', ssid)
                                conn.sendall(page)
                                conn.close()
                                test_result = None

                        elif 'GET /result' in request:
                            response = TESTING_PAGE.replace('__SSID__', '...')
                            conn.sendall(response)
                            conn.close()

                        else:
                            page = SETUP_PAGE.replace('__MSG__', '').replace('__PREV_SSID__', '')
                            conn.sendall(page)
                            conn.close()
                    except Exception as e:
                        print("HTTP error: " + str(e))
                        try:
                            conn.close()
                        except:
                            pass

            except Exception as e:
                print("Poll error: " + str(e))
