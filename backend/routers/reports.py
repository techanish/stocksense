import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Query
from database import get_db
from routers.auth import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/ledger")
def stock_ledger(
    product_id: Optional[int] = Query(None),
    location_id: Optional[int] = Query(None),
    operation_type: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: sqlite3.Connection = Depends(get_db),
    _=Depends(get_current_user),
):
    base = """
        SELECT sl.*, p.name as product_name, p.sku, p.unit_of_measure,
               l.name as location_name, w.name as warehouse_name,
               u.name as performed_by
        FROM stock_ledger sl
        JOIN products p ON p.id = sl.product_id
        JOIN locations l ON l.id = sl.location_id
        JOIN warehouses w ON w.id = l.warehouse_id
        LEFT JOIN users u ON u.id = sl.created_by
        WHERE 1=1
    """
    params = []
    if product_id:
        base += " AND sl.product_id = ?"
        params.append(product_id)
    if location_id:
        base += " AND sl.location_id = ?"
        params.append(location_id)
    if operation_type:
        base += " AND sl.operation_type = ?"
        params.append(operation_type)
    base += " ORDER BY sl.created_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]

    rows = db.execute(base, params).fetchall()
    total = db.execute(
        "SELECT COUNT(*) as cnt FROM stock_ledger" +
        (" WHERE product_id=?" if product_id else ""),
        ([product_id] if product_id else []),
    ).fetchone()["cnt"]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "entries": [dict(r) for r in rows],
    }


@router.get("/moves")
def move_history(
    operation_type: Optional[str] = Query(None),
    warehouse_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: sqlite3.Connection = Depends(get_db),
    _=Depends(get_current_user),
):
    """Unified move history across all operation types."""
    union = """
        SELECT 'receipt' as type, r.id, r.code, r.status,
               r.supplier as counterparty, w.name as warehouse_name,
               r.created_at, u.name as created_by_name
        FROM receipts r
        LEFT JOIN warehouses w ON w.id = r.warehouse_id
        LEFT JOIN users u ON u.id = r.created_by
        {where_r}
        UNION ALL
        SELECT 'delivery', d.id, d.code, d.status,
               d.customer, w.name, d.created_at, u.name
        FROM deliveries d
        LEFT JOIN warehouses w ON w.id = d.warehouse_id
        LEFT JOIN users u ON u.id = d.created_by
        {where_d}
        UNION ALL
        SELECT 'transfer', t.id, t.code, t.status,
               NULL, fl.name || ' → ' || tl.name, t.created_at, u.name
        FROM transfers t
        LEFT JOIN locations fl ON fl.id = t.from_location_id
        LEFT JOIN locations tl ON tl.id = t.to_location_id
        LEFT JOIN users u ON u.id = t.created_by
        WHERE 1=1
        UNION ALL
        SELECT 'adjustment', a.id, a.code, a.status,
               a.reason, l.name, a.created_at, u.name
        FROM adjustments a
        LEFT JOIN locations l ON l.id = a.location_id
        LEFT JOIN users u ON u.id = a.created_by
        WHERE 1=1
    """
    # Simplified: return all, apply type filter in Python for now
    wh_filter_r = "WHERE 1=1" + (f" AND r.warehouse_id={warehouse_id}" if warehouse_id else "")
    wh_filter_d = "WHERE 1=1" + (f" AND d.warehouse_id={warehouse_id}" if warehouse_id else "")
    query = union.format(where_r=wh_filter_r, where_d=wh_filter_d)
    query += f" ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}"

    rows = db.execute(query).fetchall()
    result = [dict(r) for r in rows]
    if operation_type:
        result = [r for r in result if r["type"] == operation_type]

    return {"entries": result, "limit": limit, "offset": offset}


@router.get("/stock-snapshot")
def stock_snapshot(
    warehouse_id: Optional[int] = Query(None),
    db: sqlite3.Connection = Depends(get_db),
    _=Depends(get_current_user),
):
    """Current stock levels across all products and locations."""
    base = """
        SELECT p.id as product_id, p.name as product_name, p.sku,
               p.unit_of_measure, p.reorder_level, c.name as category_name,
               l.id as location_id, l.name as location_name,
               w.id as warehouse_id, w.name as warehouse_name,
               COALESCE(s.quantity, 0) as quantity,
               CASE
                 WHEN COALESCE(s.quantity, 0) = 0 THEN 'out_of_stock'
                 WHEN COALESCE(s.quantity, 0) <= p.reorder_level THEN 'low_stock'
                 ELSE 'in_stock'
               END as stock_status
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        CROSS JOIN locations l
        JOIN warehouses w ON w.id = l.warehouse_id
        LEFT JOIN stock s ON s.product_id = p.id AND s.location_id = l.id
        WHERE p.is_active=1 AND COALESCE(s.quantity, 0) > 0
    """
    params = []
    if warehouse_id:
        base += " AND w.id = ?"
        params.append(warehouse_id)
    base += " ORDER BY p.name, w.name, l.name"

    rows = db.execute(base, params).fetchall()
    return [dict(r) for r in rows]
