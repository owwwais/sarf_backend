from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from uuid import UUID
from decimal import Decimal
from app.dependencies import get_current_user
from app.services.budget_service import budget_service
from app.schemas.category import CategoryResponse

router = APIRouter()


class MoveMoneyRequest(BaseModel):
    from_category_id: UUID
    to_category_id: UUID
    amount: Decimal


class MoveMoneyResponse(BaseModel):
    from_category: CategoryResponse
    to_category: CategoryResponse
    message: str


class BudgetSummaryResponse(BaseModel):
    to_be_budgeted: float
    total_balance: float
    total_assigned: float
    total_spent: float


@router.get("/summary", response_model=BudgetSummaryResponse)
async def get_budget_summary(current_user: dict = Depends(get_current_user)):
    summary = budget_service.get_budget_summary(current_user["id"])
    return BudgetSummaryResponse(**summary)


@router.patch("/move_money", response_model=MoveMoneyResponse)
async def move_money(
    request: MoveMoneyRequest,
    current_user: dict = Depends(get_current_user),
):
    if request.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be positive",
        )
    if request.from_category_id == request.to_category_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and target categories must be different",
        )
    try:
        from_cat, to_cat = budget_service.move_money(
            user_id=current_user["id"],
            from_category_id=request.from_category_id,
            to_category_id=request.to_category_id,
            amount=request.amount,
        )
        return MoveMoneyResponse(
            from_category=CategoryResponse(**from_cat),
            to_category=CategoryResponse(**to_cat),
            message=f"Successfully moved {request.amount} between categories",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
