import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from routers.auth import get_current_user
from models import WarehouseCreate, LocationCreate

router = APIRouter(prefix="/warehouses", tags=["warehouses"])


@router.get("")
def list_warehouses(db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    rows = db.execute("""
        SELECT w.*, COUNT(l.id) as location_count
        FROM warehouses w
        LEFT JOIN locations l ON l.warehouse_id = w.id
        GROUP BY w.id
        ORDER BY w.created_at DESC
    """).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=201)
def create_warehouse(data: WarehouseCreate, db: sqlite3.Connection = Depends(get_db), user=Depends(get_current_user)):
    existing = db.execute("SELECT id FROM warehouses WHERE code = ?", (data.code,)).fetchone()
    if existing:
        raise HTTPException(400, detail="Warehouse code already exists")
    db.execute(
        "INSERT INTO warehouses (name, code, address) VALUES (?, ?, ?)",
        (data.name, data.code, data.address),
    )
    db.commit()
    row = db.execute("SELECT * FROM warehouses WHERE code = ?", (data.code,)).fetchone()
    return dict(row)


@router.get("/{wh_id}")
def get_warehouse(wh_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    row = db.execute("SELECT * FROM warehouses WHERE id = ?", (wh_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Warehouse not found")
    return dict(row)


@router.put("/{wh_id}")
def update_warehouse(wh_id: int, data: WarehouseCreate, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    db.execute(
        "UPDATE warehouses SET name=?, code=?, address=? WHERE id=?",
        (data.name, data.code, data.address, wh_id),
    )
    db.commit()
    return dict(db.execute("SELECT * FROM warehouses WHERE id=?", (wh_id,)).fetchone())


@router.delete("/{wh_id}")
def delete_warehouse(wh_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    db.execute("UPDATE warehouses SET is_active=0 WHERE id=?", (wh_id,))
    db.commit()
    return {"message": "Warehouse deactivated"}


# ── Locations ─────────────────────────────────────────────────────────────────

@router.get("/{wh_id}/locations")
def list_locations(wh_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    rows = db.execute("SELECT * FROM locations WHERE warehouse_id=? ORDER BY name", (wh_id,)).fetchall()
    return [dict(r) for r in rows]


@router.post("/{wh_id}/locations", status_code=201)
def create_location(wh_id: int, data: LocationCreate, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    db.execute(
        "INSERT INTO locations (warehouse_id, name, code) VALUES (?, ?, ?)",
        (wh_id, data.name, data.code),
    )
    db.commit()
    row = db.execute("SELECT * FROM locations WHERE warehouse_id=? AND code=?", (wh_id, data.code)).fetchone()
    return dict(row)


@router.get("/locations/all")
def all_locations(db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    rows = db.execute("""
        SELECT l.*, w.name as warehouse_name, w.code as warehouse_code
        FROM locations l
        JOIN warehouses w ON w.id = l.warehouse_id
        ORDER BY w.name, l.name
    """).fetchall()
    return [dict(r) for r in rows]
