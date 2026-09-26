import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_db
from routers.auth import get_current_user
from models import ProductCreate, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


def _ledger_entry(db, product_id, location_id, qty_change, op_type, ref_id, ref_code, user_id, notes=None):
    """Insert a stock ledger entry and update the stock table atomically."""
    # Upsert stock
    db.execute(
        """INSERT INTO stock (product_id, location_id, quantity)
           VALUES (?, ?, ?)
           ON CONFLICT(product_id, location_id)
           DO UPDATE SET quantity = quantity + excluded.quantity""",
        (product_id, location_id, qty_change),
    )
    # Read updated quantity
    qty_after = db.execute(
        "SELECT quantity FROM stock WHERE product_id=? AND location_id=?",
        (product_id, location_id),
    ).fetchone()["quantity"]
    # Write ledger
    db.execute(
        """INSERT INTO stock_ledger
           (product_id, location_id, quantity_change, quantity_after,
            operation_type, reference_id, reference_code, notes, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (product_id, location_id, qty_change, qty_after, op_type, ref_id, ref_code, notes, user_id),
    )
    return qty_after


@router.get("")
def list_products(
    search: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    low_stock: Optional[bool] = Query(None),
    db: sqlite3.Connection = Depends(get_db),
    _=Depends(get_current_user),
):
    base = """
        SELECT p.*,
               c.name as category_name,
               COALESCE(SUM(s.quantity), 0) as total_stock
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        LEFT JOIN stock s ON s.product_id = p.id
        WHERE p.is_active = 1
    """
    params = []
    if search:
        base += " AND (p.name LIKE ? OR p.sku LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if category_id:
        base += " AND p.category_id = ?"
        params.append(category_id)
    base += " GROUP BY p.id ORDER BY p.name"

    rows = db.execute(base, params).fetchall()
    result = [dict(r) for r in rows]

    if low_stock:
        result = [r for r in result if r["total_stock"] <= r["reorder_level"]]

    return result


@router.post("", status_code=201)
def create_product(data: ProductCreate, db: sqlite3.Connection = Depends(get_db), user=Depends(get_current_user)):
    existing = db.execute("SELECT id FROM products WHERE sku = ?", (data.sku,)).fetchone()
    if existing:
        raise HTTPException(400, "SKU already exists")

    db.execute(
        """INSERT INTO products (name, sku, category_id, unit_of_measure, reorder_level, description)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (data.name, data.sku, data.category_id, data.unit_of_measure, data.reorder_level, data.description),
    )
    product_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Handle initial stock if provided
    if data.initial_stock and data.initial_stock > 0 and data.initial_location_id:
        _ledger_entry(
            db, product_id, data.initial_location_id,
            data.initial_stock, "initial", product_id, f"INIT-{product_id}",
            user["id"], "Initial stock entry",
        )

    db.commit()
    return dict(db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone())


@router.get("/{product_id}")
def get_product(product_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    row = db.execute("""
        SELECT p.*, c.name as category_name
        FROM products p LEFT JOIN categories c ON c.id = p.category_id
        WHERE p.id = ?
    """, (product_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Product not found")
    product = dict(row)

    # Stock per location
    stock_rows = db.execute("""
        SELECT s.quantity, l.name as location_name, l.id as location_id,
               w.name as warehouse_name
        FROM stock s
        JOIN locations l ON l.id = s.location_id
        JOIN warehouses w ON w.id = l.warehouse_id
        WHERE s.product_id = ? AND s.quantity > 0
        ORDER BY w.name, l.name
    """, (product_id,)).fetchall()
    product["stock_by_location"] = [dict(r) for r in stock_rows]
    product["total_stock"] = sum(r["quantity"] for r in stock_rows)
    return product


@router.put("/{product_id}")
def update_product(product_id: int, data: ProductUpdate, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    row = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Product not found")
    current = dict(row)
    db.execute(
        """UPDATE products SET
           name=?, category_id=?, unit_of_measure=?, reorder_level=?, description=?, is_active=?
           WHERE id=?""",
        (
            data.name or current["name"],
            data.category_id if data.category_id is not None else current["category_id"],
            data.unit_of_measure or current["unit_of_measure"],
            data.reorder_level if data.reorder_level is not None else current["reorder_level"],
            data.description if data.description is not None else current["description"],
            data.is_active if data.is_active is not None else current["is_active"],
            product_id,
        ),
    )
    db.commit()
    return dict(db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone())


@router.delete("/{product_id}")
def delete_product(product_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    db.execute("UPDATE products SET is_active=0 WHERE id=?", (product_id,))
    db.commit()
    return {"message": "Product deactivated"}


@router.get("/{product_id}/stock")
def product_stock(product_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    rows = db.execute("""
        SELECT s.quantity, l.id as location_id, l.name as location_name, l.code as location_code,
               w.id as warehouse_id, w.name as warehouse_name
        FROM stock s
        JOIN locations l ON l.id = s.location_id
        JOIN warehouses w ON w.id = l.warehouse_id
        WHERE s.product_id = ?
        ORDER BY s.quantity DESC
    """, (product_id,)).fetchall()
    return [dict(r) for r in rows]
