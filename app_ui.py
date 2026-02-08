#!/usr/bin/env python3
"""
واجهة مستخدم بسيطة لاختبار التطبيق
Simple UI to test the SmartBudget App
Using Streamlit
"""

import streamlit as st
import requests
from datetime import datetime

# إعدادات
API_URL = "http://localhost:8001"

# تهيئة الجلسة
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None

def get_headers():
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}", "Content-Type": "application/json"}
    return {"Content-Type": "application/json"}

# ============ API Functions ============
def api_login(email, password):
    try:
        response = requests.post(f"{API_URL}/auth/login", json={"email": email, "password": password})
        if response.status_code == 200:
            data = response.json()
            st.session_state.token = data["access_token"]
            st.session_state.user = data["user"]
            return True, "تم تسجيل الدخول بنجاح"
        return False, response.json().get("detail", "فشل تسجيل الدخول")
    except Exception as e:
        return False, str(e)

def api_register(email, password):
    try:
        response = requests.post(f"{API_URL}/auth/register", json={"email": email, "password": password})
        if response.status_code == 200:
            data = response.json()
            st.session_state.token = data["access_token"]
            st.session_state.user = data["user"]
            return True, "تم إنشاء الحساب بنجاح"
        return False, response.json().get("detail", "فشل التسجيل")
    except Exception as e:
        return False, str(e)

def api_get_accounts():
    try:
        response = requests.get(f"{API_URL}/accounts/", headers=get_headers())
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def api_create_account(name, balance, acc_type):
    try:
        response = requests.post(
            f"{API_URL}/accounts/",
            headers=get_headers(),
            json={"name": name, "balance": balance, "type": acc_type}
        )
        return response.status_code == 201, response.json()
    except Exception as e:
        return False, str(e)

def api_get_category_groups():
    try:
        response = requests.get(f"{API_URL}/categories/groups", headers=get_headers())
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def api_get_categories():
    try:
        response = requests.get(f"{API_URL}/categories/", headers=get_headers())
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def api_create_category_group(name):
    try:
        response = requests.post(
            f"{API_URL}/categories/groups",
            headers=get_headers(),
            json={"name": name}
        )
        return response.status_code == 201, response.json()
    except Exception as e:
        return False, str(e)

def api_create_category(name, group_id):
    try:
        response = requests.post(
            f"{API_URL}/categories/",
            headers=get_headers(),
            json={"name": name, "group_id": group_id}
        )
        return response.status_code == 201, response.json()
    except Exception as e:
        return False, str(e)

def api_assign_budget(category_id, amount):
    try:
        response = requests.patch(
            f"{API_URL}/categories/{category_id}/assign",
            headers=get_headers(),
            json={"amount": amount}
        )
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, str(e)

def api_get_budget_summary():
    try:
        response = requests.get(f"{API_URL}/budget/summary", headers=get_headers())
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def api_get_transactions():
    try:
        response = requests.get(f"{API_URL}/transactions/", headers=get_headers(), params={"limit": 20})
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def api_create_transaction(account_id, category_id, payee, amount, txn_type, date):
    try:
        response = requests.post(
            f"{API_URL}/transactions/",
            headers=get_headers(),
            json={
                "account_id": account_id,
                "category_id": category_id,
                "payee_name": payee,
                "amount": amount,
                "transaction_type": txn_type,
                "transaction_date": date.isoformat()
            }
        )
        return response.status_code == 201, response.json()
    except Exception as e:
        return False, str(e)

# ============ Subscriptions API ============
def api_get_subscriptions(active_only=False):
    try:
        response = requests.get(
            f"{API_URL}/subscriptions/",
            headers=get_headers(),
            params={"active_only": active_only}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def api_create_subscription(payee_name, amount, next_due_date, frequency, category_id=None, account_id=None):
    try:
        data = {
            "payee_name": payee_name,
            "estimated_amount": amount,
            "next_due_date": next_due_date.isoformat(),
            "frequency": frequency,
            "is_active": True
        }
        if category_id:
            data["category_id"] = category_id
        if account_id:
            data["account_id"] = account_id
        response = requests.post(
            f"{API_URL}/subscriptions/",
            headers=get_headers(),
            json=data
        )
        return response.status_code == 201, response.json()
    except Exception as e:
        return False, str(e)

def api_process_due_subscriptions():
    try:
        response = requests.post(
            f"{API_URL}/subscriptions/process-due",
            headers=get_headers()
        )
        if response.status_code == 200:
            return True, response.json()
        return False, response.text
    except Exception as e:
        return False, str(e)

def api_toggle_subscription(subscription_id):
    try:
        response = requests.patch(
            f"{API_URL}/subscriptions/{subscription_id}/toggle",
            headers=get_headers()
        )
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, str(e)

def api_advance_subscription(subscription_id):
    try:
        response = requests.post(
            f"{API_URL}/subscriptions/{subscription_id}/advance",
            headers=get_headers()
        )
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, str(e)

def api_delete_subscription(subscription_id):
    try:
        response = requests.delete(
            f"{API_URL}/subscriptions/{subscription_id}",
            headers=get_headers()
        )
        return response.status_code == 204, "تم الحذف"
    except Exception as e:
        return False, str(e)

def api_get_upcoming_subscriptions(days=7):
    try:
        response = requests.get(
            f"{API_URL}/subscriptions/upcoming",
            headers=get_headers(),
            params={"days": days}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

# ============ UI Pages ============
def page_login():
    st.title("🔐 تسجيل الدخول")
    
    tab1, tab2 = st.tabs(["دخول", "تسجيل جديد"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("البريد الإلكتروني", placeholder="example@email.com")
            password = st.text_input("كلمة المرور", type="password")
            submitted = st.form_submit_button("تسجيل الدخول", use_container_width=True)
            
            if submitted:
                if email and password:
                    success, msg = api_login(email, password)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("الرجاء إدخال البريد وكلمة المرور")
    
    with tab2:
        with st.form("register_form"):
            email = st.text_input("البريد الإلكتروني", placeholder="example@email.com", key="reg_email")
            password = st.text_input("كلمة المرور", type="password", key="reg_pass")
            submitted = st.form_submit_button("إنشاء حساب", use_container_width=True)
            
            if submitted:
                if email and password:
                    success, msg = api_register(email, password)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("الرجاء إدخال البريد وكلمة المرور")

def page_dashboard():
    st.title("📊 لوحة التحكم")
    
    # ملخص الميزانية
    summary = api_get_budget_summary()
    if summary:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 للتوزيع", f"{float(summary['to_be_budgeted']):,.2f} ر.س")
        with col2:
            st.metric("🏦 إجمالي الرصيد", f"{float(summary['total_balance']):,.2f} ر.س")
        with col3:
            st.metric("📋 المخصص", f"{float(summary['total_assigned']):,.2f} ر.س")
        with col4:
            st.metric("💸 المصروف", f"{float(summary['total_spent']):,.2f} ر.س")
    
    st.divider()
    
    # الحسابات
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏦 الحسابات البنكية")
        accounts = api_get_accounts()
        if accounts:
            for acc in accounts:
                with st.container(border=True):
                    st.markdown(f"**{acc['name']}**")
                    st.caption(f"النوع: {acc['type']}")
                    st.markdown(f"### {float(acc['balance']):,.2f} ر.س")
        else:
            st.info("لا توجد حسابات")
    
    with col2:
        st.subheader("📁 الفئات")
        groups = api_get_category_groups()
        categories = api_get_categories()
        
        if groups:
            for group in groups:
                with st.expander(f"📂 {group['name']}", expanded=True):
                    group_cats = [c for c in categories if c.get('group_id') == group['id']]
                    if group_cats:
                        for cat in group_cats:
                            assigned = float(cat.get('assigned_amount', 0) or 0)
                            activity = float(cat.get('activity_amount', 0) or 0)
                            available = assigned - activity
                            color = "green" if available >= 0 else "red"
                            st.markdown(f"**{cat['name']}**: :{color}[{available:,.2f} ر.س]")
                    else:
                        st.caption("لا توجد فئات")
        else:
            st.info("لا توجد مجموعات")

def page_accounts():
    st.title("🏦 الحسابات البنكية")
    
    # إضافة حساب جديد
    with st.expander("➕ إضافة حساب جديد", expanded=False):
        with st.form("add_account"):
            name = st.text_input("اسم الحساب", placeholder="البنك الأهلي")
            balance = st.number_input("الرصيد الحالي", min_value=0.0, step=100.0)
            acc_type = st.selectbox("نوع الحساب", ["checking", "savings", "credit", "cash"],
                                    format_func=lambda x: {"checking": "جاري", "savings": "توفير", "credit": "ائتمان", "cash": "نقدي"}[x])
            submitted = st.form_submit_button("إضافة", use_container_width=True)
            
            if submitted and name:
                success, result = api_create_account(name, balance, acc_type)
                if success:
                    st.success("تم إضافة الحساب بنجاح!")
                    st.rerun()
                else:
                    st.error(f"فشل: {result}")
    
    st.divider()
    
    # عرض الحسابات
    accounts = api_get_accounts()
    if accounts:
        for acc in accounts:
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"### {acc['name']}")
                    type_names = {"checking": "جاري", "savings": "توفير", "credit": "ائتمان", "cash": "نقدي"}
                    st.caption(f"النوع: {type_names.get(acc['type'], acc['type'])}")
                with col2:
                    st.metric("الرصيد", f"{float(acc['balance']):,.2f} ر.س")
                with col3:
                    st.caption(f"ID: {acc['id'][:8]}...")
    else:
        st.info("لا توجد حسابات بعد. أضف حسابك الأول!")

def page_budget():
    st.title("📋 الميزانية")
    
    # ملخص
    summary = api_get_budget_summary()
    if summary:
        st.metric("💰 متاح للتوزيع", f"{float(summary['to_be_budgeted']):,.2f} ر.س")
    
    st.divider()
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        # إضافة مجموعة
        with st.expander("➕ مجموعة جديدة"):
            with st.form("add_group"):
                name = st.text_input("اسم المجموعة", placeholder="المصاريف الثابتة")
                if st.form_submit_button("إضافة"):
                    if name:
                        success, _ = api_create_category_group(name)
                        if success:
                            st.success("تم!")
                            st.rerun()
        
        # إضافة فئة
        groups = api_get_category_groups()
        if groups:
            with st.expander("➕ فئة جديدة"):
                with st.form("add_category"):
                    name = st.text_input("اسم الفئة", placeholder="الإيجار")
                    group = st.selectbox("المجموعة", groups, format_func=lambda x: x['name'])
                    if st.form_submit_button("إضافة"):
                        if name and group:
                            success, _ = api_create_category(name, group['id'])
                            if success:
                                st.success("تم!")
                                st.rerun()
    
    with col1:
        # عرض الفئات مع إمكانية تخصيص الميزانية
        categories = api_get_categories()
        
        for group in groups:
            st.subheader(f"📂 {group['name']}")
            group_cats = [c for c in categories if c.get('group_id') == group['id']]
            
            if group_cats:
                for cat in group_cats:
                    with st.container(border=True):
                        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1.5])
                        with c1:
                            st.markdown(f"**{cat['name']}**")
                        with c2:
                            st.caption("مخصص")
                            st.write(f"{float(cat.get('assigned_amount', 0) or 0):,.0f}")
                        with c3:
                            st.caption("نشاط")
                            st.write(f"{float(cat.get('activity_amount', 0) or 0):,.0f}")
                        with c4:
                            available = float(cat.get('assigned_amount', 0) or 0) - float(cat.get('activity_amount', 0) or 0)
                            st.caption("متاح")
                            color = "green" if available >= 0 else "red"
                            st.markdown(f":{color}[{available:,.0f}]")
                        with c5:
                            # زر تخصيص الميزانية
                            assign_key = f"assign_{cat['id']}"
                            if st.button("💰 تخصيص", key=assign_key, use_container_width=True):
                                st.session_state[f"show_assign_{cat['id']}"] = True
                        
                        # نموذج التخصيص
                        if st.session_state.get(f"show_assign_{cat['id']}", False):
                            with st.form(key=f"form_assign_{cat['id']}"):
                                amount = st.number_input(
                                    "المبلغ للتخصيص",
                                    min_value=0.0,
                                    step=100.0,
                                    key=f"amount_{cat['id']}"
                                )
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    if st.form_submit_button("✅ تخصيص", use_container_width=True):
                                        if amount > 0:
                                            success, _ = api_assign_budget(cat['id'], amount)
                                            if success:
                                                st.success(f"تم تخصيص {amount:,.0f} ر.س")
                                                st.session_state[f"show_assign_{cat['id']}"] = False
                                                st.rerun()
                                with col_b:
                                    if st.form_submit_button("❌ إلغاء", use_container_width=True):
                                        st.session_state[f"show_assign_{cat['id']}"] = False
                                        st.rerun()
            else:
                st.caption("لا توجد فئات في هذه المجموعة")
            
            st.divider()

def page_transactions():
    st.title("💳 المعاملات")
    
    accounts = api_get_accounts()
    categories = api_get_categories()
    
    # إضافة معاملة
    with st.expander("➕ إضافة معاملة", expanded=False):
        if accounts:
            with st.form("add_transaction"):
                col1, col2 = st.columns(2)
                with col1:
                    account = st.selectbox("الحساب", accounts, format_func=lambda x: x['name'])
                    payee = st.text_input("الجهة", placeholder="متجر...")
                    amount = st.number_input("المبلغ", min_value=0.0, step=10.0)
                with col2:
                    category = st.selectbox("الفئة", [None] + categories, 
                                           format_func=lambda x: x['name'] if x else "-- بدون فئة --")
                    txn_type = st.selectbox("النوع", ["expense", "income"],
                                           format_func=lambda x: "مصروف" if x == "expense" else "دخل")
                    date = st.date_input("التاريخ", datetime.now())
                
                if st.form_submit_button("إضافة", use_container_width=True):
                    if account and payee and amount > 0:
                        cat_id = category['id'] if category else None
                        success, result = api_create_transaction(
                            account['id'], cat_id, payee, amount, txn_type, date
                        )
                        if success:
                            st.success("تم إضافة المعاملة!")
                            st.rerun()
                        else:
                            st.error(f"فشل: {result}")
        else:
            st.warning("أضف حساب بنكي أولاً")
    
    st.divider()
    
    # عرض المعاملات
    transactions = api_get_transactions()
    if transactions:
        for txn in transactions:
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    icon = "🔴" if txn['transaction_type'] == 'expense' else "🟢"
                    st.markdown(f"{icon} **{txn['payee_name']}**")
                    st.caption(txn['transaction_date'])
                with col2:
                    # Find category name
                    cat_name = "غير مصنف"
                    for c in categories:
                        if c['id'] == txn.get('category_id'):
                            cat_name = c['name']
                            break
                    st.caption(cat_name)
                with col3:
                    color = "red" if txn['transaction_type'] == 'expense' else "green"
                    st.markdown(f":{color}[{float(txn['amount']):,.2f} ر.س]")
    else:
        st.info("لا توجد معاملات")

def page_subscriptions():
    st.title("🔄 الاشتراكات الدورية")
    
    categories = api_get_categories()
    accounts = api_get_accounts()
    
    # زر معالجة الاشتراكات المستحقة
    col_header1, col_header2 = st.columns([3, 1])
    with col_header2:
        if st.button("⚡ معالجة المستحقات", use_container_width=True, type="primary"):
            success, result = api_process_due_subscriptions()
            if success:
                processed = result.get('processed_count', 0)
                skipped = result.get('skipped_count', 0)
                if processed > 0:
                    st.success(f"✅ تمت معالجة {processed} اشتراك!")
                elif skipped > 0:
                    st.warning(f"⏭️ تم تخطي {skipped} اشتراك (بدون حساب)")
                else:
                    st.info("لا توجد اشتراكات مستحقة اليوم")
                st.rerun()
            else:
                st.error(f"فشل: {result}")
    
    # إضافة اشتراك جديد
    with st.expander("➕ إضافة اشتراك", expanded=False):
        with st.form("add_subscription"):
            col1, col2 = st.columns(2)
            with col1:
                payee = st.text_input("اسم الجهة", placeholder="Netflix, Spotify...")
                amount = st.number_input("المبلغ المتوقع", min_value=0.0, step=10.0)
            with col2:
                frequency = st.selectbox(
                    "التكرار",
                    ["monthly", "weekly", "yearly"],
                    format_func=lambda x: {"monthly": "شهري", "weekly": "أسبوعي", "yearly": "سنوي"}[x]
                )
                next_due = st.date_input("تاريخ الاستحقاق القادم")
            
            col3, col4 = st.columns(2)
            with col3:
                category = st.selectbox(
                    "الفئة (اختياري)",
                    [None] + categories,
                    format_func=lambda x: "-- بدون فئة --" if x is None else x['name']
                )
            with col4:
                account = st.selectbox(
                    "الحساب للخصم (مطلوب للمعالجة التلقائية)",
                    [None] + accounts,
                    format_func=lambda x: "-- بدون حساب --" if x is None else x['name']
                )
            
            if st.form_submit_button("إضافة الاشتراك", use_container_width=True):
                if payee and amount > 0:
                    cat_id = category['id'] if category else None
                    acc_id = account['id'] if account else None
                    success, result = api_create_subscription(payee, amount, next_due, frequency, cat_id, acc_id)
                    if success:
                        st.success("تم إضافة الاشتراك!")
                        st.rerun()
                    else:
                        st.error(f"فشل: {result}")
    
    st.divider()
    
    # الاشتراكات القادمة
    upcoming = api_get_upcoming_subscriptions(days=14)
    if upcoming:
        st.subheader("📅 الاشتراكات القادمة (14 يوم)")
        for sub in upcoming:
            days = sub.get('days_until_due', 0)
            color = "red" if days <= 3 else "orange" if days <= 7 else "green"
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"**{sub['payee_name']}**")
                    st.caption(sub.get('category_name', 'غير مصنف'))
                with col2:
                    st.markdown(f":{color}[خلال {days} يوم]")
                with col3:
                    st.markdown(f"**{float(sub['estimated_amount']):,.2f} ر.س**")
        st.divider()
    
    # كل الاشتراكات
    st.subheader("📋 كل الاشتراكات")
    
    show_all = st.checkbox("عرض غير النشطة أيضاً")
    subscriptions = api_get_subscriptions(active_only=not show_all)
    
    if subscriptions:
        for sub in subscriptions:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1.5])
                with col1:
                    status_icon = "✅" if sub['is_active'] else "⏸️"
                    auto_icon = "🔄" if sub.get('account_id') else "📝"
                    st.markdown(f"{status_icon} {auto_icon} **{sub['payee_name']}**")
                    freq_names = {"monthly": "شهري", "weekly": "أسبوعي", "yearly": "سنوي"}
                    account_info = sub.get('account_name', 'يدوي')
                    st.caption(f"{freq_names.get(sub['frequency'], sub['frequency'])} | {sub.get('category_name', 'غير مصنف')} | {account_info}")
                with col2:
                    st.caption("المبلغ")
                    st.markdown(f"**{float(sub['estimated_amount']):,.2f}**")
                with col3:
                    st.caption("الاستحقاق")
                    st.write(sub['next_due_date'])
                with col4:
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button("⏭️", key=f"adv_{sub['id']}", help="تقديم للتاريخ التالي"):
                            api_advance_subscription(sub['id'])
                            st.rerun()
                    with c2:
                        toggle_icon = "⏸️" if sub['is_active'] else "▶️"
                        if st.button(toggle_icon, key=f"tog_{sub['id']}", help="إيقاف/تشغيل"):
                            api_toggle_subscription(sub['id'])
                            st.rerun()
                    with c3:
                        if st.button("🗑️", key=f"del_{sub['id']}", help="حذف"):
                            api_delete_subscription(sub['id'])
                            st.rerun()
    else:
        st.info("لا توجد اشتراكات. أضف اشتراكك الأول!")

# ============ Main App ============
def main():
    st.set_page_config(
        page_title="مراقب الصرف الذكي",
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # تخصيص CSS للعربية
    st.markdown("""
    <style>
        .main { direction: rtl; }
        .stButton>button { width: 100%; }
        .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)
    
    if not st.session_state.token:
        page_login()
    else:
        # Sidebar
        with st.sidebar:
            st.title("💰 مراقب الصرف")
            st.caption(f"مرحباً: {st.session_state.user.get('email', '')}")
            st.divider()
            
            page = st.radio(
                "القائمة",
                ["لوحة التحكم", "الحسابات", "الميزانية", "المعاملات", "الاشتراكات"],
                label_visibility="collapsed"
            )
            
            st.divider()
            if st.button("🚪 تسجيل الخروج", use_container_width=True):
                st.session_state.token = None
                st.session_state.user = None
                st.rerun()
        
        # Pages
        if page == "لوحة التحكم":
            page_dashboard()
        elif page == "الحسابات":
            page_accounts()
        elif page == "الميزانية":
            page_budget()
        elif page == "المعاملات":
            page_transactions()
        elif page == "الاشتراكات":
            page_subscriptions()

if __name__ == "__main__":
    main()
