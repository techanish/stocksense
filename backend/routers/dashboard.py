import sqlite3
from fastapi import APIRouter, Depends
from database import get_db
from routers.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/kpis")
def get_kpis(db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    # Total products
    total_products = db.execute(
        "SELECT COUNT(*) as cnt FROM products WHERE is_active=1"
    ).fetchone()["cnt"]

    # Total stock value (sum of all quantities)
    total_stock_qty = db.execute(
        "SELECT COALESCE(SUM(quantity), 0) as total FROM stock"
    ).fetchone()["total"]

    # Low stock items (stock <= reorder_level but > 0)
    low_stock = db.execute("""
        SELECT COUNT(DISTINCT p.id) as cnt
        FROM products p
        JOIN stock s ON s.product_id = p.id
        WHERE p.is_active=1 AND s.quantity > 0 AND s.quantity <= p.reorder_level
    """).fetchone()["cnt"]

    # Out of stock (product exists but quantity is 0 or no stock row)
    out_of_stock = db.execute("""
        SELECT COUNT(*) as cnt FROM products p
        WHERE p.is_active=1 AND (
            SELECT COALESCE(SUM(s.quantity),0) FROM stock s WHERE s.product_id=p.id
        ) = 0
    """).fetchone()["cnt"]

    # Pending receipts (draft)
    pending_receipts = db.execute(
        "SELECT COUNT(*) as cnt FROM receipts WHERE status='draft'"
    ).fetchone()["cnt"]

    # Pending deliveries (draft + waiting + ready)
    pending_deliveries = db.execute(
        "SELECT COUNT(*) as cnt FROM deliveries WHERE status IN ('draft','waiting','ready')"
    ).fetchone()["cnt"]

    # Scheduled transfers (draft)
    scheduled_transfers = db.execute(
        "SELECT COUNT(*) as cnt FROM transfers WHERE status='draft'"
    ).fetchone()["cnt"]

    # Recent operations (last 10 ledger entries)
    recent_moves = db.execute("""
        SELECT sl.*, p.name as product_name, p.sku,
               l.name as location_name, w.name as warehouse_name,
               u.name as performed_by
        FROM stock_ledger sl
        JOIN products p ON p.id = sl.product_id
        JOIN locations l ON l.id = sl.location_id
        JOIN warehouses w ON w.id = l.warehouse_id
        LEFT JOIN users u ON u.id = sl.created_by
        ORDER BY sl.created_at DESC
        LIMIT 10
    """).fetchall()

    # Operations by status (last 30 days)
    ops_summary = db.execute("""
        SELECT 'receipts' as type, status, COUNT(*) as cnt FROM receipts GROUP BY status
        UNION ALL
        SELECT 'deliveries', status, COUNT(*) FROM deliveries GROUP BY status
        UNION ALL
        SELECT 'transfers', status, COUNT(*) FROM transfers GROUP BY status
        UNION ALL
        SELECT 'adjustments', status, COUNT(*) FROM adjustments GROUP BY status
    """).fetchall()

    # Low stock products list
    low_stock_products = db.execute("""
        SELECT p.id, p.name, p.sku, p.unit_of_measure, p.reorder_level,
               c.name as category_name,
               COALESCE(SUM(s.quantity),0) as total_stock
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        LEFT JOIN stock s ON s.product_id = p.id
        WHERE p.is_active=1
        GROUP BY p.id
        HAVING total_stock <= p.reorder_level
        ORDER BY total_stock ASC
        LIMIT 10
    """).fetchall()

    return {
        "kpis": {
            "total_products": total_products,
            "total_stock_qty": round(total_stock_qty, 2),
            "low_stock_count": low_stock,
            "out_of_stock_count": out_of_stock,
            "pending_receipts": pending_receipts,
            "pending_deliveries": pending_deliveries,
            "scheduled_transfers": scheduled_transfers,
        },
        "recent_moves": [dict(r) for r in recent_moves],
        "ops_summary": [dict(r) for r in ops_summary],
        "low_stock_products": [dict(r) for r in low_stock_products],
    }
