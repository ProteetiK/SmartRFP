from fastapi import APIRouter

from backend.services import (calculate_resource_cost, update_pricing)

router = APIRouter(
    prefix="/pricing",
    tags=["Pricing"]
)


@router.get("/{rfp_id}")
def pricing(rfp_id: int):
    return calculate_resource_cost(rfp_id)

@router.put("/{rfp_id}")
def save_pricing(rfp_id: int, body: dict):
    return update_pricing(
        rfp_id,
        body["pricing"],
    )