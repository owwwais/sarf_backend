from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
from datetime import date, timedelta
from app.database import get_supabase
from app.dependencies import get_current_user
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    DetectedSubscription,
    UpcomingSubscription,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter()


@router.get("/", response_model=List[SubscriptionResponse])
async def list_subscriptions(
    active_only: bool = True,
    current_user: dict = Depends(get_current_user),
):
    """List all subscriptions for the current user"""
    supabase = get_supabase()
    
    # Try with accounts join, fallback to without if account_id column doesn't exist
    try:
        query = supabase.table("subscriptions").select(
            "*, categories(name), accounts(name)"
        ).eq("user_id", current_user["id"])
        
        if active_only:
            query = query.eq("is_active", True)
        
        response = query.order("next_due_date").execute()
    except Exception:
        # Fallback without accounts join
        query = supabase.table("subscriptions").select(
            "*, categories(name)"
        ).eq("user_id", current_user["id"])
        
        if active_only:
            query = query.eq("is_active", True)
        
        response = query.order("next_due_date").execute()
    
    results = []
    for sub in response.data:
        # Handle accounts data safely
        accounts_data = sub.get("accounts")
        account_name = None
        if accounts_data and isinstance(accounts_data, dict):
            account_name = accounts_data.get("name")
        
        results.append(SubscriptionResponse(
            id=sub["id"],
            user_id=sub["user_id"],
            payee_name=sub["payee_name"],
            estimated_amount=sub["estimated_amount"],
            next_due_date=sub["next_due_date"],
            frequency=sub["frequency"],
            is_active=sub["is_active"],
            category_id=sub.get("category_id"),
            account_id=sub.get("account_id"),
            category_name=sub.get("categories", {}).get("name") if sub.get("categories") else None,
            account_name=account_name,
            created_at=sub["created_at"],
            updated_at=sub["updated_at"],
        ))
    
    return results


@router.post("/", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new subscription"""
    supabase = get_supabase()
    
    data = subscription_data.model_dump()
    data["user_id"] = current_user["id"]
    data["estimated_amount"] = float(data["estimated_amount"])
    data["next_due_date"] = data["next_due_date"].isoformat()
    data["frequency"] = data["frequency"].value
    if data.get("category_id"):
        data["category_id"] = str(data["category_id"])
    if data.get("account_id"):
        data["account_id"] = str(data["account_id"])
    
    response = supabase.table("subscriptions").insert(data).execute()
    
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create subscription",
        )
    
    sub = response.data[0]
    return SubscriptionResponse(
        id=sub["id"],
        user_id=sub["user_id"],
        payee_name=sub["payee_name"],
        estimated_amount=sub["estimated_amount"],
        next_due_date=sub["next_due_date"],
        frequency=sub["frequency"],
        is_active=sub["is_active"],
        category_id=sub.get("category_id"),
        account_id=sub.get("account_id"),
        category_name=None,
        account_name=None,
        created_at=sub["created_at"],
        updated_at=sub["updated_at"],
    )


@router.get("/upcoming", response_model=List[UpcomingSubscription])
async def get_upcoming_subscriptions(
    days: int = 7,
    current_user: dict = Depends(get_current_user),
):
    """Get subscriptions due in the next N days"""
    results = SubscriptionService.get_upcoming_subscriptions(
        user_id=current_user["id"],
        days_ahead=days,
    )
    return [UpcomingSubscription(**r) for r in results]


@router.get("/detect", response_model=List[DetectedSubscription])
async def detect_subscriptions(
    days_lookback: int = 90,
    current_user: dict = Depends(get_current_user),
):
    """Detect potential subscriptions from transaction history"""
    detected = SubscriptionService.detect_subscriptions(
        user_id=current_user["id"],
        days_lookback=days_lookback,
    )
    return detected


@router.post("/detect/{payee_name}/confirm", response_model=SubscriptionResponse)
async def confirm_detected_subscription(
    payee_name: str,
    detected: DetectedSubscription,
    current_user: dict = Depends(get_current_user),
):
    """Confirm a detected subscription and create it"""
    supabase = get_supabase()
    
    # Calculate next due date based on last transaction and frequency
    next_due = SubscriptionService.calculate_next_due_date(
        detected.last_transaction_date,
        detected.frequency,
    )
    
    # If next due is in the past, advance it
    while next_due < date.today():
        next_due = SubscriptionService.calculate_next_due_date(next_due, detected.frequency)
    
    data = {
        "user_id": current_user["id"],
        "payee_name": detected.payee_name,
        "estimated_amount": float(detected.estimated_amount),
        "next_due_date": next_due.isoformat(),
        "frequency": detected.frequency.value,
        "category_id": str(detected.suggested_category_id) if detected.suggested_category_id else None,
        "is_active": True,
    }
    
    response = supabase.table("subscriptions").insert(data).execute()
    
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create subscription",
        )
    
    sub = response.data[0]
    return SubscriptionResponse(
        id=sub["id"],
        user_id=sub["user_id"],
        payee_name=sub["payee_name"],
        estimated_amount=sub["estimated_amount"],
        next_due_date=sub["next_due_date"],
        frequency=sub["frequency"],
        is_active=sub["is_active"],
        category_id=sub.get("category_id"),
        category_name=detected.suggested_category_name,
        created_at=sub["created_at"],
        updated_at=sub["updated_at"],
    )


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """Get a single subscription"""
    supabase = get_supabase()
    
    response = supabase.table("subscriptions").select(
        "*, categories(name), accounts(name)"
    ).eq("id", str(subscription_id)).eq("user_id", current_user["id"]).single().execute()
    
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )
    
    sub = response.data
    return SubscriptionResponse(
        id=sub["id"],
        user_id=sub["user_id"],
        payee_name=sub["payee_name"],
        estimated_amount=sub["estimated_amount"],
        next_due_date=sub["next_due_date"],
        frequency=sub["frequency"],
        is_active=sub["is_active"],
        category_id=sub.get("category_id"),
        account_id=sub.get("account_id"),
        category_name=sub.get("categories", {}).get("name") if sub.get("categories") else None,
        account_name=sub.get("accounts", {}).get("name") if sub.get("accounts") else None,
        created_at=sub["created_at"],
        updated_at=sub["updated_at"],
    )


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: UUID,
    subscription_data: SubscriptionUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update a subscription"""
    supabase = get_supabase()
    
    data = subscription_data.model_dump(exclude_unset=True)
    
    if "estimated_amount" in data:
        data["estimated_amount"] = float(data["estimated_amount"])
    if "next_due_date" in data:
        data["next_due_date"] = data["next_due_date"].isoformat()
    if "frequency" in data:
        data["frequency"] = data["frequency"].value
    if "category_id" in data and data["category_id"]:
        data["category_id"] = str(data["category_id"])
    if "account_id" in data and data["account_id"]:
        data["account_id"] = str(data["account_id"])
    
    response = supabase.table("subscriptions").update(data).eq(
        "id", str(subscription_id)
    ).eq("user_id", current_user["id"]).execute()
    
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )
    
    sub = response.data[0]
    return SubscriptionResponse(
        id=sub["id"],
        user_id=sub["user_id"],
        payee_name=sub["payee_name"],
        estimated_amount=sub["estimated_amount"],
        next_due_date=sub["next_due_date"],
        frequency=sub["frequency"],
        is_active=sub["is_active"],
        category_id=sub.get("category_id"),
        account_id=sub.get("account_id"),
        category_name=None,
        account_name=None,
        created_at=sub["created_at"],
        updated_at=sub["updated_at"],
    )


@router.post("/{subscription_id}/advance", response_model=SubscriptionResponse)
async def advance_subscription(
    subscription_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """Advance subscription to next due date (after payment)"""
    result = SubscriptionService.advance_due_date(
        subscription_id=str(subscription_id),
        user_id=current_user["id"],
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )
    
    return SubscriptionResponse(
        id=result["id"],
        user_id=result["user_id"],
        payee_name=result["payee_name"],
        estimated_amount=result["estimated_amount"],
        next_due_date=result["next_due_date"],
        frequency=result["frequency"],
        is_active=result["is_active"],
        category_id=result.get("category_id"),
        account_id=result.get("account_id"),
        category_name=None,
        account_name=None,
        created_at=result["created_at"],
        updated_at=result["updated_at"],
    )


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """Delete a subscription"""
    supabase = get_supabase()
    
    response = supabase.table("subscriptions").delete().eq(
        "id", str(subscription_id)
    ).eq("user_id", current_user["id"]).execute()
    
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )


@router.patch("/{subscription_id}/toggle", response_model=SubscriptionResponse)
async def toggle_subscription(
    subscription_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """Toggle subscription active/paused state"""
    supabase = get_supabase()
    
    # Get current state
    current = supabase.table("subscriptions").select("is_active").eq(
        "id", str(subscription_id)
    ).eq("user_id", current_user["id"]).single().execute()
    
    if not current.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )
    
    new_state = not current.data["is_active"]
    
    response = supabase.table("subscriptions").update({
        "is_active": new_state
    }).eq("id", str(subscription_id)).eq("user_id", current_user["id"]).execute()
    
    sub = response.data[0]
    return SubscriptionResponse(
        id=sub["id"],
        user_id=sub["user_id"],
        payee_name=sub["payee_name"],
        estimated_amount=sub["estimated_amount"],
        next_due_date=sub["next_due_date"],
        frequency=sub["frequency"],
        is_active=sub["is_active"],
        category_id=sub.get("category_id"),
        account_id=sub.get("account_id"),
        category_name=None,
        account_name=None,
        created_at=sub["created_at"],
        updated_at=sub["updated_at"],
    )


@router.post("/process-due")
async def process_due_subscriptions(
    current_user: dict = Depends(get_current_user),
):
    """
    Process all due subscriptions for the current user.
    Creates transactions, deducts from accounts, and advances due dates.
    """
    results = SubscriptionService.process_due_subscriptions(user_id=current_user["id"])
    
    return {
        "processed_count": len([r for r in results if r.get("status") == "processed"]),
        "skipped_count": len([r for r in results if r.get("status") == "skipped"]),
        "error_count": len([r for r in results if r.get("status") == "error"]),
        "details": results
    }
