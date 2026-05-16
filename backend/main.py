import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

from database import init_db
from routers import auth, report, transactions, positions, prices, import_

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

APP_VERSION = "1.8"


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "GagRiskReport", "version": APP_VERSION}


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        index = os.path.join(STATIC_DIR, "index.html")
        return FileResponse(index) if os.path.exists(index) else {"error": "Frontend not built"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "3010"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
