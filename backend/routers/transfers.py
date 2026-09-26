import sqlite3
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from routers.auth import get_current_user
from routers.products import _ledger_entry
from models import TransferCreate

router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.get("")
def list_transfers(db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    rows = db.execute("""
        SELECT t.*,
               fl.name as from_location_name, fw.name as from_warehouse_name,
               tl.name as to_location_name, tw.name as to_warehouse_name,
               u.name as created_by_name, COUNT(trl.id) as line_count
        FROM transfers t
        LEFT JOIN locations fl ON fl.id = t.from_location_id
        LEFT JOIN warehouses fw ON fw.id = fl.warehouse_id
        LEFT JOIN locations tl ON tl.id = t.to_location_id
        LEFT JOIN warehouses tw ON tw.id = tl.warehouse_id
        LEFT JOIN users u ON u.id = t.created_by
        LEFT JOIN transfer_lines trl ON trl.transfer_id = t.id
        GROUP BY t.id
        ORDER BY t.created_at DESC
    """).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=201)
def create_transfer(data: TransferCreate, db: sqlite3.Connection = Depends(get_db), user=Depends(get_current_user)):
    if data.from_location_id == data.to_location_id:
        raise HTTPException(400, "Source and destination cannot be the same")
    cnt = db.execute("SELECT COUNT(*) as cnt FROM transfers").fetchone()["cnt"]
    code = f"TRF-{str(cnt + 1).zfill(4)}"
    db.execute(
        "INSERT INTO transfers (code, from_location_id, to_location_id, notes, created_by) VALUES (?,?,?,?,?)",
        (code, data.from_location_id, data.to_location_id, data.notes, user["id"]),
    )
    transfer_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    for line in data.lines:
        db.execute(
            "INSERT INTO transfer_lines (transfer_id, product_id, quantity) VALUES (?,?,?)",
            (transfer_id, line.product_id, line.quantity),
        )
    db.commit()
    return _get_transfer(transfer_id, db)


@router.get("/{transfer_id}")
def get_transfer(transfer_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    return _get_transfer(transfer_id, db)


def _get_transfer(transfer_id, db):
    row = db.execute("""
        SELECT t.*,
               fl.name as from_location_name, fw.name as from_warehouse_name,
               tl.name as to_location_name, tw.name as to_warehouse_name,
               u.name as created_by_name
        FROM transfers t
        LEFT JOIN locations fl ON fl.id = t.from_location_id
        LEFT JOIN warehouses fw ON fw.id = fl.warehouse_id
        LEFT JOIN locations tl ON tl.id = t.to_location_id
        LEFT JOIN warehouses tw ON tw.id = tl.warehouse_id
        LEFT JOIN users u ON u.id = t.created_by
        WHERE t.id = ?
    """, (transfer_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Transfer not found")
    transfer = dict(row)
    lines = db.execute("""
        SELECT tl.*, p.name as product_name, p.sku, p.unit_of_measure,
               COALESCE(s.quantity, 0) as available_stock
        FROM transfer_lines tl
        JOIN products p ON p.id = tl.product_id
        LEFT JOIN stock s ON s.product_id = tl.product_id AND s.location_id = ?
        WHERE tl.transfer_id = ?
    """, (transfer["from_location_id"], transfer_id)).fetchall()
    transfer["lines"] = [dict(l) for l in lines]
    return transfer


@router.post("/{transfer_id}/validate")
def validate_transfer(transfer_id: int, db: sqlite3.Connection = Depends(get_db), user=Depends(get_current_user)):
    row = db.execute("SELECT * FROM transfers WHERE id=?", (transfer_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Transfer not found")
    if row["status"] != "draft":
        raise HTTPException(400, f"Transfer is already {row['status']}")

    lines = db.execute("SELECT * FROM transfer_lines WHERE transfer_id=?", (transfer_id,)).fetchall()
    if not lines:
        raise HTTPException(400, "No line items")

    code = row["code"]
    from_loc = row["from_location_id"]
    to_loc = row["to_location_id"]

    for line in lines:
        # Check stock at source
        stock = db.execute(
            "SELECT quantity FROM stock WHERE product_id=? AND location_id=?",
            (line["product_id"], from_loc),
        ).fetchone()
        available = stock["quantity"] if stock else 0
        if available < line["quantity"]:
            product = db.execute("SELECT name FROM products WHERE id=?", (line["product_id"],)).fetchone()
            raise HTTPException(400, f"Insufficient stock for {product['name']}: need {line['quantity']}, have {available}")

        # Deduct from source
        _ledger_entry(db, line["product_id"], from_loc, -line["quantity"],
                      "transfer_out", transfer_id, code, user["id"], f"Transfer out: {code}")
        # Add to destination
        _ledger_entry(db, line["product_id"], to_loc, line["quantity"],
                      "transfer_in", transfer_id, code, user["id"], f"Transfer in: {code}")

    validated_at = datetime.now(timezone.utc).isoformat()
    db.execute("UPDATE transfers SET status='done', validated_at=? WHERE id=?", (validated_at, transfer_id))
    db.commit()
    return _get_transfer(transfer_id, db)


@router.post("/{transfer_id}/cancel")
def cancel_transfer(transfer_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    row = db.execute("SELECT * FROM transfers WHERE id=?", (transfer_id,)).fetchone()
    if not row or row["status"] == "done":
        raise HTTPException(400, "Cannot cancel a completed transfer")
    db.execute("UPDATE transfers SET status='cancelled' WHERE id=?", (transfer_id,))
    db.commit()
    return {"message": "Transfer cancelled"}
