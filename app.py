import hashlib
import io
import secrets
import zipfile
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import streamlit as st
from supabase import create_client

# ==================================================================
# PAGE SETUP
# ==================================================================
st.set_page_config(page_title="Laptop House Buner", page_icon="💻", layout="wide")

PAYMENT_METHODS = ["Cash", "Bank Transfer", "JazzCash", "EasyPaisa", "Card", "Other"]
CATEGORIES = ["Laptop", "Accessories", "Desktop", "Other"]
CONDITIONS = ["Used", "New", "Refurbished"]
ADMIN_ROLES = ("owner", "admin")
PERIODS = ["All time", "Today", "Last 7 days", "Last 30 days"]

CSS = """
<style>
@keyframes fadeIn {from {opacity: 0; transform: translateY(6px);} to {opacity: 1; transform: none;}}
@keyframes fadeUp {from {opacity: 0; transform: translateY(14px);} to {opacity: 1; transform: none;}}
@keyframes drawCheck {to {stroke-dashoffset: 0;}}
@keyframes popIn {0% {transform: scale(.4); opacity: 0;} 70% {transform: scale(1.08);} 100% {transform: scale(1); opacity: 1;}}

.block-container {padding-top: 1.6rem; padding-bottom: 2rem; animation: fadeIn .28s ease;}
.lhb-head {display:flex; align-items:center; gap:14px; margin-bottom: 1.1rem;
  padding: 16px 20px; border-radius: 14px; color:#fff;
  background: linear-gradient(120deg,#0b1f3a 0%,#164a8a 60%,#1f6feb 100%);
  box-shadow: 0 6px 18px rgba(15,40,90,.22);}
.lhb-head .ic {font-size: 2rem; line-height:1;}
.lhb-head .t {font-size: 1.45rem; font-weight: 800; margin:0; line-height:1.2; color:#fff;}
.lhb-head .s {font-size: .9rem; margin:0; opacity:.85; color:#fff;}

.kpi-grid {display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:14px; margin: 6px 0 18px 0;}
.kpi {background:#fff; border:1px solid #e3e8ef; border-left:5px solid var(--c,#1f6feb); border-radius:12px;
  padding:14px 16px; box-shadow:0 1px 4px rgba(16,24,40,.08); animation: fadeUp .5s both;
  animation-delay: var(--d,0s); transition: transform .18s ease, box-shadow .18s ease;}
.kpi:hover {transform: translateY(-3px); box-shadow: 0 8px 18px rgba(16,24,40,.14);}
.kpi .l {color:#6b7280; font-size:.78rem; font-weight:600; text-transform:uppercase; letter-spacing:.04em;}
.kpi .v {color:#111827; font-size:1.45rem; font-weight:800; margin-top:4px; word-break:break-word;}
.kpi .i {float:right; font-size:1.3rem; opacity:.85;}

.empty {text-align:center; padding:34px 16px; border:2px dashed #cbd5e1; border-radius:14px;
  background:#f8fafc; color:#475569; animation: fadeIn .4s ease;}
.empty .e1 {font-size:2.4rem;} .empty .e2 {font-weight:700; color:#0f172a; font-size:1.1rem;}

.ok-wrap {display:flex; align-items:center; gap:16px; padding:16px 20px; border-radius:14px;
  background:#ecfdf3; border:1px solid #abefc6; margin-bottom:12px; animation: popIn .5s ease both;}
.ok-wrap svg {width:56px; height:56px;}
.ok-c {fill:none; stroke:#12b76a; stroke-width:3;}
.ok-p {fill:none; stroke:#12b76a; stroke-width:4; stroke-linecap:round; stroke-linejoin:round;
  stroke-dasharray:40; stroke-dashoffset:40; animation: drawCheck .6s .3s ease forwards;}
.ok-wrap .t1 {font-weight:800; color:#054f31; font-size:1.15rem;} .ok-wrap .t2 {color:#054f31;}

.login-card {max-width:430px; margin: 2rem auto 1rem auto; text-align:center; padding:26px 20px 8px 20px;
  border-radius:16px; background: linear-gradient(120deg,#0b1f3a,#1f6feb); color:#fff;
  box-shadow:0 10px 28px rgba(15,40,90,.25); animation: fadeUp .5s ease;}
.login-card h2 {margin:0; color:#fff;} .login-card p {opacity:.85; color:#fff;}

.stButton > button, .stDownloadButton > button {border-radius:10px; font-weight:600;
  transition: transform .15s ease, box-shadow .15s ease;}
.stButton > button:hover, .stDownloadButton > button:hover {transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(31,111,235,.25);}
.stTabs [data-baseweb="tab"] {font-weight:600;}

section[data-testid="stSidebar"] {background: linear-gradient(180deg,#0b1f3a 0%,#12315c 100%);}
section[data-testid="stSidebar"] * {color:#e8eefb;}
section[data-testid="stSidebar"] hr {border-color: rgba(255,255,255,.18);}
section[data-testid="stSidebar"] .stButton > button {background: rgba(255,255,255,.1);
  border: 1px solid rgba(255,255,255,.3); color:#fff; width:100%;}
section[data-testid="stSidebar"] .stButton > button:hover {background: rgba(255,255,255,.2);}
.side-brand {font-size:1.3rem; font-weight:800; margin-bottom:2px;}
.side-user {background: rgba(255,255,255,.1); border-radius:10px; padding:10px 12px; margin:6px 0 4px 0;}

@media (max-width: 768px) {
  .block-container {padding-left: .8rem; padding-right: .8rem;}
  .lhb-head {padding: 12px 14px;} .lhb-head .t {font-size: 1.15rem;}
  .kpi .v {font-size: 1.2rem;}
}
@media (prefers-reduced-motion: reduce) {* {animation: none !important; transition: none !important;}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ==================================================================
# DATABASE CONNECTION
# ==================================================================
@st.cache_resource
def connect_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SECRET_KEY"])


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


# ==================================================================
# GENERAL HELPERS
# ==================================================================
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
    return datetime.now(timezone(timedelta(hours=5))).date()


def parse_date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def show_table(df):
    try:
        st.dataframe(df, width="stretch", hide_index=True)
    except Exception:
        st.dataframe(df, use_container_width=True, hide_index=True)


def page_header(icon, title, sub=""):
    st.markdown(
        f'<div class="lhb-head"><div class="ic">{icon}</div><div>'
        f'<p class="t">{title}</p><p class="s">{sub}</p></div></div>',
        unsafe_allow_html=True,
    )


def cards(items):
    """items = [(icon, label, value, color)]"""
    html = '<div class="kpi-grid">'
    for n, (icon, label, value, color) in enumerate(items):
        html += (
            f'<div class="kpi" style="--c:{color};--d:{n * 0.06:.2f}s">'
            f'<span class="i">{icon}</span><div class="l">{label}</div>'
            f'<div class="v">{value}</div></div>'
        )
    st.markdown(html + "</div>", unsafe_allow_html=True)


def empty_state(icon, title, text):
    st.markdown(
        f'<div class="empty"><div class="e1">{icon}</div><div class="e2">{title}</div>'
        f"<div>{text}</div></div>",
        unsafe_allow_html=True,
    )


def flash(kind, text):
    st.session_state["flash"] = (kind, text)


def current_username():
    return (st.session_state.get("user") or {}).get("username", "")


def is_admin():
    user = st.session_state.get("user") or {}
    return str(user.get("role", "")).strip().lower() in ADMIN_ROLES


def fresh_role():
    """Re-check the role in the database (backend permission check)."""
    uname = current_username()
    if not uname:
        return ""
    rows = (
        supabase.table("users").select("role").eq("username", uname).limit(1).execute().data
    )
    return str(rows[0].get("role", "")).strip().lower() if rows else ""


def require_login():
    if not current_username() or not fresh_role():
        raise PermissionError("Please log in again.")


def require_admin():
    if fresh_role() not in ADMIN_ROLES:
        raise PermissionError("Permission denied. Only the Owner/Admin can do this.")


def col_exists(table, col):
    cache = st.session_state.setdefault("_cols", {})
    key = f"{table}.{col}"
    if key not in cache:
        try:
            supabase.table(table).select(col).limit(1).execute()
            cache[key] = True
        except Exception:
            cache[key] = False
    return cache[key]


def with_optional(table, base, extras):
    """Add optional columns only if they exist. Returns (data, skipped_names)."""
    data, skipped = dict(base), []
    for k, v in extras.items():
        if col_exists(table, k):
            data[k] = v
        else:
            skipped.append(k)
    return data, skipped


def get_data(table):
    rows, start = [], 0
    ordered = True
    while True:
        try:
            q = supabase.table(table).select("*")
            if ordered:
                q = q.order("id")
            chunk = q.range(start, start + 999).execute().data or []
        except Exception:
            if ordered and start == 0:
                ordered = False  # table without an "id" column: read without ordering
                continue
            raise
        rows.extend(chunk)
        if len(chunk) < 1000:
            break
        start += 1000
    return rows


def load_products():
    rows = get_data("products")
    if not is_admin():  # staff never receive purchase prices
        for r in rows:
            r.pop("purchase_price", None)
    return rows


def load_sale_items():
    rows = get_data("sale_items")
    if not is_admin():
        for r in rows:
            r.pop("purchase_price", None)
    return rows


def sale_status(s):
    return str(s.get("status") or "active").lower()


def active_sales(sales):
    return [s for s in sales if sale_status(s) != "cancelled"]


def spec_text(p):
    parts = [p.get("model"), p.get("processor"), p.get("ram"), p.get("storage"),
             p.get("graphics"), p.get("display_size"), p.get("condition_text")]
    return " | ".join(str(x) for x in parts if x)


def profit_map(sales, items):
    cost = {}
    for i in items:
        cost[i.get("sale_id")] = cost.get(i.get("sale_id"), 0) + num(i.get("purchase_price")) * num(i.get("quantity"))
    return {s["id"]: num(s.get("total")) - cost[s["id"]] for s in sales if s["id"] in cost}


def in_range(s, d1, d2):
    d = parse_date(s.get("sale_date"))
    return d is not None and d1 <= d <= d2


def zip_bytes(tables):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, rows in tables.items():
            z.writestr(f"{name}.csv", pd.DataFrame(rows).to_csv(index=False))
    return buf.getvalue()


def adjust_stock(pid, delta):
    """Add (delta>0) or remove (delta<0) stock safely. Returns True on success."""
    for _ in range(3):
        rows = supabase.table("products").select("id,quantity").eq("id", pid).limit(1).execute().data
        if not rows:
            return False
        cur = int(num(rows[0].get("quantity")))
        new = cur + int(delta)
        if new < 0:
            return False
        done = (
            supabase.table("products").update({"quantity": new}).eq("id", pid).eq("quantity", cur).execute().data
        )
        if done:
            return True
    return False


# ==================================================================
# PASSWORDS (same format as the existing users table)
# ==================================================================
def password_hash(password):
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200000).hex()
    return salt + "$" + hashed


def verify_password(password, saved):
    try:
        salt, digest = saved.split("$", 1)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200000).hex()
        return secrets.compare_digest(actual, digest)
    except Exception:
        return False


# ==================================================================
# PDF REPORTS (reportlab)
# ==================================================================
def build_pdf(title, subtitle, blocks):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        raise RuntimeError("PDF library missing. Add 'reportlab' to requirements.txt and reboot the app.")
    from xml.sax.saxutils import escape

    navy, blue, light = colors.HexColor("#0b1f3a"), colors.HexColor("#1f6feb"), colors.HexColor("#f3f6fb")
    stamp = datetime.now(timezone(timedelta(hours=5))).strftime("%d %b %Y, %I:%M %p")

    class NumberedCanvas(rl_canvas.Canvas):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self._saved = []

        def showPage(self):
            self._saved.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved)
            for state in self._saved:
                self.__dict__.update(state)
                w = self._pagesize[0]
                self.setStrokeColor(colors.HexColor("#cbd5e1"))
                self.line(28, 30, w - 28, 30)
                self.setFont("Helvetica", 8)
                self.setFillColor(colors.HexColor("#64748b"))
                self.drawString(28, 18, f"Laptop House Buner  |  Generated {stamp}")
                self.drawRightString(w - 28, 18, f"Page {self.getPageNumber()} of {total}")
                super().showPage()
            super().save()

    def header(canv, doc):
        w, h = doc.pagesize
        canv.saveState()
        canv.setFillColor(navy)
        canv.rect(0, h - 62, w, 62, fill=1, stroke=0)
        canv.setFillColor(blue)  # logo area: replace this box with your logo if you wish
        canv.roundRect(28, h - 52, 42, 42, 8, fill=1, stroke=0)
        canv.setFillColor(colors.white)
        canv.setFont("Helvetica-Bold", 16)
        canv.drawCentredString(49, h - 37, "LH")
        canv.setFont("Helvetica-Bold", 15)
        canv.drawString(82, h - 30, "LAPTOP HOUSE BUNER")
        canv.setFont("Helvetica", 8.5)
        canv.drawString(82, h - 44, "Shop Management System")
        canv.setFont("Helvetica-Bold", 12)
        canv.drawRightString(w - 28, h - 30, title)
        canv.setFont("Helvetica", 8.5)
        canv.drawRightString(w - 28, h - 44, subtitle)
        canv.restoreState()

    buf = io.BytesIO()
    page = landscape(A4)
    doc = SimpleDocTemplate(buf, pagesize=page, leftMargin=28, rightMargin=28, topMargin=80,
                            bottomMargin=42, title=title, author="Laptop House Buner")
    usable = page[0] - 56
    h_style = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=12, textColor=navy, spaceBefore=8, spaceAfter=6)
    p_style = ParagraphStyle("p", fontName="Helvetica", fontSize=9, leading=12, textColor=colors.HexColor("#334155"))

    def cell_styles(right, bold=False, white=False):
        name = "Helvetica-Bold" if (bold or white) else "Helvetica"
        return ParagraphStyle("c", fontName=name, fontSize=7.5, leading=9.2, alignment=2 if right else 0,
                              textColor=colors.white if white else colors.HexColor("#0f172a"))

    story = []
    for b in blocks:
        kind = b[0]
        if kind == "h":
            story.append(Paragraph(escape(b[1]), h_style))
        elif kind == "p":
            story.append(Paragraph(escape(b[1]), p_style))
            story.append(Spacer(1, 6))
        elif kind == "kpi":
            data = [[Paragraph(escape(k), cell_styles(False, bold=True)), Paragraph(escape(v), cell_styles(True, bold=True))]
                    for k, v in b[1]]
            t = Table(data, colWidths=[usable * 0.35, usable * 0.2])
            t.setStyle(TableStyle([
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, light]),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))
        elif kind == "table":
            _, head, rows, weights, right, foot = b
            if not rows:
                story.append(Paragraph("No records found for this report.", p_style))
                continue
            wsum = float(sum(weights))
            widths = [usable * w / wsum for w in weights]
            data = [[Paragraph(escape(str(h)), cell_styles(i in right, white=True)) for i, h in enumerate(head)]]
            for r in rows:
                data.append([Paragraph(escape(str(c if c is not None else "")), cell_styles(i in right))
                             for i, c in enumerate(r)])
            if foot:
                data.append([Paragraph(escape(str(c)), cell_styles(i in right, bold=True)) for i, c in enumerate(foot)])
            t = Table(data, colWidths=widths, repeatRows=1)
            style = [
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light]),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
            if foot:
                style.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dbe7fb")))
            t.setStyle(TableStyle(style))
            story.append(t)
            story.append(Spacer(1, 8))
    doc.build(story, onFirstPage=header, onLaterPages=header, canvasmaker=NumberedCanvas)
    return buf.getvalue()


def inventory_pdf(products):
    require_admin()
    units = sum(int(num(p.get("quantity"))) for p in products)
    buy = sum(stock_value(p) for p in products)
    sell = sum(stock_value(p, "selling_price") for p in products)
    rows = [[p.get("name"), p.get("category"), p.get("model"), p.get("processor"), p.get("ram"),
             p.get("storage"), p.get("serial_number"), p.get("condition_text"),
             int(num(p.get("quantity"))), pkr(p.get("purchase_price")), pkr(p.get("selling_price"))]
            for p in products]
    blocks = [
        ("h", "Inventory Summary"),
        ("kpi", [("Total number of products", str(len(products))), ("Total stock units", str(units)),
                 ("Total inventory purchase value", pkr(buy)), ("Total inventory selling value", pkr(sell))]),
        ("h", "Product List"),
        ("table", ["Product", "Category", "Model", "Processor", "RAM", "Storage", "Serial No", "Condition",
                   "Qty", "Purchase", "Selling"], rows, [15, 8, 10, 13, 6, 8, 12, 8, 4, 9, 9], {8, 9, 10}, None),
    ]
    return build_pdf("Inventory Report", f"Report date: {today_pk().strftime('%d %b %Y')}", blocks)


def sales_pdf(sales, items, d1, d2):
    require_admin()
    sales = sorted(active_sales(sales), key=lambda x: x.get("id", 0))
    by_sale = {}
    for i in items:
        by_sale.setdefault(i.get("sale_id"), []).append(i)
    rows = []
    for s in sales:
        for i in by_sale.get(s["id"], [{}]):
            rows.append([s.get("invoice_no"), str(s.get("sale_date"))[:10], s.get("customer_name"),
                         s.get("customer_phone"),
                         f"{i.get('product_name') or ''} {('- ' + i['specs']) if i.get('specs') else ''}".strip(),
                         int(num(i.get("quantity"))) if i else "", pkr(i.get("selling_price")) if i else "",
                         pkr(s.get("discount")), pkr(s.get("total")), pkr(s.get("paid_amount")),
                         pkr(max(num(s.get("total")) - num(s.get("paid_amount")), 0)), s.get("sold_by")])
    tot = sum(num(s.get("total")) for s in sales)
    paid = sum(num(s.get("paid_amount")) for s in sales)
    foot = ["TOTAL", "", "", "", "", "", "", "", pkr(tot), pkr(paid), pkr(max(tot - paid, 0)), ""]
    blocks = [("p", f"Sales from {d1.strftime('%d %b %Y')} to {d2.strftime('%d %b %Y')}. Cancelled invoices are excluded."),
              ("table", ["Invoice", "Date", "Customer", "Phone", "Product / Specs", "Qty", "Price", "Discount",
                         "Total", "Paid", "Balance", "Sold By"], rows,
               [11, 8, 11, 10, 22, 4, 8, 7, 8, 8, 8, 8], {5, 6, 7, 8, 9, 10}, foot if rows else None)]
    return build_pdf("Sold Products Report", f"{d1.strftime('%d %b %Y')} - {d2.strftime('%d %b %Y')}", blocks)


def summary_pdf(sales, items, d1, d2):
    require_admin()
    sales = active_sales(sales)
    pm = profit_map(sales, items)
    total = sum(num(s.get("total")) for s in sales)
    paid = sum(num(s.get("paid_amount")) for s in sales)
    owing = [s for s in sales if num(s.get("total")) - num(s.get("paid_amount")) > 0.5]
    perf = {}
    for s in sales:
        r = perf.setdefault(s.get("sold_by") or "Unknown", [0, 0.0, 0.0])
        r[0] += 1
        r[1] += num(s.get("total"))
        r[2] += num(s.get("paid_amount"))
    blocks = [
        ("h", "Sales Summary"),
        ("kpi", [("Sales date range", f"{d1.strftime('%d %b %Y')} to {d2.strftime('%d %b %Y')}"),
                 ("Total invoices", str(len(sales))), ("Total sales", pkr(total)),
                 ("Total received payments", pkr(paid)),
                 ("Total remaining balances", pkr(max(total - paid, 0))),
                 ("Estimated gross profit", pkr(sum(pm.values())))]),
        ("h", "Staff Sales Performance"),
        ("table", ["Staff", "Invoices", "Total Sales", "Received"],
         [[k, v[0], pkr(v[1]), pkr(v[2])] for k, v in sorted(perf.items(), key=lambda kv: -kv[1][1])],
         [30, 10, 20, 20], {1, 2, 3}, None),
        ("h", "Customers With Remaining Balance"),
        ("table", ["Invoice", "Customer", "Phone", "Total", "Paid", "Remaining"],
         [[s.get("invoice_no"), s.get("customer_name"), s.get("customer_phone"), pkr(s.get("total")),
           pkr(s.get("paid_amount")), pkr(num(s.get("total")) - num(s.get("paid_amount")))] for s in owing],
         [16, 22, 16, 14, 14, 14], {3, 4, 5}, None),
    ]
    return build_pdf("Sales Summary", f"{d1.strftime('%d %b %Y')} - {d2.strftime('%d %b %Y')}", blocks)


# ==================================================================
# SALE BACKEND OPERATIONS (permission checked in Python)
# ==================================================================
def update_sale(sale_id, customer, phone, qty, price, discount, notes):
    require_admin()
    sale = supabase.table("sales").select("*").eq("id", sale_id).limit(1).execute().data
    if not sale:
        raise ValueError("Sale not found.")
    sale = sale[0]
    if sale_status(sale) == "cancelled":
        raise ValueError("Cancelled sales cannot be edited.")
    items = supabase.table("sale_items").select("*").eq("sale_id", sale_id).execute().data or []
    upd = {"customer_name": customer.strip(), "customer_phone": phone.strip()}
    if col_exists("sales", "notes"):
        upd["notes"] = notes.strip()

    stock_changed, item_changed, old_item = 0, False, None
    try:
        if len(items) == 1:
            it = items[0]
            old_item = it
            old_qty = int(num(it.get("quantity")))
            subtotal = price * qty
            if discount > subtotal:
                raise ValueError("Discount cannot be more than the subtotal.")
            total = subtotal - discount
            if total < num(sale.get("paid_amount")) - 0.5:
                raise ValueError("New total is less than the amount already paid. Cancel the sale instead.")
            delta = int(qty) - old_qty
            if delta != 0:
                if not it.get("product_id") or not adjust_stock(it["product_id"], -delta):
                    raise ValueError("Not enough stock (or product missing) for this quantity change.")
                stock_changed = delta
            supabase.table("sale_items").update({"quantity": int(qty), "selling_price": price}).eq("id", it["id"]).execute()
            item_changed = True
            upd.update({"total": total, "discount": discount})
        supabase.table("sales").update(upd).eq("id", sale_id).execute()
    except Exception:
        try:  # roll back
            if item_changed and old_item:
                supabase.table("sale_items").update(
                    {"quantity": old_item.get("quantity"), "selling_price": old_item.get("selling_price")}
                ).eq("id", old_item["id"]).execute()
            if stock_changed and old_item:
                adjust_stock(old_item["product_id"], stock_changed)
        except Exception:
            pass
        raise


def restore_stock_for_sale(sale_id):
    """Put sold units back into stock. Returns number of items that could not be restored."""
    missing = 0
    items = supabase.table("sale_items").select("*").eq("sale_id", sale_id).execute().data or []
    for it in items:
        if not (it.get("product_id") and adjust_stock(it["product_id"], int(num(it.get("quantity"))))):
            missing += 1
    return missing


def cancel_sale(sale_id, reason):
    require_admin()
    if not col_exists("sales", "status"):
        raise ValueError("Cancel needs the 'status' column. Run the SQL migration first.")
    sale = supabase.table("sales").select("*").eq("id", sale_id).limit(1).execute().data
    if not sale:
        raise ValueError("Sale not found.")
    if sale_status(sale[0]) == "cancelled":
        raise ValueError("This sale is already cancelled.")
    missing = restore_stock_for_sale(sale_id)
    upd = {"status": "cancelled"}
    if col_exists("sales", "cancelled_at"):
        upd["cancelled_at"] = datetime.now(timezone.utc).isoformat()
    if col_exists("sales", "cancel_reason"):
        upd["cancel_reason"] = reason.strip()
    supabase.table("sales").update(upd).eq("id", sale_id).execute()
    return missing


def delete_sale_full(sale_id):
    """Permanently delete one invoice (stock restored first unless already cancelled)."""
    require_admin()
    sale = supabase.table("sales").select("*").eq("id", sale_id).limit(1).execute().data
    if not sale:
        return 0
    missing = 0 if sale_status(sale[0]) == "cancelled" else restore_stock_for_sale(sale_id)
    supabase.table("payments").delete().eq("sale_id", sale_id).execute()
    supabase.table("sale_items").delete().eq("sale_id", sale_id).execute()
    supabase.table("sales").delete().eq("id", sale_id).execute()
    return missing


def reset_sale_payments(sale_id):
    require_admin()
    supabase.table("payments").delete().eq("sale_id", sale_id).execute()
    supabase.table("sales").update({"paid_amount": 0}).eq("id", sale_id).execute()


def reset_products(ids, fields):
    require_admin()
    upd = {}
    if "Stock quantity → 0" in fields:
        upd["quantity"] = 0
    if "Purchase and selling price → 0" in fields:
        upd["purchase_price"] = 0
        upd["selling_price"] = 0
    if "Serial number → blank" in fields:
        upd["serial_number"] = ""
    if "Warranty days → 0" in fields:
        upd["warranty_days"] = 0
    if "Warranty terms → blank" in fields and col_exists("products", "warranty_terms"):
        upd["warranty_terms"] = ""
    if not upd:
        raise ValueError("Nothing to reset for the chosen options.")
    for pid in ids:
        supabase.table("products").update(upd).eq("id", pid).execute()


# ==================================================================
# LOGIN
# ==================================================================
def login():
    st.markdown(
        '<div class="login-card"><h2>💻 Laptop House Buner</h2><p>Shop Management System</p></div>',
        unsafe_allow_html=True,
    )
    if st.session_state.get("failed_logins", 0) >= 5:
        st.error("Too many failed attempts. Refresh the page to try again.")
        return
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("🔐 Login", type="primary")
    if submit:
        try:
            users = supabase.table("users").select("*").eq("username", username.strip()).limit(1).execute().data
            if users and verify_password(password, users[0].get("password_hash", "")):
                st.session_state.user = {"id": users[0].get("id"), "username": users[0].get("username"),
                                         "role": users[0].get("role", "staff")}
                st.session_state.failed_logins = 0
                st.rerun()
            else:
                st.session_state.failed_logins = st.session_state.get("failed_logins", 0) + 1
                st.error("Incorrect username or password.")
        except Exception as e:
            st.error(f"Login error: {e}")


# ==================================================================
# DASHBOARD
# ==================================================================
def dashboard():
    page_header("🏠", "Dashboard", f"Welcome, {current_username()} — {today_pk().strftime('%A, %d %B %Y')}")
    admin = is_admin()
    with st.expander("⚙️ Dashboard settings"):
        d1, d2 = st.columns(2)
        period = d1.selectbox("Sales period", PERIODS, key="set_period")
        low_limit = d2.number_input("Low-stock limit (units)", min_value=0, value=3, step=1, key="set_low_stock")

    with st.spinner("Loading dashboard..."):
        products = load_products()
        sales = active_sales(get_data("sales"))
    if period != "All time":
        days = {"Today": 0, "Last 7 days": 6, "Last 30 days": 29}[period]
        start = today_pk() - timedelta(days=days)
        sales = [s for s in sales if (parse_date(s.get("sale_date")) or date.min) >= start]

    stock = sum(max(int(num(p.get("quantity"))), 0) for p in products)
    if admin:
        total = sum(num(s.get("total")) for s in sales)
        pending = sum(max(num(s.get("total")) - num(s.get("paid_amount")), 0) for s in sales)
        cards([("📦", "Total Products", len(products), "#1f6feb"), ("🧮", "Stock Units", stock, "#7c3aed"),
               ("💰", f"Sales ({period})", pkr(total), "#12b76a"), ("⏳", "Pending Balances", pkr(pending), "#f79009"),
               ("🧾", "Invoices", len(sales), "#0ea5e9")])
    else:
        mine = [s for s in sales if s.get("sold_by") == current_username()]
        cards([("📦", "Total Products", len(products), "#1f6feb"), ("🧮", "Stock Units", stock, "#7c3aed"),
               ("🧾", f"My Invoices ({period})", len(mine), "#0ea5e9"),
               ("💰", "My Sales", pkr(sum(num(s.get("total")) for s in mine)), "#12b76a")])

    stock_totals_section(products, admin)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"### ⚠️ Low Stock (≤ {int(low_limit)})")
        low = [p for p in products if int(num(p.get("quantity"))) <= int(low_limit)]
        if low:
            show_table(pd.DataFrame([{"Product": p.get("name"), "Model": p.get("model"),
                                      "Qty": int(num(p.get("quantity")))} for p in low]))
        else:
            empty_state("✅", "Stock looks good", "No products are below your low-stock limit.")
    with c2:
        st.markdown("### 🕒 Recent Sales")
        recent = sorted(sales, key=lambda x: x.get("id", 0), reverse=True)[:8]
        if recent:
            show_table(pd.DataFrame([{"Invoice": s.get("invoice_no"), "Customer": s.get("customer_name"),
                                      "Date": s.get("sale_date"), "Total": pkr(s.get("total")),
                                      "Balance": pkr(max(num(s.get("total")) - num(s.get("paid_amount")), 0))}
                                     for s in recent]))
        else:
            empty_state("🧾", "No sales yet", "Completed sales will appear here.")


# ==================================================================
# PRODUCTS & STOCK
# ==================================================================
def option_index(options, value):
    return options.index(value) if value in options else 0


# Product pages. Products are grouped by their existing "category" text. Nothing is changed in the database.
PRODUCT_GROUPS = {
    "Laptop": ("💻", "Laptops", "Laptop products, specifications and stock", "Laptop"),
    "Accessories": ("🎧", "Accessories", "Accessories, parts and add-ons", "Accessories"),
    "Desktop": ("🖥️", "Desktop Computers", "Desktop computers and all-in-one PCs", "Desktop"),
    "Other": ("📦", "Other Products", "Products in any other category", "Other"),
    "All": ("🗂️", "All Products", "Every product in your inventory", "Laptop"),
}


# ---------- stock value (ADMIN ONLY: uses purchase prices) ----------
def pkr_exact(value):
    """Rs with no decimals for whole rupees, 2 decimals only when needed (so totals always add up on screen)."""
    try:
        v = round(float(value or 0), 2)
    except Exception:
        return "Rs 0"
    return f"Rs {v:,.0f}" if abs(v - round(v)) < 0.005 else f"Rs {v:,.2f}"


def stock_value(p, price_field="purchase_price"):
    """Available quantity x price. Sold units are already removed from 'quantity', so they are never included."""
    return max(int(num(p.get("quantity"))), 0) * num(p.get(price_field))


def stock_summary(products):
    names = ("Laptop", "Accessories", "Desktop", "Other")
    groups = {g: {"products": 0, "in_stock": 0, "units": 0, "value": 0.0, "selling": 0.0} for g in names}
    for p in products:
        e = groups[category_group(p.get("category"))]
        q = max(int(num(p.get("quantity"))), 0)
        e["products"] += 1
        e["in_stock"] += 1 if q > 0 else 0
        e["units"] += q
        e["value"] += stock_value(p)
        e["selling"] += stock_value(p, "selling_price")
    total = {k: sum(groups[g][k] for g in names) for k in ("products", "in_stock", "units", "value", "selling")}
    for e in list(groups.values()) + [total]:
        e["value"] = round(e["value"], 2)
        e["selling"] = round(e["selling"], 2)
    return groups, total


def restock_calc(cur_qty, old_price, add_qty, unit_cost, weighted):
    """New quantity and purchase price after adding stock (weighted average uses only units really in stock)."""
    base = max(int(cur_qty), 0)
    new_qty = int(cur_qty) + int(add_qty)
    if not weighted:
        new_price = old_price
    elif base <= 0:
        new_price = unit_cost
    else:
        new_price = round((base * old_price + add_qty * unit_cost) / (base + add_qty), 4)
    return new_qty, new_price


def add_stock(pid, add_qty, unit_cost, weighted):
    """Adds purchased units to an existing product (same product ID, no duplicate). Admin only."""
    require_admin()
    if int(add_qty) <= 0 or unit_cost < 0:
        raise ValueError("Quantity must be at least 1 and the price cannot be negative.")
    for _ in range(3):
        rows = supabase.table("products").select("id,quantity,purchase_price").eq("id", pid).limit(1).execute().data
        if not rows:
            raise ValueError("Product not found. It may have been deleted.")
        cur, old_pp = int(num(rows[0].get("quantity"))), num(rows[0].get("purchase_price"))
        new_qty, new_pp = restock_calc(cur, old_pp, int(add_qty), unit_cost, weighted)
        upd = {"quantity": new_qty}
        if new_pp != old_pp:
            upd["purchase_price"] = new_pp
        done = supabase.table("products").update(upd).eq("id", pid).eq("quantity", cur).execute().data
        if done:
            return {"old_qty": cur, "new_qty": new_qty, "old_pp": old_pp, "new_pp": new_pp}
    raise ValueError("Stock changed while saving. Please try again.")


def stock_category_table(products, admin):
    """Products and available quantity per category plus a grand total. Purchase value is shown to Admin only."""
    groups, total = stock_summary(products)

    def line(name, e):
        row = {"Category": name, "Products": e["products"], "Available Qty": e["units"]}
        if admin:
            row["Total Purchase Value"] = pkr_exact(e["value"])
        return row

    show_table(pd.DataFrame([line(PRODUCT_GROUPS[g][1], e) for g, e in groups.items()] + [line("GRAND TOTAL", total)]))
    return groups, total


def stock_investment_section(products):
    try:
        require_admin()  # backend check: staff can never reach purchase values
    except PermissionError:
        return
    groups, total = stock_summary(products)
    st.markdown("### 💼 Stock Investment (Admin only)")
    cards([("💰", "Total Stock Value (purchase cost)", pkr_exact(total["value"]), "#12b76a")])
    negative = [p for p in products if int(num(p.get("quantity"))) < 0]
    if negative:
        st.warning(f"{len(negative)} product(s) have negative stock and are counted as 0. "
                   "Please correct their quantity in Edit / Delete.")
    st.caption("Total Value = available quantity × purchase price, summed over all products. Units already sold are never included.")
    with st.expander("📋 Stock value of every product"):
        detail = sorted(
            [{"Product": p.get("name"), "Model": p.get("model"), "Category": PRODUCT_GROUPS[category_group(p.get("category"))][1],
              "Available Qty": max(int(num(p.get("quantity"))), 0), "Purchase Price": pkr_exact(num(p.get("purchase_price"))),
              "Total Value": pkr_exact(stock_value(p)), "_v": stock_value(p)} for p in products], key=lambda r: -r["_v"])
        if detail:
            show_table(pd.DataFrame([{k: v for k, v in r.items() if k != "_v"} for r in detail]))
            calc = round(sum(r["_v"] for r in detail), 2)
            st.caption(("✅ " if abs(calc - total["value"]) < 0.01 else "❌ ") + f"Sum of all product values = {pkr_exact(calc)} "
                       f"(grand total = {pkr_exact(total['value'])})")
        else:
            st.caption("No products yet.")


def stock_totals_section(products, admin):
    if admin:
        try:
            require_admin()
        except PermissionError:
            admin = False  # never show values unless Admin is confirmed in the database
    st.markdown("### 📦 Stock Count & Totals")
    groups, _ = stock_summary(products)
    cards([(PRODUCT_GROUPS[g][0], PRODUCT_GROUPS[g][1], f"{e['products']} product{'' if e['products'] == 1 else 's'} · {e['units']:,} unit{'' if e['units'] == 1 else 's'}", "#1f6feb")
           for g, e in groups.items()])
    stock_category_table(products, admin)
    if admin:
        stock_investment_section(products)


def category_group(category):
    """Maps any stored category text to one page. Every product lands on exactly one page."""
    t = str(category or "").strip().lower()
    if "accessor" in t:
        return "Accessories"
    if "laptop" in t or "notebook" in t or "macbook" in t:
        return "Laptop"
    if "desktop" in t or "computer" in t or "all in one" in t or "all-in-one" in t or "pc" in t.replace("-", " ").split():
        return "Desktop"
    return "Other"


def inventory_view(products, admin, slug="All", empty_title="No products yet"):
    if not products:
        empty_state("📦", empty_title, "Products added by the Owner will appear here.")
        return
    search = st.text_input("🔍 Search (name, model, processor, serial)", key=f"flt_prod_search_{slug}")
    rows = []
    for p in products:
        text = " ".join(str(p.get(k, "")) for k in ("name", "model", "processor", "serial_number", "ram", "storage")).lower()
        if search.strip() and search.strip().lower() not in text:
            continue
        row = {"ID": p.get("id"), "Product": p.get("name"), "Category": p.get("category"), "Model": p.get("model"),
               "Processor": p.get("processor"), "RAM": p.get("ram"), "Storage": p.get("storage"),
               "Graphics": p.get("graphics"), "Display": p.get("display_size"), "Condition": p.get("condition_text"),
               "Serial No": p.get("serial_number")}
        if admin:
            row["Purchase Price"] = num(p.get("purchase_price"))
        row["Selling Price"] = num(p.get("selling_price"))
        row["Qty"] = int(num(p.get("quantity")))
        if admin:
            row["Stock Value (Cost)"] = round(stock_value(p), 2)
        row["Warranty Days"] = int(num(p.get("warranty_days")))
        row["Warranty Terms"] = p.get("warranty_terms")
        rows.append(row)
    df = pd.DataFrame(rows).dropna(axis=1, how="all") if rows else pd.DataFrame()
    if df.empty:
        empty_state("🔍", "No match", "No product matches your search.")
    else:
        show_table(df)
        if admin and "Stock Value (Cost)" in df.columns:
            st.markdown(f"**Total stock value of the products shown (cost): {pkr_exact(df['Stock Value (Cost)'].sum())}** "
                        f"| Units: {int(df['Qty'].clip(lower=0).sum()):,}")


def product_form_fields(prefix, p=None, default_cat=None):
    p = p or {}
    c1, c2, c3 = st.columns(3)
    name = c1.text_input("Product Name", value=p.get("name") or "", key=f"{prefix}_name")
    cats = CATEGORIES + ([p["category"]] if p.get("category") and p["category"] not in CATEGORIES else [])
    category = c2.selectbox("Category", cats, index=option_index(cats, p.get("category") or default_cat), key=f"{prefix}_cat")
    model = c3.text_input("Model", value=p.get("model") or "", key=f"{prefix}_model")
    c4, c5, c6 = st.columns(3)
    processor = c4.text_input("Processor", value=p.get("processor") or "", key=f"{prefix}_cpu")
    ram = c5.text_input("RAM", value=p.get("ram") or "", key=f"{prefix}_ram")
    storage = c6.text_input("Storage", value=p.get("storage") or "", key=f"{prefix}_sto")
    c7, c8, c9 = st.columns(3)
    graphics = c7.text_input("Graphics", value=p.get("graphics") or "", key=f"{prefix}_gpu")
    display = c8.text_input("Display Size", value=p.get("display_size") or "", key=f"{prefix}_disp")
    conds = CONDITIONS + ([p["condition_text"]] if p.get("condition_text") and p["condition_text"] not in CONDITIONS else [])
    condition = c9.selectbox("Condition", conds, index=option_index(conds, p.get("condition_text")), key=f"{prefix}_cond")
    serial = st.text_input("Serial Number", value=p.get("serial_number") or "", key=f"{prefix}_serial")
    c10, c11, c12, c13 = st.columns(4)
    purchase = c10.number_input("Purchase Price (Rs)", min_value=0.0, step=500.0, value=num(p.get("purchase_price")), key=f"{prefix}_pp")
    selling = c11.number_input("Selling Price (Rs)", min_value=0.0, step=500.0, value=num(p.get("selling_price")), key=f"{prefix}_sp")
    qty = c12.number_input("Quantity", min_value=0, step=1, value=int(num(p.get("quantity"))), key=f"{prefix}_qty")
    warranty = c13.number_input("Warranty Days", min_value=0, step=1, value=int(num(p.get("warranty_days"))), key=f"{prefix}_wd")
    terms = st.text_area("Warranty Terms", value=p.get("warranty_terms") or "", key=f"{prefix}_wt")
    base = {"name": name.strip(), "category": category, "model": model.strip(), "processor": processor.strip(),
            "ram": ram.strip(), "storage": storage.strip(), "condition_text": condition, "serial_number": serial.strip(),
            "purchase_price": purchase, "selling_price": selling, "quantity": int(qty), "warranty_days": int(warranty)}
    extras = {"graphics": graphics.strip(), "display_size": display.strip(), "warranty_terms": terms.strip()}
    return base, extras


def validate_product(base, products, own_id=None):
    if not base["name"]:
        return "Product name is required."
    if base["selling_price"] < base["purchase_price"]:
        return "Selling price is lower than purchase price. Please check the prices."
    sn = base["serial_number"].lower()
    if sn and any(str(p.get("serial_number", "")).strip().lower() == sn and p["id"] != own_id for p in products):
        return "Another product already uses this serial number."
    return None


def add_product_tab(products, group="All"):
    with st.form(f"add_product_{group}", clear_on_submit=True):
        st.markdown("### ➕ Add New Product")
        base, extras = product_form_fields(f"add_{group}", None, PRODUCT_GROUPS[group][3])
        submit = st.form_submit_button("💾 Save Product", type="primary")
    if submit:
        try:
            require_admin()
            err = validate_product(base, products)
            if err:
                st.error(err)
                return
            data, skipped = with_optional("products", base, extras)
            supabase.table("products").insert(data).execute()
            msg = f"Product saved successfully. It appears under {PRODUCT_GROUPS[category_group(base['category'])][1]}."
            if skipped:
                msg += f" (Not saved because columns are missing in Supabase: {', '.join(skipped)} — see the SQL migration.)"
            flash("success", msg)
            st.rerun()
        except PermissionError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Save failed: {e}")


def add_stock_tab(products, group="All"):
    if not products:
        empty_state("📥", "No products on this page", "Add a product first, then add stock to it here.")
        return
    ids = [p["id"] for p in products]
    labels = {p["id"]: f'#{p["id"]} - {p.get("name")} {p.get("model") or ""} (Stock {int(num(p.get("quantity")))})' for p in products}
    pid = st.selectbox("Select product", ids, format_func=lambda i: labels[i], key=f"stk_pid_{group}")
    p = next(x for x in products if x["id"] == pid)
    cur_q, cur_pp = int(num(p.get("quantity"))), num(p.get("purchase_price"))
    cards([("🧮", "Current Stock", cur_q, "#7c3aed"), ("💵", "Purchase Price / Unit", pkr_exact(cur_pp), "#1f6feb"),
           ("💰", "Current Stock Value", pkr_exact(stock_value(p)), "#12b76a")])
    c1, c2 = st.columns(2)
    add_qty = c1.number_input("Quantity to add", min_value=1, value=1, step=1, key=f"stk_q_{group}_{pid}")
    unit_cost = c2.number_input("Purchase price per unit for this purchase (Rs)", min_value=0.0, value=cur_pp, step=500.0,
                                key=f"stk_c_{group}_{pid}")
    mode = st.radio("Purchase price after adding", ["Weighted average of old and new stock (recommended)", "Keep current purchase price"],
                    key=f"stk_m_{group}_{pid}")
    weighted = mode.startswith("Weighted")
    new_q, new_pp = restock_calc(cur_q, cur_pp, int(add_qty), float(unit_cost), weighted)
    new_val = max(new_q, 0) * new_pp
    cards([("🧮", "New Stock", new_q, "#7c3aed"), ("💵", "New Purchase Price / Unit", pkr_exact(new_pp), "#1f6feb"),
           ("💰", "New Stock Value", pkr_exact(new_val), "#12b76a"), ("➕", "Value Added", pkr_exact(new_val - stock_value(p)), "#0ea5e9")])
    st.caption("This updates the same product (no duplicate is created) and past sales are not changed. "
               "To record the money you paid, add an expense under Income & Expenses (Laptop / Accessories Purchasing).")
    ok = st.checkbox("I confirm this stock was purchased and should be added", key=f"stk_ok_{group}_{pid}")
    if st.button("📥 Add Stock", type="primary", disabled=not ok, key=f"stk_b_{group}_{pid}"):
        fp = (pid, int(add_qty), round(float(unit_cost), 2), weighted)
        last = st.session_state.get("stock_last_fp")
        if last and last[0] == fp and (datetime.now() - last[1]).total_seconds() < 60:
            st.error("This same stock addition was saved a moment ago. Blocked to avoid adding it twice.")
            return
        try:
            res = add_stock(pid, int(add_qty), float(unit_cost), weighted)
            st.session_state["stock_last_fp"] = (fp, datetime.now())
            flash("success", f"Added {int(add_qty)} unit(s) to {p.get('name')}. Stock is now {res['new_qty']}, "
                             f"purchase price {pkr_exact(res['new_pp'])}, stock value {pkr_exact(max(res['new_qty'], 0) * res['new_pp'])}.")
            st.rerun()
        except PermissionError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Could not add stock: {e}")


def edit_delete_tab(products, all_products, group="All"):
    if not products:
        empty_state("✏️", "Nothing to edit", "There are no products on this page yet.")
        return
    ids = [p["id"] for p in products]
    labels = {p["id"]: f'#{p["id"]} - {p.get("name")} {p.get("model") or ""} (Stock {int(num(p.get("quantity")))})' for p in products}
    pid = st.selectbox("Select product", ids, format_func=lambda i: labels[i], key=f"edit_pid_{group}")
    p = next(x for x in products if x["id"] == pid)
    st.caption(f"Current stock: {int(num(p.get('quantity')))} | Purchase price: {pkr_exact(num(p.get('purchase_price')))} | "
               f"Stock value: {pkr_exact(stock_value(p))}. Saving new quantity or price recalculates all totals.")

    with st.form(f"edit_form_{pid}"):
        st.markdown("### ✏️ Edit Product")
        base, extras = product_form_fields(f"ed{pid}", p)
        save = st.form_submit_button("💾 Save Changes", type="primary")
    if save:
        try:
            require_admin()
            err = validate_product(base, all_products, own_id=pid)
            if err:
                st.error(err)
            else:
                data, skipped = with_optional("products", base, extras)
                supabase.table("products").update(data).eq("id", pid).execute()
                msg = "Product updated."
                if category_group(base["category"]) != category_group(p.get("category")):
                    msg += f" It now appears under {PRODUCT_GROUPS[category_group(base['category'])][1]}."
                if skipped:
                    msg += f" (Columns missing in Supabase, not saved: {', '.join(skipped)}.)"
                flash("success", msg)
                st.rerun()
        except PermissionError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Update failed: {e}")

    st.markdown("### 🗑️ Delete Product")
    linked = supabase.table("sale_items").select("id").eq("product_id", pid).limit(1).execute().data
    st.download_button("⬇️ Download this product (backup CSV)", pd.DataFrame([p]).to_csv(index=False),
                       file_name=f"product_{pid}.csv", mime="text/csv", key=f"bk_{pid}")
    if linked:
        st.warning("This product is linked to existing sales, so it cannot be deleted (this protects your sales records). "
                   "Safe option: retire it by setting its stock to 0.")
        ok = st.checkbox("I want to retire this product (set stock to 0)", key=f"ret_c_{pid}")
        if st.button("Retire Product", disabled=not ok, key=f"ret_b_{pid}"):
            try:
                require_admin()
                supabase.table("products").update({"quantity": 0}).eq("id", pid).execute()
                flash("success", "Product retired (stock set to 0). Sales records are untouched.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed: {e}")
    else:
        st.warning(f"You are about to permanently delete: **{p.get('name')}**. This cannot be undone.")
        ok = st.checkbox("Yes, I want to delete this product", key=f"del_c_{pid}")
        if st.button("Delete Product", disabled=not ok, key=f"del_b_{pid}"):
            try:
                require_admin()
                supabase.table("products").delete().eq("id", pid).execute()
                flash("success", "Product deleted.")
                st.rerun()
            except Exception as e:
                st.error(f"Delete failed: {e}")


def product_cards(products, admin, group, all_products):
    low_limit = int(st.session_state.get("set_low_stock", 3))
    qty = [int(num(p.get("quantity"))) for p in products]
    items = [("📦", "Products", len(products), "#1f6feb"), ("🧮", "Stock Units", sum(qty), "#7c3aed"),
             ("⚠️", f"Low Stock (1 to {low_limit})", sum(1 for q in qty if 0 < q <= low_limit), "#f79009"),
             ("🚫", "Out of Stock", sum(1 for q in qty if q <= 0), "#d92d20")]
    if admin:
        items.append(("💰", "Stock Value (cost)", pkr_exact(sum(stock_value(p) for p in products)), "#12b76a"))
        items.append(("🏷️", "Stock Value (selling)", pkr_exact(sum(stock_value(p, "selling_price") for p in products)), "#0ea5e9"))
    cards(items)
    if group == "All":
        counts = {g: sum(1 for p in all_products if category_group(p.get("category")) == g) for g in ("Laptop", "Accessories", "Desktop", "Other")}
        cards([(PRODUCT_GROUPS[g][0], PRODUCT_GROUPS[g][1], counts[g], "#1f6feb") for g in counts])
        stock_category_table(all_products, admin)
    if group == "Other":
        found = sorted({str(p.get("category") or "(no category)") for p in products})
        if found:
            st.caption("Categories shown on this page: " + ", ".join(found))


def products_page(group="All"):
    icon, title, sub, _ = PRODUCT_GROUPS[group]
    page_header(icon, title, sub)
    admin = is_admin()
    all_products = load_products()
    products = all_products if group == "All" else [p for p in all_products if category_group(p.get("category")) == group]
    product_cards(products, admin, group, all_products)
    empty_title = f"No products in {title} yet"
    if not admin:
        inventory_view(products, False, group, empty_title)
        return
    t1, t2, t3, t4 = st.tabs(["📋 Inventory", "➕ Add Product", "📥 Add Stock", "✏️ Edit / Delete"])
    with t1:
        inventory_view(products, True, group, empty_title)
    with t2:
        add_product_tab(all_products, group)
    with t3:
        add_stock_tab(products, group)
    with t4:
        edit_delete_tab(products, all_products, group)


# ==================================================================
# NEW SALE / BILLING
# ==================================================================
def build_receipt(r):
    return "\n".join([
        "LAPTOP HOUSE BUNER", "=" * 40, f"Invoice : {r['invoice']}", f"Date    : {r['date']}",
        f"Customer: {r['customer']}", f"Phone   : {r['phone']}", f"Sold By : {r['sold_by']}", "-" * 40,
        f"Product : {r['product']}", f"Specs   : {r['specs']}", f"Qty     : {r['qty']}",
        f"Price   : {pkr(r['price'])}", f"Subtotal: {pkr(r['subtotal'])}", f"Discount: {pkr(r['discount'])}",
        f"TOTAL   : {pkr(r['total'])}", f"Paid    : {pkr(r['paid'])} ({r['method']})",
        f"Balance : {pkr(r['balance'])}", f"Warranty: {r['warranty_days']} days (until {r['warranty_expiry']})",
        "-" * 40, f"Notes   : {r['notes']}", "", "Thank you for shopping with us!"])


def billing_page():
    page_header("🧾", "New Sale / Billing", "Create a customer bill")
    admin = is_admin()

    last = st.session_state.get("last_receipt")
    if last:
        st.markdown(
            '<div class="ok-wrap"><svg viewBox="0 0 52 52"><circle class="ok-c" cx="26" cy="26" r="24"/>'
            '<path class="ok-p" d="M14 27l8 8 16-18"/></svg><div><div class="t1">Sale completed!</div>'
            f'<div class="t2">Invoice number: <b>{last["invoice"]}</b></div></div></div>', unsafe_allow_html=True)
        st.code(build_receipt(last))
        st.download_button("⬇️ Download Invoice (text file)", build_receipt(last),
                           file_name=f"{last['invoice']}.txt", mime="text/plain")
        if st.button("➕ Start another sale", type="primary"):
            st.session_state.last_receipt = None
            st.rerun()
        return

    products = [p for p in load_products() if int(num(p.get("quantity"))) > 0]
    if not products:
        empty_state("📦", "No stock available", "Add products or stock first in the Laptops, Accessories, Desktop or Other Products pages.")
        return

    nonce = st.session_state.setdefault("sale_nonce", 0)
    by_id = {p["id"]: p for p in products}
    ids = list(by_id)
    labels = {p["id"]: f'{p.get("name")} | {p.get("model") or "-"} | {p.get("ram") or "-"}/{p.get("storage") or "-"} '
                       f'| {pkr(p.get("selling_price"))} | Stock {int(num(p.get("quantity")))}' for p in products}

    st.markdown("#### 👤 Customer")
    c1, c2 = st.columns(2)
    customer = c1.text_input("Customer Name", key=f"cust_{nonce}")
    phone = c2.text_input("Customer Phone", key=f"phone_{nonce}")

    st.markdown("#### 💻 Product")
    pid = st.selectbox("Select Product", ids, format_func=lambda i: labels[i], key=f"prod_{nonce}")
    product = by_id[pid]
    stock = int(num(product.get("quantity")))
    st.info(f"**Specifications:** {spec_text(product) or 'Not provided'}  \n"
            f"**Serial No:** {product.get('serial_number') or '-'}  \n"
            f"**Warranty:** {int(num(product.get('warranty_days')))} days")

    q1, q2, q3 = st.columns(3)
    quantity = q1.number_input("Quantity", min_value=1, max_value=stock, value=1, step=1, key=f"qty_{nonce}_{pid}")
    list_price = num(product.get("selling_price"))
    if admin:
        price = q2.number_input("Selling Price (Rs)", min_value=0.0, value=list_price, step=500.0, key=f"price_{nonce}_{pid}")
    else:
        price = list_price
        q2.number_input("Selling Price (Rs)", value=list_price, disabled=True, key=f"price_ro_{nonce}_{pid}")
    subtotal = price * quantity
    discount = q3.number_input("Discount (Rs)", min_value=0.0, max_value=float(subtotal), value=0.0, step=100.0,
                               key=f"disc_{nonce}_{pid}_{quantity}")
    total = subtotal - discount

    st.markdown("#### 💳 Payment")
    p1, p2 = st.columns(2)
    paid = p1.number_input("Paid Amount (Rs)", min_value=0.0, max_value=float(total), value=float(total), step=500.0,
                           key=f"paid_{nonce}_{int(total * 100)}")
    method = p2.selectbox("Payment Method", PAYMENT_METHODS, key=f"method_{nonce}")
    notes = st.text_area("Notes", key=f"notes_{nonce}")
    balance = total - paid
    cards([("🧮", "Subtotal", pkr(subtotal), "#1f6feb"), ("💰", "Total Amount", pkr(total), "#12b76a"),
           ("⏳", "Remaining Balance", pkr(balance), "#f79009")])
    confirm = st.checkbox("✅ I have checked the customer, product and amount", key=f"confirm_{nonce}")

    if not st.button("💾 Complete Sale", type="primary", disabled=not confirm):
        return
    if not customer.strip() or not phone.strip():
        st.error("Customer name and phone are required.")
        return
    try:
        require_login()
    except Exception as e:
        st.error(str(e))
        return

    fp = (customer.strip().lower(), phone.strip(), pid, int(quantity), round(total, 2))
    last_fp = st.session_state.get("last_fp")
    if last_fp and last_fp[0] == fp and (datetime.now() - last_fp[1]).total_seconds() < 60:
        st.error("This looks like a duplicate of the sale you just saved. Sale blocked.")
        return

    with st.spinner("Saving sale..."):
        fresh = supabase.table("products").select("*").eq("id", pid).limit(1).execute().data
        if not fresh:
            st.error("This product no longer exists.")
            return
        fresh = fresh[0]
        fresh_qty = int(num(fresh.get("quantity")))
        if int(quantity) > fresh_qty:
            st.error(f"Not enough stock. Only {fresh_qty} unit(s) available.")
            return

        unit_price = price if admin else num(fresh.get("selling_price"))
        sub = unit_price * int(quantity)
        disc = min(discount, sub)
        final_total = sub - disc
        paid_final = min(paid, final_total)
        sale_date = today_pk()
        warranty_days = int(num(fresh.get("warranty_days")))
        expiry = sale_date + timedelta(days=warranty_days)
        invoice = "LHB-" + sale_date.strftime("%Y%m%d") + "-" + secrets.token_hex(4).upper()

        reserved, sale_id, item_saved, pay_saved = False, None, False, False
        try:
            upd = supabase.table("products").update({"quantity": fresh_qty - int(quantity)}).eq("id", pid).eq("quantity", fresh_qty).execute().data
            if not upd:
                st.error("Stock changed while saving. Please try again.")
                return
            reserved = True
            base_sale = {"invoice_no": invoice, "customer_name": customer.strip(), "customer_phone": phone.strip(),
                         "sale_date": sale_date.isoformat(), "sold_by": current_username(), "total": final_total,
                         "paid_amount": paid_final, "discount": disc}
            sale_data, _ = with_optional("sales", base_sale, {"notes": notes.strip(), "payment_method": method, "status": "active"})
            sale_id = supabase.table("sales").insert(sale_data).execute().data[0]["id"]
            supabase.table("sale_items").insert({
                "sale_id": sale_id, "product_id": pid, "product_name": fresh.get("name"), "specs": spec_text(fresh),
                "quantity": int(quantity), "selling_price": unit_price, "purchase_price": num(fresh.get("purchase_price")),
                "warranty_days": warranty_days, "warranty_expiry": expiry.isoformat()}).execute()
            item_saved = True
            if paid_final > 0:
                note = f"Initial payment ({method})" + (f" - {notes.strip()}" if notes.strip() else "")
                supabase.table("payments").insert({"sale_id": sale_id, "amount": paid_final,
                                                   "received_by": current_username(), "note": note}).execute()
                pay_saved = True
        except Exception as e:
            try:
                if pay_saved:
                    supabase.table("payments").delete().eq("sale_id", sale_id).execute()
                if item_saved:
                    supabase.table("sale_items").delete().eq("sale_id", sale_id).execute()
                if sale_id:
                    supabase.table("sales").delete().eq("id", sale_id).execute()
                if reserved:
                    supabase.table("products").update({"quantity": fresh_qty}).eq("id", pid).execute()
            except Exception:
                pass
            st.error(f"Sale failed and was cancelled: {e}")
            return

    st.session_state.last_fp = (fp, datetime.now())
    st.session_state.sale_nonce = nonce + 1
    st.session_state.last_receipt = {
        "invoice": invoice, "date": sale_date.isoformat(), "customer": customer.strip(), "phone": phone.strip(),
        "sold_by": current_username(), "product": fresh.get("name"), "specs": spec_text(fresh) or "-",
        "qty": int(quantity), "price": unit_price, "subtotal": sub, "discount": disc, "total": final_total,
        "paid": paid_final, "method": method, "balance": final_total - paid_final, "warranty_days": warranty_days,
        "warranty_expiry": expiry.isoformat(), "notes": notes.strip() or "-"}
    st.toast("Sale completed!", icon="✅")
    st.rerun()


# ==================================================================
# SALES HISTORY
# ==================================================================
def build_history(sales, items, admin, has_status):
    by_sale = {}
    for it in items:
        by_sale.setdefault(it.get("sale_id"), []).append(it)
    rows = []
    for s in sorted(sales, key=lambda x: x.get("id", 0), reverse=True):
        cancelled = sale_status(s) == "cancelled"
        total, paid, disc = num(s.get("total")), num(s.get("paid_amount")), num(s.get("discount"))
        sitems = by_sale.get(s.get("id"), [])
        subtotal = sum(num(i.get("selling_price")) * num(i.get("quantity")) for i in sitems)
        base = {"Invoice No": s.get("invoice_no"), "Customer": s.get("customer_name"), "Phone": s.get("customer_phone"),
                "Date": s.get("sale_date"), "Sold By": s.get("sold_by")}
        if has_status:
            base["Status"] = "Cancelled" if cancelled else "Active"
        for i in (sitems or [{}]):
            qty, sp = num(i.get("quantity")), num(i.get("selling_price"))
            row = dict(base)
            row.update({"Product": i.get("product_name", ""), "Specs": i.get("specs", ""), "Qty": int(qty),
                        "Selling Price": sp, "Discount": disc, "Total": total, "Paid": paid,
                        "Remaining": 0 if cancelled else max(total - paid, 0)})
            if admin:
                pp = num(i.get("purchase_price"))
                share = (sp * qty / subtotal) if subtotal else 0
                row["Purchase Price"] = pp
                row["Profit"] = 0 if (cancelled or not i) else round(sp * qty - pp * qty - disc * share, 2)
            rows.append(row)
    return pd.DataFrame(rows)


def receive_payment_tab(sales):
    unpaid = sorted([s for s in active_sales(sales) if num(s.get("total")) - num(s.get("paid_amount")) > 0.5],
                    key=lambda x: x.get("id", 0), reverse=True)
    if not unpaid:
        empty_state("🎉", "All paid", "All customers have paid in full.")
        return
    ids = [s["id"] for s in unpaid]
    labels = {s["id"]: f'{s.get("invoice_no")} | {s.get("customer_name")} | Balance {pkr(num(s.get("total")) - num(s.get("paid_amount")))}' for s in unpaid}
    sid = st.selectbox("Select invoice", ids, format_func=lambda i: labels[i], key="rcv_sid")
    sale = next(s for s in unpaid if s["id"] == sid)
    balance = num(sale.get("total")) - num(sale.get("paid_amount"))
    r1, r2 = st.columns(2)
    amount = r1.number_input("Amount received (Rs)", min_value=0.0, max_value=float(balance), value=float(balance),
                             step=500.0, key=f"rcv_{sid}")
    method = r2.selectbox("Payment Method", PAYMENT_METHODS, key=f"rcv_m_{sid}")
    ok = st.checkbox("Confirm this payment was received", key=f"rcv_c_{sid}")
    if st.button("💵 Save Payment", disabled=not ok):
        if amount <= 0:
            st.error("Enter an amount greater than zero.")
            return
        try:
            require_login()
            latest = supabase.table("sales").select("*").eq("id", sid).limit(1).execute().data[0]
            if sale_status(latest) == "cancelled":
                st.error("This sale is cancelled.")
                return
            new_paid = num(latest.get("paid_amount")) + amount
            if new_paid > num(latest.get("total")) + 0.5:
                st.error("Payment is more than the remaining balance.")
                return
            supabase.table("sales").update({"paid_amount": new_paid}).eq("id", sid).execute()
            supabase.table("payments").insert({"sale_id": sid, "amount": amount, "received_by": current_username(),
                                               "note": f"Balance payment ({method})"}).execute()
            flash("success", "Payment saved.")
            st.rerun()
        except Exception as e:
            st.error(f"Payment failed: {e}")


def manage_sales_tab(sales, items):
    if not sales:
        empty_state("🧾", "No sales", "Nothing to manage yet.")
        return
    sales = sorted(sales, key=lambda x: x.get("id", 0), reverse=True)
    ids = [s["id"] for s in sales]
    labels = {s["id"]: f'{s.get("invoice_no")} | {s.get("customer_name")} | {pkr(s.get("total"))}'
                       f'{" | CANCELLED" if sale_status(s) == "cancelled" else ""}' for s in sales}
    sid = st.selectbox("Select invoice", ids, format_func=lambda i: labels[i], key="mng_sid")
    sale = next(s for s in sales if s["id"] == sid)
    sitems = [i for i in items if i.get("sale_id") == sid]
    cancelled = sale_status(sale) == "cancelled"
    if cancelled:
        st.info("This sale is cancelled. Stock was returned. It cannot be edited.")

    st.markdown("### ✏️ Edit Sale")
    with st.form(f"edit_sale_{sid}"):
        e1, e2 = st.columns(2)
        cust = e1.text_input("Customer Name", value=sale.get("customer_name") or "", key=f"es_c_{sid}")
        ph = e2.text_input("Customer Phone", value=sale.get("customer_phone") or "", key=f"es_p_{sid}")
        if len(sitems) == 1:
            it = sitems[0]
            e3, e4, e5 = st.columns(3)
            q = e3.number_input("Quantity", min_value=1, value=max(int(num(it.get("quantity"))), 1), step=1, key=f"es_q_{sid}")
            pr = e4.number_input("Selling Price (Rs)", min_value=0.0, value=num(it.get("selling_price")), step=500.0, key=f"es_pr_{sid}")
            di = e5.number_input("Discount (Rs)", min_value=0.0, value=num(sale.get("discount")), step=100.0, key=f"es_d_{sid}")
        else:
            st.caption("This invoice has no single item, so only customer details can be edited.")
            q, pr, di = 1, 0.0, 0.0
        nt = st.text_area("Notes", value=sale.get("notes") or "", key=f"es_n_{sid}") if col_exists("sales", "notes") else ""
        st.caption(f"Already paid: {pkr(sale.get('paid_amount'))}. Payments are changed only in 'Receive Payment'. "
                   "Changing quantity automatically adjusts stock.")
        go = st.form_submit_button("💾 Save Sale Changes", type="primary", disabled=cancelled)
    if go:
        if not cust.strip() or not ph.strip():
            st.error("Customer name and phone are required.")
        else:
            try:
                update_sale(sid, cust, ph, int(q), float(pr), float(di), nt)
                flash("success", "Sale updated and stock adjusted.")
                st.rerun()
            except Exception as e:
                st.error(f"Edit failed: {e}")

    st.markdown("### 🚫 Cancel Sale")
    if not col_exists("sales", "status"):
        st.warning("Cancelling needs the 'status' column. Run the SQL migration, then press 'Re-check database' in Admin Settings.")
    elif not cancelled:
        st.write("Cancelling returns the sold units to stock and keeps the invoice and payment history for your records. "
                 "The invoice is excluded from sales totals.")
        reason = st.text_input("Reason for cancelling", key=f"cx_r_{sid}")
        ok = st.checkbox("Yes, cancel this sale and return the stock", key=f"cx_c_{sid}")
        if st.button("Cancel This Sale", disabled=not (ok and reason.strip()), key=f"cx_b_{sid}"):
            try:
                missing = cancel_sale(sid, reason)
                flash("success", "Sale cancelled and stock restored." + (
                    f" Warning: {missing} item(s) could not be returned to stock (product deleted)." if missing else ""))
                st.rerun()
            except Exception as e:
                st.error(f"Cancel failed: {e}")

    with st.expander("🗑️ Permanently delete this invoice"):
        st.warning("Permanent. Items and payments of this invoice are deleted and stock is returned (if not already cancelled). "
                   "Download the backup first. Cancelling is usually the better choice.")
        pays = supabase.table("payments").select("*").eq("sale_id", sid).execute().data or []
        st.download_button("⬇️ Backup this invoice (ZIP)", zip_bytes({"sale": [sale], "sale_items": sitems, "payments": pays}),
                           file_name=f"backup_{sale.get('invoice_no')}.zip", mime="application/zip", key=f"dbk_{sid}")
        typed = st.text_input(f"Type the invoice number ({sale.get('invoice_no')}) to confirm", key=f"dl_t_{sid}")
        if st.button("Delete Invoice Permanently", disabled=typed.strip() != str(sale.get("invoice_no")), key=f"dl_b_{sid}"):
            try:
                missing = delete_sale_full(sid)
                flash("success", "Invoice deleted." + (f" Warning: {missing} item(s) not returned to stock." if missing else ""))
                st.rerun()
            except Exception as e:
                st.error(f"Delete failed: {e}")


def sales_history():
    page_header("📚", "Sales History", "Invoices, payments and balances")
    admin = is_admin()
    sales = get_data("sales")
    items = load_sale_items() if not admin else get_data("sale_items")
    has_status = col_exists("sales", "status")

    tabs = ["📋 History", "💵 Receive Payment"] + (["🛠️ Edit / Cancel / Delete"] if admin else [])
    t = st.tabs(tabs)
    with t[0]:
        if not sales:
            empty_state("🧾", "No sales yet", "Completed sales will appear here.")
        else:
            df = build_history(sales, items, admin, has_status)
            f1, f2, f3 = st.columns([3, 1, 1])
            search = f1.text_input("🔍 Search invoice, customer or phone", key="flt_hist_search")
            unpaid = f2.checkbox("Only unpaid", key="flt_hist_unpaid")
            hide_c = f3.checkbox("Hide cancelled", value=True, key="flt_hist_cancel") if has_status else False
            view = df
            if search.strip():
                s = search.strip().lower()
                view = view[view["Invoice No"].astype(str).str.lower().str.contains(s, na=False)
                            | view["Customer"].astype(str).str.lower().str.contains(s, na=False)
                            | view["Phone"].astype(str).str.lower().str.contains(s, na=False)]
            if unpaid:
                view = view[view["Remaining"] > 0]
            if hide_c:
                view = view[view["Status"] != "Cancelled"]
            if view.empty:
                empty_state("🔍", "No matching invoices", "Try a different search or filter.")
            else:
                show_table(view)
    with t[1]:
        receive_payment_tab(sales)
    if admin:
        with t[2]:
            manage_sales_tab(sales, items)


# ==================================================================
# REPORTS & PDF (ADMIN ONLY)
# ==================================================================
def reports():
    page_header("📊", "Reports & PDFs", "Business performance and downloadable reports")
    if not is_admin():
        st.error("Access denied. Reports are for the Owner/Admin only.")
        return
    products, all_sales, items = get_data("products"), get_data("sales"), get_data("sale_items")
    sales = active_sales(all_sales)
    t1, t2 = st.tabs(["📈 Summary", "📄 PDF Reports"])

    with t1:
        total = sum(num(s.get("total")) for s in sales)
        received = sum(num(s.get("paid_amount")) for s in sales)
        remaining = sum(max(num(s.get("total")) - num(s.get("paid_amount")), 0) for s in sales)
        profit = sum(profit_map(sales, items).values())
        cards([("📦", "Total Products", len(products), "#1f6feb"),
               ("🧮", "Total Stock Units", sum(max(int(num(p.get("quantity"))), 0) for p in products), "#7c3aed"),
               ("💼", "Stock Value (purchase cost)", pkr_exact(sum(stock_value(p) for p in products)), "#12b76a"),
               ("🧾", "Total Invoices", len(sales), "#0ea5e9"), ("💰", "Total Sales", pkr(total), "#12b76a"),
               ("💵", "Received Payments", pkr(received), "#16a34a"), ("⏳", "Remaining Balances", pkr(remaining), "#f79009"),
               ("📈", "Estimated Gross Profit", pkr(profit), "#db2777")])
        st.markdown("### 👥 Staff Sales Performance")
        pm = profit_map(sales, items)
        perf = {}
        for s in sales:
            r = perf.setdefault(s.get("sold_by") or "Unknown", {"Invoices": 0, "Sales": 0.0, "Received": 0.0, "Profit": 0.0})
            r["Invoices"] += 1
            r["Sales"] += num(s.get("total"))
            r["Received"] += num(s.get("paid_amount"))
            r["Profit"] += pm.get(s["id"], 0)
        if perf:
            show_table(pd.DataFrame([{"Staff": k, "Invoices": v["Invoices"], "Total Sales": pkr(v["Sales"]),
                                      "Received": pkr(v["Received"]), "Estimated Profit": pkr(v["Profit"])}
                                     for k, v in sorted(perf.items(), key=lambda kv: -kv[1]["Sales"])]))
        else:
            empty_state("👥", "No sales yet", "Staff performance will appear after the first sale.")
        st.markdown("### 💰 Customers With Remaining Balance")
        owing = [s for s in sales if num(s.get("total")) - num(s.get("paid_amount")) > 0.5]
        if owing:
            show_table(pd.DataFrame([{"Invoice": s.get("invoice_no"), "Customer": s.get("customer_name"),
                                      "Phone": s.get("customer_phone"), "Total": pkr(s.get("total")),
                                      "Paid": pkr(s.get("paid_amount")),
                                      "Remaining": pkr(num(s.get("total")) - num(s.get("paid_amount")))} for s in owing]))
        else:
            empty_state("🎉", "No pending balances", "Every customer has paid in full.")

    with t2:
        def make(key, fn, *args):
            try:
                with st.spinner("Creating PDF..."):
                    st.session_state[key] = fn(*args)
                st.toast("PDF is ready", icon="📄")
            except Exception as e:
                st.session_state.pop(key, None)
                st.error(f"Could not create PDF: {e}")

        st.markdown("### 📦 Inventory PDF")
        st.caption("Contains purchase prices and inventory values (Admin only).")
        if st.button("Generate Inventory PDF"):
            make("pdf_inv", inventory_pdf, products)
        if st.session_state.get("pdf_inv"):
            st.download_button("⬇️ Download Inventory PDF", st.session_state["pdf_inv"],
                               file_name=f"inventory_{today_pk().isoformat()}.pdf", mime="application/pdf")
        st.divider()
        st.markdown("### 🧾 Sales PDFs")
        rng = st.date_input("Select date range", value=(today_pk() - timedelta(days=29), today_pk()), key="flt_pdf_range")
        if isinstance(rng, (tuple, list)) and len(rng) == 2:
            d1, d2 = rng
            in_sales = [s for s in all_sales if in_range(s, d1, d2)]
            ids = {s["id"] for s in in_sales}
            in_items = [i for i in items if i.get("sale_id") in ids]
            a, b = st.columns(2)
            with a:
                if st.button("Generate Sold Products PDF"):
                    make("pdf_sales", sales_pdf, in_sales, in_items, d1, d2)
                if st.session_state.get("pdf_sales"):
                    st.download_button("⬇️ Download Sold Products PDF", st.session_state["pdf_sales"],
                                       file_name=f"sold_products_{d1}_{d2}.pdf", mime="application/pdf")
            with b:
                if st.button("Generate Sales Summary PDF"):
                    make("pdf_sum", summary_pdf, in_sales, in_items, d1, d2)
                if st.session_state.get("pdf_sum"):
                    st.download_button("⬇️ Download Sales Summary PDF", st.session_state["pdf_sum"],
                                       file_name=f"sales_summary_{d1}_{d2}.pdf", mime="application/pdf")
            st.caption("Press 'Generate' again after changing the date range to refresh the PDF.")
        else:
            st.info("Please select both a start date and an end date.")


# ==================================================================
# INCOME & EXPENSE MANAGEMENT (ADMIN ONLY)
# ==================================================================
INCOME_CATEGORIES = ["Laptop Sales Payments", "Accessories Sales", "Repairing Income",
                     "Software Installation Income", "Other Services Income", "Other Business Income"]
EXPENSE_CATEGORIES = ["Shop Rent", "Electricity Bill", "Internet Bill", "Staff Salaries", "Transportation / Fuel",
                      "Laptop Purchasing", "Accessories Purchasing", "Repairing / Maintenance",
                      "Marketing / Advertising", "Office Supplies", "Food / Tea", "Taxes / Government Fees",
                      "Other Expenses"]
# Buying stock is tracked separately: the cost of products actually SOLD (COGS) is what reduces profit.
INVENTORY_EXPENSE_CATEGORIES = ("Laptop Purchasing", "Accessories Purchasing")
FIN_METHODS = ["Cash", "Bank", "JazzCash", "EasyPaisa", "Other"]
FIN_PERIODS = ["Today", "Yesterday", "This Week", "This Month", "Last Month", "Custom Date Range", "All Time"]
ALL_TIME_START = date(2000, 1, 1)

FIN_CFG = {
    "income": {"table": "business_income", "title": "income_title", "date": "income_date", "party": "received_from",
               "cats": INCOME_CATEGORIES, "title_label": "Income Title", "party_label": "Received From",
               "ref_label": "Reference / Invoice Number"},
    "expense": {"table": "business_expenses", "title": "expense_title", "date": "expense_date", "party": "paid_to",
                "cats": EXPENSE_CATEGORIES, "title_label": "Expense Title", "party_label": "Paid To",
                "ref_label": "Receipt / Reference Number"},
}

FIN_SQL = """create table if not exists business_income (
  id bigint generated always as identity primary key,
  income_title text not null,
  category text not null,
  amount numeric(14,2) not null check (amount > 0),
  payment_method text not null default 'Cash'
    check (payment_method in ('Cash','Bank','JazzCash','EasyPaisa','Other')),
  income_date date not null default current_date,
  received_from text,
  description text,
  reference_no text,
  created_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_business_income_date on business_income (income_date);

create table if not exists business_expenses (
  id bigint generated always as identity primary key,
  expense_title text not null,
  category text not null,
  amount numeric(14,2) not null check (amount > 0),
  payment_method text not null default 'Cash'
    check (payment_method in ('Cash','Bank','JazzCash','EasyPaisa','Other')),
  expense_date date not null default current_date,
  paid_to text,
  description text,
  reference_no text,
  created_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_business_expenses_date on business_expenses (expense_date);

alter table business_income enable row level security;
alter table business_expenses enable row level security;

grant usage on schema public to service_role;
grant select, insert, update, delete on public.business_income to service_role;
grant select, insert, update, delete on public.business_expenses to service_role;
grant usage, select on all sequences in schema public to service_role;"""


# ---------------- backend: permissions + database writes ----------------
def fin_tables_ok():
    cache = st.session_state.setdefault("_cols", {})
    for t in ("business_income", "business_expenses"):
        if not cache.get(f"{t}.id"):
            cache.pop(f"{t}.id", None)  # never trust a cached "missing": re-check every time
    return col_exists("business_income", "id") and col_exists("business_expenses", "id")


def load_fin_data():
    require_admin()
    raw = {n: get_data(n) for n in ("products", "sales", "sale_items", "payments")}
    for key, table in (("income", "business_income"), ("expenses", "business_expenses")):
        raw[key] = get_data(table) if col_exists(table, "id") else []
    return raw


def fin_insert(kind, vals):
    require_admin()
    data = dict(vals)
    data["created_by"] = current_username()
    supabase.table(FIN_CFG[kind]["table"]).insert(data).execute()


def fin_update(kind, row_id, vals):
    require_admin()
    data = dict(vals)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    done = supabase.table(FIN_CFG[kind]["table"]).update(data).eq("id", row_id).execute().data
    if not done:
        raise ValueError("Record not found. It may have been deleted.")


def fin_delete(kind, row_id):
    require_admin()
    supabase.table(FIN_CFG[kind]["table"]).delete().eq("id", row_id).execute()


def fin_validate(kind, vals, ctx):
    cfg = FIN_CFG[kind]
    if not vals[cfg["title"]]:
        return f"{cfg['title_label']} is required."
    if vals["amount"] <= 0:
        return "Amount must be greater than zero."
    if vals["amount"] > 1_000_000_000:
        return "Amount is too large. Please check it."
    d = parse_date(vals[cfg["date"]])
    if d is None or d > today_pk():
        return "The date cannot be in the future."
    if kind == "income" and vals["reference_no"] and vals["reference_no"].strip().lower() in ctx["invoice_nos"]:
        return ("This reference is an existing invoice. Customer payments for billing invoices are included "
                "automatically (use Sales History → Receive Payment). Recording it here would count the money twice.")
    return None


def fin_is_duplicate(kind, vals):
    cfg = FIN_CFG[kind]
    fp = (kind, vals[cfg["title"]].lower(), round(vals["amount"], 2), vals[cfg["date"]], vals["category"])
    last = st.session_state.get("fin_last_fp")
    return bool(last and last[0] == fp and (datetime.now() - last[1]).total_seconds() < 60), fp


# ---------------- calculations ----------------
def method_from_note(note):
    text = str(note or "")
    for m in PAYMENT_METHODS:
        if f"({m})" in text:
            return {"Bank Transfer": "Bank", "Card": "Bank"}.get(m, m)
    return "Unspecified"


def payment_date(p, sale):
    v = p.get("created_at")
    if v:
        try:
            dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
            if dt.tzinfo:
                dt = dt.astimezone(timezone(timedelta(hours=5)))
            return dt.date()
        except Exception:
            d = parse_date(v)
            if d:
                return d
    return parse_date(sale.get("sale_date"))


def build_fin_context(raw):
    """Turns raw tables into one clean ledger. Each customer payment is counted exactly once."""
    sales = raw["sales"]
    active = active_sales(sales)
    sale_by_id = {s["id"]: s for s in sales}
    prod_by_id = {p["id"]: p for p in raw["products"]}
    items_by_sale, cost_by_sale = {}, {}
    for i in raw["sale_items"]:
        sid = i.get("sale_id")
        items_by_sale.setdefault(sid, []).append(i)
        cost_by_sale[sid] = cost_by_sale.get(sid, 0) + num(i.get("purchase_price")) * num(i.get("quantity"))

    income, pay_sum = [], {}
    for p in raw["payments"]:
        s = sale_by_id.get(p.get("sale_id"))
        if not s or sale_status(s) == "cancelled":
            continue  # payments of cancelled invoices are treated as refunded
        amt = num(p.get("amount"))
        pay_sum[s["id"]] = pay_sum.get(s["id"], 0) + amt
        its = items_by_sale.get(s["id"], [])
        prod = prod_by_id.get(its[0].get("product_id")) if its else None
        cat = "Accessories Sales" if prod and str(prod.get("category", "")).lower() == "accessories" else "Laptop Sales Payments"
        income.append({"id": None, "kind": "sales", "date": payment_date(p, s), "source": "Sales payment (auto)",
                       "title": f"Payment for {s.get('invoice_no')}", "category": cat, "amount": amt,
                       "method": method_from_note(p.get("note")), "party": s.get("customer_name") or "",
                       "reference": s.get("invoice_no") or "", "by": p.get("received_by") or ""})
    raw_income = {r["id"]: r for r in raw["income"]}
    for r in raw["income"]:
        income.append({"id": r.get("id"), "kind": "manual", "date": parse_date(r.get("income_date")),
                       "source": "Manual entry", "title": r.get("income_title") or "", "category": r.get("category") or "",
                       "amount": num(r.get("amount")), "method": r.get("payment_method") or "Other",
                       "party": r.get("received_from") or "", "reference": r.get("reference_no") or "",
                       "by": r.get("created_by") or ""})
    raw_exp = {r["id"]: r for r in raw["expenses"]}
    expenses = [{"id": r.get("id"), "kind": "expense", "date": parse_date(r.get("expense_date")),
                 "title": r.get("expense_title") or "", "category": r.get("category") or "",
                 "inventory": (r.get("category") or "") in INVENTORY_EXPENSE_CATEGORIES,
                 "amount": num(r.get("amount")), "method": r.get("payment_method") or "Other",
                 "party": r.get("paid_to") or "", "reference": r.get("reference_no") or "",
                 "by": r.get("created_by") or ""} for r in raw["expenses"]]
    mismatch = [s for s in active if abs(pay_sum.get(s["id"], 0) - num(s.get("paid_amount"))) > 0.5]
    return {"active": active, "income": income, "expenses": expenses, "cost_by_sale": cost_by_sale,
            "invoice_nos": {str(s.get("invoice_no", "")).strip().lower() for s in sales},
            "raw_income": raw_income, "raw_expenses": raw_exp, "mismatch": mismatch, "pay_sum": pay_sum,
            "stock_cost": sum(stock_value(p) for p in raw["products"])}


def fin_calc(ctx, d1, d2):
    def inside(d):
        return d is not None and d1 <= d <= d2

    sales_p = [s for s in ctx["active"] if inside(parse_date(s.get("sale_date")))]
    inc = [r for r in ctx["income"] if inside(r["date"])]
    exp = [r for r in ctx["expenses"] if inside(r["date"])]
    revenue = sum(num(s.get("total")) for s in sales_p)
    cogs = sum(ctx["cost_by_sale"].get(s["id"], 0) for s in sales_p)
    received = sum(r["amount"] for r in inc if r["kind"] == "sales")
    other = sum(r["amount"] for r in inc if r["kind"] == "manual")
    op = sum(r["amount"] for r in exp if not r["inventory"])
    inv = sum(r["amount"] for r in exp if r["inventory"])
    gross = revenue - cogs
    return {
        "sales": sales_p, "income": inc, "expenses": exp, "revenue": revenue, "cogs": cogs, "gross": gross,
        "received": received, "other": other, "total_income": received + other, "op": op, "inv": inv,
        "expense_total": op + inv, "net": gross + other - op,
        "outstanding": sum(max(num(s.get("total")) - num(s.get("paid_amount")), 0) for s in sales_p),
        "no_cost": sum(1 for s in sales_p if s["id"] not in ctx["cost_by_sale"]),
        "cash_in": sum(r["amount"] for r in inc if r["method"] == "Cash"),
        "cash_out": sum(r["amount"] for r in exp if r["method"] == "Cash"),
    }


def period_range(label, custom=None):
    t = today_pk()
    if label == "Today":
        return t, t
    if label == "Yesterday":
        y = t - timedelta(days=1)
        return y, y
    if label == "This Week":
        return t - timedelta(days=t.weekday()), t
    if label == "This Month":
        return t.replace(day=1), t
    if label == "Last Month":
        end = t.replace(day=1) - timedelta(days=1)
        return end.replace(day=1), end
    if label == "All Time":
        return ALL_TIME_START, t
    return custom


def fin_rng_text(d1, d2):
    if d1 <= ALL_TIME_START:
        return f"All time (up to {d2.strftime('%d %b %Y')})"
    if d1 == d2:
        return d1.strftime("%d %b %Y")
    return f"{d1.strftime('%d %b %Y')} to {d2.strftime('%d %b %Y')}"


def pl_lines(c):
    return [
        ("Total Sales Revenue (invoiced, after discounts)", c["revenue"], "main"),
        ("Less: Cost of Goods Sold (purchase cost of items sold)", -c["cogs"], "main"),
        ("GROSS PROFIT", c["gross"], "total"),
        ("Add: Other Business Income (manual entries)", c["other"], "main"),
        ("Less: Operating Expenses", -c["op"], "main"),
        ("NET PROFIT", c["net"], "total"),
        ("Memo: Customer payments received (actual money)", c["received"], "memo"),
        ("Memo: Outstanding customer balances (invoices in period)", c["outstanding"], "memo"),
        ("Memo: Inventory purchases recorded (NOT deducted from profit)", c["inv"], "memo"),
        ("Memo: Total money received (customer payments + manual income)", c["total_income"], "memo"),
        ("Memo: Total money paid out (all recorded expenses)", c["expense_total"], "memo"),
    ]


def money_by_method(c):
    agg = {}
    for r in c["income"]:
        agg.setdefault(r["method"], [0.0, 0.0])[0] += r["amount"]
    for r in c["expenses"]:
        agg.setdefault(r["method"], [0.0, 0.0])[1] += r["amount"]
    order = FIN_METHODS + ["Unspecified"]
    keys = sorted(agg, key=lambda m: order.index(m) if m in order else 99)
    return [(m, agg[m][0], agg[m][1], agg[m][0] - agg[m][1]) for m in keys]


def group_amounts(rows):
    agg = {}
    for r in rows:
        e = agg.setdefault(r["category"] or "Uncategorised", [0, 0.0])
        e[0] += 1
        e[1] += r["amount"]
    return sorted(((k, v[0], v[1]) for k, v in agg.items()), key=lambda x: -x[2])


def trend_df(c, d1, d2):
    monthly = (d2 - d1).days > 62

    def key(d):
        return d.strftime("%Y-%m") if monthly else d.isoformat()

    data = {}
    for r in c["income"]:
        data.setdefault(key(r["date"]), [0.0, 0.0])[0] += r["amount"]
    for r in c["expenses"]:
        data.setdefault(key(r["date"]), [0.0, 0.0])[1] += r["amount"]
    if not data:
        return pd.DataFrame(columns=["Money In", "Money Out"])
    if not monthly:
        d = d1
        while d <= d2:
            data.setdefault(d.isoformat(), [0.0, 0.0])
            d += timedelta(days=1)
    keys = sorted(data)
    return pd.DataFrame({"Money In": [data[k][0] for k in keys], "Money Out": [data[k][1] for k in keys]}, index=keys)


def fin_sales_rows(ctx, c):
    rows = []
    for s in sorted(c["sales"], key=lambda x: x.get("id", 0)):
        total, paid = num(s.get("total")), num(s.get("paid_amount"))
        cost = ctx["cost_by_sale"].get(s["id"], 0)
        rows.append({"invoice": s.get("invoice_no"), "date": str(s.get("sale_date"))[:10], "customer": s.get("customer_name"),
                     "sold_by": s.get("sold_by"), "revenue": total, "paid": paid, "balance": max(total - paid, 0),
                     "cogs": cost, "gross": total - cost})
    return rows


# ---------------- PDF reports ----------------
def _cat_table(rows, label="Category"):
    data = group_amounts(rows)
    return ("table", [label, "Entries", "Amount"], [[k, n, pkr(a)] for k, n, a in data], [50, 10, 20], {1, 2},
            ["TOTAL", sum(n for _, n, _ in data), pkr(sum(a for _, _, a in data))] if data else None)


def _method_table(c):
    rows = money_by_method(c)
    return ("table", ["Payment Method", "Money Received", "Money Paid Out", "Net"],
            [[m, pkr(a), pkr(b), pkr(n)] for m, a, b, n in rows], [30, 20, 20, 20], {1, 2, 3},
            ["TOTAL", pkr(sum(r[1] for r in rows)), pkr(sum(r[2] for r in rows)), pkr(sum(r[3] for r in rows))] if rows else None)


def _pl_blocks(ctx, c):
    a = fin_calc(ctx, ALL_TIME_START, today_pk())
    blocks = [("h", "Profit & Loss Statement"),
              ("kpi", [(lbl, pkr(v)) for lbl, v, _ in pl_lines(c)]),
              ("p", "Revenue is what was invoiced; received money is shown separately. Unpaid balances are never counted as received. "
                    "Gross profit uses purchase_price and selling_price from the sold items. Buying stock is not deducted as an expense; "
                    "only the cost of items actually sold is (COGS)."),
              ("h", "Operating Expenses by Category"),
              _cat_table([r for r in c["expenses"] if not r["inventory"]]),
              ("h", "Money by Payment Method"), _method_table(c),
              ("kpi", [("Cash in hand (all recorded cash transactions)", pkr(a["cash_in"] - a["cash_out"]))])]
    if c["no_cost"]:
        blocks.append(("p", f"Note: {c['no_cost']} invoice(s) have no item records, so their cost could not be calculated."))
    return blocks


def _income_blocks(c, d1, d2, daily_totals=False):
    rows = sorted(c["income"], key=lambda r: (r["date"], r["amount"]))
    blocks = [("h", "Income Summary"),
              ("kpi", [("Total money received", pkr(c["total_income"])), ("Customer payments (from billing, automatic)", pkr(c["received"])),
                       ("Other business income (manual entries)", pkr(c["other"])), ("Number of income entries", str(len(rows)))]),
              ("h", "Income by Category"), _cat_table(c["income"])]
    if daily_totals and d1 != d2:
        by_day = {}
        for r in rows:
            by_day[r["date"]] = by_day.get(r["date"], 0) + r["amount"]
        blocks += [("h", "Daily Totals"), ("table", ["Date", "Income"], [[k.strftime("%d %b %Y"), pkr(v)] for k, v in sorted(by_day.items())],
                                           [20, 20], {1}, ["TOTAL", pkr(sum(by_day.values()))] if by_day else None)]
    blocks += [("h", "Income by Payment Method"),
               ("table", ["Payment Method", "Amount"], [[m, pkr(a)] for m, a, _, _ in money_by_method(c) if a], [30, 20], {1}, None),
               ("h", "Income Details")]
    shown, note = cap_rows(rows)
    if note:
        blocks.append(("p", note))
    blocks.append(("table", ["Date", "Source", "Title", "Category", "Received From", "Method", "Reference", "Amount"],
                   [[r["date"].strftime("%d %b %Y"), r["source"], r["title"], r["category"], r["party"], r["method"],
                     r["reference"], pkr(r["amount"])] for r in shown],
                   [9, 12, 20, 16, 14, 8, 12, 10], {7}, ["TOTAL", "", "", "", "", "", "", pkr(c["total_income"])] if rows else None))
    return blocks


def _expense_blocks(c):
    rows = sorted(c["expenses"], key=lambda r: (r["date"], r["amount"]))
    blocks = [("h", "Expense Summary"),
              ("kpi", [("Total expenses recorded", pkr(c["expense_total"])), ("Operating expenses (reduce profit)", pkr(c["op"])),
                       ("Inventory purchases (tracked separately)", pkr(c["inv"])), ("Number of expense entries", str(len(rows)))]),
              ("h", "Expenses by Category"), _cat_table(c["expenses"]), ("h", "Expense Details")]
    shown, note = cap_rows(rows)
    if note:
        blocks.append(("p", note))
    blocks.append(("table", ["Date", "Title", "Category", "Type", "Paid To", "Method", "Receipt / Ref", "Amount"],
                   [[r["date"].strftime("%d %b %Y"), r["title"], r["category"], "Inventory" if r["inventory"] else "Operating",
                     r["party"], r["method"], r["reference"], pkr(r["amount"])] for r in shown],
                   [9, 20, 16, 9, 14, 8, 12, 10], {7}, ["TOTAL", "", "", "", "", "", "", pkr(c["expense_total"])] if rows else None))
    return blocks


def _sales_blocks(ctx, c):
    rows = fin_sales_rows(ctx, c)
    shown, note = cap_rows(rows)
    blocks = [("h", "Sales Invoices in Period (Revenue vs Received)")]
    if note:
        blocks.append(("p", note))
    blocks.append(("table", ["Invoice", "Date", "Customer", "Sold By", "Revenue", "Paid", "Balance", "Cost (COGS)", "Gross Profit"],
                   [[r["invoice"], r["date"], r["customer"], r["sold_by"], pkr(r["revenue"]), pkr(r["paid"]), pkr(r["balance"]),
                     pkr(r["cogs"]), pkr(r["gross"])] for r in shown],
                   [14, 9, 18, 10, 11, 11, 11, 11, 11], {4, 5, 6, 7, 8},
                   ["TOTAL", "", "", "", pkr(c["revenue"]), pkr(sum(r["paid"] for r in rows)), pkr(c["outstanding"]),
                    pkr(c["cogs"]), pkr(c["gross"])] if rows else None))
    return blocks


def fin_pdf(ctx, d1, d2, kind):
    require_admin()
    c = fin_calc(ctx, d1, d2)
    titles = {"daily": "Daily Income Report", "monthly": "Monthly Income Report", "expense": "Expense Report",
              "pl": "Profit & Loss Report", "complete": "Complete Financial Report"}
    if kind in ("daily", "monthly"):
        blocks = _income_blocks(c, d1, d2, daily_totals=(kind == "monthly"))
    elif kind == "expense":
        blocks = _expense_blocks(c)
    elif kind == "pl":
        blocks = _pl_blocks(ctx, c)
    else:
        blocks = ([("kpi", [("Period", fin_rng_text(d1, d2)), ("Prepared by", current_username())])] + _pl_blocks(ctx, c)
                  + _income_blocks(c, d1, d2, daily_totals=True) + _expense_blocks(c) + _sales_blocks(ctx, c))
    return build_pdf(titles[kind], fin_rng_text(d1, d2), blocks)


# ---------------- Excel workbook ----------------
def fin_excel(ctx, d1, d2):
    require_admin()
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        raise RuntimeError("Excel library missing. Add 'openpyxl' to requirements.txt and reboot the app.")
    c = fin_calc(ctx, d1, d2)
    stamp = backup_now().strftime("%d %b %Y, %I:%M %p")
    navy = PatternFill("solid", fgColor="0B1F3A")
    light = PatternFill("solid", fgColor="DBE7FB")
    thin = Side(style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    money_fmt = '"Rs "#,##0.00'
    sub = f"Period: {fin_rng_text(d1, d2)}   |   Prepared: {stamp}"
    wb = Workbook()

    def heading(ws, title):
        ws["A1"] = f"LAPTOP HOUSE BUNER — {title}"
        ws["A1"].font = Font(bold=True, size=14, color="0B1F3A")
        ws["A2"] = sub
        ws["A2"].font = Font(italic=True, color="64748B")
        ws.sheet_properties.tabColor = "1F6FEB"

    ws = wb.active
    ws.title = "Profit & Loss"
    heading(ws, "Profit & Loss")
    for j, h in enumerate(("Item", "Amount (Rs)"), 1):
        cell = ws.cell(row=3, column=j, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = navy
    r = 3
    for label, value, kind in pl_lines(c):
        r += 1
        ws.cell(row=r, column=1, value=label)
        cell = ws.cell(row=r, column=2, value=round(value, 2))
        cell.number_format = money_fmt
        if kind == "total":
            ws.cell(row=r, column=1).font = Font(bold=True)
            cell.font = Font(bold=True)
            ws.cell(row=r, column=1).fill = light
            cell.fill = light
        elif kind == "memo":
            ws.cell(row=r, column=1).font = Font(italic=True, color="475569")
    r += 2
    ws.cell(row=r, column=1, value="Money by payment method").font = Font(bold=True)
    for j, h in enumerate(("Method", "Received", "Paid out", "Net"), 1):
        cell = ws.cell(row=r + 1, column=j, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = navy
    rr = r + 1
    for m, a_, b_, n_ in money_by_method(c):
        rr += 1
        ws.cell(row=rr, column=1, value=m)
        for j, v in enumerate((a_, b_, n_), 2):
            ws.cell(row=rr, column=j, value=round(v, 2)).number_format = money_fmt
    ws.column_dimensions["A"].width = 66
    for col in "BCD":
        ws.column_dimensions[col].width = 18

    def sheet(title, header, rows, money_cols):
        ws = wb.create_sheet(title)
        heading(ws, title)
        for j, h in enumerate(header, 1):
            cell = ws.cell(row=3, column=j, value=h)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = navy
            cell.border = border
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        widths = [len(h) + 4 for h in header]
        for i, row in enumerate(rows, 4):
            for j, v in enumerate(row, 1):
                cell = ws.cell(row=i, column=j, value=v)
                if isinstance(v, str):
                    if v.startswith("="):
                        cell.data_type = "s"
                    widths[j - 1] = max(widths[j - 1], min(len(v) + 2, 50))
                elif isinstance(v, date):
                    cell.number_format = "DD-MMM-YYYY"
                    widths[j - 1] = max(widths[j - 1], 14)
                elif j - 1 in money_cols:
                    cell.number_format = money_fmt
                    widths[j - 1] = max(widths[j - 1], len(f"{v:,.2f}") + 6)
        if rows:
            t = 4 + len(rows)
            ws.cell(row=t, column=1, value="TOTAL").font = Font(bold=True)
            for j in money_cols:
                cell = ws.cell(row=t, column=j + 1, value=round(sum(x[j] for x in rows), 2))
                cell.number_format = money_fmt
                cell.font = Font(bold=True)
            for j in range(1, len(header) + 1):
                ws.cell(row=t, column=j).fill = light
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(j)].width = max(10, min(w, 50))
        ws.freeze_panes = "A4"
        ws.auto_filter.ref = f"A3:{get_column_letter(len(header))}{max(len(rows) + 3, 3)}"
        ws.print_title_rows = "3:3"
        ws.page_setup.orientation = "landscape"

    inc = sorted(c["income"], key=lambda x: (x["date"], x["amount"]))
    sheet("Income", ["Date", "Source", "Title", "Category", "Received From", "Method", "Reference", "Amount (Rs)"],
          [[x["date"], x["source"], x["title"], x["category"], x["party"], x["method"], x["reference"], x["amount"]] for x in inc], {7})
    exp = sorted(c["expenses"], key=lambda x: (x["date"], x["amount"]))
    sheet("Expenses", ["Date", "Title", "Category", "Type", "Paid To", "Method", "Receipt / Ref", "Amount (Rs)"],
          [[x["date"], x["title"], x["category"], "Inventory purchase" if x["inventory"] else "Operating", x["party"], x["method"],
            x["reference"], x["amount"]] for x in exp], {7})
    sheet("Sales", ["Invoice", "Date", "Customer", "Sold By", "Revenue (Rs)", "Paid (Rs)", "Balance (Rs)", "Cost / COGS (Rs)", "Gross Profit (Rs)"],
          [[x["invoice"], x["date"], x["customer"], x["sold_by"], x["revenue"], x["paid"], x["balance"], x["cogs"], x["gross"]]
           for x in fin_sales_rows(ctx, c)], {4, 5, 6, 7, 8})
    pays = [x for x in inc if x["kind"] == "sales"]
    sheet("Payments", ["Date", "Invoice", "Customer", "Category", "Method", "Received By", "Amount (Rs)"],
          [[x["date"], x["reference"], x["party"], x["category"], x["method"], x["by"], x["amount"]] for x in pays], {6})
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def verify_fin_excel(data, c):
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(data))
    exp = {"Income": len(c["income"]), "Expenses": len(c["expenses"]), "Sales": len(c["sales"]),
           "Payments": sum(1 for r in c["income"] if r["kind"] == "sales")}
    out = []
    for name, n in exp.items():
        found = wb[name].max_row - 3 - (1 if n else 0)
        out.append((found == n, f"{name}: {found} of {n} rows"))
    return out


# ---------------- UI ----------------
def fin_chart(df, color):
    if df.empty:
        st.caption("No data for this period.")
        return
    try:
        st.bar_chart(df, color=color)
    except Exception:
        st.bar_chart(df)


def ledger_df(rows, kind):
    out = []
    for r in sorted(rows, key=lambda r: (r["date"] or date.min, r["id"] or 0), reverse=True):
        base = {"ID": str(r["id"]) if r["id"] is not None else "auto", "Date": r["date"].isoformat() if r["date"] else ""}
        if kind == "income":
            base.update({"Source": r["source"], "Title": r["title"], "Category": r["category"], "Received From": r["party"]})
        else:
            base.update({"Title": r["title"], "Category": r["category"],
                         "Type": "Inventory purchase" if r["inventory"] else "Operating", "Paid To": r["party"]})
        base.update({"Method": r["method"], "Reference": r["reference"], "Amount": r["amount"], "Added By": r["by"]})
        out.append(base)
    return pd.DataFrame(out)


def fin_form(kind, prefix, row=None):
    cfg = FIN_CFG[kind]
    row = row or {}
    c1, c2 = st.columns(2)
    title = c1.text_input(cfg["title_label"], value=row.get(cfg["title"]) or "", key=f"{prefix}_t")
    cats = cfg["cats"] + ([row["category"]] if row.get("category") and row["category"] not in cfg["cats"] else [])
    cat = c2.selectbox("Category", cats, index=option_index(cats, row.get("category")), key=f"{prefix}_c")
    c3, c4, c5 = st.columns(3)
    amount = c3.number_input("Amount (PKR)", min_value=0.0, step=100.0, value=num(row.get("amount")), key=f"{prefix}_a")
    methods = FIN_METHODS + ([row["payment_method"]] if row.get("payment_method") and row["payment_method"] not in FIN_METHODS else [])
    method = c4.selectbox("Payment Method", methods, index=option_index(methods, row.get("payment_method")), key=f"{prefix}_m")
    d = parse_date(row.get(cfg["date"])) or today_pk()
    dt = c5.date_input("Date", value=min(d, today_pk()), max_value=today_pk(), key=f"{prefix}_d")
    c6, c7 = st.columns(2)
    party = c6.text_input(cfg["party_label"], value=row.get(cfg["party"]) or "", key=f"{prefix}_p")
    ref = c7.text_input(cfg["ref_label"], value=row.get("reference_no") or "", key=f"{prefix}_r")
    desc = st.text_area("Description", value=row.get("description") or "", key=f"{prefix}_x")
    return {cfg["title"]: title.strip(), "category": cat, "amount": float(amount), "payment_method": method,
            cfg["date"]: dt.isoformat(), cfg["party"]: party.strip(), "description": desc.strip(), "reference_no": ref.strip()}


def fin_crud(kind, ctx, c, tables_ok):
    cfg = FIN_CFG[kind]
    is_inc = kind == "income"
    rows = c["income"] if is_inc else c["expenses"]
    t1, t2, t3 = st.tabs(["📋 Records", f"➕ Add {'Income' if is_inc else 'Expense'}", "✏️ Edit / Delete"])

    with t1:
        if is_inc:
            cards([("💰", "Total Income Received", pkr(c["total_income"]), "#12b76a"),
                   ("🧾", "Customer Payments (auto)", pkr(c["received"]), "#1f6feb"),
                   ("✍️", "Manual Income", pkr(c["other"]), "#7c3aed"), ("📄", "Entries", len(rows), "#0ea5e9")])
        else:
            cards([("💸", "Total Expenses", pkr(c["expense_total"]), "#d92d20"),
                   ("🏪", "Operating Expenses", pkr(c["op"]), "#f79009"),
                   ("📦", "Inventory Purchases", pkr(c["inv"]), "#7c3aed"), ("📄", "Entries", len(rows), "#0ea5e9")])
        f1, f2, f3 = st.columns([2, 1, 1])
        search = f1.text_input("🔍 Search title, party or reference", key=f"flt_{kind}_search").strip().lower()
        cat = f2.selectbox("Category", ["All categories"] + cfg["cats"], key=f"flt_{kind}_cat")
        src = f3.selectbox("Source", ["All sources", "Sales payments (auto)", "Manual entries"], key="flt_income_src") if is_inc else "All sources"
        view = [r for r in rows
                if (not search or search in f"{r['title']} {r['party']} {r['reference']}".lower())
                and (cat == "All categories" or r["category"] == cat)
                and (src == "All sources" or (src.startswith("Sales") and r["kind"] == "sales") or (src.startswith("Manual") and r["kind"] == "manual"))]
        if not view:
            empty_state("💰" if is_inc else "💸", "No records", "Nothing matches the selected period and filters.")
        else:
            show_table(ledger_df(view, kind))
            st.markdown(f"**Total shown: {pkr(sum(r['amount'] for r in view))}** ({len(view)} entries)")
            st.markdown("##### By category")
            show_table(pd.DataFrame([{"Category": k, "Entries": n, "Amount": a} for k, n, a in group_amounts(view)]))
        if is_inc:
            st.caption("Customer payments from New Sale / Billing appear automatically with source 'Sales payment (auto)'. "
                       "They cannot be edited here (use Sales History) so nothing is counted twice.")

    with t2:
        if not tables_ok:
            st.warning("Run the SQL migration first (see the warning at the top of this page).")
        else:
            if is_inc:
                st.info("Do NOT enter sales made through New Sale / Billing here: they are already included automatically. "
                        "Use this form for repairs, software work, accessories or goods sold outside billing and other income. "
                        "If you sell goods outside billing, also record their purchase cost as an expense so profit stays accurate.")
            else:
                st.info("Stock purchases (Laptop Purchasing / Accessories Purchasing) are recorded as cash paid out but are NOT deducted "
                        "from profit. Profit uses the purchase cost of the items actually sold.")
            with st.form(f"add_{kind}", clear_on_submit=True):
                vals = fin_form(kind, f"add_{kind}")
                submit = st.form_submit_button("💾 Save", type="primary")
            if submit:
                err = fin_validate(kind, vals, ctx)
                dup, fp = fin_is_duplicate(kind, vals)
                if err:
                    st.error(err)
                elif dup:
                    st.error("This looks like a duplicate of the entry you just saved. Entry blocked.")
                else:
                    try:
                        fin_insert(kind, vals)
                        st.session_state["fin_last_fp"] = (fp, datetime.now())
                        flash("success", f"{'Income' if is_inc else 'Expense'} saved.")
                        st.rerun()
                    except PermissionError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Save failed: {e}")

    with t3:
        editable = [r for r in rows if r["kind"] != "sales"]
        if not tables_ok or not editable:
            empty_state("✏️", "Nothing to edit", "Manual entries in the selected period appear here. Change the period at the top to find older entries.")
        else:
            editable = sorted(editable, key=lambda r: (r["date"], r["id"]), reverse=True)
            ids = [r["id"] for r in editable]
            labels = {r["id"]: f"#{r['id']} | {r['date']} | {r['title']} | {pkr(r['amount'])}" for r in editable}
            rid = st.selectbox("Select entry", ids, format_func=lambda i: labels[i], key=f"edit_{kind}_id")
            raw = ctx["raw_income" if is_inc else "raw_expenses"].get(rid, {})
            with st.form(f"edit_{kind}_form_{rid}"):
                vals = fin_form(kind, f"ed_{kind}{rid}", raw)
                save = st.form_submit_button("💾 Save Changes", type="primary")
            if save:
                err = fin_validate(kind, vals, ctx)
                if err:
                    st.error(err)
                else:
                    try:
                        fin_update(kind, rid, vals)
                        flash("success", "Entry updated.")
                        st.rerun()
                    except PermissionError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Update failed: {e}")
            st.markdown("##### 🗑️ Delete this entry")
            st.warning(f"You are about to permanently delete: **{labels[rid]}**. This cannot be undone.")
            ok = st.checkbox("Yes, delete this entry", key=f"del_{kind}_c_{rid}")
            if st.button("Delete Entry", disabled=not ok, key=f"del_{kind}_b_{rid}"):
                try:
                    fin_delete(kind, rid)
                    flash("success", "Entry deleted.")
                    st.rerun()
                except PermissionError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Delete failed: {e}")


def fin_dashboard(ctx, c, label, d1, d2):
    today = today_pk()
    a = fin_calc(ctx, ALL_TIME_START, today)
    month = fin_calc(ctx, today.replace(day=1), today)
    st.markdown("### 🏦 Overall Financial Position (all time)")
    cards([("🧾", "Total Sales Income (invoiced)", pkr(a["revenue"]), "#1f6feb"),
           ("💵", "Total Payments Received", pkr(a["received"]), "#12b76a"),
           ("⏳", "Outstanding Customer Balances", pkr(a["outstanding"]), "#f79009"),
           ("🏭", "Product Purchase Cost (sold items)", pkr(a["cogs"]), "#7c3aed"),
           ("💸", "Total Business Expenses", pkr(a["expense_total"]), "#d92d20"),
           ("📈", "Net Profit", pkr(a["net"]), "#12b76a" if a["net"] >= 0 else "#d92d20"),
           ("👛", "Cash in Hand (recorded cash)", pkr(a["cash_in"] - a["cash_out"]), "#0ea5e9"),
           ("📅", "Total Expenses This Month", pkr(month["expense_total"]), "#db2777")])
    with st.expander("More figures"):
        cards([("✍️", "Other Business Income", pkr(a["other"]), "#7c3aed"),
               ("🏪", "Operating Expenses (in profit)", pkr(a["op"]), "#f79009"),
               ("📦", "Inventory Purchases (not in profit)", pkr(a["inv"]), "#0ea5e9"),
               ("🗄️", "Stock on Hand (at purchase cost)", pkr(ctx["stock_cost"]), "#1f6feb")])
    st.caption("Sales income is what you invoiced. Payments received is the money actually collected. "
               "Outstanding balances are unpaid and are never counted as received cash.")

    st.markdown(f"### 📅 {label} — {fin_rng_text(d1, d2)}")
    cards([("💰", "Income Received", pkr(c["total_income"]), "#12b76a"), ("💸", "Expenses Paid", pkr(c["expense_total"]), "#d92d20"),
           ("💵", "Customer Payments Received", pkr(c["received"]), "#1f6feb"),
           ("⏳", "Outstanding (invoices in period)", pkr(c["outstanding"]), "#f79009"),
           ("🧾", "Sales Revenue", pkr(c["revenue"]), "#0ea5e9"), ("📊", "Gross Profit", pkr(c["gross"]), "#7c3aed"),
           ("📈", "Net Profit", pkr(c["net"]), "#12b76a" if c["net"] >= 0 else "#d92d20")])

    st.markdown("#### Money in vs money out")
    fin_chart(trend_df(c, d1, d2), ["#12b76a", "#d92d20"])
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("#### Expenses by category")
        df = pd.DataFrame([{"Category": k, "Amount": a_} for k, _, a_ in group_amounts(c["expenses"])])
        fin_chart(df.set_index("Category") if not df.empty else df, "#d92d20")
    with g2:
        st.markdown("#### Income by category")
        df = pd.DataFrame([{"Category": k, "Amount": a_} for k, _, a_ in group_amounts(c["income"])])
        fin_chart(df.set_index("Category") if not df.empty else df, "#12b76a")

    st.markdown("#### 🧮 Profit & Loss statement")
    show_table(pd.DataFrame([{"Item": lbl, "Amount": pkr(v)} for lbl, v, _ in pl_lines(c)]))
    if c["no_cost"]:
        st.warning(f"{c['no_cost']} invoice(s) in this period have no item records, so their cost is unknown and profit may be overstated.")
    st.markdown("#### 💳 Money by payment method")
    mm = money_by_method(c)
    if mm:
        show_table(pd.DataFrame([{"Method": m, "Received": pkr(x), "Paid Out": pkr(y), "Net": pkr(z)} for m, x, y, z in mm]))
    else:
        st.caption("No money movements in this period.")

    if ctx["mismatch"]:
        with st.expander(f"⚠️ {len(ctx['mismatch'])} invoice(s) where payment records differ from the paid amount"):
            st.write("Income uses the payment records. These invoices have a paid amount that does not match their payment records "
                     "(for example after a data reset). Please review them in Sales History.")
            show_table(pd.DataFrame([{"Invoice": s.get("invoice_no"), "Customer": s.get("customer_name"),
                                      "Paid amount on invoice": num(s.get("paid_amount")),
                                      "Sum of payment records": ctx["pay_sum"].get(s["id"], 0)} for s in ctx["mismatch"]]))
    with st.expander("ℹ️ How profit is calculated"):
        st.markdown(
            "- **Revenue** = invoice totals (after discount). **Received money** = payment records. Unpaid balances are not cash.\n"
            "- **Cost of goods sold** = purchase price x quantity of the items actually sold.\n"
            "- **Gross profit** = revenue − cost of goods sold.\n"
            "- **Net profit** = gross profit + other business income − operating expenses.\n"
            "- **Laptop/Accessories Purchasing** expenses are cash paid out but are *not* deducted from profit (that would double-count "
            "the cost already included in cost of goods sold).\n"
            "- Cancelled invoices are excluded, and their payments are treated as refunded.\n"
            "- **Cash in hand** = all recorded Cash income − all recorded Cash expenses. Customer payments recorded before this update "
            "have no payment method and are not counted as cash. Add an 'Other Business Income' entry (Cash) for your opening balance.")


def fin_reports_tab(ctx, d1, d2):
    st.caption(f"Reports use the period selected at the top: **{fin_rng_text(d1, d2)}** (the daily and monthly reports have their own pickers).")
    p1, p2 = st.columns(2)
    day = p1.date_input("Day for the Daily Income Report", value=today_pk(), max_value=today_pk(), key="flt_fin_day")
    months, y, m = [], today_pk().year, today_pk().month
    for _ in range(24):
        months.append(date(y, m, 1))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    msel = p2.selectbox("Month for the Monthly Income Report", months, format_func=lambda d: d.strftime("%B %Y"), key="flt_fin_month")
    mend = (date(msel.year + (msel.month == 12), msel.month % 12 + 1, 1) - timedelta(days=1))
    mend = min(mend, today_pk())

    specs = [("daily", "📅 Daily Income Report", "PDF", lambda: fin_pdf(ctx, day, day, "daily"), f"Daily_Income_Report_{day}.pdf", fin_rng_text(day, day)),
             ("monthly", "🗓️ Monthly Income Report", "PDF", lambda: fin_pdf(ctx, msel, mend, "monthly"), f"Monthly_Income_Report_{msel:%Y-%m}.pdf", fin_rng_text(msel, mend)),
             ("expense", "💸 Expense Report", "PDF", lambda: fin_pdf(ctx, d1, d2, "expense"), f"Expense_Report_{d1}_{d2}.pdf", fin_rng_text(d1, d2)),
             ("pl", "🧮 Profit & Loss Report", "PDF", lambda: fin_pdf(ctx, d1, d2, "pl"), f"Profit_and_Loss_{d1}_{d2}.pdf", fin_rng_text(d1, d2)),
             ("complete", "📚 Complete Financial Report", "PDF", lambda: fin_pdf(ctx, d1, d2, "complete"), f"Complete_Financial_Report_{d1}_{d2}.pdf", fin_rng_text(d1, d2)),
             ("excel", "📗 Financial Excel Workbook", "Excel", lambda: fin_excel(ctx, d1, d2), f"Financial_Workbook_{d1}_{d2}.xlsx", fin_rng_text(d1, d2))]
    cols = st.columns(3)
    for n, (key, title, short, fn, fname, rng_text) in enumerate(specs):
        with cols[n % 3]:
            st.markdown(f"#### {title}")
            st.caption(f"Period: {rng_text}")
            if st.button(f"Generate {short}", key=f"fin_gen_{key}", type="primary"):
                try:
                    with st.spinner("Creating report..."):
                        data = fn()
                    item = {"data": data, "name": fname, "label": rng_text, "checks": []}
                    if key == "excel":
                        item["checks"] = verify_fin_excel(data, fin_calc(ctx, d1, d2))
                    st.session_state[f"fin_{key}"] = item
                    st.toast("Report ready", icon="📄")
                except PermissionError as e:
                    st.error(str(e))
                except Exception as e:
                    st.session_state.pop(f"fin_{key}", None)
                    st.error(f"Could not create the report: {e}")
            item = st.session_state.get(f"fin_{key}")
            if item:
                mime = "application/pdf" if item["name"].endswith(".pdf") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                st.download_button(f"⬇️ Download {short} ({len(item['data']) / 1024:,.0f} KB)", item["data"], file_name=item["name"],
                                   mime=mime, key=f"fin_dl_{key}")
                if item["label"] != rng_text:
                    st.warning("The period changed after this file was created. Generate it again.")
                if item["checks"]:
                    with st.expander("Data checks"):
                        for ok, text in item["checks"]:
                            st.write(("✅ " if ok else "❌ ") + text)


def finance_page():
    page_header("💹", "Income & Expenses", "Admin only: income, expenses, profit & loss")
    if not is_admin():
        st.error("Access denied. This section is for the Owner/Admin only.")
        return
    tables_ok = fin_tables_ok()
    if not tables_ok:
        st.warning("The Income and Expense tables are not created yet. Run the SQL below once in Supabase "
                   "(SQL Editor → New query → Run), then press the button. Sales-based figures work meanwhile.")
        with st.expander("Show the SQL"):
            st.code(FIN_SQL + "\n\nnotify pgrst, 'reload schema';", language="sql")
        for t in ("business_income", "business_expenses"):
            try:
                supabase.table(t).select("id").limit(1).execute()
            except Exception as e:
                st.caption(f"Database says for {t}: {e}")
        if st.button("Re-check database"):
            st.session_state.pop("_cols", None)
            st.rerun()

    s1, s2 = st.columns([1, 2])
    label = s1.selectbox("📅 Period", FIN_PERIODS, index=3, key="flt_fin_period")
    custom = None
    if label == "Custom Date Range":
        t = today_pk()
        rng = s2.date_input("Select dates", value=(t.replace(day=1), t), key="flt_fin_range")
        if not (isinstance(rng, (tuple, list)) and len(rng) == 2):
            st.info("Please select both a start date and an end date.")
            return
        custom = tuple(rng)
        if custom[0] > custom[1]:
            st.error("The start date must be before the end date.")
            return
    d1, d2 = period_range(label, custom)
    s2.caption(f"Showing: {fin_rng_text(d1, d2)}")

    try:
        with st.spinner("Calculating..."):
            ctx = build_fin_context(load_fin_data())
    except PermissionError as e:
        st.error(str(e))
        return
    except Exception as e:
        st.error(f"Could not load financial data: {e}")
        return
    c = fin_calc(ctx, d1, d2)

    t1, t2, t3, t4 = st.tabs(["📊 Dashboard", "💰 Income", "💸 Expenses", "📑 Reports & Downloads"])
    with t1:
        fin_dashboard(ctx, c, label, d1, d2)
    with t2:
        fin_crud("income", ctx, c, tables_ok)
    with t3:
        fin_crud("expense", ctx, c, tables_ok)
    with t4:
        fin_reports_tab(ctx, d1, d2)


# ==================================================================
# STAFF MANAGEMENT (ADMIN ONLY)
# ==================================================================
def staff_management():
    page_header("👥", "Staff Management", "Create and view staff accounts")
    if not is_admin():
        st.error("Access denied. Staff Management is for the Owner/Admin only.")
        return
    users = get_data("users")
    if users:
        rows = []
        for u in users:
            row = {"Username": u.get("username"), "Role": u.get("role")}
            if u.get("created_at"):
                row["Created"] = str(u["created_at"])[:10]
            rows.append(row)
        show_table(pd.DataFrame(rows))
    else:
        empty_state("👥", "No users", "Create the first staff account below.")
    st.divider()
    with st.form("create_staff", clear_on_submit=True):
        st.markdown("### ➕ Create Staff Account")
        username = st.text_input("Username")
        pw = st.text_input("Password (minimum 6 characters)", type="password")
        pw2 = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Create Staff Account", type="primary")
    if submit:
        uname = username.strip()
        if not uname:
            st.error("Username is required.")
        elif len(pw) < 6:
            st.error("Password must be at least 6 characters.")
        elif pw != pw2:
            st.error("Passwords do not match.")
        elif any(str(u.get("username", "")).lower() == uname.lower() for u in users):
            st.error("This username already exists.")
        else:
            try:
                require_admin()
                supabase.table("users").insert({"username": uname, "password_hash": password_hash(pw), "role": "staff"}).execute()
                flash("success", f"Staff account '{uname}' created.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not create account: {e}")


# ==================================================================
# BACKUP & EXPORT CENTER (ADMIN ONLY)
# ==================================================================
BACKUP_TABLES = [("Products", "products"), ("Sales", "sales"), ("Sale Items", "sale_items"),
                 ("Payments", "payments"), ("Staff Accounts", "users"),
                 ("Business Income", "business_income"), ("Business Expenses", "business_expenses")]
DEFAULT_COLUMNS = {
    "products": ["id", "name", "category", "model", "processor", "ram", "storage", "condition_text",
                 "serial_number", "purchase_price", "selling_price", "quantity", "warranty_days"],
    "sales": ["id", "invoice_no", "customer_name", "customer_phone", "sale_date", "sold_by", "total",
              "paid_amount", "discount"],
    "sale_items": ["id", "sale_id", "product_id", "product_name", "specs", "quantity", "selling_price",
                   "purchase_price", "warranty_days", "warranty_expiry"],
    "payments": ["id", "sale_id", "amount", "received_by", "note"],
    "users": ["id", "username", "role", "created_at"],
    "business_income": ["id", "income_title", "category", "amount", "payment_method", "income_date", "received_from",
                        "description", "reference_no", "created_by", "created_at"],
    "business_expenses": ["id", "expense_title", "category", "amount", "payment_method", "expense_date", "paid_to",
                          "description", "reference_no", "created_by", "created_at"],
}
SAFE_USER_FIELDS = ("id", "username", "role", "created_at")  # whitelist: hashes are never exported
PDF_ROW_CAP = 5000
EXCEL_STYLE_CAP = 20000
MONEY_WORDS = ("price", "total", "amount", "paid", "discount")


def backup_now():
    return datetime.now(timezone(timedelta(hours=5)))


def safe_users(rows):
    return [{k: r.get(k) for k in SAFE_USER_FIELDS if k in r} for r in rows]


def collect_backup_data():
    require_admin()
    tables = {n: get_data(n) for n in ("products", "sales", "sale_items", "payments")}
    tables["users"] = safe_users(get_data("users"))
    for t in ("business_income", "business_expenses"):  # new tables may not exist yet
        tables[t] = get_data(t) if col_exists(t, "id") else []
    return tables


def table_columns(key, rows):
    cols = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    return cols or DEFAULT_COLUMNS[key]


def cap_rows(rows):
    if len(rows) > PDF_ROW_CAP:
        return rows[:PDF_ROW_CAP], (f"Showing the first {PDF_ROW_CAP:,} of {len(rows):,} records in this section. "
                                    "The Excel backup contains every record.")
    return rows, None


def excel_backup(tables, now, who):
    require_admin()
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        raise RuntimeError("Excel library missing. Add 'openpyxl' to requirements.txt and reboot the app.")
    stamp = now.strftime("%d %b %Y, %I:%M %p")
    navy = PatternFill("solid", fgColor="0B1F3A")
    band = PatternFill("solid", fgColor="F3F6FB")
    thin = Side(style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    wb = Workbook()
    ws = wb.active
    ws.title = "Backup Info"
    ws["A1"] = "LAPTOP HOUSE BUNER — Excel Backup"
    ws["A1"].font = Font(bold=True, size=16, color="0B1F3A")
    info = [("Backup date & time", stamp), ("Created by", who), ("Scope", "All records (no date filter)"),
            ("Security", "Staff passwords and password hashes are NOT included.")]
    for r, (k, v) in enumerate(info, 3):
        ws.cell(row=r, column=1, value=k).font = Font(bold=True)
        ws.cell(row=r, column=2, value=v)
    r = 3 + len(info) + 1
    for j, h in enumerate(("Worksheet", "Records"), 1):
        c = ws.cell(row=r, column=j, value=h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = navy
    for title, key in BACKUP_TABLES:
        r += 1
        ws.cell(row=r, column=1, value=title)
        ws.cell(row=r, column=2, value=len(tables[key]))
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 58
    ws.sheet_properties.tabColor = "0B1F3A"

    for title, key in BACKUP_TABLES:
        rows = tables[key]
        cols = table_columns(key, rows)
        ws = wb.create_sheet(title)
        ws["A1"] = f"Laptop House Buner — {title}"
        ws["A1"].font = Font(bold=True, size=14, color="0B1F3A")
        ws["A2"] = f"Backup date & time: {stamp}   |   Records: {len(rows)}"
        ws["A2"].font = Font(italic=True, color="64748B")
        for j, c in enumerate(cols, 1):
            cell = ws.cell(row=3, column=j, value=c.replace("_", " ").title())
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = navy
            cell.border = border
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.row_dimensions[3].height = 24
        widths = [len(c) + 4 for c in cols]
        money = [any(w in c.lower() for w in MONEY_WORDS) for c in cols]
        fancy = len(rows) <= EXCEL_STYLE_CAP
        for i, row in enumerate(rows, 4):
            for j, c in enumerate(cols, 1):
                v = row.get(c)
                if isinstance(v, (dict, list)):
                    v = str(v)
                cell = ws.cell(row=i, column=j, value=v)
                if isinstance(v, str):
                    if v.startswith("="):
                        cell.data_type = "s"  # keep text as text (no formulas from data)
                    widths[j - 1] = max(widths[j - 1], min(len(v) + 2, 60))
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    if money[j - 1]:
                        cell.number_format = "#,##0.00"
                    widths[j - 1] = max(widths[j - 1], len(f"{v:,.2f}") + 2)
                if fancy:
                    cell.border = border
                    if i % 2 == 1:
                        cell.fill = band
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(j)].width = max(10, min(w, 60))
        ws.freeze_panes = "A4"
        ws.auto_filter.ref = f"A3:{get_column_letter(len(cols))}{max(len(rows) + 3, 3)}"
        ws.print_title_rows = "3:3"
        ws.page_setup.orientation = "landscape"
        ws.sheet_properties.tabColor = "1F6FEB"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def verify_excel(data, tables):
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(data))
    return [(title, len(tables[key]), wb[title].max_row - 3) for title, key in BACKUP_TABLES]


def backup_pdf(tables, d1, d2, who):
    require_admin()
    stamp = backup_now().strftime("%d %b %Y, %I:%M %p")
    products = sorted(tables["products"], key=lambda p: str(p.get("name") or "").lower())
    sales = sorted([s for s in tables["sales"] if in_range(s, d1, d2)], key=lambda x: x.get("id", 0))
    by_id = {s["id"]: s for s in sales}
    items = [i for i in tables["sale_items"] if i.get("sale_id") in by_id]
    pays = [p for p in tables["payments"] if p.get("sale_id") in by_id]
    act = active_sales(sales)
    pm = profit_map(act, items)
    total = sum(num(s.get("total")) for s in act)
    paid = sum(num(s.get("paid_amount")) for s in act)
    disc = sum(num(s.get("discount")) for s in act)
    owing = [s for s in act if num(s.get("total")) - num(s.get("paid_amount")) > 0.5]
    units = sum(int(num(p.get("quantity"))) for p in products)
    buy_val = sum(stock_value(p) for p in products)
    sell_val = sum(stock_value(p, "selling_price") for p in products)
    rng = f"{d1.strftime('%d %b %Y')} to {d2.strftime('%d %b %Y')}"
    blocks = [
        ("h", "Report Information"),
        ("kpi", [("Report generated", stamp), ("Generated by", who), ("Sales date range", rng),
                 ("Products in inventory", str(len(products))), ("Invoices in range", str(len(sales))),
                 ("Payment records in range", str(len(pays)))]),
        ("h", "Sales Summary and Totals"),
        ("kpi", [("Total invoices (excluding cancelled)", str(len(act))),
                 ("Cancelled invoices", str(len(sales) - len(act))), ("Total sales", pkr(total)),
                 ("Total discounts given", pkr(disc)), ("Total received payments", pkr(paid)),
                 ("Total remaining balances", pkr(max(total - paid, 0))),
                 ("Estimated gross profit (Admin only)", pkr(sum(pm.values())))]),
    ]

    rows, note = cap_rows(sorted(owing, key=lambda s: -(num(s.get("total")) - num(s.get("paid_amount")))))
    blocks.append(("h", "Remaining Customer Balances"))
    if note:
        blocks.append(("p", note))
    blocks.append(("table", ["Invoice", "Customer", "Phone", "Date", "Total", "Paid", "Remaining"],
                   [[s.get("invoice_no"), s.get("customer_name"), s.get("customer_phone"), str(s.get("sale_date"))[:10],
                     pkr(s.get("total")), pkr(s.get("paid_amount")),
                     pkr(num(s.get("total")) - num(s.get("paid_amount")))] for s in rows],
                   [16, 22, 15, 12, 12, 12, 12], {4, 5, 6},
                   ["TOTAL", "", "", "", pkr(sum(num(s.get('total')) for s in owing)),
                    pkr(sum(num(s.get('paid_amount')) for s in owing)),
                    pkr(sum(num(s.get('total')) - num(s.get('paid_amount')) for s in owing))] if owing else None))

    rows, note = cap_rows(products)
    blocks.append(("h", "Complete Product Inventory"))
    blocks.append(("kpi", [("Total products", str(len(products))), ("Total stock units", str(units)),
                           ("Inventory purchase value", pkr(buy_val)), ("Inventory selling value", pkr(sell_val))]))
    if note:
        blocks.append(("p", note))
    blocks.append(("table", ["Product", "Category", "Model", "Processor", "RAM", "Storage", "Serial No", "Condition",
                             "Qty", "Purchase", "Selling"],
                   [[p.get("name"), p.get("category"), p.get("model"), p.get("processor"), p.get("ram"),
                     p.get("storage"), p.get("serial_number"), p.get("condition_text"), int(num(p.get("quantity"))),
                     pkr(p.get("purchase_price")), pkr(p.get("selling_price"))] for p in rows],
                   [15, 8, 10, 13, 6, 8, 12, 8, 4, 9, 9], {8, 9, 10}, None))

    rows, note = cap_rows(sales)
    blocks.append(("h", f"Complete Sales History ({rng})"))
    if note:
        blocks.append(("p", note))
    blocks.append(("table", ["Invoice", "Date", "Customer", "Phone", "Sold By", "Status", "Total", "Discount", "Paid", "Balance"],
                   [[s.get("invoice_no"), str(s.get("sale_date"))[:10], s.get("customer_name"), s.get("customer_phone"),
                     s.get("sold_by"), "Cancelled" if sale_status(s) == "cancelled" else "Active", pkr(s.get("total")),
                     pkr(s.get("discount")), pkr(s.get("paid_amount")),
                     "-" if sale_status(s) == "cancelled" else pkr(max(num(s.get("total")) - num(s.get("paid_amount")), 0))]
                    for s in rows],
                   [14, 9, 16, 12, 10, 8, 10, 9, 10, 10], {6, 7, 8, 9},
                   ["TOTAL (active)", "", "", "", "", "", pkr(total), pkr(disc), pkr(paid), pkr(max(total - paid, 0))] if act else None))

    rows, note = cap_rows(items)
    blocks.append(("h", "Sale Items and Customer Details"))
    blocks.append(("p", "Item profit = selling price x quantity minus purchase price x quantity (before invoice discounts)."))
    if note:
        blocks.append(("p", note))
    trows = []
    for i in rows:
        s = by_id.get(i.get("sale_id"), {})
        canc = sale_status(s) == "cancelled"
        q = num(i.get("quantity"))
        trows.append([f"{s.get('invoice_no')}{' (Cancelled)' if canc else ''}", s.get("customer_name"), s.get("customer_phone"),
                      i.get("product_name"), i.get("specs"), int(q), pkr(i.get("selling_price")), pkr(i.get("purchase_price")),
                      "-" if canc else pkr((num(i.get("selling_price")) - num(i.get("purchase_price"))) * q),
                      str(i.get("warranty_expiry") or "")[:10]])
    blocks.append(("table", ["Invoice", "Customer", "Phone", "Product", "Specs", "Qty", "Sell Price", "Purchase", "Profit", "Warranty Until"],
                   trows, [14, 14, 11, 14, 20, 4, 9, 9, 9, 10], {5, 6, 7, 8}, None))

    rows, note = cap_rows(pays)
    blocks.append(("h", "Payment Records"))
    if note:
        blocks.append(("p", note))
    blocks.append(("table", ["Payment ID", "Invoice", "Customer", "Amount", "Received By", "Note", "Date"],
                   [[p.get("id"), by_id.get(p.get("sale_id"), {}).get("invoice_no"),
                     by_id.get(p.get("sale_id"), {}).get("customer_name"), pkr(p.get("amount")), p.get("received_by"),
                     p.get("note"), str(p.get("created_at") or p.get("payment_date") or "")[:16]] for p in rows],
                   [8, 14, 16, 11, 12, 30, 14], {3}, None))
    return build_pdf("Complete Backup Report", rng, blocks)


def prepare_backup(kind, d1, d2):
    """Build one export (zip / excel / pdf). Returns a dict describing the prepared file."""
    require_admin()
    now = backup_now()
    who = current_username()
    day = now.strftime("%Y-%m-%d")
    base = f"Laptop_House_Buner_Backup_{day}"
    tables = collect_backup_data()
    counts = {key: len(tables[key]) for _, key in BACKUP_TABLES}
    checks = []

    if kind == "excel":
        data = excel_backup(tables, now, who)
        for title, exp, found in verify_excel(data, tables):
            checks.append((exp == found, f"{title}: {found} of {exp} records in worksheet"))
        name, mime = base + ".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    elif kind == "pdf":
        data = backup_pdf(tables, d1, d2, who)
        checks.append((data[:4] == b"%PDF", f"Valid PDF file ({len(data) / 1024:,.0f} KB)"))
        name, mime = base + ".pdf", "application/pdf"

    else:
        xlsx = excel_backup(tables, now, who)
        in_sales = [s for s in tables["sales"] if in_range(s, d1, d2)]
        ids = {s["id"] for s in in_sales}
        in_items = [i for i in tables["sale_items"] if i.get("sale_id") in ids]
        pdfs = {
            "Complete_Backup_Report.pdf": backup_pdf(tables, d1, d2, who),
            "Inventory_Report.pdf": inventory_pdf(tables["products"]),
            "Sold_Products_Report.pdf": sales_pdf(in_sales, in_items, d1, d2),
            "Sales_Summary.pdf": summary_pdf(in_sales, in_items, d1, d2),
        }
        info = "\n".join([
            "LAPTOP HOUSE BUNER - BACKUP INFORMATION", "=" * 44,
            f"Backup date & time : {now.strftime('%d %b %Y, %I:%M %p')} (Pakistan time)",
            f"Created by         : {who}",
            f"PDF sales range    : {d1.isoformat()} to {d2.isoformat()}",
            "Database data      : ALL records (CSV and Excel are not date-filtered)", "",
            "RECORD COUNTS"] + [f"  {title:<15}: {counts[key]}" for title, key in BACKUP_TABLES] + ["",
            "CONTENTS",
            f"  excel/{base}.xlsx    - one worksheet per table",
            "  pdf/                 - 4 PDF reports",
            "  data_csv/            - one CSV file per table", "",
            "SECURITY",
            "  Staff passwords and password hashes are NOT included.",
            "  No Supabase secrets or credentials are included.",
            "  Staff accounts contain only: id, username, role, created_at.",
            "  Keep this file private: it contains purchase prices, profit and customer details."])
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"{base}/backup_info.txt", info)
            z.writestr(f"{base}/excel/{base}.xlsx", xlsx)
            for n, b in pdfs.items():
                z.writestr(f"{base}/pdf/{n}", b)
            for _, key in BACKUP_TABLES:
                csv = pd.DataFrame(tables[key], columns=table_columns(key, tables[key])).to_csv(index=False)
                z.writestr(f"{base}/data_csv/{key}.csv", "\ufeff" + csv)
        data = buf.getvalue()
        name, mime = base + ".zip", "application/zip"
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            checks.append((z.testzip() is None, f"ZIP is valid and contains {len(z.namelist())} files"))
            for title, key in BACKUP_TABLES:
                text = z.read(f"{base}/data_csv/{key}.csv").decode("utf-8-sig")
                found = len(pd.read_csv(io.StringIO(text)))
                checks.append((found == counts[key], f"{title} CSV: {found} of {counts[key]} records"))
            users_header = z.read(f"{base}/data_csv/users.csv").decode("utf-8-sig").splitlines()[0].lower()
            checks.append(("password" not in users_header and "hash" not in users_header,
                           "Staff file contains no password or hash column"))
            checks.append((all(b[:4] == b"%PDF" for b in pdfs.values()), f"{len(pdfs)} PDF reports are valid"))
        for title, exp, found in verify_excel(xlsx, tables):
            checks.append((exp == found, f"Excel {title}: {found} of {exp} records"))

    return {"data": data, "file_name": name, "mime": mime, "checks": checks, "counts": counts,
            "time": now.strftime("%d %b %Y %I:%M %p"), "range": (d1, d2), "size": len(data)}


def run_backup(kind, label, d1, d2):
    try:
        with st.spinner(f"Preparing {label}... this can take a moment for large data."):
            item = prepare_backup(kind, d1, d2)
    except PermissionError as e:
        st.error(str(e))
        return
    except Exception as e:
        st.session_state.pop(f"bk_{kind}", None)
        st.error(f"{label} failed: {e}")
        return
    st.session_state[f"bk_{kind}"] = item
    st.session_state.setdefault("bk_log", []).append(
        {"Time": item["time"], "Type": label, "File": item["file_name"], "Size (KB)": round(item["size"] / 1024),
         "Checks passed": f"{sum(1 for ok, _ in item['checks'] if ok)}/{len(item['checks'])}"})
    if all(ok for ok, _ in item["checks"]):
        st.success(f"{label} is ready. All data checks passed. Use the download button below.")
        st.toast(f"{label} ready", icon="✅")
    else:
        st.warning(f"{label} was created, but some checks failed. Please read the check list below before relying on it.")


def backup_center():
    page_header("💾", "Backup & Export", "Download complete backups of your shop data")
    if not is_admin():
        st.error("Access denied. Backup & Export is for the Owner/Admin only.")
        return
    st.info("Backups are created on demand and downloaded to your device. Nothing is stored, deleted or overwritten on the "
            "server. Staff passwords, password hashes and Supabase secrets are never included. "
            "Keep downloaded files private: they contain purchase prices, profit and customer details.")

    try:
        sales = get_data("sales")
    except Exception as e:
        st.error(f"Could not read sales: {e}")
        return
    dates = [d for d in (parse_date(s.get("sale_date")) for s in sales) if d]
    default = (min(dates) if dates else today_pk() - timedelta(days=29), max(today_pk(), max(dates) if dates else today_pk()))
    rng = st.date_input("📅 Sales report date range (applies to PDF reports; Excel and CSV data always contain ALL records)",
                        value=default, key="flt_bk_range")
    if not (isinstance(rng, (tuple, list)) and len(rng) == 2):
        st.info("Please select both a start date and an end date.")
        return
    d1, d2 = rng
    if d1 > d2:
        st.error("The start date must be before the end date.")
        return

    specs = [("zip", "📦", "Complete ZIP Backup", "ZIP", "One ZIP with the Excel workbook, 4 PDF reports, CSV data for every table and a backup information file."),
             ("excel", "📗", "Excel Backup", "Excel", "One .xlsx workbook with a formatted worksheet per table, filters, frozen headers and backup date/time."),
             ("pdf", "📕", "PDF Backup", "PDF", "Branded PDF: inventory, sales history, sale items, payments, totals, balances and gross profit.")]
    cols = st.columns(3)
    for col, (kind, icon, title, short, desc) in zip(cols, specs):
        with col:
            st.markdown(f"#### {icon} {title}")
            st.caption(desc)
            if st.button(f"Prepare {short} Backup", key=f"bk_btn_{kind}", type="primary"):
                run_backup(kind, title, d1, d2)
            item = st.session_state.get(f"bk_{kind}")
            if item:
                st.download_button(f"⬇️ Download {short} ({item['size'] / 1024:,.0f} KB)", item["data"],
                                   file_name=item["file_name"], mime=item["mime"], key=f"bk_dl_{kind}")
                st.caption(f"Prepared: {item['time']}  \nFile: {item['file_name']}")
                if item["range"] != (d1, d2) and kind != "excel":
                    st.warning("The date range changed after this file was prepared. Press Prepare again to update it.")
                with st.expander("Data checks"):
                    for ok, text in item["checks"]:
                        st.write(("✅ " if ok else "❌ ") + text)

    st.divider()
    st.markdown("### 🕒 Backups prepared in this session")
    log = st.session_state.get("bk_log", [])
    if log:
        show_table(pd.DataFrame(log[::-1][:20]))
        if st.button("Clear prepared files from memory"):
            for k in ("bk_zip", "bk_excel", "bk_pdf", "bk_log"):
                st.session_state.pop(k, None)
            st.rerun()
    else:
        empty_state("💾", "No backups prepared yet", "Press one of the Prepare buttons above.")
    st.caption("Large data: PDF sections show up to 5,000 records each (the PDF says so when this happens). "
               "The Excel and CSV files always contain every record.")


# ==================================================================
# ADMIN SETTINGS (RESET + MAINTENANCE) — ADMIN ONLY
# ==================================================================
def admin_settings():
    page_header("⚙️", "Admin Settings", "Backup, reset and maintenance tools")
    if not is_admin():
        st.error("Access denied. Admin settings are for the Owner/Admin only.")
        return
    t1, t2, t3, t4 = st.tabs(["🔧 Maintenance", "🧹 Reset Products", "🗂️ Reset Sales / Payments", "🔄 Reset Filters"])

    with t1:
        st.write("Full backups (ZIP, Excel and PDF) are now in the **💾 Backup & Export** page in the sidebar. "
                 "Always download a backup before using any Reset option.")
        if st.button("Re-check database columns"):
            st.session_state.pop("_cols", None)
            st.success("Done. The app will re-check optional columns.")

    with t2:
        st.markdown("#### Reset selected product information")
        products = get_data("products")
        if not products:
            empty_state("📦", "No products", "Nothing to reset.")
        else:
            labels = {p["id"]: f'#{p["id"]} {p.get("name")} {p.get("model") or ""}' for p in products}
            sel = st.multiselect("Step 1 — Choose products (maximum 20)", list(labels), format_func=lambda i: labels[i], key="rp_sel")
            opts = ["Stock quantity → 0", "Purchase and selling price → 0", "Serial number → blank",
                    "Warranty days → 0", "Warranty terms → blank"]
            fields = st.multiselect("Step 2 — Choose what to reset", opts, key="rp_fields")
            if sel and fields:
                st.warning(f"**What will happen:** for {len(sel)} selected product(s): {', '.join(fields)}. "
                           "The products themselves and all sales records are NOT deleted.")
                chosen = [p for p in products if p["id"] in sel]
                st.download_button("Step 3 — ⬇️ Download backup of these products", pd.DataFrame(chosen).to_csv(index=False),
                                   file_name="products_backup_before_reset.csv", mime="text/csv")
                b1 = st.checkbox("I downloaded the backup", key="rp_b1")
                typed = st.text_input("Step 4 — Type RESET PRODUCTS to confirm", key="rp_typed")
                b2 = st.checkbox("Second confirmation: I understand this changes my product data", key="rp_b2")
                ready = b1 and b2 and typed.strip() == "RESET PRODUCTS" and len(sel) <= 20
                if len(sel) > 20:
                    st.error("Please select at most 20 products at a time.")
                if st.button("Reset Selected Products", disabled=not ready, type="primary"):
                    try:
                        reset_products(sel, fields)
                        flash("success", f"{len(sel)} product(s) reset.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Reset failed: {e}")

    with t3:
        st.markdown("#### Reset selected sales / payment records")
        sales = sorted(get_data("sales"), key=lambda x: x.get("id", 0), reverse=True)
        if not sales:
            empty_state("🧾", "No sales", "Nothing to reset.")
        else:
            labels = {s["id"]: f'{s.get("invoice_no")} | {s.get("customer_name")} | {pkr(s.get("total"))}' for s in sales}
            sel = st.multiselect("Step 1 — Choose invoices (maximum 10)", list(labels), format_func=lambda i: labels[i], key="rs_sel")
            action = st.radio("Step 2 — Choose action", [
                "Reset payments only (payment records deleted, paid amount set to 0)",
                "Delete invoices completely (stock returned, items and payments deleted)"], key="rs_action")
            if sel:
                full = action.startswith("Delete")
                st.warning(f"**What will happen:** {len(sel)} invoice(s) selected. " + (
                    "Each invoice, its items and its payments will be permanently deleted and sold units go back to stock."
                    if full else "All payment records of these invoices will be deleted and their paid amount becomes Rs 0."))
                ids = set(sel)
                st.download_button("Step 3 — ⬇️ Download backup of these invoices (ZIP)", zip_bytes({
                    "sales": [s for s in sales if s["id"] in ids],
                    "sale_items": [i for i in get_data("sale_items") if i.get("sale_id") in ids],
                    "payments": [p for p in get_data("payments") if p.get("sale_id") in ids]}),
                    file_name="sales_backup_before_reset.zip", mime="application/zip")
                b1 = st.checkbox("I downloaded the backup", key="rs_b1")
                typed = st.text_input("Step 4 — Type DELETE SALES to confirm", key="rs_typed")
                b2 = st.checkbox("Second confirmation: I understand this cannot be undone", key="rs_b2")
                ready = b1 and b2 and typed.strip() == "DELETE SALES" and len(sel) <= 10
                if len(sel) > 10:
                    st.error("Please select at most 10 invoices at a time.")
                if st.button("Apply Reset to Selected Invoices", disabled=not ready, type="primary"):
                    try:
                        warn = 0
                        for sid in sel:
                            if full:
                                warn += delete_sale_full(sid)
                            else:
                                reset_sale_payments(sid)
                        flash("success", f"Done for {len(sel)} invoice(s)." + (f" {warn} item(s) could not be returned to stock." if warn else ""))
                        st.rerun()
                    except Exception as e:
                        st.error(f"Reset failed: {e}")

    with t4:
        st.markdown("#### Reset application filters and dashboard settings")
        st.write("This only clears search boxes, filters, the dashboard period and the low-stock limit. **No database data is changed.**")
        if st.button("Reset Filters & Dashboard Settings"):
            for k in list(st.session_state.keys()):
                if str(k).startswith(("flt_", "set_")):
                    del st.session_state[k]
            flash("success", "Filters and dashboard settings were reset.")
            st.rerun()


# ==================================================================
# MAIN
# ==================================================================
def main():
    if "user" not in st.session_state:
        login()
        return

    admin = is_admin()
    st.sidebar.markdown('<div class="side-brand">💻 Laptop House Buner</div>', unsafe_allow_html=True)
    st.sidebar.markdown(
        f'<div class="side-user">👤 <b>{current_username()}</b><br>'
        f'<small>{"Owner / Admin" if admin else "Staff"}</small></div>', unsafe_allow_html=True)
    st.sidebar.divider()

    pages = {"🏠 Dashboard": dashboard,
             "💻 Laptops": lambda: products_page("Laptop"),
             "🎧 Accessories": lambda: products_page("Accessories"),
             "🖥️ Desktop Computers": lambda: products_page("Desktop"),
             "📦 Other Products": lambda: products_page("Other"),
             "🗂️ All Products": lambda: products_page("All"),
             "🧾 New Sale / Billing": billing_page, "📚 Sales History": sales_history}
    if admin:
        pages.update({"📊 Reports & PDFs": reports, "💹 Income & Expenses": finance_page,
                      "💾 Backup & Export": backup_center,
                      "👥 Staff Management": staff_management, "⚙️ Admin Settings": admin_settings})
    choice = st.sidebar.radio("Navigation", list(pages), label_visibility="collapsed")
    st.sidebar.divider()
    if st.sidebar.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

    flash_msg = st.session_state.pop("flash", None)
    if flash_msg:
        kind, text = flash_msg
        (st.success if kind == "success" else st.error)(text)
        st.toast(text, icon="✅" if kind == "success" else "⚠️")

    pages[choice]()


main()
