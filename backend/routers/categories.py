import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from routers.auth import get_current_user
from models import CategoryCreate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
def list_categories(db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    rows = db.execute("""
        SELECT c.*, COUNT(p.id) as product_count
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.id AND p.is_active = 1
        GROUP BY c.id
        ORDER BY c.name
    """).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=201)
def create_category(data: CategoryCreate, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    db.execute("INSERT INTO categories (name, description) VALUES (?, ?)", (data.name, data.description))
    db.commit()
    row = db.execute("SELECT * FROM categories ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row)


@router.put("/{cat_id}")
def update_category(cat_id: int, data: CategoryCreate, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    db.execute("UPDATE categories SET name=?, description=? WHERE id=?", (data.name, data.description, cat_id))
    db.commit()
    return dict(db.execute("SELECT * FROM categories WHERE id=?", (cat_id,)).fetchone())


@router.delete("/{cat_id}")
def delete_category(cat_id: int, db: sqlite3.Connection = Depends(get_db), _=Depends(get_current_user)):
    db.execute("DELETE FROM categories WHERE id=?", (cat_id,))
    db.commit()
    return {"message": "Category deleted"}
