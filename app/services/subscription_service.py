from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict
from collections import defaultdict
from app.database import get_supabase
from app.schemas.subscription import DetectedSubscription, SubscriptionFrequency
import statistics


class SubscriptionService:
    
    @staticmethod
    def detect_subscriptions(user_id: str, days_lookback: int = 90) -> List[DetectedSubscription]:
        """
        Detect potential subscriptions from transaction history.
        Algorithm:
        1. Get all expense transactions from the last N days
        2. Group by payee_name (fuzzy matching)
        3. Analyze patterns: frequency, amount consistency
        4. Score confidence based on pattern strength
        """
        supabase = get_supabase()
        
        start_date = (date.today() - timedelta(days=days_lookback)).isoformat()
        
        response = supabase.table("transactions").select(
            "id, payee_name, amount, transaction_date, category_id"
        ).eq("user_id", user_id).eq(
            "transaction_type", "expense"
        ).gte("transaction_date", start_date).order("transaction_date").execute()
        
        transactions = response.data
        if not transactions:
            return []
        
        # Group transactions by normalized payee name
        payee_groups: Dict[str, List[dict]] = defaultdict(list)
        for txn in transactions:
            normalized_payee = SubscriptionService._normalize_payee(txn["payee_name"])
            payee_groups[normalized_payee].append(txn)
        
        detected = []
        for payee, txns in payee_groups.items():
            if len(txns) < 2:
                continue
            
            result = SubscriptionService._analyze_pattern(payee, txns)
            if result and result.confidence >= 0.5:
                detected.append(result)
        
        # Sort by confidence descending
        detected.sort(key=lambda x: x.confidence, reverse=True)
        return detected
    
    @staticmethod
    def _normalize_payee(payee: str) -> str:
        """Normalize payee name for grouping"""
        return payee.lower().strip()
    
    @staticmethod
    def _analyze_pattern(payee: str, transactions: List[dict]) -> Optional[DetectedSubscription]:
        """Analyze transaction pattern for a single payee"""
        if len(transactions) < 2:
            return None
        
        # Extract amounts and dates
        amounts = [float(txn["amount"]) for txn in transactions]
        dates = [date.fromisoformat(txn["transaction_date"]) for txn in transactions]
        dates.sort()
        
        # Calculate time deltas between transactions
        deltas = []
        for i in range(1, len(dates)):
            delta = (dates[i] - dates[i-1]).days
            deltas.append(delta)
        
        if not deltas:
            return None
        
        avg_delta = statistics.mean(deltas)
        
        # Determine frequency based on average delta
        frequency, freq_confidence = SubscriptionService._determine_frequency(avg_delta, deltas)
        if not frequency:
            return None
        
        # Calculate amount consistency
        amount_confidence = SubscriptionService._calculate_amount_confidence(amounts)
        
        # Overall confidence
        confidence = (freq_confidence * 0.6) + (amount_confidence * 0.4)
        
        # Get the most common category
        category_id = None
        category_name = None
        category_counts = defaultdict(int)
        for txn in transactions:
            if txn.get("category_id"):
                category_counts[txn["category_id"]] += 1
        
        if category_counts:
            most_common_cat = max(category_counts, key=category_counts.get)
            category_id = most_common_cat
            # Fetch category name
            supabase = get_supabase()
            cat_response = supabase.table("categories").select("name").eq("id", most_common_cat).single().execute()
            if cat_response.data:
                category_name = cat_response.data["name"]
        
        return DetectedSubscription(
            payee_name=transactions[0]["payee_name"],  # Use original case
            estimated_amount=Decimal(str(round(statistics.mean(amounts), 2))),
            frequency=frequency,
            confidence=round(confidence, 2),
            transaction_count=len(transactions),
            last_transaction_date=max(dates),
            suggested_category_id=category_id,
            suggested_category_name=category_name,
        )
    
    @staticmethod
    def _determine_frequency(avg_delta: float, deltas: List[int]) -> tuple:
        """Determine subscription frequency from average delta between transactions"""
        # Weekly: 5-9 days
        # Monthly: 25-35 days
        # Yearly: 350-380 days
        
        if 5 <= avg_delta <= 9:
            # Check consistency for weekly
            variance = statistics.variance(deltas) if len(deltas) > 1 else 0
            confidence = max(0, 1 - (variance / 10))
            return SubscriptionFrequency.weekly, confidence
        
        elif 25 <= avg_delta <= 35:
            # Check consistency for monthly
            variance = statistics.variance(deltas) if len(deltas) > 1 else 0
            confidence = max(0, 1 - (variance / 50))
            return SubscriptionFrequency.monthly, confidence
        
        elif 350 <= avg_delta <= 380:
            # Yearly subscriptions
            variance = statistics.variance(deltas) if len(deltas) > 1 else 0
            confidence = max(0, 1 - (variance / 200))
            return SubscriptionFrequency.yearly, confidence
        
        return None, 0
    
    @staticmethod
    def _calculate_amount_confidence(amounts: List[float]) -> float:
        """Calculate confidence based on amount consistency"""
        if len(amounts) < 2:
            return 0.5
        
        mean_amount = statistics.mean(amounts)
        if mean_amount == 0:
            return 0
        
        # Calculate coefficient of variation
        std_dev = statistics.stdev(amounts)
        cv = std_dev / mean_amount
        
        # Lower CV = more consistent = higher confidence
        confidence = max(0, 1 - (cv * 2))
        return confidence
    
    @staticmethod
    def calculate_next_due_date(last_date: date, frequency: SubscriptionFrequency) -> date:
        """Calculate next due date based on frequency"""
        if frequency == SubscriptionFrequency.weekly:
            return last_date + timedelta(days=7)
        elif frequency == SubscriptionFrequency.monthly:
            # Add roughly one month
            next_month = last_date.month + 1
            next_year = last_date.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            # Handle day overflow (e.g., Jan 31 -> Feb 28)
            try:
                return last_date.replace(year=next_year, month=next_month)
            except ValueError:
                # Day doesn't exist in next month, use last day
                if next_month == 12:
                    return date(next_year + 1, 1, 1) - timedelta(days=1)
                return date(next_year, next_month + 1, 1) - timedelta(days=1)
        elif frequency == SubscriptionFrequency.yearly:
            try:
                return last_date.replace(year=last_date.year + 1)
            except ValueError:
                # Feb 29 in non-leap year
                return date(last_date.year + 1, 2, 28)
        return last_date
    
    @staticmethod
    def get_upcoming_subscriptions(user_id: str, days_ahead: int = 7) -> List[dict]:
        """Get subscriptions due in the next N days"""
        supabase = get_supabase()
        
        end_date = (date.today() + timedelta(days=days_ahead)).isoformat()
        today = date.today().isoformat()
        
        response = supabase.table("subscriptions").select(
            "*, categories(name)"
        ).eq("user_id", user_id).eq(
            "is_active", True
        ).gte("next_due_date", today).lte("next_due_date", end_date).order("next_due_date").execute()
        
        results = []
        for sub in response.data:
            due_date = date.fromisoformat(sub["next_due_date"])
            days_until = (due_date - date.today()).days
            results.append({
                "id": sub["id"],
                "payee_name": sub["payee_name"],
                "estimated_amount": sub["estimated_amount"],
                "next_due_date": sub["next_due_date"],
                "days_until_due": days_until,
                "category_name": sub.get("categories", {}).get("name") if sub.get("categories") else None,
            })
        
        return results
    
    @staticmethod
    def advance_due_date(subscription_id: str, user_id: str) -> Optional[dict]:
        """Advance subscription to next due date after payment"""
        supabase = get_supabase()
        
        # Get current subscription
        response = supabase.table("subscriptions").select("*").eq(
            "id", subscription_id
        ).eq("user_id", user_id).single().execute()
        
        if not response.data:
            return None
        
        sub = response.data
        current_due = date.fromisoformat(sub["next_due_date"])
        frequency = SubscriptionFrequency(sub["frequency"])
        
        next_due = SubscriptionService.calculate_next_due_date(current_due, frequency)
        
        # Update subscription
        update_response = supabase.table("subscriptions").update({
            "next_due_date": next_due.isoformat()
        }).eq("id", subscription_id).execute()
        
        return update_response.data[0] if update_response.data else None
    
    @staticmethod
    def process_due_subscriptions(user_id: str = None) -> List[dict]:
        """
        Process all due subscriptions automatically.
        - Creates transactions for each due subscription
        - Deducts from account balance
        - Updates category activity
        - Advances to next due date
        
        Args:
            user_id: Optional - process for specific user, or all users if None
        
        Returns:
            List of processed subscription results
        """
        supabase = get_supabase()
        today = date.today().isoformat()
        
        # Get all due subscriptions
        query = supabase.table("subscriptions").select("*").eq(
            "is_active", True
        ).lte("next_due_date", today)
        
        if user_id:
            query = query.eq("user_id", user_id)
        
        response = query.execute()
        
        if not response.data:
            return []
        
        processed = []
        
        for sub in response.data:
            result = SubscriptionService._process_single_subscription(sub)
            if result:
                processed.append(result)
        
        return processed
    
    @staticmethod
    def _process_single_subscription(sub: dict) -> Optional[dict]:
        """Process a single due subscription"""
        supabase = get_supabase()
        
        # Must have account_id to process automatically
        if not sub.get("account_id"):
            return {
                "subscription_id": sub["id"],
                "status": "skipped",
                "reason": "no_account_id",
                "payee_name": sub["payee_name"]
            }
        
        try:
            amount = float(sub["estimated_amount"])
            
            # 1. Create the transaction
            txn_data = {
                "user_id": sub["user_id"],
                "account_id": sub["account_id"],
                "category_id": sub.get("category_id"),
                "payee_name": sub["payee_name"],
                "amount": amount,
                "transaction_type": "expense",
                "transaction_date": sub["next_due_date"],
                "memo": f"اشتراك دوري - {sub['payee_name']}",
                "is_cleared": True
            }
            
            txn_response = supabase.table("transactions").insert(txn_data).execute()
            
            if not txn_response.data:
                return {
                    "subscription_id": sub["id"],
                    "status": "error",
                    "reason": "failed_to_create_transaction",
                    "payee_name": sub["payee_name"]
                }
            
            # 2. Update account balance (deduct)
            account_response = supabase.table("accounts").select("balance").eq(
                "id", sub["account_id"]
            ).single().execute()
            
            if account_response.data:
                current_balance = float(account_response.data["balance"])
                new_balance = current_balance - amount
                supabase.table("accounts").update({
                    "balance": new_balance
                }).eq("id", sub["account_id"]).execute()
            
            # 3. Update category activity_amount if category exists
            if sub.get("category_id"):
                cat_response = supabase.table("categories").select("activity_amount").eq(
                    "id", sub["category_id"]
                ).single().execute()
                
                if cat_response.data:
                    current_activity = float(cat_response.data.get("activity_amount") or 0)
                    new_activity = current_activity + amount
                    supabase.table("categories").update({
                        "activity_amount": new_activity
                    }).eq("id", sub["category_id"]).execute()
            
            # 4. Advance subscription to next due date
            current_due = date.fromisoformat(sub["next_due_date"])
            frequency = SubscriptionFrequency(sub["frequency"])
            next_due = SubscriptionService.calculate_next_due_date(current_due, frequency)
            
            supabase.table("subscriptions").update({
                "next_due_date": next_due.isoformat()
            }).eq("id", sub["id"]).execute()
            
            return {
                "subscription_id": sub["id"],
                "status": "processed",
                "payee_name": sub["payee_name"],
                "amount": amount,
                "transaction_id": txn_response.data[0]["id"],
                "next_due_date": next_due.isoformat()
            }
            
        except Exception as e:
            return {
                "subscription_id": sub["id"],
                "status": "error",
                "reason": str(e),
                "payee_name": sub["payee_name"]
            }
