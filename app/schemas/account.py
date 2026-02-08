from pydantic import BaseModel
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class AccountBase(BaseModel):
    name: str
    balance: Decimal = Decimal("0.00")
    type: Literal["checking", "savings", "credit", "cash"]


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    balance: Optional[Decimal] = None
    type: Optional[Literal["checking", "savings", "credit", "cash"]] = None
    is_active: Optional[bool] = None


class AccountResponse(AccountBase):
    id: UUID
    user_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
