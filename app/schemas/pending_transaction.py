from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class PendingStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    auto_approved = "auto_approved"


class IngestionSource(str, Enum):
    sms = "sms"
    ocr = "ocr"
    clipboard = "clipboard"


class SMSIngestRequest(BaseModel):
    sms_body: str
    sender: Optional[str] = None
    received_at: Optional[datetime] = None


class OCRIngestRequest(BaseModel):
    ocr_text: str


class PendingTransactionResponse(BaseModel):
    id: UUID
    user_id: UUID
    raw_text: str
    source: str
    parsed_payee: Optional[str]
    parsed_amount: Optional[float]
    parsed_date: Optional[date]
    suggested_account_id: Optional[UUID]
    suggested_category_id: Optional[UUID]
    confidence_score: float
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApproveTransactionRequest(BaseModel):
    account_id: UUID
    category_id: Optional[UUID] = None
    payee_name: Optional[str] = None
    amount: Optional[Decimal] = None
    transaction_date: Optional[date] = None
    memo: Optional[str] = None


class BatchApproveRequest(BaseModel):
    transaction_ids: list[UUID]


class CategorySuggestion(BaseModel):
    category_id: UUID
    category_name: str
    confidence: float


class PendingTransactionWithSuggestions(PendingTransactionResponse):
    category_suggestions: list[CategorySuggestion] = []
    account_name: Optional[str] = None
    category_name: Optional[str] = None
