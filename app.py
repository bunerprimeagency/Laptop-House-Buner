import hashlib
import secrets
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import streamlit as st
from supabase import create_client

# ------------------------------------------------------------------
# PAGE SETUP
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Laptop House Buner",
    page_icon="💻",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e3e8ef;
        border-left: 5px solid #1f6feb;
        border-radius: 10px;
        padding: 14px 18px;
        box-shadow: 0 1px 4px rgba(16, 24, 40, 0.08);
    }
    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #111827 !important;
    }
    section[data-testid="stSidebar"] {border-right: 1px solid #e3e8ef;}
    .lhb-title {font-size: 2rem; font-weight: 800; margin-bottom: 0;}
    .lhb-sub {color: #6b7280; margin-top: 0; margin-bottom: 1rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<p class="lhb-title">💻 Laptop House Buner</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="lhb-sub">Shop Management System</p>', unsafe_allow_html=True
)

PAYMENT_METHODS = ["Cash", "Bank Transfer", "JazzCash", "EasyPaisa", "Card", "Other"]
ADMIN_ROLES = ("owner", "admin")


# ------------------------------------------------------------------
# DATABASE CONNECTION
# ------------------------------------------------------------------
@st.cache_resource
def connect_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SECRET_KEY"],
    )


try:
    supabase = connect_supabase()
    supabase.table("products").select("id").limit(1).execute()
except Exception as e:
    st.error(
        "Supabase connection failed. Please check your Streamlit Secrets "
        "(SUPABASE_URL and SUPABASE_SECRET_KEY) and your database tables."
    )
    st.caption(f"Error type: {type(e).__name__}")
    st.stop()


# ------------------------------------------------------------------
# GENERAL HELPERS
# ------------------------------------------------------------------
def pkr(value):
    try:
        return f"Rs {float(value or 0):,.0f}"
    except Exception:
        return "Rs 0"


def num(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def today_pk():
    """Today's date in Pakistan time (UTC+5)."""
    return datetime.now(timezone(timedelta(hours=5))).date()


def show_table(df):
    try:
        st.dataframe(df, width="stretch", hide_index=True)
    except TypeError:
        st.dataframe(df, use_container_width=True, hide_index=True)


def is_admin():
    user = st.session_state.get("user") or {}
    return str(user.get("role", "")).strip().lower() in ADMIN_ROLES


def current_username():
    return (st.session_state.get("user") or {}).get("username", "")


def get_data(table):
    """Read every row of a table (handles more than 1000 rows)."""
    rows, start = [], 0
    while True:
        chunk = (
            supabase.table(table)
            .select("*")
            .order("id")
            .range(start, start + 999)
            .execute()
            .data
            or []
        )
        rows.extend(chunk)
        if len(chunk) < 1000:
            break
        start += 1000
    return rows


def load_products():
    """Staff never receive purchase prices."""
    rows = get_data("products")
    if not is_admin():
        for r in rows:
            r.pop("purchase_price", None)
    return rows


def load_sale_items():
    """Staff never receive purchase prices."""
    rows = get_data("sale_items")
    if not is_admin():
        for r in rows:
            r.pop("purchase_price", None)
    return rows


def insert_with_fallback(table, full_data, base_data):
    """Try inserting all fields; if some columns do not exist, insert base fields."""
    try:
        return supabase.table(table).insert(full_data).execute(), True
    except Exception as e:
        msg = str(e).lower()
        if "column" in msg or "pgrst204" in msg or "schema cache" in msg:
            return supabase.table(table).insert(base_data).execute(), False
        raise


def spec_text(p):
    parts = [
        p.get("model"),
        p.get("processor"),
        p.get("ram"),
        p.get("storage"),
        p.get("graphics"),
        p.get("display_size"),
        p.get("condition_text"),
    ]
    return " | ".join(str(x) for x in parts if x)


# ------------------------------------------------------------------
# PASSWORDS (same format as the existing users table)
# ------------------------------------------------------------------
def password_hash(password):
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 200000
    ).hex()
    return salt + "$" + hashed


def verify_password(password, saved):
    try:
        salt, digest = saved.split("$", 1)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 200000
        ).hex()
        return secrets.compare_digest(actual, digest)
    except Exception:
        return False


# ------------------------------------------------------------------
# LOGIN
# ------------------------------------------------------------------
def login():
    st.subheader("🔐 Login")

    if st.session_state.get("failed_logins", 0) >= 5:
        st.error("Too many failed attempts. Refresh the page to try again.")
        return

    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

    if submit:
        try:
            users = (
                supabase.table("users")
                .select("*")
                .eq("username", username.strip())
                .limit(1)
                .execute()
                .data
            )
            if users and verify_password(password, users[0].get("password_hash", "")):
                st.session_state.user = {
                    "id": users[0].get("id"),
                    "username": users[0].get("username"),
                    "role": users[0].get("role", "staff"),
                }
                st.session_state.failed_logins = 0
                st.rerun()
            else:
                st.session_state.failed_logins = (
                    st.session_state.get("failed_logins", 0) + 1
                )
                st.error("Incorrect username or password.")
        except Exception as e:
            st.error(f"Login error: {e}")


# ------------------------------------------------------------------
# HISTORY BUILDER (used by Sales History)
# ------------------------------------------------------------------
def build_history(sales, items, admin):
    items_by_sale = {}
    for it in items:
        items_by_sale.setdefault(it.get("sale_id"), []).append(it)

    rows = []
    for s in sorted(sales, key=lambda x: x.get("id", 0), reverse=True):
        total = num(s.get("total"))
        paid = num(s.get("paid_amount"))
        discount = num(s.get("discount"))
        sale_items = items_by_sale.get(s.get("id"), [])
        subtotal = sum(num(i.get("selling_price")) * num(i.get("quantity")) for i in sale_items)

        base = {
            "Invoice No": s.get("invoice_no"),
            "Customer": s.get("customer_name"),
            "Phone": s.get("customer_phone"),
            "Date": s.get("sale_date"),
            "Sold By": s.get("sold_by"),
        }

        if not sale_items:
            row = dict(base)
            row.update(
                {
                    "Product": "",
                    "Specs": "",
                    "Qty": 0,
                    "Selling Price": 0,
                    "Total": total,
                    "Paid": paid,
                    "Remaining": max(total - paid, 0),
                }
            )
            if admin:
                row["Purchase Price"] = 0
                row["Profit"] = 0
            rows.append(row)
            continue

        for i in sale_items:
            qty = num(i.get("quantity"))
            sp = num(i.get("selling_price"))
            row = dict(base)
            row.update(
                {
                    "Product": i.get("product_name"),
                    "Specs": i.get("specs"),
                    "Qty": int(qty),
                    "Selling Price": sp,
                    "Total": total,
                    "Paid": paid,
                    "Remaining": max(total - paid, 0),
                }
            )
            if admin:
                pp = num(i.get("purchase_price"))
                share = (sp * qty / subtotal) if subtotal else 0
                row["Purchase Price"] = pp
                row["Profit"] = round(sp * qty - pp * qty - discount * share, 2)
            rows.append(row)

    return pd.DataFrame(rows)


# ------------------------------------------------------------------
# DASHBOARD
# ------------------------------------------------------------------
def dashboard():
    st.subheader("🏠 Dashboard")

    products = load_products()
    sales = get_data("sales")

    total_stock = sum(int(num(p.get("quantity"))) for p in products)
    today_str = today_pk().isoformat()
    today_sales = [s for s in sales if str(s.get("sale_date", ""))[:10] == today_str]

    if is_admin():
        total_sales = sum(num(s.get("total")) for s in sales)
        pending = sum(max(num(s.get("total")) - num(s.get("paid_amount")), 0) for s in sales)

        a, b, c, d = st.columns(4)
        a.metric("Total Products", len(products))
        b.metric("Stock Units", total_stock)
        c.metric("Total Sales", pkr(total_sales))
        d.metric("Pending Balances", pkr(pending))

        e, f, g = st.columns(3)
        e.metric("Invoices", len(sales))
        f.metric("Today's Invoices", len(today_sales))
        g.metric("Today's Sales", pkr(sum(num(s.get("total")) for s in today_sales)))
    else:
        mine = [s for s in sales if s.get("sold_by") == current_username()]
        mine_today = [s for s in today_sales if s.get("sold_by") == current_username()]
        a, b, c, d = st.columns(4)
        a.metric("Total Products", len(products))
        b.metric("Stock Units", total_stock)
        c.metric("My Invoices", len(mine))
        d.metric("My Sales Today", pkr(sum(num(s.get("total")) for s in mine_today)))

    st.markdown("### ⚠️ Low Stock (3 or fewer)")
    low = [p for p in products if 0 <= int(num(p.get("quantity"))) <= 3]
    if low:
        show_table(
            pd.DataFrame(
                [
                    {
                        "Product": p.get("name"),
                        "Model": p.get("model"),
                        "Quantity": int(num(p.get("quantity"))),
                    }
                    for p in low
                ]
            )
        )
    else:
        st.success("No low-stock products.")

    st.markdown("### 🕒 Recent Sales")
    recent = sorted(sales, key=lambda x: x.get("id", 0), reverse=True)[:8]
    if recent:
        show_table(
            pd.DataFrame(
                [
                    {
                        "Invoice": s.get("invoice_no"),
                        "Customer": s.get("customer_name"),
                        "Date": s.get("sale_date"),
                        "Sold By": s.get("sold_by"),
                        "Total": pkr(s.get("total")),
                        "Remaining": pkr(max(num(s.get("total")) - num(s.get("paid_amount")), 0)),
                    }
                    for s in recent
                ]
            )
        )
    else:
        st.info("No sales yet.")


# ------------------------------------------------------------------
# PRODUCTS & STOCK
# ------------------------------------------------------------------
def products_page():
    st.subheader("📦 Products & Stock")

    admin = is_admin()
    products = load_products()

    if products:
        search = st.text_input("🔍 Search products (name, model, processor, serial)")
        rows = []
        for p in products:
            text = " ".join(
                str(p.get(k, "")) for k in ("name", "model", "processor", "serial_number", "ram", "storage")
            ).lower()
            if search.strip() and search.strip().lower() not in text:
                continue
            row = {
                "ID": p.get("id"),
                "Product": p.get("name"),
                "Category": p.get("category"),
                "Model": p.get("model"),
                "Processor": p.get("processor"),
                "RAM": p.get("ram"),
                "Storage": p.get("storage"),
                "Graphics": p.get("graphics"),
                "Display": p.get("display_size"),
                "Condition": p.get("condition_text"),
                "Serial No": p.get("serial_number"),
            }
            if admin:
                row["Purchase Price"] = num(p.get("purchase_price"))
            row["Selling Price"] = num(p.get("selling_price"))
            row["Qty"] = int(num(p.get("quantity")))
            row["Warranty Days"] = int(num(p.get("warranty_days")))
            row["Warranty Terms"] = p.get("warranty_terms")
            rows.append(row)
        df = pd.DataFrame(rows)
        # hide columns that are completely empty (e.g. columns not in database yet)
        df = df.dropna(axis=1, how="all")
        show_table(df)
    else:
        st.info("No products added yet.")

    if not admin:
        return

    st.divider()

    # ---------------- ADD PRODUCT ----------------
    with st.form("add_product", clear_on_submit=True):
        st.markdown("### ➕ Add New Product")
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Product Name")
        category = c2.selectbox("Category", ["Laptop", "Accessories", "Desktop", "Other"])
        model = c3.text_input("Model")

        c4, c5, c6 = st.columns(3)
        processor = c4.text_input("Processor")
        ram = c5.text_input("RAM")
        storage = c6.text_input("Storage")

        c7, c8, c9 = st.columns(3)
        graphics = c7.text_input("Graphics")
        display_size = c8.text_input("Display Size")
        condition = c9.selectbox("Condition", ["Used", "New", "Refurbished"])

        serial = st.text_input("Serial Number")

        c10, c11, c12, c13 = st.columns(4)
        purchase = c10.number_input("Purchase Price (Rs)", min_value=0.0, step=500.0)
        selling = c11.number_input("Selling Price (Rs)", min_value=0.0, step=500.0)
        quantity = c12.number_input("Quantity", min_value=0, step=1)
        warranty = c13.number_input("Warranty Days", min_value=0, step=1)

        warranty_terms = st.text_area("Warranty Terms")
        submit = st.form_submit_button("💾 Save Product")

    if submit:
        if not name.strip():
            st.error("Product name is required.")
        elif selling < purchase:
            st.error("Selling price is lower than purchase price. Please check the prices.")
        elif serial.strip() and any(
            str(p.get("serial_number", "")).strip().lower() == serial.strip().lower()
            for p in products
        ):
            st.error("A product with this serial number already exists.")
        else:
            base = {
                "name": name.strip(),
                "category": category,
                "model": model.strip(),
                "processor": processor.strip(),
                "ram": ram.strip(),
                "storage": storage.strip(),
                "condition_text": condition,
                "serial_number": serial.strip(),
                "purchase_price": purchase,
                "selling_price": selling,
                "quantity": int(quantity),
                "warranty_days": int(warranty),
            }
            full = dict(base)
            full.update(
                {
                    "graphics": graphics.strip(),
                    "display_size": display_size.strip(),
                    "warranty_terms": warranty_terms.strip(),
                }
            )
            try:
                _, all_saved = insert_with_fallback("products", full, base)
                st.session_state.flash = (
                    "success",
                    "Product saved successfully."
                    if all_saved
                    else "Product saved, but Graphics / Display Size / Warranty Terms were NOT "
                    "saved because those columns are missing in Supabase. "
                    "See the optional SQL in the setup instructions.",
                )
                st.rerun()
            except Exception as e:
                st.error(f"Save failed: {e}")

    # ---------------- EDIT / DELETE ----------------
    if products:
        st.divider()
        st.markdown("### ✏️ Edit Product Price / Stock")
        ids = [p["id"] for p in products]
        labels = {
            p["id"]: f'#{p["id"]} - {p.get("name")} {p.get("model") or ""} (Stock {int(num(p.get("quantity")))})'
            for p in products
        }
        pid = st.selectbox("Select product", ids, format_func=lambda i: labels[i], key="edit_pid")
        p = next(x for x in products if x["id"] == pid)

        e1, e2, e3 = st.columns(3)
        new_purchase = e1.number_input(
            "Purchase Price (Rs)", min_value=0.0, value=num(p.get("purchase_price")),
            step=500.0, key=f"ep_{pid}",
        )
        new_selling = e2.number_input(
            "Selling Price (Rs)", min_value=0.0, value=num(p.get("selling_price")),
            step=500.0, key=f"es_{pid}",
        )
        new_qty = e3.number_input(
            "Quantity", min_value=0, value=int(num(p.get("quantity"))),
            step=1, key=f"eq_{pid}",
        )

        if st.button("Update Product"):
            try:
                supabase.table("products").update(
                    {
                        "purchase_price": new_purchase,
                        "selling_price": new_selling,
                        "quantity": int(new_qty),
                    }
                ).eq("id", pid).execute()
                st.session_state.flash = ("success", "Product updated.")
                st.rerun()
            except Exception as e:
                st.error(f"Update failed: {e}")

        with st.expander("🗑️ Delete this product"):
            st.warning("This cannot be undone. Products that already appear in sales may not be deletable.")
            confirm = st.checkbox("I understand and want to delete this product", key=f"del_c_{pid}")
            if st.button("Delete Product", disabled=not confirm):
                try:
                    supabase.table("products").delete().eq("id", pid).execute()
                    st.session_state.flash = ("success", "Product deleted.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete failed (it may be linked to sales): {e}")


# ------------------------------------------------------------------
# NEW SALE / BILLING
# ------------------------------------------------------------------
def build_receipt(sale_info):
    lines = [
        "LAPTOP HOUSE BUNER",
        "=" * 40,
        f"Invoice : {sale_info['invoice']}",
        f"Date    : {sale_info['date']}",
        f"Customer: {sale_info['customer']}",
        f"Phone   : {sale_info['phone']}",
        f"Sold By : {sale_info['sold_by']}",
        "-" * 40,
        f"Product : {sale_info['product']}",
        f"Specs   : {sale_info['specs']}",
        f"Qty     : {sale_info['qty']}",
        f"Price   : {pkr(sale_info['price'])}",
        f"Subtotal: {pkr(sale_info['subtotal'])}",
        f"Discount: {pkr(sale_info['discount'])}",
        f"TOTAL   : {pkr(sale_info['total'])}",
        f"Paid    : {pkr(sale_info['paid'])} ({sale_info['method']})",
        f"Balance : {pkr(sale_info['balance'])}",
        f"Warranty: {sale_info['warranty_days']} days (until {sale_info['warranty_expiry']})",
        "-" * 40,
        f"Notes   : {sale_info['notes']}",
        "",
        "Thank you for shopping with us!",
    ]
    return "\n".join(lines)


def billing_page():
    st.subheader("🧾 New Sale / Billing")
    admin = is_admin()

    # show receipt of the last completed sale
    last = st.session_state.get("last_receipt")
    if last:
        st.success(f"Sale completed. Invoice number: {last['invoice']}")
        st.code(build_receipt(last))
        st.download_button(
            "⬇️ Download Invoice (text file)",
            data=build_receipt(last),
            file_name=f"{last['invoice']}.txt",
            mime="text/plain",
        )
        if st.button("Start another sale"):
            st.session_state.last_receipt = None
            st.rerun()
        return

    products = [p for p in load_products() if int(num(p.get("quantity"))) > 0]
    if not products:
        st.warning("No products in stock. Add products first in Products & Stock.")
        return

    nonce = st.session_state.setdefault("sale_nonce", 0)
    by_id = {p["id"]: p for p in products}
    ids = list(by_id)
    labels = {
        p["id"]: f'{p.get("name")} | {p.get("model") or "-"} | {p.get("ram") or "-"}/{p.get("storage") or "-"} '
        f'| {pkr(p.get("selling_price"))} | Stock {int(num(p.get("quantity")))}'
        for p in products
    }

    st.markdown("#### 👤 Customer")
    c1, c2 = st.columns(2)
    customer = c1.text_input("Customer Name", key=f"cust_{nonce}")
    phone = c2.text_input("Customer Phone", key=f"phone_{nonce}")

    st.markdown("#### 💻 Product")
    pid = st.selectbox("Select Product", ids, format_func=lambda i: labels[i], key=f"prod_{nonce}")
    product = by_id[pid]
    stock = int(num(product.get("quantity")))

    st.info(
        f"**Specifications:** {spec_text(product) or 'Not provided'}  \n"
        f"**Serial No:** {product.get('serial_number') or '-'}  \n"
        f"**Warranty:** {int(num(product.get('warranty_days')))} days"
    )

    q1, q2, q3 = st.columns(3)
    quantity = q1.number_input(
        "Quantity", min_value=1, max_value=stock, value=1, step=1, key=f"qty_{nonce}_{pid}"
    )
    list_price = num(product.get("selling_price"))
    if admin:
        price = q2.number_input(
            "Selling Price (Rs)", min_value=0.0, value=list_price, step=500.0,
            key=f"price_{nonce}_{pid}",
        )
    else:
        price = list_price
        q2.number_input("Selling Price (Rs)", value=list_price, disabled=True, key=f"price_ro_{nonce}_{pid}")

    subtotal = price * quantity
    discount = q3.number_input(
        "Discount (Rs)", min_value=0.0, max_value=float(subtotal), value=0.0, step=100.0,
        key=f"disc_{nonce}_{pid}_{quantity}",
    )
    total = subtotal - discount

    st.markdown("#### 💳 Payment")
    p1, p2 = st.columns(2)
    paid = p1.number_input(
        "Paid Amount (Rs)", min_value=0.0, max_value=float(total), value=float(total), step=500.0,
        key=f"paid_{nonce}_{int(total * 100)}",
    )
    method = p2.selectbox("Payment Method", PAYMENT_METHODS, key=f"method_{nonce}")
    notes = st.text_area("Notes", key=f"notes_{nonce}")

    balance = total - paid
    m1, m2, m3 = st.columns(3)
    m1.metric("Subtotal", pkr(subtotal))
    m2.metric("Total Amount", pkr(total))
    m3.metric("Remaining Balance", pkr(balance))

    confirm = st.checkbox("✅ I have checked the customer, product and amount", key=f"confirm_{nonce}")

    if st.button("💾 Complete Sale", type="primary", disabled=not confirm):
        if not customer.strip():
            st.error("Customer name is required.")
            return
        if not phone.strip():
            st.error("Customer phone is required.")
            return

        # duplicate protection: same sale within 60 seconds
        fingerprint = (customer.strip().lower(), phone.strip(), pid, int(quantity), round(total, 2))
        last_fp = st.session_state.get("last_fp")
        if last_fp and last_fp[0] == fingerprint and (datetime.now() - last_fp[1]).total_seconds() < 60:
            st.error("This looks like a duplicate of the sale you just saved. Sale blocked.")
            return

        # re-read the product from the database for safe stock + price
        try:
            fresh = supabase.table("products").select("*").eq("id", pid).limit(1).execute().data
        except Exception as e:
            st.error(f"Could not verify stock: {e}")
            return
        if not fresh:
            st.error("This product no longer exists.")
            return
        fresh = fresh[0]
        fresh_qty = int(num(fresh.get("quantity")))
        if int(quantity) > fresh_qty:
            st.error(f"Not enough stock. Only {fresh_qty} unit(s) available.")
            return

        # staff must use the database price, never a browser value
        unit_price = price if admin else num(fresh.get("selling_price"))
        sub = unit_price * int(quantity)
        disc = min(discount, sub)
        final_total = sub - disc
        paid_final = min(paid, final_total)
        remaining = final_total - paid_final

        sale_date = today_pk()
        warranty_days = int(num(fresh.get("warranty_days")))
        warranty_expiry = sale_date + timedelta(days=warranty_days)
        invoice = "LHB-" + sale_date.strftime("%Y%m%d") + "-" + secrets.token_hex(4).upper()

        stock_reserved = False
        sale_id = None
        item_saved = False
        payment_saved = False
        try:
            # 1) reserve stock (only succeeds if nobody changed it meanwhile)
            upd = (
                supabase.table("products")
                .update({"quantity": fresh_qty - int(quantity)})
                .eq("id", pid)
                .eq("quantity", fresh_qty)
                .execute()
                .data
            )
            if not upd:
                st.error("Stock changed while saving. Please try again.")
                return
            stock_reserved = True

            # 2) sale record
            base_sale = {
                "invoice_no": invoice,
                "customer_name": customer.strip(),
                "customer_phone": phone.strip(),
                "sale_date": sale_date.isoformat(),
                "sold_by": current_username(),
                "total": final_total,
                "paid_amount": paid_final,
                "discount": disc,
            }
            full_sale = dict(base_sale)
            full_sale.update({"notes": notes.strip(), "payment_method": method})
            res, _ = insert_with_fallback("sales", full_sale, base_sale)
            sale_id = res.data[0]["id"]

            # 3) sale item
            supabase.table("sale_items").insert(
                {
                    "sale_id": sale_id,
                    "product_id": pid,
                    "product_name": fresh.get("name"),
                    "specs": spec_text(fresh),
                    "quantity": int(quantity),
                    "selling_price": unit_price,
                    "purchase_price": num(fresh.get("purchase_price")),
                    "warranty_days": warranty_days,
                    "warranty_expiry": warranty_expiry.isoformat(),
                }
            ).execute()
            item_saved = True

            # 4) payment
            if paid_final > 0:
                note = f"Initial payment ({method})"
                if notes.strip():
                    note += f" - {notes.strip()}"
                supabase.table("payments").insert(
                    {
                        "sale_id": sale_id,
                        "amount": paid_final,
                        "received_by": current_username(),
                        "note": note,
                    }
                ).execute()
                payment_saved = True

        except Exception as e:
            # roll back everything that was saved
            try:
                if payment_saved and sale_id:
                    supabase.table("payments").delete().eq("sale_id", sale_id).execute()
                if item_saved and sale_id:
                    supabase.table("sale_items").delete().eq("sale_id", sale_id).execute()
                if sale_id:
                    supabase.table("sales").delete().eq("id", sale_id).execute()
                if stock_reserved:
                    supabase.table("products").update({"quantity": fresh_qty}).eq("id", pid).execute()
            except Exception:
                pass
            st.error(f"Sale failed and was cancelled: {e}")
            return

        st.session_state.last_fp = (fingerprint, datetime.now())
        st.session_state.sale_nonce = nonce + 1
        st.session_state.last_receipt = {
            "invoice": invoice,
            "date": sale_date.isoformat(),
            "customer": customer.strip(),
            "phone": phone.strip(),
            "sold_by": current_username(),
            "product": fresh.get("name"),
            "specs": spec_text(fresh) or "-",
            "qty": int(quantity),
            "price": unit_price,
            "subtotal": sub,
            "discount": disc,
            "total": final_total,
            "paid": paid_final,
            "method": method,
            "balance": remaining,
            "warranty_days": warranty_days,
            "warranty_expiry": warranty_expiry.isoformat(),
            "notes": notes.strip() or "-",
        }
        st.rerun()


# ------------------------------------------------------------------
# SALES HISTORY
# ------------------------------------------------------------------
def sales_history():
    st.subheader("📚 Sales History")
    admin = is_admin()

    sales = get_data("sales")
    if not sales:
        st.info("No sales available.")
        return

    items = load_sale_items()
    df = build_history(sales, items, admin)

    f1, f2 = st.columns([3, 1])
    search = f1.text_input("🔍 Search invoice, customer or phone")
    only_unpaid = f2.checkbox("Only unpaid balances")

    view = df.copy()
    if search.strip():
        s = search.strip().lower()
        mask = (
            view["Invoice No"].astype(str).str.lower().str.contains(s, na=False)
            | view["Customer"].astype(str).str.lower().str.contains(s, na=False)
            | view["Phone"].astype(str).str.lower().str.contains(s, na=False)
        )
        view = view[mask]
    if only_unpaid:
        view = view[view["Remaining"] > 0]

    show_table(view)

    # ---------------- RECEIVE BALANCE ----------------
    st.divider()
    st.markdown("### 💵 Receive Balance Payment")
    unpaid = [s for s in sales if num(s.get("total")) - num(s.get("paid_amount")) > 0.5]
    if not unpaid:
        st.success("All customers have paid in full.")
        return

    unpaid = sorted(unpaid, key=lambda x: x.get("id", 0), reverse=True)
    sale_ids = [s["id"] for s in unpaid]
    labels = {
        s["id"]: f'{s.get("invoice_no")} | {s.get("customer_name")} | '
        f'Balance {pkr(num(s.get("total")) - num(s.get("paid_amount")))}'
        for s in unpaid
    }
    sid = st.selectbox("Select invoice", sale_ids, format_func=lambda i: labels[i])
    sale = next(s for s in unpaid if s["id"] == sid)
    balance = num(sale.get("total")) - num(sale.get("paid_amount"))

    r1, r2 = st.columns(2)
    amount = r1.number_input(
        "Amount received (Rs)", min_value=0.0, max_value=float(balance),
        value=float(balance), step=500.0, key=f"rcv_{sid}",
    )
    method = r2.selectbox("Payment Method", PAYMENT_METHODS, key=f"rcv_m_{sid}")
    confirm = st.checkbox("Confirm this payment was received", key=f"rcv_c_{sid}")

    if st.button("Save Payment", disabled=not confirm):
        if amount <= 0:
            st.error("Enter an amount greater than zero.")
            return
        try:
            latest = supabase.table("sales").select("*").eq("id", sid).limit(1).execute().data[0]
            new_paid = num(latest.get("paid_amount")) + amount
            if new_paid > num(latest.get("total")) + 0.5:
                st.error("Payment is more than the remaining balance.")
                return
            supabase.table("sales").update({"paid_amount": new_paid}).eq("id", sid).execute()
            supabase.table("payments").insert(
                {
                    "sale_id": sid,
                    "amount": amount,
                    "received_by": current_username(),
                    "note": f"Balance payment ({method})",
                }
            ).execute()
            st.session_state.flash = ("success", "Payment saved.")
            st.rerun()
        except Exception as e:
            st.error(f"Payment failed: {e}")


# ------------------------------------------------------------------
# ADMIN REPORTS
# ------------------------------------------------------------------
def reports():
    if not is_admin():
        st.error("Access denied. Reports are for the Owner/Admin only.")
        return

    st.subheader("📊 Admin Reports")

    products = get_data("products")
    sales = get_data("sales")
    items = get_data("sale_items")

    total_stock = sum(int(num(p.get("quantity"))) for p in products)
    total_sales = sum(num(s.get("total")) for s in sales)
    received = sum(num(s.get("paid_amount")) for s in sales)
    remaining = sum(max(num(s.get("total")) - num(s.get("paid_amount")), 0) for s in sales)
    cost = sum(num(i.get("purchase_price")) * num(i.get("quantity")) for i in items)
    sale_ids_with_items = {i.get("sale_id") for i in items}
    revenue_with_items = sum(num(s.get("total")) for s in sales if s.get("id") in sale_ids_with_items)
    gross_profit = revenue_with_items - cost

    a, b, c, d = st.columns(4)
    a.metric("Total Products", len(products))
    b.metric("Total Stock Units", total_stock)
    c.metric("Total Invoices", len(sales))
    d.metric("Total Sales", pkr(total_sales))

    e, f, g = st.columns(3)
    e.metric("Total Received Payments", pkr(received))
    f.metric("Remaining Customer Balances", pkr(remaining))
    g.metric("Estimated Gross Profit", pkr(gross_profit))

    st.markdown("### 👥 Staff Sales Performance")
    if sales:
        profit_by_sale = {}
        cost_by_sale = {}
        for i in items:
            cost_by_sale[i.get("sale_id")] = cost_by_sale.get(i.get("sale_id"), 0) + num(
                i.get("purchase_price")
            ) * num(i.get("quantity"))

        perf = {}
        for s in sales:
            who = s.get("sold_by") or "Unknown"
            row = perf.setdefault(who, {"Invoices": 0, "Sales": 0.0, "Received": 0.0, "Profit": 0.0})
            row["Invoices"] += 1
            row["Sales"] += num(s.get("total"))
            row["Received"] += num(s.get("paid_amount"))
            if s.get("id") in cost_by_sale:
                row["Profit"] += num(s.get("total")) - cost_by_sale[s.get("id")]

        perf_df = pd.DataFrame(
            [
                {
                    "Staff": k,
                    "Invoices": v["Invoices"],
                    "Total Sales": pkr(v["Sales"]),
                    "Received": pkr(v["Received"]),
                    "Estimated Profit": pkr(v["Profit"]),
                }
                for k, v in sorted(perf.items(), key=lambda kv: kv[1]["Sales"], reverse=True)
            ]
        )
        show_table(perf_df)
    else:
        st.info("No sales yet.")

    st.markdown("### 💰 Customers With Remaining Balance")
    owing = [s for s in sales if num(s.get("total")) - num(s.get("paid_amount")) > 0.5]
    if owing:
        show_table(
            pd.DataFrame(
                [
                    {
                        "Invoice": s.get("invoice_no"),
                        "Customer": s.get("customer_name"),
                        "Phone": s.get("customer_phone"),
                        "Total": pkr(s.get("total")),
                        "Paid": pkr(s.get("paid_amount")),
                        "Remaining": pkr(num(s.get("total")) - num(s.get("paid_amount"))),
                    }
                    for s in owing
                ]
            )
        )
    else:
        st.success("No pending balances.")


# ------------------------------------------------------------------
# STAFF MANAGEMENT (ADMIN ONLY)
# ------------------------------------------------------------------
def staff_management():
    if not is_admin():
        st.error("Access denied. Staff Management is for the Owner/Admin only.")
        return

    st.subheader("👥 Staff Management")

    users = get_data("users")
    if users:
        rows = []
        for u in users:
            row = {"Username": u.get("username"), "Role": u.get("role")}
            if u.get("created_at"):
                row["Created"] = str(u.get("created_at"))[:10]
            rows.append(row)
        show_table(pd.DataFrame(rows))
    else:
        st.info("No users found.")

    st.divider()
    with st.form("create_staff", clear_on_submit=True):
        st.markdown("### ➕ Create Staff Account")
        username = st.text_input("Username")
        password = st.text_input("Password (minimum 6 characters)", type="password")
        password2 = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Create Staff Account")

    if submit:
        uname = username.strip()
        if not uname:
            st.error("Username is required.")
        elif len(password) < 6:
            st.error("Password must be at least 6 characters.")
        elif password != password2:
            st.error("Passwords do not match.")
        elif any(str(u.get("username", "")).lower() == uname.lower() for u in users):
            st.error("This username already exists.")
        else:
            try:
                supabase.table("users").insert(
                    {
                        "username": uname,
                        "password_hash": password_hash(password),
                        "role": "staff",
                    }
                ).execute()
                st.session_state.flash = ("success", f"Staff account '{uname}' created.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not create account: {e}")


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
def main():
    if "user" not in st.session_state:
        login()
        return

    admin = is_admin()

    st.sidebar.markdown("## 💻 Laptop House Buner")
    st.sidebar.write(f'👤 **{current_username()}**')
    st.sidebar.caption("Role: " + ("Owner / Admin" if admin else "Staff"))
    st.sidebar.divider()

    menu = ["Dashboard", "Products & Stock", "New Sale / Billing", "Sales History"]
    if admin:
        menu += ["Reports", "Staff Management"]

    page = st.sidebar.radio("Menu", menu)

    st.sidebar.divider()
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # one-time messages after saving
    flash = st.session_state.pop("flash", None)
    if flash:
        kind, text = flash
        (st.success if kind == "success" else st.error)(text)

    if page == "Dashboard":
        dashboard()
    elif page == "Products & Stock":
        products_page()
    elif page == "New Sale / Billing":
        billing_page()
    elif page == "Sales History":
        sales_history()
    elif page == "Reports":
        reports()
    elif page == "Staff Management":
        staff_management()


main()
