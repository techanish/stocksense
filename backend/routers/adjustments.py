import sqlite3
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from routers.auth import get_current_user
from routers.products import _ledger_entry
from models import AdjustmentCreate

router = APIRouter(prefix="/adjustments", tags=["adjustments"])


@router.get("")
def list_adjustments(db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    rows = db.execute("""
        SELECT a.*, l.name as location_name, w.name as warehouse_name,
               u.name as created_by_name, COUNT(al.id) as line_count
        FROM adjustments a
        LEFT JOIN locations l ON l.id = a.location_id
        LEFT JOIN warehouses w ON w.id = l.warehouse_id
        LEFT JOIN users u ON u.id = a.created_by
        LEFT JOIN adjustment_lines al ON al.adjustment_id = a.id
        GROUP BY a.id
        ORDER BY a.created_at DESC
    """).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=201)
def create_adjustment(data: AdjustmentCreate, db: sqlite3.Connection = Depends(get_db), user=Depends(get_current_user)):
    cnt = db.execute("SELECT COUNT(*) as cnt FROM adjustments").fetchone()["cnt"]
    code = f"ADJ-{str(cnt + 1).zfill(4)}"
    db.execute(
        "INSERT INTO adjustments (code, location_id, reason, notes, created_by) VALUES (?,?,?,?,?)",
        (code, data.location_id, data.reason, data.notes, user["id"]),
    )
    adj_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    for line in data.lines:
        # Get current recorded qty
        stock_row = db.execute(
            "SELECT quantity FROM stock WHERE product_id=? AND location_id=?",
            (line.product_id, data.location_id),
        ).fetchone()
        recorded = stock_row["quantity"] if stock_row else 0
        diff = line.quantity_counted - recorded
        db.execute(
            """INSERT INTO adjustment_lines
               (adjustment_id, product_id, quantity_recorded, quantity_counted, quantity_difference)
               VALUES (?,?,?,?,?)""",
            (adj_id, line.product_id, recorded, line.quantity_counted, diff),
        )

    db.commit()
    return _get_adjustment(adj_id, db)


@router.get("/{adj_id}")
def get_adjustment(adj_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    return _get_adjustment(adj_id, db)


def _get_adjustment(adj_id, db):
    row = db.execute("""
        SELECT a.*, l.name as location_name, w.name as warehouse_name, u.name as created_by_name
        FROM adjustments a
        LEFT JOIN locations l ON l.id = a.location_id
        LEFT JOIN warehouses w ON w.id = l.warehouse_id
        LEFT JOIN users u ON u.id = a.created_by
        WHERE a.id = ?
    """, (adj_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Adjustment not found")
    adj = dict(row)
    lines = db.execute("""
        SELECT al.*, p.name as product_name, p.sku, p.unit_of_measure
        FROM adjustment_lines al
        JOIN products p ON p.id = al.product_id
        WHERE al.adjustment_id = ?
    """, (adj_id,)).fetchall()
    adj["lines"] = [dict(l) for l in lines]
    return adj


@router.post("/{adj_id}/validate")
def validate_adjustment(adj_id: int, db: sqlite3.Connection = Depends(get_db), user=Depends(get_current_user)):
    row = db.execute("SELECT * FROM adjustments WHERE id=?", (adj_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Adjustment not found")
    if row["status"] != "draft":
        raise HTTPException(400, f"Adjustment is already {row['status']}")

    lines = db.execute("SELECT * FROM adjustment_lines WHERE adjustment_id=?", (adj_id,)).fetchall()
    if not lines:
        raise HTTPException(400, "No line items")

    code = row["code"]
    for line in lines:
        diff = line["quantity_difference"]
        if diff != 0:
            _ledger_entry(
                db, line["product_id"], row["location_id"],
                diff, "adjustment", adj_id, code,
                user["id"], f"Stock adjustment: {code} — reason: {row['reason'] or 'N/A'}",
            )

    validated_at = datetime.now(timezone.utc).isoformat()
    db.execute("UPDATE adjustments SET status='validated', validated_at=? WHERE id=?", (validated_at, adj_id))
    db.commit()
    return _get_adjustment(adj_id, db)


@router.post("/{adj_id}/cancel")
def cancel_adjustment(adj_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    row = db.execute("SELECT * FROM adjustments WHERE id=?", (adj_id,)).fetchone()
    if not row or row["status"] == "validated":
        raise HTTPException(400, "Cannot cancel a validated adjustment")
    db.execute("UPDATE adjustments SET status='cancelled' WHERE id=?", (adj_id,))
    db.commit()
    return {"message": "Adjustment cancelled"}
