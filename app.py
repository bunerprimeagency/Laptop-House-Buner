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

    pages = {"🏠 Dashboard": dashboard, "📦 Products & Stock": products_page,
             "🧾 New Sale / Billing": billing_page, "📚 Sales History": sales_history}
    if admin:
        pages.update({"📊 Reports & PDFs": reports,
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
