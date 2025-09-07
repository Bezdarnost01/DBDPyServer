# test.py
import httpx
import webbrowser
import threading
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

API_BASE = "https://dbdclub.live"   # без завершающего /
API_PREFIX = "/api/v"               # у тебя так
TIMEOUT = 15.0

HOST = "127.0.0.1"
PORT = 5005
LOCAL_CB = f"http://{HOST}:{PORT}/callback"
LOCAL_REALM = f"http://{HOST}:{PORT}"

httpd = None  # будет создан ниже

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        from html import escape
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query, keep_blank_values=True)

        cb_url = f"{API_BASE}{API_PREFIX}/auth/provider/steam/launcher-callback"
        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                r = client.get(cb_url, params=qs)
                r.raise_for_status()
            data = r.json()
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"Ошибка запроса к API: {escape(str(e))}".encode("utf-8"))
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return

        name = data.get("name") or "безымянный"
        steam_id = data.get("steam_id")
        user_id = data.get("user_id")

        print(f"\n[OK] Привет, {name}! (steam_id={steam_id}, user_id={user_id})")

        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, *args, **kwargs):
        return

def build_local_auth_url(auth_url: str) -> str:
    """
    Меняем в выдаваемой сервером ссылке:
      - openid.return_to -> LOCAL_CB
      - openid.realm     -> LOCAL_REALM
    и корректно пересобираем URL.
    """
    parts = urlparse(auth_url)
    qs = parse_qs(parts.query, keep_blank_values=True)

    qs["openid.return_to"] = [LOCAL_CB]
    qs["openid.realm"] = [LOCAL_REALM]

    new_query = urlencode(qs, doseq=True)
    return urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, new_query, parts.fragment))

def main():
    global httpd

    # 1) поднимаем локальный сервер (в отдельном НЕ-daemon потоке)
    httpd = HTTPServer((HOST, PORT), CallbackHandler)
    t = threading.Thread(target=httpd.serve_forever, daemon=False)
    t.start()

    # 2) берём auth_url с твоего API
    url = f"{API_BASE}{API_PREFIX}/auth/provider/steam/launcher-url"
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.get(url)
            r.raise_for_status()
        auth_url = r.json().get("auth_url")
    except Exception as e:
        print(f"[ERR] не смог получить launcher-url: {e}")
        # выключим сервер, если подняли
        try:
            httpd.shutdown()
        except Exception:
            pass
        sys.exit(1)

    if not auth_url:
        print("[ERR] сервер не вернул auth_url")
        try:
            httpd.shutdown()
        except Exception:
            pass
        sys.exit(2)

    # 3) перестраиваем ссылку под локальный колбэк и realm
    local_auth_url = build_local_auth_url(auth_url)

    print(f"[INFO] Открываю браузер для авторизации...")
    print(f"[INFO] Жду колбэка по {LOCAL_CB} ...\n")
    webbrowser.open(local_auth_url)

    # 4) БЛОКИРУЕМСЯ, пока не придёт колбэк (shutdown в handler)
    t.join()
    print("\n[INFO] Колбэк получен, выходим.")

if __name__ == "__main__":
    main()
