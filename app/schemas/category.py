from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class CategoryGroupBase(BaseModel):
    name: str
    sort_order: int = 0


class CategoryGroupCreate(CategoryGroupBase):
    pass


class CategoryGroupResponse(CategoryGroupBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class CategoryBase(BaseModel):
    name: str
    group_id: Optional[UUID] = None
    target_amount: Decimal = Decimal("0.00")
    sort_order: int = 0


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    group_id: Optional[UUID] = None
    target_amount: Optional[Decimal] = None
    is_hidden: Optional[bool] = None
    sort_order: Optional[int] = None


class CategoryAssign(BaseModel):
    amount: Decimal


class CategoryResponse(CategoryBase):
    id: UUID
    user_id: UUID
    assigned_amount: Decimal
    activity_amount: Decimal
    available_amount: Decimal = Decimal("0.00")
    is_hidden: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    def __init__(self, **data):
        if "available_amount" not in data:
            assigned = data.get("assigned_amount", Decimal("0.00"))
            activity = data.get("activity_amount", Decimal("0.00"))
            data["available_amount"] = assigned - activity
        super().__init__(**data)
