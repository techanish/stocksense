import sqlite3
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from routers.auth import get_current_user
from routers.products import _ledger_entry
from models import ReceiptCreate, ReceiptUpdate

router = APIRouter(prefix="/receipts", tags=["receipts"])


def _next_code(db, prefix, table):
    row = db.execute(f"SELECT COUNT(*) as cnt FROM {table}").fetchone()
    return f"{prefix}-{str(row['cnt'] + 1).zfill(4)}"


@router.get("")
def list_receipts(db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    rows = db.execute("""
        SELECT r.*, w.name as warehouse_name, u.name as created_by_name,
               COUNT(rl.id) as line_count
        FROM receipts r
        LEFT JOIN warehouses w ON w.id = r.warehouse_id
        LEFT JOIN users u ON u.id = r.created_by
        LEFT JOIN receipt_lines rl ON rl.receipt_id = r.id
        GROUP BY r.id
        ORDER BY r.created_at DESC
    """).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=201)
def create_receipt(data: ReceiptCreate, db: sqlite3.Connection = Depends(get_db), user=Depends(get_current_user)):
    code = _next_code(db, "REC", "receipts")
    db.execute(
        "INSERT INTO receipts (code, supplier, warehouse_id, notes, created_by) VALUES (?,?,?,?,?)",
        (code, data.supplier, data.warehouse_id, data.notes, user["id"]),
    )
    receipt_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    for line in data.lines:
        db.execute(
            "INSERT INTO receipt_lines (receipt_id, product_id, location_id, quantity_expected, quantity_received) VALUES (?,?,?,?,?)",
            (receipt_id, line.product_id, line.location_id, line.quantity_expected, line.quantity_received or 0),
        )
    db.commit()
    return _get_receipt(receipt_id, db)


@router.get("/{receipt_id}")
def get_receipt(receipt_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    return _get_receipt(receipt_id, db)


def _get_receipt(receipt_id, db):
    row = db.execute("""
        SELECT r.*, w.name as warehouse_name, u.name as created_by_name
        FROM receipts r
        LEFT JOIN warehouses w ON w.id = r.warehouse_id
        LEFT JOIN users u ON u.id = r.created_by
        WHERE r.id = ?
    """, (receipt_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Receipt not found")
    receipt = dict(row)
    lines = db.execute("""
        SELECT rl.*, p.name as product_name, p.sku, p.unit_of_measure,
               l.name as location_name
        FROM receipt_lines rl
        JOIN products p ON p.id = rl.product_id
        JOIN locations l ON l.id = rl.location_id
        WHERE rl.receipt_id = ?
    """, (receipt_id,)).fetchall()
    receipt["lines"] = [dict(l) for l in lines]
    return receipt


@router.put("/{receipt_id}")
def update_receipt(receipt_id: int, data: ReceiptUpdate, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    row = db.execute("SELECT * FROM receipts WHERE id=?", (receipt_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Receipt not found")
    if row["status"] != "draft":
        raise HTTPException(400, "Only draft receipts can be edited")

    if data.supplier is not None:
        db.execute("UPDATE receipts SET supplier=? WHERE id=?", (data.supplier, receipt_id))
    if data.notes is not None:
        db.execute("UPDATE receipts SET notes=? WHERE id=?", (data.notes, receipt_id))
    if data.lines is not None:
        db.execute("DELETE FROM receipt_lines WHERE receipt_id=?", (receipt_id,))
        for line in data.lines:
            db.execute(
                "INSERT INTO receipt_lines (receipt_id, product_id, location_id, quantity_expected, quantity_received) VALUES (?,?,?,?,?)",
                (receipt_id, line.product_id, line.location_id, line.quantity_expected, line.quantity_received or 0),
            )
    db.commit()
    return _get_receipt(receipt_id, db)


@router.post("/{receipt_id}/validate")
def validate_receipt(receipt_id: int, db: sqlite3.Connection = Depends(get_db), user=Depends(get_current_user)):
    row = db.execute("SELECT * FROM receipts WHERE id=?", (receipt_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Receipt not found")
    if row["status"] != "draft":
        raise HTTPException(400, f"Receipt is already {row['status']}")

    lines = db.execute("SELECT * FROM receipt_lines WHERE receipt_id=?", (receipt_id,)).fetchall()
    if not lines:
        raise HTTPException(400, "Receipt has no line items")

    receipt_code = row["code"]
    for line in lines:
        qty = line["quantity_received"] or line["quantity_expected"]
        if qty > 0:
            _ledger_entry(
                db, line["product_id"], line["location_id"],
                qty, "receipt", receipt_id, receipt_code,
                user["id"], f"Goods receipt: {receipt_code}",
            )

    validated_at = datetime.now(timezone.utc).isoformat()
    db.execute(
        "UPDATE receipts SET status='validated', validated_at=? WHERE id=?",
        (validated_at, receipt_id),
    )
    db.commit()
    return _get_receipt(receipt_id, db)


@router.post("/{receipt_id}/cancel")
def cancel_receipt(receipt_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    row = db.execute("SELECT * FROM receipts WHERE id=?", (receipt_id,)).fetchone()
    if not row or row["status"] == "validated":
        raise HTTPException(400, "Cannot cancel a validated receipt")
    db.execute("UPDATE receipts SET status='cancelled' WHERE id=?", (receipt_id,))
    db.commit()
    return {"message": "Receipt cancelled"}
