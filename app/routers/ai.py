from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID

from app.dependencies import get_current_user
from app.database import get_supabase
from app.services.ai_service import ai_service


router = APIRouter(prefix="/ai", tags=["AI"])


class SMSAnalyzeRequest(BaseModel):
    sms_body: str
    sender: Optional[str] = None
    received_at: Optional[datetime] = None


class SMSAnalyzeResponse(BaseModel):
    payee: str
    amount: float
    date: date
    transaction_type: str
    category_id: Optional[str] = None
    category_name: str
    is_transaction: bool
    confidence: float


class CreateTransactionFromSMSRequest(BaseModel):
    sms_body: str
    account_id: UUID
    category_id: Optional[UUID] = None
    sender: Optional[str] = None


class MonthlyReportRequest(BaseModel):
    year: int
    month: int


@router.post("/analyze-sms", response_model=SMSAnalyzeResponse)
async def analyze_sms(
    request: SMSAnalyzeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Analyze SMS message to extract transaction details using AI"""
    supabase = get_supabase()
    
    # Fetch user categories for AI matching
    cat_response = supabase.table("categories").select("id, name").eq("user_id", current_user["id"]).execute()
    user_categories = cat_response.data if cat_response.data else []
    
    result = ai_service.parse_sms_transaction(request.sms_body, user_categories)
    
    return SMSAnalyzeResponse(
        payee=result["payee"],
        amount=float(result["amount"]),
        date=result["date"],
        transaction_type=result["transaction_type"],
        category_id=result.get("category_id"),
        category_name=result.get("category_name", "أخرى"),
        is_transaction=result["is_transaction"],
        confidence=result["confidence"]
    )


@router.post("/create-from-sms")
async def create_transaction_from_sms(
    request: CreateTransactionFromSMSRequest,
    current_user: dict = Depends(get_current_user),
):
    """Analyze SMS and automatically create a transaction"""
    supabase = get_supabase()
    
    # Fetch user categories for AI matching
    cat_response = supabase.table("categories").select("id, name").eq("user_id", current_user["id"]).execute()
    user_categories = cat_response.data if cat_response.data else []
    
    # Parse SMS with categories
    parsed = ai_service.parse_sms_transaction(request.sms_body, user_categories)
    
    if not parsed["is_transaction"]:
        return {
            "success": False,
            "message": "الرسالة لا تحتوي على معاملة مالية",
            "parsed": parsed
        }
    
    # Use AI-detected category if not provided
    category_id = request.category_id or parsed.get("category_id")
    
    # Create transaction
    transaction_data = {
        "user_id": current_user["id"],
        "account_id": str(request.account_id),
        "amount": float(parsed["amount"]),
        "transaction_type": parsed["transaction_type"],
        "payee_name": parsed["payee"],
        "transaction_date": parsed["date"].isoformat(),
    }
    
    if category_id:
        transaction_data["category_id"] = str(category_id)
    
    try:
        # Insert transaction
        response = supabase.table("transactions").insert(transaction_data).execute()
        transaction = response.data[0] if response.data else None
        
        if transaction:
            # Update account balance
            amount = float(parsed["amount"])
            if parsed["transaction_type"] == "expense":
                amount = -amount
            
            try:
                supabase.rpc("update_account_balance", {
                    "p_account_id": str(request.account_id),
                    "p_amount": amount
                }).execute()
            except Exception as balance_err:
                print(f"Balance update error (non-critical): {balance_err}")
            
            # Update category activity (direct update)
            if category_id and parsed["transaction_type"] == "expense":
                try:
                    cat_data = supabase.table("categories").select("activity_amount").eq("id", str(category_id)).single().execute()
                    current_activity = float(cat_data.data.get("activity_amount", 0)) if cat_data.data else 0
                    new_activity = current_activity + float(parsed["amount"])
                    supabase.table("categories").update({
                        "activity_amount": new_activity
                    }).eq("id", str(category_id)).execute()
                except Exception as cat_err:
                    print(f"Category activity update error (non-critical): {cat_err}")
        
        return {
            "success": True,
            "message": "تم إنشاء المعاملة بنجاح",
            "transaction": transaction,
            "parsed": {
                "payee": parsed["payee"],
                "amount": float(parsed["amount"]),
                "type": parsed["transaction_type"],
                "category_suggestion": parsed.get("category_suggestion", "أخرى"),
                "confidence": parsed["confidence"]
            }
        }
    except Exception as e:
        import traceback
        print(f"Create from SMS error: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"فشل في إنشاء المعاملة: {str(e)}"
        )


@router.post("/monthly-report")
async def generate_monthly_report(
    request: MonthlyReportRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generate AI-powered monthly financial report"""
    supabase = get_supabase()
    
    # Calculate date range
    start_date = date(request.year, request.month, 1)
    if request.month == 12:
        end_date = date(request.year + 1, 1, 1)
    else:
        end_date = date(request.year, request.month + 1, 1)
    
    # Fetch transactions for the month
    response = supabase.table("transactions").select(
        "*, categories(name)"
    ).eq("user_id", current_user["id"]).gte(
        "date", start_date.isoformat()
    ).lt(
        "date", end_date.isoformat()
    ).execute()
    
    transactions = []
    for t in response.data:
        transactions.append({
            "amount": float(t["amount"]),
            "transaction_type": t["transaction_type"],
            "payee_name": t.get("payee_name", ""),
            "category_name": t.get("categories", {}).get("name") if t.get("categories") else "غير مصنف",
            "date": t["date"]
        })
    
    # Get month name in Arabic
    month_names = {
        1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل",
        5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس",
        9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
    }
    month_name = f"{month_names[request.month]} {request.year}"
    
    # Generate report using AI
    report = ai_service.generate_monthly_report(transactions, month_name)
    
    return {
        "month": month_name,
        "report": report
    }


class AutoProcessSMSRequest(BaseModel):
    sms_body: str
    sender: Optional[str] = None


@router.post("/auto-process-sms")
async def auto_process_sms(
    request: AutoProcessSMSRequest,
    current_user: dict = Depends(get_current_user),
):
    """Automatically process SMS: detect transaction, match category, use primary account"""
    supabase = get_supabase()
    
    # Get user's primary account (first account or account with highest balance)
    acc_response = supabase.table("accounts").select("id, name, balance").eq(
        "user_id", current_user["id"]
    ).order("balance", desc=True).limit(1).execute()
    
    if not acc_response.data:
        return {
            "success": False,
            "message": "لا يوجد حساب مسجل. يرجى إضافة حساب أولاً.",
            "processed": False
        }
    
    primary_account = acc_response.data[0]
    
    # Fetch user categories for AI matching
    cat_response = supabase.table("categories").select("id, name").eq("user_id", current_user["id"]).execute()
    user_categories = cat_response.data if cat_response.data else []
    
    # Parse SMS with categories
    parsed = ai_service.parse_sms_transaction(request.sms_body, user_categories)
    
    print(f"[AUTO-PROCESS] Parsed result: {parsed}")
    print(f"[AUTO-PROCESS] is_transaction={parsed.get('is_transaction')}, amount={parsed.get('amount')}, category_id={parsed.get('category_id')}")
    
    # Check if valid transaction (has amount > 0)
    if not parsed["is_transaction"] or float(parsed.get("amount", 0)) <= 0:
        return {
            "success": True,
            "message": "الرسالة ليست معاملة مالية",
            "processed": False,
            "parsed": parsed
        }
    
    # Use AI-detected category
    category_id = parsed.get("category_id")
    
    # Create transaction
    transaction_data = {
        "user_id": current_user["id"],
        "account_id": primary_account["id"],
        "amount": float(parsed["amount"]),
        "transaction_type": parsed["transaction_type"],
        "payee_name": parsed["payee"],
        "transaction_date": parsed["date"].isoformat(),
    }
    
    if category_id:
        transaction_data["category_id"] = str(category_id)
    
    try:
        response = supabase.table("transactions").insert(transaction_data).execute()
        transaction = response.data[0] if response.data else None
        
        if transaction:
            # Update account balance
            amount = float(parsed["amount"])
            if parsed["transaction_type"] == "expense":
                amount = -amount
            
            try:
                supabase.rpc("update_account_balance", {
                    "p_account_id": primary_account["id"],
                    "p_amount": amount
                }).execute()
            except Exception as e:
                print(f"Balance update error: {e}")
            
            # Update category activity (direct update)
            if category_id and parsed["transaction_type"] == "expense":
                try:
                    # Get current activity amount
                    cat_data = supabase.table("categories").select("activity_amount").eq("id", str(category_id)).single().execute()
                    current_activity = float(cat_data.data.get("activity_amount", 0)) if cat_data.data else 0
                    new_activity = current_activity + float(parsed["amount"])
                    
                    # Update activity amount
                    supabase.table("categories").update({
                        "activity_amount": new_activity
                    }).eq("id", str(category_id)).execute()
                    print(f"[AUTO-PROCESS] Category {category_id} activity updated: {current_activity} -> {new_activity}")
                except Exception as e:
                    print(f"Category activity error: {e}")
        
        return {
            "success": True,
            "message": "تم إنشاء المعاملة تلقائياً",
            "processed": True,
            "transaction": transaction,
            "account_used": primary_account["name"],
            "category_matched": parsed.get("category_name", "غير مصنف"),
            "parsed": {
                "payee": parsed["payee"],
                "amount": float(parsed["amount"]),
                "type": parsed["transaction_type"],
                "confidence": parsed["confidence"]
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"فشل في إنشاء المعاملة: {str(e)}"
        )


@router.get("/status")
async def ai_status():
    """Check AI service status"""
    return {
        "gemini_available": ai_service.client is not None,
        "service": "Gemini 2.0 Flash Lite" if ai_service.client else "Fallback (Regex)"
    }
