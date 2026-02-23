from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import erp_service

router = APIRouter(prefix="/erp", tags=["erp"])


class PurchaseIn(BaseModel):
    item_code: str = Field(..., example="RM-MEAT-001")
    quantity: float = Field(..., gt=0)
    unit: str = Field(..., example="kg")
    reference: str | None = ""


class SaleIn(BaseModel):
    menu_code: str = Field(..., example="FG-DOS-001")
    quantity: int = Field(..., gt=0)
    reference: str | None = ""


@router.post("/purchase")
def post_purchase(payload: PurchaseIn) -> dict:
    try:
        con = erp_service.get_connection()
        try:
            alerts = erp_service.purchase_item(
                con,
                payload.item_code,
                payload.quantity,
                payload.unit,
                reference=payload.reference or "",
            )
            return {"ok": True, "reorder_alerts": alerts}
        finally:
            con.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sale")
def post_sale(payload: SaleIn) -> dict:
    try:
        con = erp_service.get_connection()
        try:
            alerts = erp_service.sell_menu(
                con,
                payload.menu_code,
                payload.quantity,
                reference=payload.reference or "",
            )
            return {"ok": True, "reorder_alerts": alerts}
        finally:
            con.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/inventory")
def get_inventory() -> dict:
    try:
        con = erp_service.get_connection()
        try:
            snap = erp_service.inventory_snapshot(con)
            return {"items": snap}
        finally:
            con.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/reorder-alerts")
def get_reorder_alerts() -> dict:
    try:
        con = erp_service.get_connection()
        try:
            alerts = erp_service.reorder_alerts(con)
            return {"items": alerts}
        finally:
            con.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
