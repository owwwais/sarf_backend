from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
from app.database import get_supabase
from app.dependencies import get_current_user
from app.schemas.account import AccountCreate, AccountUpdate, AccountResponse

router = APIRouter()


@router.get("/", response_model=List[AccountResponse])
async def list_accounts(current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    response = supabase.table("accounts").select("*").eq("user_id", current_user["id"]).eq("is_active", True).execute()
    return [AccountResponse(**account) for account in response.data]


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: AccountCreate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    data = account_data.model_dump()
    data["user_id"] = current_user["id"]
    data["balance"] = float(data["balance"])
    response = supabase.table("accounts").insert(data).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create account",
        )
    return AccountResponse(**response.data[0])


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    response = supabase.table("accounts").select("*").eq("id", str(account_id)).eq("user_id", current_user["id"]).single().execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    return AccountResponse(**response.data)


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: UUID,
    account_data: AccountUpdate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    data = account_data.model_dump(exclude_unset=True)
    if "balance" in data:
        data["balance"] = float(data["balance"])
    response = supabase.table("accounts").update(data).eq("id", str(account_id)).eq("user_id", current_user["id"]).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    return AccountResponse(**response.data[0])


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    response = supabase.table("accounts").update({"is_active": False}).eq("id", str(account_id)).eq("user_id", current_user["id"]).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
