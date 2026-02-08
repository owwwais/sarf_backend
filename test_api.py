#!/usr/bin/env python3
"""
واجهة بسيطة لاختبار الـ Backend API
Simple Backend API Tester
"""

import requests
import json
from typing import Optional

BASE_URL = "http://localhost:8001"

class APITester:
    def __init__(self):
        self.token: Optional[str] = None
        self.user: Optional[dict] = None
    
    def _headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        return {"Content-Type": "application/json"}
    
    def _print_response(self, name: str, response):
        print(f"\n{'='*50}")
        print(f"📡 {name}")
        print(f"{'='*50}")
        print(f"Status: {response.status_code}")
        try:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return data
        except:
            print(f"Response: {response.text}")
            return None

    # ============ Auth ============
    def login(self, email: str, password: str):
        """تسجيل الدخول"""
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password}
        )
        data = self._print_response("تسجيل الدخول / Login", response)
        if response.status_code == 200 and data:
            self.token = data.get("access_token")
            self.user = data.get("user")
            print(f"\n✅ تم تسجيل الدخول بنجاح!")
            print(f"   User ID: {self.user.get('id')}")
            print(f"   Email: {self.user.get('email')}")
        return data

    def register(self, email: str, password: str):
        """إنشاء حساب جديد"""
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={"email": email, "password": password}
        )
        data = self._print_response("التسجيل / Register", response)
        if response.status_code == 200 and data:
            self.token = data.get("access_token")
            self.user = data.get("user")
        return data

    # ============ Accounts ============
    def get_accounts(self):
        """جلب الحسابات البنكية"""
        response = requests.get(f"{BASE_URL}/accounts/", headers=self._headers())
        return self._print_response("الحسابات البنكية / Accounts", response)

    def create_account(self, name: str, balance: float, account_type: str = "checking"):
        """إنشاء حساب بنكي"""
        response = requests.post(
            f"{BASE_URL}/accounts/",
            headers=self._headers(),
            json={"name": name, "balance": balance, "type": account_type}
        )
        return self._print_response("إنشاء حساب / Create Account", response)

    # ============ Categories ============
    def get_category_groups(self):
        """جلب مجموعات الفئات"""
        response = requests.get(f"{BASE_URL}/categories/groups", headers=self._headers())
        return self._print_response("مجموعات الفئات / Category Groups", response)

    def get_categories(self):
        """جلب الفئات"""
        response = requests.get(f"{BASE_URL}/categories/", headers=self._headers())
        return self._print_response("الفئات / Categories", response)

    def create_category_group(self, name: str):
        """إنشاء مجموعة فئات"""
        response = requests.post(
            f"{BASE_URL}/categories/groups",
            headers=self._headers(),
            json={"name": name}
        )
        return self._print_response("إنشاء مجموعة / Create Group", response)

    def create_category(self, name: str, group_id: str):
        """إنشاء فئة"""
        response = requests.post(
            f"{BASE_URL}/categories/",
            headers=self._headers(),
            json={"name": name, "group_id": group_id}
        )
        return self._print_response("إنشاء فئة / Create Category", response)

    # ============ Budget ============
    def get_budget_summary(self):
        """ملخص الميزانية"""
        response = requests.get(f"{BASE_URL}/budget/summary", headers=self._headers())
        return self._print_response("ملخص الميزانية / Budget Summary", response)

    # ============ Transactions ============
    def get_transactions(self, limit: int = 10):
        """جلب المعاملات"""
        response = requests.get(
            f"{BASE_URL}/transactions/",
            headers=self._headers(),
            params={"limit": limit}
        )
        return self._print_response("المعاملات / Transactions", response)

    # ============ Subscriptions ============
    def get_subscriptions(self):
        """جلب الاشتراكات"""
        response = requests.get(
            f"{BASE_URL}/subscriptions/",
            headers=self._headers(),
            params={"active_only": False}
        )
        return self._print_response("الاشتراكات / Subscriptions", response)

    # ============ Health ============
    def health_check(self):
        """فحص صحة الخادم"""
        response = requests.get(f"{BASE_URL}/health")
        return self._print_response("فحص الخادم / Health Check", response)


def print_menu():
    print("\n" + "="*60)
    print("🧪 أداة اختبار الـ Backend API")
    print("="*60)
    print("""
الأوامر المتاحة:
────────────────
[0] فحص صحة الخادم (Health Check)
[1] تسجيل الدخول (Login)
[2] التسجيل (Register)
────────────────
[3] جلب الحسابات (Get Accounts)
[4] إنشاء حساب (Create Account)
────────────────
[5] جلب مجموعات الفئات (Get Category Groups)
[6] جلب الفئات (Get Categories)
[7] إنشاء مجموعة فئات (Create Category Group)
[8] إنشاء فئة (Create Category)
────────────────
[9] ملخص الميزانية (Budget Summary)
[10] جلب المعاملات (Get Transactions)
[11] جلب الاشتراكات (Get Subscriptions)
────────────────
[q] خروج (Quit)
""")


def main():
    tester = APITester()
    
    print("\n🚀 مرحباً بك في أداة اختبار الـ Backend!")
    print(f"   الخادم: {BASE_URL}")
    
    # فحص الخادم أولاً
    tester.health_check()
    
    while True:
        print_menu()
        
        if tester.token:
            print(f"✅ مسجل الدخول كـ: {tester.user.get('email', 'Unknown')}")
        else:
            print("❌ غير مسجل الدخول")
        
        choice = input("\nاختر رقم الأمر: ").strip()
        
        try:
            if choice == "q":
                print("\n👋 مع السلامة!")
                break
            
            elif choice == "0":
                tester.health_check()
            
            elif choice == "1":
                email = input("البريد الإلكتروني: ").strip()
                password = input("كلمة المرور: ").strip()
                tester.login(email, password)
            
            elif choice == "2":
                email = input("البريد الإلكتروني: ").strip()
                password = input("كلمة المرور: ").strip()
                tester.register(email, password)
            
            elif choice == "3":
                if not tester.token:
                    print("⚠️ يجب تسجيل الدخول أولاً!")
                else:
                    tester.get_accounts()
            
            elif choice == "4":
                if not tester.token:
                    print("⚠️ يجب تسجيل الدخول أولاً!")
                else:
                    name = input("اسم الحساب: ").strip()
                    balance = float(input("الرصيد: ").strip())
                    acc_type = input("النوع (checking/savings/credit/cash) [checking]: ").strip() or "checking"
                    tester.create_account(name, balance, acc_type)
            
            elif choice == "5":
                if not tester.token:
                    print("⚠️ يجب تسجيل الدخول أولاً!")
                else:
                    tester.get_category_groups()
            
            elif choice == "6":
                if not tester.token:
                    print("⚠️ يجب تسجيل الدخول أولاً!")
                else:
                    tester.get_categories()
            
            elif choice == "7":
                if not tester.token:
                    print("⚠️ يجب تسجيل الدخول أولاً!")
                else:
                    name = input("اسم المجموعة: ").strip()
                    tester.create_category_group(name)
            
            elif choice == "8":
                if not tester.token:
                    print("⚠️ يجب تسجيل الدخول أولاً!")
                else:
                    name = input("اسم الفئة: ").strip()
                    group_id = input("معرف المجموعة (Group ID): ").strip()
                    tester.create_category(name, group_id)
            
            elif choice == "9":
                if not tester.token:
                    print("⚠️ يجب تسجيل الدخول أولاً!")
                else:
                    tester.get_budget_summary()
            
            elif choice == "10":
                if not tester.token:
                    print("⚠️ يجب تسجيل الدخول أولاً!")
                else:
                    tester.get_transactions()
            
            elif choice == "11":
                if not tester.token:
                    print("⚠️ يجب تسجيل الدخول أولاً!")
                else:
                    tester.get_subscriptions()
            
            else:
                print("❌ اختيار غير صحيح!")
        
        except Exception as e:
            print(f"\n❌ خطأ: {e}")
        
        input("\nاضغط Enter للمتابعة...")


if __name__ == "__main__":
    main()
