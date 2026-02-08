from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import date
from decimal import Decimal
from enum import Enum


class SubscriptionFrequency(str, Enum):
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class SubscriptionCreate(BaseModel):
    payee_name: str = Field(..., min_length=1)
    estimated_amount: Decimal = Field(..., gt=0)
    next_due_date: date
    frequency: SubscriptionFrequency = SubscriptionFrequency.monthly
    category_id: Optional[UUID] = None
    account_id: Optional[UUID] = None  # الحساب للخصم منه
    is_active: bool = True


class SubscriptionUpdate(BaseModel):
    payee_name: Optional[str] = None
    estimated_amount: Optional[Decimal] = None
    next_due_date: Optional[date] = None
    frequency: Optional[SubscriptionFrequency] = None
    category_id: Optional[UUID] = None
    account_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class SubscriptionResponse(BaseModel):
    id: UUID
    user_id: UUID
    payee_name: str
    estimated_amount: Decimal
    next_due_date: date
    frequency: SubscriptionFrequency
    is_active: bool
    category_id: Optional[UUID] = None
    account_id: Optional[UUID] = None
    category_name: Optional[str] = None
    account_name: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class DetectedSubscription(BaseModel):
    payee_name: str
    estimated_amount: Decimal
    frequency: SubscriptionFrequency
    confidence: float = Field(..., ge=0, le=1)
    transaction_count: int
    last_transaction_date: date
    suggested_category_id: Optional[UUID] = None
    suggested_category_name: Optional[str] = None


class UpcomingSubscription(BaseModel):
    id: UUID
    payee_name: str
    estimated_amount: Decimal
    next_due_date: date
    days_until_due: int
    category_name: Optional[str] = None
