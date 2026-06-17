from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.routes import cupons, pedidos, produtos, views
from fastapi.responses import FileResponse

BASE_DIR = Path(__file__).resolve().parents[1]

init_db()

app = FastAPI(
    title="Sistema de pedidos de cafeteria",
    description="API para gerenciamento de pedidos",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(produtos.router)
app.include_router(cupons.router)
app.include_router(pedidos.router)
app.include_router(views.router)

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(
        BASE_DIR / "static" / "favicon.svg",
        media_type="image/svg+xml",
    )

@app.get("/", tags=["root"])
def read_root():
    return {
        "mensagem": "Sistema de pedidos de cafeteria",
        "docs": "/docs",
        "redoc": "/redoc",
    }

@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
