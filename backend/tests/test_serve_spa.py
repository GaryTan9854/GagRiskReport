#!/usr/bin/env python3
"""serve_spa 的守門測試（零依賴，這個 venv 裡沒有 pytest／httpx）。

    cd backend && ./venv/bin/python tests/test_serve_spa.py

守兩件事：
1. 路徑穿越 —— `..%2f` 系列不准讀到 static/ 以外的檔案。2026-09-20 修之前，
   `/%2e%2e%2f%2e%2e%2fdeploy.sh` 與 6 層的 `/etc/passwd` 都是 200 加真實內容，
   等於 backend/.env、gag_risk.db、~/.cloudflared/ 憑證全都讀得到。
2. 真的存在的檔案要用自己的 content-type 送出去 —— 被 SPA fallback 吃掉的話
   manifest.json 會拿到 200 + text/html，瀏覽器靜靜地不當它是 manifest
   （只看狀態碼會全綠，一定要看 content-type）。

自動起一個 uvicorn 打真的 HTTP：路徑編碼這一段的行為在 uvicorn/starlette 手上，
單元測 realpath 邏輯驗不到。
"""
import http.client
import os
import socket
import subprocess
import sys
import time

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(BACKEND, "static")
CANARY_NAME = "_test_canary_do_not_commit.txt"
CANARY_BODY = "SECRET-CANARY-DO-NOT-SERVE"

failures = []


def check(name, ok, detail=""):
    print(("  ✅ " if ok else "  ❌ ") + name + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def get(port, path):
    """不經過任何 URL 正規化，原樣送出 request line。"""
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        c.putrequest("GET", path, skip_host=True, skip_accept_encoding=True)
        c.putheader("Host", "127.0.0.1")
        c.endheaders()
        r = c.getresponse()
        return r.status, r.getheader("content-type") or "", r.read().decode("utf-8", "replace")
    finally:
        c.close()


def main():
    created = []

    def ensure(path, body, is_dir=False):
        if not os.path.exists(path):
            created.append(path)
            if is_dir:
                os.makedirs(path)
            else:
                with open(path, "w") as f:
                    f.write(body)

    ensure(STATIC, None, is_dir=True)
    ensure(os.path.join(STATIC, "assets"), None, is_dir=True)
    ensure(os.path.join(STATIC, "index.html"), "<!doctype html><title>SPA</title>")
    ensure(os.path.join(STATIC, "manifest.json"), '{"name":"GagRiskReport"}')
    # static/ 外面的誘餌，跟 .env 同一層
    canary = os.path.join(BACKEND, CANARY_NAME)
    ensure(canary, CANARY_BODY)
    # 指向 static/ 外面的 symlink：os.path.isfile 會說是，只有 realpath 擋得住
    link = os.path.join(STATIC, "_test_escape_link.txt")
    if not os.path.exists(link):
        created.append(link)
        os.symlink(canary, link)

    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1",
         "--port", str(port), "--no-access-log"],
        cwd=BACKEND, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            try:
                get(port, "/api/health")
                break
            except OSError:
                time.sleep(0.2)
        else:
            raise SystemExit("uvicorn 起不來")

        print("路徑穿越：")
        attacks = [
            "/%2e%2e%2f" + CANARY_NAME,
            "/../" + CANARY_NAME,
            "/..%2f" + CANARY_NAME,
            "/.%2e%2f" + CANARY_NAME,
            "/%2e%2e%2f%2e%2e%2fdeploy.sh",
            "/" + "%2e%2e%2f" * 8 + "etc/passwd",
            "/_test_escape_link.txt",
        ]
        for path in attacks:
            status, ctype, body = get(port, path)
            leaked = CANARY_BODY in body or "root:" in body or "REMOTE_HOST" in body
            check(path, not leaked, f"{status} 洩漏了 {body[:40]!r}")

        print("正常行為：")
        status, ctype, body = get(port, "/manifest.json")
        check("/manifest.json 回真的檔案", status == 200 and "GagRiskReport" in body, f"{status} {body[:40]!r}")
        check("/manifest.json 的 content-type 不是 html",
              "html" not in ctype, f"content-type={ctype}")
        status, _, body = get(port, "/some/spa/route")
        check("未知路徑退回 index.html", status == 200 and "<!doctype html>" in body.lower(), str(status))
        status, _, body = get(port, "/api/health")
        check("/api/health 沒被 SPA 路由吃掉", '"status"' in body, body[:60])
    finally:
        proc.terminate()
        proc.wait(timeout=10)
        for path in reversed(created):
            try:
                os.remove(path) if not os.path.isdir(path) or os.path.islink(path) else os.rmdir(path)
            except OSError:
                pass

    print()
    if failures:
        print(f"❌ {len(failures)} 項失敗：" + "、".join(failures))
        return 1
    print("✅ 全過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
