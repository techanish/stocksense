from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routers import (
    auth,
    warehouses,
    categories,
    products,
    receipts,
    deliveries,
    transfers,
    adjustments,
    dashboard,
    reports,
)

app = FastAPI(
    title="StockSense API",
    description="Modular Inventory Management System API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "StockSense Backend"}

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(warehouses.router, prefix="/api/warehouses", tags=["Warehouses"])
app.include_router(categories.router, prefix="/api/categories", tags=["Categories"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(receipts.router, prefix="/api/receipts", tags=["Receipts"])
app.include_router(deliveries.router, prefix="/api/deliveries", tags=["Deliveries"])
app.include_router(transfers.router, prefix="/api/transfers", tags=["Transfers"])
app.include_router(adjustments.router, prefix="/api/adjustments", tags=["Adjustments"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
