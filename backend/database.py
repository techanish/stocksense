import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "stocksense.db")


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    schema = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'staff',
        otp TEXT,
        otp_expires_at TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS warehouses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL,
        address TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        warehouse_id INTEGER REFERENCES warehouses(id),
        name TEXT NOT NULL,
        code TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sku TEXT UNIQUE NOT NULL,
        category_id INTEGER REFERENCES categories(id),
        unit_of_measure TEXT NOT NULL,
        reorder_level REAL DEFAULT 0,
        description TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER REFERENCES products(id),
        location_id INTEGER REFERENCES locations(id),
        quantity REAL DEFAULT 0,
        UNIQUE(product_id, location_id)
    );

    CREATE TABLE IF NOT EXISTS stock_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER REFERENCES products(id),
        location_id INTEGER REFERENCES locations(id),
        quantity_change REAL NOT NULL,
        quantity_after REAL NOT NULL,
        operation_type TEXT NOT NULL,
        reference_id INTEGER,
        reference_code TEXT,
        notes TEXT,
        created_by INTEGER REFERENCES users(id),
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        supplier TEXT,
        warehouse_id INTEGER REFERENCES warehouses(id),
        status TEXT DEFAULT 'draft',
        notes TEXT,
        created_by INTEGER REFERENCES users(id),
        validated_at TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS receipt_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt_id INTEGER REFERENCES receipts(id) ON DELETE CASCADE,
        product_id INTEGER REFERENCES products(id),
        location_id INTEGER REFERENCES locations(id),
        quantity_expected REAL DEFAULT 0,
        quantity_received REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS deliveries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        customer TEXT,
        warehouse_id INTEGER REFERENCES warehouses(id),
        status TEXT DEFAULT 'draft',
        notes TEXT,
        created_by INTEGER REFERENCES users(id),
        validated_at TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS delivery_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        delivery_id INTEGER REFERENCES deliveries(id) ON DELETE CASCADE,
        product_id INTEGER REFERENCES products(id),
        location_id INTEGER REFERENCES locations(id),
        quantity_demanded REAL DEFAULT 0,
        quantity_picked REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS transfers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        from_location_id INTEGER REFERENCES locations(id),
        to_location_id INTEGER REFERENCES locations(id),
        status TEXT DEFAULT 'draft',
        notes TEXT,
        created_by INTEGER REFERENCES users(id),
        validated_at TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS transfer_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transfer_id INTEGER REFERENCES transfers(id) ON DELETE CASCADE,
        product_id INTEGER REFERENCES products(id),
        quantity REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS adjustments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        location_id INTEGER REFERENCES locations(id),
        status TEXT DEFAULT 'draft',
        reason TEXT,
        notes TEXT,
        created_by INTEGER REFERENCES users(id),
        validated_at TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS adjustment_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adjustment_id INTEGER REFERENCES adjustments(id) ON DELETE CASCADE,
        product_id INTEGER REFERENCES products(id),
        quantity_recorded REAL DEFAULT 0,
        quantity_counted REAL DEFAULT 0,
        quantity_difference REAL DEFAULT 0
    );
    """

    for statement in schema.strip().split(";"):
        stmt = statement.strip()
        if stmt:
            cursor.execute(stmt)

    # Seed default warehouse + location if empty
    cursor.execute("SELECT COUNT(*) FROM warehouses")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO warehouses (name, code, address) VALUES (?, ?, ?)",
            ("Main Warehouse", "WH-MAIN", "Default Location"),
        )
        wh_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO locations (warehouse_id, name, code) VALUES (?, ?, ?)",
            (wh_id, "Default Location", "LOC-DEFAULT"),
        )

    conn.commit()
    conn.close()
    print("✅ Database initialized")
