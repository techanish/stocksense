import sqlite3
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from routers.auth import get_current_user
from routers.products import _ledger_entry
from models import DeliveryCreate, DeliveryUpdate

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


@router.get("")
def list_deliveries(db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    rows = db.execute("""
        SELECT d.*, w.name as warehouse_name, u.name as created_by_name,
               COUNT(dl.id) as line_count
        FROM deliveries d
        LEFT JOIN warehouses w ON w.id = d.warehouse_id
        LEFT JOIN users u ON u.id = d.created_by
        LEFT JOIN delivery_lines dl ON dl.delivery_id = d.id
        GROUP BY d.id
        ORDER BY d.created_at DESC
    """).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=201)
def create_delivery(data: DeliveryCreate, db: sqlite3.Connection = Depends(get_db), user=Depends(get_current_user)):
    row_cnt = db.execute("SELECT COUNT(*) as cnt FROM deliveries").fetchone()["cnt"]
    code = f"DEL-{str(row_cnt + 1).zfill(4)}"
    db.execute(
        "INSERT INTO deliveries (code, customer, warehouse_id, notes, created_by) VALUES (?,?,?,?,?)",
        (code, data.customer, data.warehouse_id, data.notes, user["id"]),
    )
    delivery_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    for line in data.lines:
        db.execute(
            "INSERT INTO delivery_lines (delivery_id, product_id, location_id, quantity_demanded, quantity_picked) VALUES (?,?,?,?,?)",
            (delivery_id, line.product_id, line.location_id, line.quantity_demanded, line.quantity_picked or 0),
        )
    db.commit()
    return _get_delivery(delivery_id, db)


@router.get("/{delivery_id}")
def get_delivery(delivery_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    return _get_delivery(delivery_id, db)


def _get_delivery(delivery_id, db):
    row = db.execute("""
        SELECT d.*, w.name as warehouse_name, u.name as created_by_name
        FROM deliveries d
        LEFT JOIN warehouses w ON w.id = d.warehouse_id
        LEFT JOIN users u ON u.id = d.created_by
        WHERE d.id = ?
    """, (delivery_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Delivery not found")
    delivery = dict(row)
    lines = db.execute("""
        SELECT dl.*, p.name as product_name, p.sku, p.unit_of_measure,
               l.name as location_name,
               COALESCE(s.quantity, 0) as available_stock
        FROM delivery_lines dl
        JOIN products p ON p.id = dl.product_id
        JOIN locations l ON l.id = dl.location_id
        LEFT JOIN stock s ON s.product_id = dl.product_id AND s.location_id = dl.location_id
        WHERE dl.delivery_id = ?
    """, (delivery_id,)).fetchall()
    delivery["lines"] = [dict(l) for l in lines]
    return delivery


@router.put("/{delivery_id}")
def update_delivery(delivery_id: int, data: DeliveryUpdate, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    row = db.execute("SELECT * FROM deliveries WHERE id=?", (delivery_id,)).fetchone()
    if not row or row["status"] not in ("draft", "waiting", "ready"):
        raise HTTPException(400, "Cannot edit this delivery")
    if data.customer is not None:
        db.execute("UPDATE deliveries SET customer=? WHERE id=?", (data.customer, delivery_id))
    if data.notes is not None:
        db.execute("UPDATE deliveries SET notes=? WHERE id=?", (data.notes, delivery_id))
    if data.lines is not None:
        db.execute("DELETE FROM delivery_lines WHERE delivery_id=?", (delivery_id,))
        for line in data.lines:
            db.execute(
                "INSERT INTO delivery_lines (delivery_id, product_id, location_id, quantity_demanded, quantity_picked) VALUES (?,?,?,?,?)",
                (delivery_id, line.product_id, line.location_id, line.quantity_demanded, line.quantity_picked or 0),
            )
    db.commit()
    return _get_delivery(delivery_id, db)


@router.post("/{delivery_id}/validate")
def validate_delivery(delivery_id: int, db: sqlite3.Connection = Depends(get_db), user=Depends(get_current_user)):
    row = db.execute("SELECT * FROM deliveries WHERE id=?", (delivery_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Delivery not found")
    if row["status"] == "done":
        raise HTTPException(400, "Delivery already completed")

    lines = db.execute("SELECT * FROM delivery_lines WHERE delivery_id=?", (delivery_id,)).fetchall()
    if not lines:
        raise HTTPException(400, "No line items")

    delivery_code = row["code"]
    for line in lines:
        qty = line["quantity_picked"] or line["quantity_demanded"]
        # Check sufficient stock
        stock_row = db.execute(
            "SELECT quantity FROM stock WHERE product_id=? AND location_id=?",
            (line["product_id"], line["location_id"]),
        ).fetchone()
        available = stock_row["quantity"] if stock_row else 0
        if available < qty:
            product = db.execute("SELECT name FROM products WHERE id=?", (line["product_id"],)).fetchone()
            raise HTTPException(400, f"Insufficient stock for {product['name']}: need {qty}, have {available}")

        _ledger_entry(
            db, line["product_id"], line["location_id"],
            -qty, "delivery", delivery_id, delivery_code,
            user["id"], f"Goods delivery: {delivery_code}",
        )

    validated_at = datetime.now(timezone.utc).isoformat()
    db.execute("UPDATE deliveries SET status='done', validated_at=? WHERE id=?", (validated_at, delivery_id))
    db.commit()
    return _get_delivery(delivery_id, db)


@router.post("/{delivery_id}/cancel")
def cancel_delivery(delivery_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    row = db.execute("SELECT * FROM deliveries WHERE id=?", (delivery_id,)).fetchone()
    if not row or row["status"] == "done":
        raise HTTPException(400, "Cannot cancel a completed delivery")
    db.execute("UPDATE deliveries SET status='cancelled' WHERE id=?", (delivery_id,))
    db.commit()
    return {"message": "Delivery cancelled"}
