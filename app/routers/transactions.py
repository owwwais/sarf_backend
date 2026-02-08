from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from uuid import UUID
from datetime import date
from decimal import Decimal
from app.database import get_supabase
from app.dependencies import get_current_user
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse

router = APIRouter()


@router.get("/", response_model=List[TransactionResponse])
async def list_transactions(
    account_id: Optional[UUID] = None,
    category_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    query = supabase.table("transactions").select("*").eq("user_id", current_user["id"])
    if account_id:
        query = query.eq("account_id", str(account_id))
    if category_id:
        query = query.eq("category_id", str(category_id))
    if start_date:
        query = query.gte("transaction_date", start_date.isoformat())
    if end_date:
        query = query.lte("transaction_date", end_date.isoformat())
    response = query.order("transaction_date", desc=True).range(offset, offset + limit - 1).execute()
    return [TransactionResponse(**txn) for txn in response.data]


@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    txn_data: TransactionCreate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    data = txn_data.model_dump()
    data["user_id"] = current_user["id"]
    data["account_id"] = str(data["account_id"])
    if data["category_id"]:
        data["category_id"] = str(data["category_id"])
    data["amount"] = float(data["amount"])
    data["transaction_date"] = data["transaction_date"].isoformat()
    response = supabase.table("transactions").insert(data).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create transaction",
        )
    txn = response.data[0]
    amount = Decimal(str(txn["amount"]))
    account_response = supabase.table("accounts").select("balance").eq("id", txn["account_id"]).single().execute()
    current_balance = Decimal(str(account_response.data["balance"]))
    if txn["transaction_type"] == "expense":
        new_balance = current_balance - amount
    elif txn["transaction_type"] == "income":
        new_balance = current_balance + amount
    else:
        new_balance = current_balance
    supabase.table("accounts").update({"balance": float(new_balance)}).eq("id", txn["account_id"]).execute()
    if txn["category_id"] and txn["transaction_type"] == "expense":
        cat_response = supabase.table("categories").select("activity_amount").eq("id", txn["category_id"]).single().execute()
        current_activity = Decimal(str(cat_response.data["activity_amount"]))
        new_activity = current_activity + amount
        supabase.table("categories").update({"activity_amount": float(new_activity)}).eq("id", txn["category_id"]).execute()
    return TransactionResponse(**txn)


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    response = supabase.table("transactions").select("*").eq("id", str(transaction_id)).eq("user_id", current_user["id"]).single().execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    return TransactionResponse(**response.data)


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: UUID,
    txn_data: TransactionUpdate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    old_txn = supabase.table("transactions").select("*").eq("id", str(transaction_id)).eq("user_id", current_user["id"]).single().execute()
    if not old_txn.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    data = txn_data.model_dump(exclude_unset=True)
    if "account_id" in data:
        data["account_id"] = str(data["account_id"])
    if "category_id" in data and data["category_id"]:
        data["category_id"] = str(data["category_id"])
    if "amount" in data:
        data["amount"] = float(data["amount"])
    if "transaction_date" in data:
        data["transaction_date"] = data["transaction_date"].isoformat()
    response = supabase.table("transactions").update(data).eq("id", str(transaction_id)).execute()
    return TransactionResponse(**response.data[0])


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    txn = supabase.table("transactions").select("*").eq("id", str(transaction_id)).eq("user_id", current_user["id"]).single().execute()
    if not txn.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    amount = Decimal(str(txn.data["amount"]))
    account_response = supabase.table("accounts").select("balance").eq("id", txn.data["account_id"]).single().execute()
    current_balance = Decimal(str(account_response.data["balance"]))
    if txn.data["transaction_type"] == "expense":
        new_balance = current_balance + amount
    elif txn.data["transaction_type"] == "income":
        new_balance = current_balance - amount
    else:
        new_balance = current_balance
    supabase.table("accounts").update({"balance": float(new_balance)}).eq("id", txn.data["account_id"]).execute()
    if txn.data["category_id"] and txn.data["transaction_type"] == "expense":
        cat_response = supabase.table("categories").select("activity_amount").eq("id", txn.data["category_id"]).single().execute()
        current_activity = Decimal(str(cat_response.data["activity_amount"]))
        new_activity = current_activity - amount
        supabase.table("categories").update({"activity_amount": float(new_activity)}).eq("id", txn.data["category_id"]).execute()
    supabase.table("transactions").delete().eq("id", str(transaction_id)).execute()
