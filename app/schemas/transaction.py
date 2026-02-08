from pydantic import BaseModel
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal


class TransactionBase(BaseModel):
    account_id: UUID
    category_id: Optional[UUID] = None
    payee_name: str
    amount: Decimal
    transaction_type: Literal["expense", "income", "transfer"]
    transaction_date: date
    memo: Optional[str] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    account_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    payee_name: Optional[str] = None
    amount: Optional[Decimal] = None
    transaction_type: Optional[Literal["expense", "income", "transfer"]] = None
    transaction_date: Optional[date] = None
    memo: Optional[str] = None
    is_cleared: Optional[bool] = None


class TransactionResponse(TransactionBase):
    id: UUID
    user_id: UUID
    is_cleared: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
