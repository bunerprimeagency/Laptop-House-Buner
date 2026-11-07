import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import date
import hashlib
import secrets

st.set_page_config(
    page_title="Laptop House Buner",
    page_icon="💻",
    layout="wide"
)

st.title("💻 Laptop House Buner")
st.caption("Shop Management System | Supabase Database")


@st.cache_resource
def connect_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SECRET_KEY"]
    )


try:
    supabase = connect_supabase()
    supabase.table("products").select("id").limit(1).execute()
    st.sidebar.success("Supabase Connected")
except Exception as e:
    st.error("Supabase connection failed. Check secrets.toml and database tables.")
    st.code(str(e))
    st.stop()


def get_data(table):
    return supabase.table(table).select("*").execute().data or []


def save_product(data):
    return supabase.table("products").insert(data).execute()


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


def login():
    st.subheader("Staff Login")

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
                .execute().data
            )

            if users and verify_password(
                password, users[0]["password_hash"]
            ):
                st.session_state.user = users[0]
                st.rerun()
            else:
                st.error("Incorrect username or password.")
        except Exception as e:
            st.error(f"Login error: {e}")


def dashboard():
    products = get_data("products")
    sales = get_data("sales")

    total_stock = sum(int(p.get("quantity") or 0) for p in products)
    total_sales = sum(float(s.get("total") or 0) for s in sales)

    a, b, c = st.columns(3)
    a.metric("Total Products", len(products))
    b.metric("Stock Units", total_stock)
    c.metric("Total Sales", f"Rs {total_sales:,.0f}")


def products_page():
    st.subheader("📦 Products & Stock")

    products = get_data("products")

    if products:
        st.dataframe(pd.DataFrame(products), use_container_width=True)
    else:
        st.info("No products added yet.")

    if st.session_state.user.get("role") != "owner":
        return

    with st.form("add_product", clear_on_submit=True):
        st.markdown("### Add New Product")

        name = st.text_input("Product Name")
        category = st.selectbox("Category", ["Laptop", "Accessories"])
        model = st.text_input("Model")
        processor = st.text_input("Processor")
        ram = st.text_input("RAM")
        storage = st.text_input("Storage")
        condition = st.selectbox("Condition", ["Used", "New", "Refurbished"])
        serial = st.text_input("Serial Number")

        purchase = st.number_input("Purchase Price", min_value=0.0)
        selling = st.number_input("Selling Price", min_value=0.0)
        quantity = st.number_input("Quantity", min_value=0, step=1)
        warranty = st.number_input("Warranty Days", min_value=0, step=1)

        submit = st.form_submit_button("Save Product to Supabase")

    if submit:
        if not name.strip():
            st.error("Product name is required.")
            return

        try:
            save_product({
                "name": name.strip(),
                "category": category,
                "model": model,
                "processor": processor,
                "ram": ram,
                "storage": storage,
                "condition_text": condition,
                "serial_number": serial,
                "purchase_price": purchase,
                "selling_price": selling,
                "quantity": int(quantity),
                "warranty_days": int(warranty)
            })

            st.success("Product saved directly to Supabase!")
            st.rerun()

        except Exception as e:
            st.error(f"Save failed: {e}")


def billing_page():
    st.subheader("🧾 New Sale / Billing")

    products = [
        p for p in get_data("products")
        if int(p.get("quantity") or 0) > 0
    ]

    if not products:
        st.warning("First add products in Products & Stock.")
        return

    options = {
        f'{p["name"]} - Rs {p["selling_price"]} - Stock {p["quantity"]}': p
        for p in products
    }

    with st.form("new_sale"):
        customer = st.text_input("Customer Name")
        phone = st.text_input("Customer Phone")
        selected = st.selectbox("Select Product", list(options))
        product = options[selected]

        quantity = st.number_input(
            "Quantity",
            min_value=1,
            max_value=int(product["quantity"]),
            step=1
        )

        price = float(product["selling_price"])
        total = price * quantity
        st.write(f"Total: Rs {total:,.2f}")

        paid = st.number_input(
            "Paid Amount", min_value=0.0, max_value=total
        )

        submit = st.form_submit_button("Save Sale to Supabase")

    if submit:
        try:
            invoice = "LHB-" + date.today().strftime("%Y%m%d") + "-" + secrets.token_hex(3).upper()

            sale = supabase.table("sales").insert({
                "invoice_no": invoice,
                "customer_name": customer,
                "customer_phone": phone,
                "sale_date": date.today().isoformat(),
                "sold_by": st.session_state.user["username"],
                "total": total,
                "paid_amount": paid,
                "discount": 0
            }).execute().data[0]

            supabase.table("sale_items").insert({
                "sale_id": sale["id"],
                "product_id": product["id"],
                "product_name": product["name"],
                "specs": product.get("model", ""),
                "quantity": int(quantity),
                "selling_price": price,
                "purchase_price": float(product.get("purchase_price") or 0),
                "warranty_days": int(product.get("warranty_days") or 0),
                "warranty_expiry": date.today().isoformat()
            }).execute()

            supabase.table("products").update({
                "quantity": int(product["quantity"]) - int(quantity)
            }).eq("id", product["id"]).execute()

            if paid > 0:
                supabase.table("payments").insert({
                    "sale_id": sale["id"],
                    "amount": paid,
                    "received_by": st.session_state.user["username"],
                    "note": "Initial payment"
                }).execute()

            st.success(f"Sale saved! Invoice: {invoice}")
            st.rerun()

        except Exception as e:
            st.error(f"Sale error: {e}")


def sales_history():
    st.subheader("📚 Sales History")
    sales = get_data("sales")

    if sales:
        st.dataframe(pd.DataFrame(sales), use_container_width=True)
    else:
        st.info("No sales available.")


def reports():
    st.subheader("📊 Reports")

    sales = get_data("sales")
    products = get_data("products")

    total = sum(float(s.get("total") or 0) for s in sales)
    paid = sum(float(s.get("paid_amount") or 0) for s in sales)

    a, b, c = st.columns(3)
    a.metric("Invoices", len(sales))
    b.metric("Sales", f"Rs {total:,.2f}")
    c.metric("Received", f"Rs {paid:,.2f}")


def main():
    if "user" not in st.session_state:
        login()
        return

    st.sidebar.title("Laptop House Buner")
    st.sidebar.write(
        f'User: {st.session_state.user["username"]}'
    )

    page = st.sidebar.radio(
        "Menu",
        [
            "Dashboard",
            "Products & Stock",
            "New Sale / Billing",
            "Sales History",
            "Reports"
        ]
    )

    if st.sidebar.button("Logout"):
        del st.session_state.user
        st.rerun()

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


main()