from __future__ import annotations

from typing import Dict, List, Optional

from backend import erp_core


def get_connection():
    return erp_core.connect()


# ---- Items ----
def list_items(con, item_type: Optional[str] = None, active_only: bool = True) -> List[Dict]:
    return erp_core.list_items(con, item_type=item_type, active_only=active_only)


def upsert_item(
    con,
    item_code: str,
    item_name: str,
    item_type: str,
    line: str,
    base_unit: str,
) -> int:
    with con:
        return erp_core.upsert_item(con, item_code, item_name, item_type, line, base_unit)


def update_item(
    con,
    item_code: str,
    item_name: Optional[str],
    item_type: Optional[str],
    line: Optional[str],
    base_unit: Optional[str],
    is_active: Optional[int],
) -> None:
    with con:
        erp_core.update_item(con, item_code, item_name, item_type, line, base_unit, is_active)


# ---- BOM ----
def list_bom(con, parent_code: str) -> List[Dict]:
    return erp_core.list_bom(con, parent_code)


def add_bom_line(
    con,
    parent_code: str,
    child_code: str,
    quantity: float,
    unit: str,
    loss_rate: float = 0.0,
) -> None:
    with con:
        erp_core.add_bom_line(con, parent_code, child_code, quantity, unit, loss_rate)


def delete_bom_line(con, parent_code: str, child_code: str) -> None:
    with con:
        erp_core.delete_bom_line(con, parent_code, child_code)


# ---- Transactions ----
def list_transactions(
    con,
    item_code: Optional[str] = None,
    tx_type: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[Dict]:
    return erp_core.list_transactions(
        con,
        item_code=item_code,
        tx_type=tx_type,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )


# ---- Inventory operations ----
def purchase_item(
    con,
    item_code: str,
    quantity: float,
    unit: str,
    reference: str = "",
) -> List[Dict]:
    with con:
        erp_core.purchase(con, item_code, quantity, unit, reference=reference)
        return erp_core.reorder_alerts(con)


def sell_menu(
    con,
    menu_code: str,
    quantity: int,
    reference: str = "",
) -> List[Dict]:
    with con:
        return erp_core.sale(con, menu_code, quantity, reference=reference)


def inventory_snapshot(con) -> List[Dict]:
    return erp_core.inventory_snapshot(con)


def reorder_alerts(con) -> List[Dict]:
    return erp_core.reorder_alerts(con)


# ---- ROP ----
def recalc_rop(
    con,
    item_code: str,
    avg_daily_usage: float,
    lead_time_days: float,
    safety_days: float,
    reorder_qty: float,
) -> Dict:
    item = erp_core.get_item_by_code(con, item_code)
    rop = erp_core.calc_rop(avg_daily_usage, lead_time_days, safety_days)
    with con:
        erp_core.set_inventory_policy(con, item["item_id"], reorder_point=rop, reorder_qty=reorder_qty)
    return {"reorder_point": rop, "reorder_qty": reorder_qty}
