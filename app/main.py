from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routes import cupons, pedidos, produtos

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

app.include_router(produtos.router)
app.include_router(cupons.router)
app.include_router(pedidos.router)

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
