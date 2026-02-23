from __future__ import annotations

import datetime as dt
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).resolve().parent / "erp_phase1.sqlite3"))


# ---------- Helpers ----------
def now_iso() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat(sep=" ")


def connect(db_path: str = DB_PATH) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON;")
    return con


# ---------- Schema ----------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS items (
  item_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  item_code     TEXT NOT NULL UNIQUE,
  item_name     TEXT NOT NULL,
  item_type     TEXT NOT NULL CHECK (item_type IN ('RM','SF','CP','FG')),
  line          TEXT NOT NULL,
  base_unit     TEXT NOT NULL CHECK (base_unit IN ('g','ea')),
  is_active     INTEGER NOT NULL DEFAULT 1,
  created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
  item_id         INTEGER PRIMARY KEY,
  current_stock   REAL NOT NULL DEFAULT 0,
  reserved_stock  REAL NOT NULL DEFAULT 0,
  reorder_point   REAL,
  reorder_qty     REAL,
  updated_at      TEXT NOT NULL,
  FOREIGN KEY(item_id) REFERENCES items(item_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bom (
  bom_id          INTEGER PRIMARY KEY AUTOINCREMENT,
  parent_item_id  INTEGER NOT NULL,
  child_item_id   INTEGER NOT NULL,
  quantity        REAL NOT NULL,
  unit            TEXT NOT NULL CHECK (unit IN ('g','ea')),
  loss_rate       REAL NOT NULL DEFAULT 0,
  created_at      TEXT NOT NULL,
  UNIQUE(parent_item_id, child_item_id),
  FOREIGN KEY(parent_item_id) REFERENCES items(item_id) ON DELETE CASCADE,
  FOREIGN KEY(child_item_id)  REFERENCES items(item_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
  tx_id            INTEGER PRIMARY KEY AUTOINCREMENT,
  tx_type          TEXT NOT NULL CHECK (tx_type IN ('SALE','PURCHASE','ADJUST')),
  item_id          INTEGER NOT NULL,
  quantity         REAL NOT NULL,
  unit             TEXT NOT NULL CHECK (unit IN ('g','ea')),
  reference        TEXT,
  created_at       TEXT NOT NULL,
  FOREIGN KEY(item_id) REFERENCES items(item_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tx_item ON transactions(item_id, created_at);
"""


def init_db() -> None:
    con = connect()
    with con:
        con.executescript(SCHEMA_SQL)
    con.close()


# ---------- Data access ----------
def upsert_item(
    con: sqlite3.Connection,
    item_code: str,
    item_name: str,
    item_type: str,
    line: str,
    base_unit: str,
) -> int:
    cur = con.execute(
        """
        INSERT INTO items (item_code, item_name, item_type, line, base_unit, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(item_code) DO UPDATE SET
          item_name=excluded.item_name,
          item_type=excluded.item_type,
          line=excluded.line,
          base_unit=excluded.base_unit
        RETURNING item_id;
        """,
        (item_code, item_name, item_type, line, base_unit, now_iso()),
    )
    item_id = cur.fetchone()["item_id"]

    con.execute(
        """
        INSERT INTO inventory (item_id, current_stock, reserved_stock, reorder_point, reorder_qty, updated_at)
        VALUES (?, 0, 0, NULL, NULL, ?)
        ON CONFLICT(item_id) DO NOTHING;
        """,
        (item_id, now_iso()),
    )
    return item_id


def get_item_by_code(con: sqlite3.Connection, item_code: str) -> sqlite3.Row:
    cur = con.execute("SELECT * FROM items WHERE item_code = ? AND is_active = 1;", (item_code,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Item not found/active: {item_code}")
    return row


def set_inventory_policy(
    con: sqlite3.Connection,
    item_id: int,
    reorder_point: Optional[float],
    reorder_qty: Optional[float],
) -> None:
    con.execute(
        """
        UPDATE inventory
        SET reorder_point = ?, reorder_qty = ?, updated_at = ?
        WHERE item_id = ?;
        """,
        (reorder_point, reorder_qty, now_iso(), item_id),
    )


def add_bom_line(
    con: sqlite3.Connection,
    parent_code: str,
    child_code: str,
    quantity: float,
    unit: str,
    loss_rate: float = 0.0,
) -> None:
    parent = get_item_by_code(con, parent_code)
    child = get_item_by_code(con, child_code)

    con.execute(
        """
        INSERT INTO bom (parent_item_id, child_item_id, quantity, unit, loss_rate, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(parent_item_id, child_item_id) DO UPDATE SET
          quantity=excluded.quantity,
          unit=excluded.unit,
          loss_rate=excluded.loss_rate;
        """,
        (parent["item_id"], child["item_id"], quantity, unit, loss_rate, now_iso()),
    )


def bom_children(con: sqlite3.Connection, parent_item_id: int) -> List[sqlite3.Row]:
    cur = con.execute(
        """
        SELECT b.*, ci.item_code AS child_code, ci.item_name AS child_name, ci.item_type AS child_type, ci.base_unit AS child_base_unit
        FROM bom b
        JOIN items ci ON ci.item_id = b.child_item_id
        WHERE b.parent_item_id = ?;
        """,
        (parent_item_id,),
    )
    return list(cur.fetchall())


def delete_bom_line(con: sqlite3.Connection, parent_code: str, child_code: str) -> None:
    parent = get_item_by_code(con, parent_code)
    child = get_item_by_code(con, child_code)
    con.execute(
        """
        DELETE FROM bom
        WHERE parent_item_id = ? AND child_item_id = ?;
        """,
        (parent["item_id"], child["item_id"]),
    )


def list_items(
    con: sqlite3.Connection,
    item_type: Optional[str] = None,
    active_only: bool = True,
) -> List[Dict]:
    sql = """
        SELECT item_code, item_name, item_type, line, base_unit, is_active, created_at
        FROM items
        WHERE 1=1
    """
    params: List = []
    if item_type:
        sql += " AND item_type = ?"
        params.append(item_type)
    if active_only:
        sql += " AND is_active = 1"
    sql += " ORDER BY item_type, item_code;"
    cur = con.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def update_item(
    con: sqlite3.Connection,
    item_code: str,
    item_name: Optional[str],
    item_type: Optional[str],
    line: Optional[str],
    base_unit: Optional[str],
    is_active: Optional[int],
) -> None:
    fields: List[str] = []
    params: List = []
    if item_name is not None:
        fields.append("item_name = ?")
        params.append(item_name)
    if item_type is not None:
        fields.append("item_type = ?")
        params.append(item_type)
    if line is not None:
        fields.append("line = ?")
        params.append(line)
    if base_unit is not None:
        fields.append("base_unit = ?")
        params.append(base_unit)
    if is_active is not None:
        fields.append("is_active = ?")
        params.append(is_active)
    if not fields:
        return
    params.append(item_code)
    con.execute(f"UPDATE items SET {', '.join(fields)} WHERE item_code = ?;", params)


def list_bom(con: sqlite3.Connection, parent_code: str) -> List[Dict]:
    parent = get_item_by_code(con, parent_code)
    rows = bom_children(con, parent["item_id"])
    out = []
    for r in rows:
        out.append(
            {
                "parent_code": parent_code,
                "child_code": r["child_code"],
                "child_name": r["child_name"],
                "child_type": r["child_type"],
                "quantity": r["quantity"],
                "unit": r["unit"],
                "loss_rate": r["loss_rate"],
            }
        )
    return out


def list_transactions(
    con: sqlite3.Connection,
    item_code: Optional[str] = None,
    tx_type: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[Dict]:
    sql = """
        SELECT t.tx_id, t.tx_type, t.quantity, t.unit, t.reference, t.created_at,
               i.item_code, i.item_name, i.item_type
        FROM transactions t
        JOIN items i ON i.item_id = t.item_id
        WHERE 1=1
    """
    params: List = []
    if item_code:
        sql += " AND i.item_code = ?"
        params.append(item_code)
    if tx_type:
        sql += " AND t.tx_type = ?"
        params.append(tx_type)
    if since:
        sql += " AND t.created_at >= ?"
        params.append(since)
    if until:
        sql += " AND t.created_at <= ?"
        params.append(until)
    sql += " ORDER BY t.created_at DESC LIMIT ? OFFSET ?;"
    params.extend([limit, offset])
    cur = con.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def calc_rop(avg_daily_usage: float, lead_time_days: float, safety_days: float) -> float:
    return (avg_daily_usage * lead_time_days) + (avg_daily_usage * safety_days)


# ---------- Inventory operations ----------
def convert_to_base_units(item: sqlite3.Row, qty: float, unit: str) -> float:
    base = item["base_unit"]
    unit = unit.lower()

    if base == "g":
        if unit == "g":
            return qty
        if unit == "kg":
            return qty * 1000.0
        raise ValueError(f"Invalid unit for {item['item_code']} (base=g): {unit}")
    else:
        if unit == "ea":
            return qty
        raise ValueError(f"Invalid unit for {item['item_code']} (base=ea): {unit}")


def post_transaction(
    con: sqlite3.Connection,
    tx_type: str,
    item_id: int,
    qty_in_base: float,
    unit: str,
    reference: str = "",
) -> None:
    con.execute(
        """
        UPDATE inventory
        SET current_stock = current_stock + ?, updated_at = ?
        WHERE item_id = ?;
        """,
        (qty_in_base, now_iso(), item_id),
    )
    con.execute(
        """
        INSERT INTO transactions (tx_type, item_id, quantity, unit, reference, created_at)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (tx_type, item_id, qty_in_base, unit, reference, now_iso()),
    )


def purchase(con: sqlite3.Connection, item_code: str, qty: float, unit: str, reference: str = "") -> None:
    item = get_item_by_code(con, item_code)
    qty_base = convert_to_base_units(item, qty, unit)
    post_transaction(con, "PURCHASE", item["item_id"], qty_base, item["base_unit"], reference=reference)


def adjust(con: sqlite3.Connection, item_code: str, qty: float, unit: str, reference: str = "") -> None:
    item = get_item_by_code(con, item_code)
    qty_base = convert_to_base_units(item, qty, unit)
    post_transaction(con, "ADJUST", item["item_id"], qty_base, item["base_unit"], reference=reference)


def _accumulate_requirements(
    con: sqlite3.Connection,
    parent_item_id: int,
    multiplier: float,
    out: Dict[int, float],
    explode_sf: bool,
) -> None:
    children = bom_children(con, parent_item_id)
    for ch in children:
        child_id = int(ch["child_item_id"])
        qty_per_parent = float(ch["quantity"])
        loss_rate = float(ch["loss_rate"])
        total = qty_per_parent * multiplier * (1.0 + max(loss_rate, 0.0))
        out[child_id] = out.get(child_id, 0.0) + total

        if explode_sf and ch["child_type"] == "SF":
            _accumulate_requirements(con, child_id, total, out, explode_sf)


def sale(
    con: sqlite3.Connection,
    menu_code: str,
    qty_menus: int,
    reference: str = "",
    explode_sf: bool = False,
) -> List[Dict]:
    menu = get_item_by_code(con, menu_code)
    if menu["item_type"] != "FG":
        raise ValueError(f"Sale expects FG menu item. Got {menu_code} type={menu['item_type']}")

    post_transaction(
        con,
        "SALE",
        menu["item_id"],
        -float(qty_menus),
        "ea",
        reference=f"MENU_SALE {reference}",
    )

    requirements: Dict[int, float] = {}
    _accumulate_requirements(con, menu["item_id"], float(qty_menus), requirements, explode_sf)

    if not requirements:
        raise ValueError(f"No BOM lines found for menu: {menu_code}")

    for child_id, qty in requirements.items():
        con.execute(
            """
            SELECT item_id, base_unit FROM items WHERE item_id = ?;
            """,
            (child_id,),
        )
        row = con.fetchone()
        post_transaction(
            con,
            "SALE",
            child_id,
            -float(qty),
            row["base_unit"],
            reference=f"{menu_code} x{qty_menus} {reference}",
        )

    return reorder_alerts(con)


def reorder_alerts(con: sqlite3.Connection) -> List[Dict]:
    cur = con.execute(
        """
        SELECT i.item_code, i.item_name, i.item_type, i.base_unit,
               inv.current_stock, inv.reorder_point, inv.reorder_qty
        FROM inventory inv
        JOIN items i ON i.item_id = inv.item_id
        WHERE inv.reorder_point IS NOT NULL
          AND inv.current_stock <= inv.reorder_point
          AND i.is_active = 1
        ORDER BY i.item_type, i.item_code;
        """
    )
    out = []
    for r in cur.fetchall():
        out.append(
            {
                "item_code": r["item_code"],
                "item_name": r["item_name"],
                "item_type": r["item_type"],
                "base_unit": r["base_unit"],
                "current_stock": r["current_stock"],
                "reorder_point": r["reorder_point"],
                "suggest_reorder_qty": r["reorder_qty"],
            }
        )
    return out


def inventory_snapshot(con: sqlite3.Connection) -> List[Dict]:
    cur = con.execute(
        """
        SELECT i.item_code, i.item_name, i.item_type, i.base_unit,
               inv.current_stock, inv.reorder_point, inv.reorder_qty, inv.updated_at
        FROM inventory inv
        JOIN items i ON i.item_id = inv.item_id
        WHERE i.is_active = 1
        ORDER BY i.item_type, i.item_code;
        """
    )
    return [dict(r) for r in cur.fetchall()]


def seed_gogiji_phase1() -> None:
    con = connect()
    try:
        with con:
            upsert_item(con, "RM-MEAT-001", "우삼겹", "RM", "MEAT", "g")
            upsert_item(con, "RM-GRAIN-001", "쌀", "RM", "GRAIN", "g")
            upsert_item(con, "RM-EGG-001", "계란", "RM", "EGG", "ea")
            upsert_item(con, "RM-VEG-001", "대파", "RM", "VEG", "g")
            upsert_item(con, "RM-ETC-001", "고추가루", "RM", "ETC", "g")
            upsert_item(con, "RM-ETC-002", "참기름", "RM", "ETC", "g")
            upsert_item(con, "RM-ETC-003", "설탕", "RM", "ETC", "g")
            upsert_item(con, "RM-ETC-004", "미원", "RM", "ETC", "g")
            upsert_item(con, "RM-ETC-005", "맛소금", "RM", "ETC", "g")
            upsert_item(con, "RM-SAUCE-001", "쌈장", "RM", "SAUCE", "g")

            upsert_item(con, "SF-SIDE-001", "볶음김치(시판)", "SF", "SIDE", "g")
            upsert_item(con, "SF-SIDE-002", "무말랭이(시판)", "SF", "SIDE", "g")
            upsert_item(con, "SF-KIT-001", "제육볶음 밀키트", "SF", "KIT", "g")
            upsert_item(con, "SF-SAUCE-001", "장국베이스(시판)", "SF", "SAUCE", "g")

            upsert_item(con, "CP-PACK-001", "도시락 용기", "CP", "PACK", "ea")
            upsert_item(con, "CP-PACK-002", "국 용기", "CP", "PACK", "ea")
            upsert_item(con, "CP-ETC-001", "일회용 수저", "CP", "ETC", "ea")
            upsert_item(con, "CP-ETC-002", "일회용 나무젓가락", "CP", "ETC", "ea")
            upsert_item(con, "CP-ETC-003", "보온팩", "CP", "ETC", "ea")
            upsert_item(con, "CP-ETC-004", "비닐", "CP", "ETC", "ea")

            upsert_item(con, "FG-DOS-001", "우삼겹 도시락", "FG", "DOS", "ea")

            meat = get_item_by_code(con, "RM-MEAT-001")
            set_inventory_policy(con, meat["item_id"], reorder_point=6000.0, reorder_qty=10000.0)

            add_bom_line(con, "FG-DOS-001", "RM-MEAT-001", 250.0, "g")
            add_bom_line(con, "FG-DOS-001", "RM-GRAIN-001", 230.0, "g")
            add_bom_line(con, "FG-DOS-001", "RM-EGG-001", 0.4, "ea")
            add_bom_line(con, "FG-DOS-001", "RM-VEG-001", 70.0, "g")
            add_bom_line(con, "FG-DOS-001", "RM-ETC-001", 4.0, "g")
            add_bom_line(con, "FG-DOS-001", "RM-ETC-002", 5.0, "g")
            add_bom_line(con, "FG-DOS-001", "RM-ETC-003", 2.0, "g")
            add_bom_line(con, "FG-DOS-001", "RM-ETC-004", 0.5, "g")
            add_bom_line(con, "FG-DOS-001", "RM-ETC-005", 1.0, "g")
            add_bom_line(con, "FG-DOS-001", "RM-SAUCE-001", 25.0, "g")

            add_bom_line(con, "FG-DOS-001", "SF-SAUCE-001", 200.0, "g")
            add_bom_line(con, "FG-DOS-001", "SF-SIDE-002", 25.0, "g")
            add_bom_line(con, "FG-DOS-001", "SF-SIDE-001", 70.0, "g")
            add_bom_line(con, "FG-DOS-001", "SF-KIT-001", 30.0, "g")

            add_bom_line(con, "FG-DOS-001", "CP-PACK-001", 1.0, "ea")
            add_bom_line(con, "FG-DOS-001", "CP-PACK-002", 1.0, "ea")
            add_bom_line(con, "FG-DOS-001", "CP-ETC-001", 1.0, "ea")
            add_bom_line(con, "FG-DOS-001", "CP-ETC-002", 1.0, "ea")
            add_bom_line(con, "FG-DOS-001", "CP-ETC-003", 1.0, "ea")
            add_bom_line(con, "FG-DOS-001", "CP-ETC-004", 1.0, "ea")
    finally:
        con.close()
