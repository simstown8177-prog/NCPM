from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from backend.erp_core import (
    add_bom_line,
    calc_rop,
    connect,
    init_db,
    inventory_snapshot,
    list_bom,
    list_items,
    list_transactions,
    purchase,
    reorder_alerts,
    sale,
    seed_gogiji_phase1,
    set_inventory_policy,
    update_item,
    delete_bom_line,
    upsert_item,
)

app = FastAPI(title="ERP Phase 1 (GOGIJI)")


class PurchaseIn(BaseModel):
    item_code: str = Field(..., example="RM-MEAT-001")
    quantity: float = Field(..., gt=0)
    unit: str = Field(..., example="kg")
    reference: str | None = ""


class SaleIn(BaseModel):
    menu_code: str = Field(..., example="FG-DOS-001")
    quantity: int = Field(..., gt=0)
    reference: str | None = ""


class ItemCreate(BaseModel):
    item_code: str = Field(..., example="RM-MEAT-001")
    item_name: str
    item_type: str = Field(..., description="RM/SF/CP/FG")
    line: str
    base_unit: str = Field(..., description="g/ea")


class ItemUpdate(BaseModel):
    item_name: str | None = None
    item_type: str | None = None
    line: str | None = None
    base_unit: str | None = None
    is_active: int | None = Field(None, description="1 or 0")


class BomLineIn(BaseModel):
    parent_code: str
    child_code: str
    quantity: float = Field(..., gt=0)
    unit: str = Field(..., description="g/ea")
    loss_rate: float = Field(0.0, ge=0.0)


class RopRecalcIn(BaseModel):
    item_code: str
    avg_daily_usage: float = Field(..., gt=0)
    lead_time_days: float = Field(..., gt=0)
    safety_days: float = Field(..., ge=0)
    reorder_qty: float = Field(..., gt=0)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.post("/admin/seed")
def seed() -> dict:
    try:
        seed_gogiji_phase1()
        return {"ok": True, "message": "Seeded GogiJi Phase1"}
    except Exception as exc:  # pragma: no cover - simple error surface
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/items")
def get_items(
    item_type: str | None = None,
    active_only: bool = True,
) -> dict:
    try:
        con = connect()
        try:
            items = list_items(con, item_type=item_type, active_only=active_only)
            return {"items": items}
        finally:
            con.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/items")
def create_item(payload: ItemCreate) -> dict:
    try:
        con = connect()
        try:
            with con:
                upsert_item(
                    con,
                    payload.item_code,
                    payload.item_name,
                    payload.item_type,
                    payload.line,
                    payload.base_unit,
                )
            return {"ok": True}
        finally:
            con.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/items/{item_code}")
def patch_item(item_code: str, payload: ItemUpdate) -> dict:
    try:
        con = connect()
        try:
            with con:
                update_item(
                    con,
                    item_code,
                    payload.item_name,
                    payload.item_type,
                    payload.line,
                    payload.base_unit,
                    payload.is_active,
                )
            return {"ok": True}
        finally:
            con.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/bom/{parent_code}")
def get_bom(parent_code: str) -> dict:
    try:
        con = connect()
        try:
            items = list_bom(con, parent_code)
            return {"items": items}
        finally:
            con.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/bom")
def post_bom(payload: BomLineIn) -> dict:
    try:
        con = connect()
        try:
            with con:
                add_bom_line(
                    con,
                    payload.parent_code,
                    payload.child_code,
                    payload.quantity,
                    payload.unit,
                    payload.loss_rate,
                )
            return {"ok": True}
        finally:
            con.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/bom")
def delete_bom(parent_code: str, child_code: str) -> dict:
    try:
        con = connect()
        try:
            with con:
                delete_bom_line(con, parent_code, child_code)
            return {"ok": True}
        finally:
            con.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/purchase")
def post_purchase(payload: PurchaseIn) -> dict:
    try:
        con = connect()
        try:
            with con:
                purchase(con, payload.item_code, payload.quantity, payload.unit, reference=payload.reference or "")
                alerts = reorder_alerts(con)
            return {"ok": True, "reorder_alerts": alerts}
        finally:
            con.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/sale")
def post_sale(payload: SaleIn) -> dict:
    try:
        con = connect()
        try:
            with con:
                alerts = sale(con, payload.menu_code, payload.quantity, reference=payload.reference or "")
            return {"ok": True, "reorder_alerts": alerts}
        finally:
            con.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/inventory")
def get_inventory() -> dict:
    try:
        con = connect()
        try:
            snap = inventory_snapshot(con)
            return {"items": snap}
        finally:
            con.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/reorder-alerts")
def get_reorder_alerts() -> dict:
    try:
        con = connect()
        try:
            alerts = reorder_alerts(con)
            return {"items": alerts}
        finally:
            con.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/transactions")
def get_transactions(
    item_code: str | None = None,
    tx_type: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict:
    try:
        con = connect()
        try:
            rows = list_transactions(
                con,
                item_code=item_code,
                tx_type=tx_type,
                since=since,
                until=until,
                limit=limit,
                offset=offset,
            )
            return {"items": rows}
        finally:
            con.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/rop/recalculate")
def recalc_rop(payload: RopRecalcIn) -> dict:
    try:
        con = connect()
        try:
            with con:
                item = None
                cur = con.execute(
                    "SELECT item_id FROM items WHERE item_code = ? AND is_active = 1;",
                    (payload.item_code,),
                )
                item = cur.fetchone()
                if not item:
                    raise ValueError(f"Item not found/active: {payload.item_code}")
                rop = calc_rop(payload.avg_daily_usage, payload.lead_time_days, payload.safety_days)
                set_inventory_policy(con, item["item_id"], reorder_point=rop, reorder_qty=payload.reorder_qty)
            return {"ok": True, "reorder_point": rop, "reorder_qty": payload.reorder_qty}
        finally:
            con.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
