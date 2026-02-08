from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime
import json
import re
from app.config import get_settings

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class AIService:
    def __init__(self):
        settings = get_settings()
        self.client = None
        self.model_name = "gemini-2.0-flash-lite"
        
        # Initialize Gemini client
        if GEMINI_AVAILABLE and settings.gemini_api_key:
            self.client = genai.Client(api_key=settings.gemini_api_key)

    def parse_sms_transaction(self, sms_body: str, user_categories: List[dict] = None) -> dict:
        """Parse SMS text to extract transaction details using Gemini"""
        if not self.client:
            return self._fallback_parse(sms_body, user_categories)

        # Build category list for AI
        if user_categories:
            category_names = [cat.get('name', '') for cat in user_categories]
            category_list = "، ".join(category_names)
            category_instruction = f"""- category_id: معرف الفئة المناسبة من القائمة التالية (اختر الأنسب فقط)
- category_name: اسم الفئة المختارة

الفئات المتاحة:
{json.dumps({cat.get('id'): cat.get('name') for cat in user_categories}, ensure_ascii=False)}

اختر category_id من المعرفات أعلاه فقط."""
        else:
            category_instruction = "- category_suggestion: اقتراح فئة مناسبة بالعربية"

        prompt = f"""أنت محلل رسائل SMS مالية متخصص في رسائل البنوك السعودية.
استخرج تفاصيل المعاملة من الرسالة وأرجع كائن JSON يحتوي على:
- payee: اسم المتجر/التاجر (نص، مطلوب)
- amount: مبلغ المعاملة كرقم (float، مطلوب)
- date: تاريخ المعاملة بتنسيق YYYY-MM-DD (نص، اختياري - استخدم null إذا لم يوجد)
- transaction_type: إما "expense" للمصروفات أو "income" للدخل (نص، مطلوب)
{category_instruction}
- is_transaction: هل هذه معاملة مالية صحيحة (boolean)

البنوك السعودية الشائعة: الراجحي، الأهلي، الرياض، البلاد، ساب، الإنماء، العربي
العملة عادة ريال سعودي SAR.

أرجع JSON صالح فقط بدون أي نص إضافي أو تنسيق markdown.

الرسالة: {sms_body}"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            text = response.text.strip()
            print(f"[AI] Raw Gemini response: {text}")
            
            # Clean markdown if present
            if text.startswith("```"):
                text = re.sub(r'^```json?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)
            
            result = json.loads(text)
            print(f"[AI] Parsed JSON: {result}")
            
            # Determine if it's a transaction based on amount
            amount = Decimal(str(result.get("amount", 0)))
            is_transaction = amount > 0 and result.get("is_transaction", True)
            
            return {
                "payee": result.get("payee", "غير معروف"),
                "amount": amount,
                "date": self._parse_date(result.get("date")),
                "transaction_type": result.get("transaction_type", "expense"),
                "category_id": result.get("category_id"),
                "category_name": result.get("category_name", result.get("category_suggestion", "أخرى")),
                "is_transaction": is_transaction,
                "confidence": 0.95
            }
        except Exception as e:
            print(f"Gemini parsing error: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_parse(sms_body, user_categories)

    def generate_monthly_report(self, transactions: List[dict], month: str, categories: List[dict] = None) -> dict:
        """Generate a smart monthly financial report using Gemini"""
        if not self.client:
            return self._fallback_report(transactions, month)

        # Prepare transaction summary
        total_income = sum(t.get('amount', 0) for t in transactions if t.get('transaction_type') == 'income')
        total_expense = sum(t.get('amount', 0) for t in transactions if t.get('transaction_type') == 'expense')
        
        # Group by category
        category_spending = {}
        for t in transactions:
            if t.get('transaction_type') == 'expense':
                cat = t.get('category_name', 'غير مصنف')
                category_spending[cat] = category_spending.get(cat, 0) + t.get('amount', 0)
        
        # Prepare data for AI
        transactions_summary = json.dumps({
            "month": month,
            "total_income": float(total_income),
            "total_expense": float(total_expense),
            "net_savings": float(total_income - total_expense),
            "transaction_count": len(transactions),
            "category_breakdown": {k: float(v) for k, v in category_spending.items()},
            "top_expenses": sorted(
                [{"payee": t.get('payee_name', ''), "amount": float(t.get('amount', 0))} 
                 for t in transactions if t.get('transaction_type') == 'expense'],
                key=lambda x: x['amount'], reverse=True
            )[:10]
        }, ensure_ascii=False)

        prompt = f"""أنت مستشار مالي ذكي. قم بتحليل البيانات المالية التالية وأنشئ تقريراً شهرياً شاملاً.

البيانات:
{transactions_summary}

أنشئ تقريراً بتنسيق JSON يحتوي على:
{{
    "summary": "ملخص قصير وواضح عن الوضع المالي هذا الشهر (2-3 جمل)",
    "highlights": ["أهم 3-5 نقاط بارزة"],
    "concerns": ["أي مخاوف أو تحذيرات مالية إن وجدت"],
    "tips": ["3-5 نصائح عملية لتحسين الوضع المالي"],
    "category_analysis": {{
        "highest_spending": "الفئة الأعلى إنفاقاً",
        "recommendation": "توصية لتقليل الإنفاق"
    }},
    "savings_rate": "نسبة الادخار كنص (مثل: 20%)",
    "financial_health": "تقييم الصحة المالية: ممتاز/جيد/متوسط/يحتاج تحسين",
    "next_month_goal": "هدف مقترح للشهر القادم"
}}

أرجع JSON صالح فقط بدون أي نص إضافي."""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = re.sub(r'^```json?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)
            
            report = json.loads(text)
            report['raw_data'] = {
                'total_income': float(total_income),
                'total_expense': float(total_expense),
                'net_savings': float(total_income - total_expense),
                'transaction_count': len(transactions),
                'category_breakdown': {k: float(v) for k, v in category_spending.items()}
            }
            return report
        except Exception as e:
            print(f"Gemini report error: {e}")
            return self._fallback_report(transactions, month)

    def _fallback_report(self, transactions: List[dict], month: str) -> dict:
        """Fallback report when AI is unavailable"""
        total_income = sum(t.get('amount', 0) for t in transactions if t.get('transaction_type') == 'income')
        total_expense = sum(t.get('amount', 0) for t in transactions if t.get('transaction_type') == 'expense')
        net_savings = total_income - total_expense
        savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0
        
        return {
            "summary": f"في شهر {month}، بلغ إجمالي دخلك {total_income:,.2f} ر.س وإجمالي مصروفاتك {total_expense:,.2f} ر.س.",
            "highlights": [
                f"إجمالي المعاملات: {len(transactions)}",
                f"صافي الادخار: {net_savings:,.2f} ر.س"
            ],
            "concerns": [] if net_savings >= 0 else ["المصروفات تجاوزت الدخل هذا الشهر"],
            "tips": ["راجع مصروفاتك الشهرية بانتظام", "حاول تخصيص 20% من دخلك للادخار"],
            "savings_rate": f"{savings_rate:.1f}%",
            "financial_health": "جيد" if savings_rate > 10 else "يحتاج تحسين",
            "raw_data": {
                'total_income': float(total_income),
                'total_expense': float(total_expense),
                'net_savings': float(net_savings),
                'transaction_count': len(transactions)
            }
        }

    def _fallback_parse(self, text: str, user_categories: List[dict] = None) -> dict:
        """Fallback regex-based parsing when Gemini is unavailable"""
        amount_patterns = [
            r'(?:SAR|ر\.س|ريال)\s*([\d,]+\.?\d*)',
            r'([\d,]+\.?\d*)\s*(?:SAR|ر\.س|ريال)',
            r'Amount:?\s*([\d,]+\.?\d*)',
            r'المبلغ:?\s*([\d,]+\.?\d*)',
        ]
        
        amount = Decimal("0")
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(",", "")
                amount = Decimal(amount_str)
                break

        payee_patterns = [
            r'(?:at|من|لدى|في)\s+([A-Za-z\s\u0600-\u06FF]+?)(?:\s+(?:SAR|ر\.س|on|في))',
            r'Purchase\s+(?:at|from)\s+([A-Za-z\s]+)',
        ]
        
        payee = "غير معروف"
        for pattern in payee_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                payee = match.group(1).strip()
                break

        is_income = any(word in text.lower() for word in ['credit', 'deposit', 'received', 'salary', 'إيداع', 'راتب', 'تحويل وارد'])
        
        # Try to match first category if available
        category_id = None
        category_name = "أخرى"
        if user_categories and len(user_categories) > 0:
            category_id = user_categories[0].get('id')
            category_name = user_categories[0].get('name', 'أخرى')

        return {
            "payee": payee,
            "amount": amount,
            "date": date.today(),
            "transaction_type": "income" if is_income else "expense",
            "category_id": category_id,
            "category_name": category_name,
            "is_transaction": amount > 0,
            "confidence": 0.5
        }

    def _parse_date(self, date_str: Optional[str]) -> date:
        """Parse date string to date object"""
        if not date_str:
            return date.today()
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            return date.today()


# Singleton instance
ai_service = AIService()
