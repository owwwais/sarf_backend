from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
from decimal import Decimal
from app.database import get_supabase
from app.dependencies import get_current_user
from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryAssign,
    CategoryGroupCreate,
    CategoryGroupResponse,
)

router = APIRouter()


@router.get("/groups", response_model=List[CategoryGroupResponse])
async def list_category_groups(current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    response = supabase.table("category_groups").select("*").eq("user_id", current_user["id"]).order("sort_order").execute()
    return [CategoryGroupResponse(**group) for group in response.data]


@router.post("/groups", response_model=CategoryGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_category_group(
    group_data: CategoryGroupCreate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    data = group_data.model_dump()
    data["user_id"] = current_user["id"]
    response = supabase.table("category_groups").insert(data).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create category group",
        )
    return CategoryGroupResponse(**response.data[0])


@router.get("/", response_model=List[CategoryResponse])
async def list_categories(current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    response = supabase.table("categories").select("*").eq("user_id", current_user["id"]).eq("is_hidden", False).order("sort_order").execute()
    return [CategoryResponse(**cat) for cat in response.data]


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    data = category_data.model_dump()
    data["user_id"] = current_user["id"]
    data["target_amount"] = float(data["target_amount"])
    if data["group_id"]:
        data["group_id"] = str(data["group_id"])
    response = supabase.table("categories").insert(data).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create category",
        )
    return CategoryResponse(**response.data[0])


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    response = supabase.table("categories").select("*").eq("id", str(category_id)).eq("user_id", current_user["id"]).single().execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return CategoryResponse(**response.data)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    category_data: CategoryUpdate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    data = category_data.model_dump(exclude_unset=True)
    if "target_amount" in data:
        data["target_amount"] = float(data["target_amount"])
    if "group_id" in data and data["group_id"]:
        data["group_id"] = str(data["group_id"])
    response = supabase.table("categories").update(data).eq("id", str(category_id)).eq("user_id", current_user["id"]).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return CategoryResponse(**response.data[0])


@router.patch("/{category_id}/assign", response_model=CategoryResponse)
async def assign_to_category(
    category_id: UUID,
    assign_data: CategoryAssign,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    cat_response = supabase.table("categories").select("*").eq("id", str(category_id)).eq("user_id", current_user["id"]).single().execute()
    if not cat_response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    current_assigned = Decimal(str(cat_response.data["assigned_amount"]))
    new_assigned = current_assigned + assign_data.amount
    response = supabase.table("categories").update({"assigned_amount": float(new_assigned)}).eq("id", str(category_id)).execute()
    return CategoryResponse(**response.data[0])


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    response = supabase.table("categories").update({"is_hidden": True}).eq("id", str(category_id)).eq("user_id", current_user["id"]).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
