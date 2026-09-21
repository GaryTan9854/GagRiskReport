import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

from database import init_db
from routers import auth, report, transactions, positions, prices, import_, transfers

init_db()

app = FastAPI(title="GAG Global Risk Report", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3010",
        "https://gaglobal.visadelab.xyz",
        "https://visadelab.xyz",
        "https://portal.visadelab.xyz",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/api")
app.include_router(report.router,       prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(positions.router,    prefix="/api")
app.include_router(prices.router,       prefix="/api")
app.include_router(import_.router,      prefix="/api")
app.include_router(transfers.router,    prefix="/api")

APP_VERSION = "2.7"


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "GagRiskReport", "version": APP_VERSION}


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        # ★ 先送真的存在的檔案（manifest.json / icon-*.png / pwa.js / sw.js），再退回 SPA。
        #   realpath + 前綴檢查缺一不可：少了它，`..%2f..%2f` 就能讀到 static/ 以外的
        #   任何檔案（.env、gag_risk.db、~/.cloudflared/ 憑證、/etc/passwd 都試出來過）。
        #   2026-09-20 與 TunaWealth／TunaTravel／TunaTCM／TunaRecipe 同一段一起補。
        if full_path:
            root = os.path.realpath(STATIC_DIR)
            candidate = os.path.realpath(os.path.join(root, full_path))
            if candidate.startswith(root + os.sep) and os.path.isfile(candidate):
                return FileResponse(candidate)
        index = os.path.join(STATIC_DIR, "index.html")
        return FileResponse(index) if os.path.exists(index) else {"error": "Frontend not built"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "3010"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
