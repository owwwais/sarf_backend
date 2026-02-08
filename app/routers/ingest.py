from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import date
from app.database import get_supabase
from app.dependencies import get_current_user
from app.services.ai_service import ai_service
from app.schemas.pending_transaction import (
    SMSIngestRequest,
    OCRIngestRequest,
    PendingTransactionResponse,
    PendingTransactionWithSuggestions,
    ApproveTransactionRequest,
    CategorySuggestion,
)
from app.schemas.transaction import TransactionResponse

router = APIRouter()


@router.post("/sms", response_model=PendingTransactionResponse, status_code=status.HTTP_201_CREATED)
async def ingest_sms(
    request: SMSIngestRequest,
    current_user: dict = Depends(get_current_user),
):
    """Parse SMS and create pending transaction for review"""
    parsed = ai_service.parse_sms_transaction(request.sms_body)
    
    if not parsed.get("is_transaction", False):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="SMS does not appear to be a financial transaction"
        )

    supabase = get_supabase()
    
    suggested_category_id = None
    if parsed["payee"] != "Unknown":
        suggested_category_id = await _find_category_by_payee(
            supabase, current_user["id"], parsed["payee"]
        )

    accounts = supabase.table("accounts").select("id").eq(
        "user_id", current_user["id"]
    ).eq("is_active", True).limit(1).execute()
    suggested_account_id = accounts.data[0]["id"] if accounts.data else None

    data = {
        "user_id": current_user["id"],
        "raw_text": request.sms_body,
        "source": "sms",
        "parsed_payee": parsed["payee"],
        "parsed_amount": float(parsed["amount"]),
        "parsed_date": parsed["date"].isoformat() if parsed["date"] else None,
        "suggested_account_id": suggested_account_id,
        "suggested_category_id": str(suggested_category_id) if suggested_category_id else None,
        "confidence_score": parsed.get("confidence", 0.5),
        "status": "pending",
    }

    response = supabase.table("pending_transactions").insert(data).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create pending transaction"
        )

    if parsed["payee"] != "Unknown":
        await _store_payee_embedding(supabase, current_user["id"], parsed["payee"], suggested_category_id)

    return PendingTransactionResponse(**response.data[0])


@router.post("/ocr", response_model=PendingTransactionResponse, status_code=status.HTTP_201_CREATED)
async def ingest_ocr(
    request: OCRIngestRequest,
    current_user: dict = Depends(get_current_user),
):
    """Parse OCR text and create pending transaction for review"""
    parsed = ai_service.parse_ocr_text(request.ocr_text)

    supabase = get_supabase()

    suggested_category_id = None
    if parsed["payee"] != "Unknown":
        suggested_category_id = await _find_category_by_payee(
            supabase, current_user["id"], parsed["payee"]
        )

    accounts = supabase.table("accounts").select("id").eq(
        "user_id", current_user["id"]
    ).eq("is_active", True).limit(1).execute()
    suggested_account_id = accounts.data[0]["id"] if accounts.data else None

    data = {
        "user_id": current_user["id"],
        "raw_text": request.ocr_text,
        "source": "ocr",
        "parsed_payee": parsed["payee"],
        "parsed_amount": float(parsed["amount"]),
        "parsed_date": parsed["date"].isoformat() if parsed["date"] else None,
        "suggested_account_id": suggested_account_id,
        "suggested_category_id": str(suggested_category_id) if suggested_category_id else None,
        "confidence_score": parsed.get("confidence", 0.5),
        "status": "pending",
    }

    response = supabase.table("pending_transactions").insert(data).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create pending transaction"
        )

    return PendingTransactionResponse(**response.data[0])


@router.get("/pending", response_model=List[PendingTransactionWithSuggestions])
async def list_pending_transactions(
    status_filter: Optional[str] = "pending",
    current_user: dict = Depends(get_current_user),
):
    """List all pending transactions in inbox"""
    supabase = get_supabase()
    
    query = supabase.table("pending_transactions").select("*").eq(
        "user_id", current_user["id"]
    )
    
    if status_filter:
        query = query.eq("status", status_filter)
    
    response = query.order("created_at", desc=True).execute()

    categories = supabase.table("categories").select("id, name").eq(
        "user_id", current_user["id"]
    ).eq("is_hidden", False).execute()
    category_map = {cat["id"]: cat["name"] for cat in categories.data}

    accounts = supabase.table("accounts").select("id, name").eq(
        "user_id", current_user["id"]
    ).eq("is_active", True).execute()
    account_map = {acc["id"]: acc["name"] for acc in accounts.data}

    results = []
    for pending in response.data:
        suggestions = await _get_category_suggestions(
            supabase, current_user["id"], pending.get("parsed_payee", ""), categories.data
        )
        
        item = PendingTransactionWithSuggestions(
            **pending,
            category_suggestions=suggestions,
            account_name=account_map.get(pending.get("suggested_account_id")),
            category_name=category_map.get(pending.get("suggested_category_id")),
        )
        results.append(item)

    return results


@router.post("/pending/{pending_id}/approve", response_model=TransactionResponse)
async def approve_pending_transaction(
    pending_id: UUID,
    request: ApproveTransactionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Approve a pending transaction and create actual transaction"""
    supabase = get_supabase()

    pending = supabase.table("pending_transactions").select("*").eq(
        "id", str(pending_id)
    ).eq("user_id", current_user["id"]).single().execute()

    if not pending.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending transaction not found"
        )

    if pending.data["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction already processed"
        )

    payee = request.payee_name or pending.data.get("parsed_payee", "Unknown")
    amount = float(request.amount) if request.amount else pending.data.get("parsed_amount", 0)
    txn_date = request.transaction_date or pending.data.get("parsed_date") or date.today()

    txn_data = {
        "user_id": current_user["id"],
        "account_id": str(request.account_id),
        "category_id": str(request.category_id) if request.category_id else None,
        "payee_name": payee,
        "amount": amount,
        "transaction_type": "expense",
        "transaction_date": txn_date.isoformat() if isinstance(txn_date, date) else txn_date,
        "memo": request.memo,
        "raw_sms_body": pending.data["raw_text"],
    }

    txn_response = supabase.table("transactions").insert(txn_data).execute()
    if not txn_response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create transaction"
        )

    txn = txn_response.data[0]
    
    account = supabase.table("accounts").select("balance").eq("id", str(request.account_id)).single().execute()
    new_balance = Decimal(str(account.data["balance"])) - Decimal(str(amount))
    supabase.table("accounts").update({"balance": float(new_balance)}).eq("id", str(request.account_id)).execute()

    if request.category_id:
        cat = supabase.table("categories").select("activity_amount").eq("id", str(request.category_id)).single().execute()
        new_activity = Decimal(str(cat.data["activity_amount"])) + Decimal(str(amount))
        supabase.table("categories").update({"activity_amount": float(new_activity)}).eq("id", str(request.category_id)).execute()

        await _update_payee_embedding(supabase, current_user["id"], payee, str(request.category_id))

    supabase.table("pending_transactions").update({"status": "approved"}).eq("id", str(pending_id)).execute()

    return TransactionResponse(**txn)


@router.post("/pending/{pending_id}/reject")
async def reject_pending_transaction(
    pending_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """Reject a pending transaction"""
    supabase = get_supabase()

    pending = supabase.table("pending_transactions").select("id, status").eq(
        "id", str(pending_id)
    ).eq("user_id", current_user["id"]).single().execute()

    if not pending.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending transaction not found"
        )

    supabase.table("pending_transactions").update({"status": "rejected"}).eq("id", str(pending_id)).execute()

    return {"message": "Transaction rejected"}


@router.get("/pending/count")
async def get_pending_count(
    current_user: dict = Depends(get_current_user),
):
    """Get count of pending transactions for badge"""
    supabase = get_supabase()
    
    response = supabase.table("pending_transactions").select("id", count="exact").eq(
        "user_id", current_user["id"]
    ).eq("status", "pending").execute()

    return {"count": response.count or 0}


async def _find_category_by_payee(supabase, user_id: str, payee: str) -> Optional[str]:
    """Find category using payee embeddings"""
    embedding = ai_service.get_embedding(payee)
    
    if not embedding:
        existing = supabase.table("payee_embeddings").select("category_id").eq(
            "user_id", user_id
        ).ilike("payee_name", f"%{payee}%").limit(1).execute()
        return existing.data[0]["category_id"] if existing.data else None

    try:
        result = supabase.rpc("match_payee_embedding", {
            "query_embedding": embedding,
            "match_user_id": user_id,
            "match_threshold": 0.7,
            "match_count": 1
        }).execute()
        
        if result.data:
            return result.data[0]["category_id"]
    except Exception as e:
        print(f"Vector search error: {e}")

    return None


async def _store_payee_embedding(supabase, user_id: str, payee: str, category_id: Optional[str]):
    """Store payee embedding for future matching"""
    embedding = ai_service.get_embedding(payee)
    
    if not embedding:
        return

    try:
        supabase.table("payee_embeddings").upsert({
            "user_id": user_id,
            "payee_name": payee,
            "category_id": category_id,
            "embedding": embedding,
        }, on_conflict="user_id,payee_name").execute()
    except Exception as e:
        print(f"Store embedding error: {e}")


async def _update_payee_embedding(supabase, user_id: str, payee: str, category_id: str):
    """Update payee-category mapping when user approves"""
    embedding = ai_service.get_embedding(payee)

    try:
        supabase.table("payee_embeddings").upsert({
            "user_id": user_id,
            "payee_name": payee,
            "category_id": category_id,
            "embedding": embedding if embedding else None,
            "usage_count": 1,
        }, on_conflict="user_id,payee_name").execute()
        
        supabase.rpc("increment_payee_usage", {"p_user_id": user_id, "p_payee_name": payee}).execute()
    except Exception as e:
        print(f"Update embedding error: {e}")


async def _get_category_suggestions(supabase, user_id: str, payee: str, categories: list) -> List[CategorySuggestion]:
    """Get category suggestions for a payee"""
    if not payee or payee == "Unknown":
        return []

    suggestions = []
    
    embedding = ai_service.get_embedding(payee)
    if embedding:
        try:
            result = supabase.rpc("match_payee_embedding", {
                "query_embedding": embedding,
                "match_user_id": user_id,
                "match_threshold": 0.5,
                "match_count": 3
            }).execute()
            
            for match in result.data or []:
                cat = next((c for c in categories if c["id"] == match["category_id"]), None)
                if cat:
                    suggestions.append(CategorySuggestion(
                        category_id=match["category_id"],
                        category_name=cat["name"],
                        confidence=match["similarity"]
                    ))
        except Exception as e:
            print(f"Suggestion error: {e}")

    return suggestions
