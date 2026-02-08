from decimal import Decimal
from uuid import UUID
from app.database import get_supabase


class BudgetService:
    def __init__(self):
        self.supabase = get_supabase()

    def move_money(
        self,
        user_id: str,
        from_category_id: UUID,
        to_category_id: UUID,
        amount: Decimal,
    ) -> tuple:
        from_cat = self.supabase.table("categories").select("*").eq("id", str(from_category_id)).eq("user_id", user_id).single().execute()
        if not from_cat.data:
            raise ValueError("Source category not found")
        to_cat = self.supabase.table("categories").select("*").eq("id", str(to_category_id)).eq("user_id", user_id).single().execute()
        if not to_cat.data:
            raise ValueError("Target category not found")
        from_assigned = Decimal(str(from_cat.data["assigned_amount"]))
        if from_assigned < amount:
            raise ValueError("Insufficient funds in source category")
        new_from_assigned = from_assigned - amount
        to_assigned = Decimal(str(to_cat.data["assigned_amount"]))
        new_to_assigned = to_assigned + amount
        self.supabase.table("categories").update({"assigned_amount": float(new_from_assigned)}).eq("id", str(from_category_id)).execute()
        self.supabase.table("categories").update({"assigned_amount": float(new_to_assigned)}).eq("id", str(to_category_id)).execute()
        updated_from = self.supabase.table("categories").select("*").eq("id", str(from_category_id)).single().execute()
        updated_to = self.supabase.table("categories").select("*").eq("id", str(to_category_id)).single().execute()
        return updated_from.data, updated_to.data

    def get_to_be_budgeted(self, user_id: str) -> Decimal:
        accounts = self.supabase.table("accounts").select("balance").eq("user_id", user_id).eq("is_active", True).execute()
        total_balance = sum(Decimal(str(acc["balance"])) for acc in accounts.data)
        categories = self.supabase.table("categories").select("assigned_amount").eq("user_id", user_id).eq("is_hidden", False).execute()
        total_assigned = sum(Decimal(str(cat["assigned_amount"])) for cat in categories.data)
        return total_balance - total_assigned

    def get_budget_summary(self, user_id: str) -> dict:
        to_be_budgeted = self.get_to_be_budgeted(user_id)
        accounts = self.supabase.table("accounts").select("balance").eq("user_id", user_id).eq("is_active", True).execute()
        total_balance = sum(Decimal(str(acc["balance"])) for acc in accounts.data)
        categories = self.supabase.table("categories").select("assigned_amount, activity_amount").eq("user_id", user_id).eq("is_hidden", False).execute()
        total_assigned = sum(Decimal(str(cat["assigned_amount"])) for cat in categories.data)
        total_activity = sum(Decimal(str(cat["activity_amount"])) for cat in categories.data)
        return {
            "to_be_budgeted": float(to_be_budgeted),
            "total_balance": float(total_balance),
            "total_assigned": float(total_assigned),
            "total_spent": float(total_activity),
        }


budget_service = BudgetService()
