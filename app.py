
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("silver_line.db")

PARTNER_TYPES = [
    "Community Partner - Grocery Shop",
    "Community Partner - Barber Shop",
    "Community Partner - Gym",
    "Community Partner - Car Wash / Detailing",
    "Professional Partner - AC Technician",
    "Professional Partner - Property Dealer",
    "Professional Partner - Furniture Store",
    "Professional Partner - Appliance Repair Shop",
    "Professional Partner - Builder / Contractor",
    "Institutional Partner - Employer Partnership",
    "Institutional Partner - Housing Society Activation",
    "Institutional Partner - School / University / Bank / Factory / Hospital"
]

SALE_STATUSES = ["Lead", "In Follow-up", "Closed Sale", "Rejected", "Cancelled"]

def connect():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    con = connect()
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS partners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        partner_code TEXT UNIQUE,
        partner_name TEXT,
        contact_person TEXT,
        phone TEXT,
        city TEXT,
        area TEXT,
        partner_type TEXT,
        status TEXT,
        created_at TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        partner_code TEXT,
        customer_name TEXT,
        customer_phone TEXT,
        product_interest TEXT,
        branch TEXT,
        sale_value REAL,
        commission REAL,
        sale_status TEXT,
        payment_status TEXT,
        created_at TEXT
    )
    """)
    con.commit()
    con.close()

def run_query(query, params=(), fetch=False):
    con = connect()
    if fetch:
        df = pd.read_sql_query(query, con, params=params)
        con.close()
        return df
    cur = con.cursor()
    cur.execute(query, params)
    con.commit()
    con.close()

def generate_partner_code(city, partner_type, partner_id):
    city_code = "".join([c for c in city.upper() if c.isalpha()])[:3] or "RD"
    type_code = partner_type.split("-")[-1].strip().split()[0].upper()[:3]
    return f"SL-{city_code}-{type_code}-{partner_id:04d}"

def add_partner(partner_name, contact_person, phone, city, area, partner_type, status):
    con = connect()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO partners(partner_code, partner_name, contact_person, phone, city, area, partner_type, status, created_at)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, ("TEMP", partner_name, contact_person, phone, city, area, partner_type, status, datetime.now().strftime("%Y-%m-%d %H:%M")))
    partner_id = cur.lastrowid
    code = generate_partner_code(city, partner_type, partner_id)
    cur.execute("UPDATE partners SET partner_code=? WHERE id=?", (code, partner_id))
    con.commit()
    con.close()
    return code

def add_referral(partner_code, customer_name, customer_phone, product_interest, branch, sale_value, sale_status):
    commission = 1000 if sale_status == "Closed Sale" else 0
    payment_status = "Pending" if sale_status == "Closed Sale" else ""
    run_query("""
        INSERT INTO referrals(partner_code, customer_name, customer_phone, product_interest, branch, sale_value, commission, sale_status, payment_status, created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?)
    """, (partner_code, customer_name, customer_phone, product_interest, branch, sale_value, commission, sale_status, payment_status, datetime.now().strftime("%Y-%m-%d %H:%M")))

def get_partners():
    return run_query("SELECT * FROM partners ORDER BY id DESC", fetch=True)

def get_referrals():
    return run_query("SELECT * FROM referrals ORDER BY id DESC", fetch=True)

def format_money(x):
    return f"Rs. {x:,.0f}"

init_db()

st.set_page_config(page_title="RD Silver Line Portal", layout="wide")
st.title("RD Silver Line Partner Portal")
st.caption("Referral partner management system for RD Electronics")

menu = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Add Partner", "Add Referral / Lead", "Partners", "Referrals", "Commission Report"]
)

partners = get_partners()
referrals = get_referrals()

if menu == "Dashboard":
    total_partners = len(partners)
    total_leads = len(referrals)
    closed = referrals[referrals["sale_status"] == "Closed Sale"] if not referrals.empty else referrals
    total_sales = closed["sale_value"].sum() if not closed.empty else 0
    total_commission = closed["commission"].sum() if not closed.empty else 0
    conversion = (len(closed) / total_leads * 100) if total_leads else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Active Partners", total_partners)
    c2.metric("Total Leads", total_leads)
    c3.metric("Closed Sales", len(closed))
    c4.metric("Sales Generated", format_money(total_sales))
    c5.metric("Conversion Rate", f"{conversion:.1f}%")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Sales by Partner Type")
        if not referrals.empty and not partners.empty:
            merged = referrals.merge(partners[["partner_code", "partner_type"]], on="partner_code", how="left")
            chart = merged[merged["sale_status"]=="Closed Sale"].groupby("partner_type")["sale_value"].sum().reset_index()
            if not chart.empty:
                st.bar_chart(chart, x="partner_type", y="sale_value")
            else:
                st.info("No closed sales yet.")
        else:
            st.info("No sales data yet.")

    with col2:
        st.subheader("Lead Status")
        if not referrals.empty:
            st.bar_chart(referrals["sale_status"].value_counts())
        else:
            st.info("No referral data yet.")

    st.subheader("Top Partners")
    if not referrals.empty:
        top = referrals[referrals["sale_status"]=="Closed Sale"].groupby("partner_code").agg(
            closed_sales=("id","count"),
            total_sales=("sale_value","sum"),
            commission=("commission","sum")
        ).reset_index().sort_values("total_sales", ascending=False).head(10)
        st.dataframe(top, use_container_width=True)
    else:
        st.info("No partner performance data yet.")

elif menu == "Add Partner":
    st.subheader("Register Silver Line Partner")
    with st.form("partner_form"):
        partner_name = st.text_input("Partner / Business Name")
        contact_person = st.text_input("Contact Person")
        phone = st.text_input("Phone Number")
        city = st.text_input("City")
        area = st.text_input("Area / Location")
        partner_type = st.selectbox("Partner Type", PARTNER_TYPES)
        status = st.selectbox("Status", ["Active", "Inactive"])
        submitted = st.form_submit_button("Create Partner")
    if submitted:
        if partner_name and phone and city:
            code = add_partner(partner_name, contact_person, phone, city, area, partner_type, status)
            st.success(f"Partner created successfully. Partner Code: {code}")
        else:
            st.error("Partner name, phone and city are required.")

elif menu == "Add Referral / Lead":
    st.subheader("Register Referral / Lead")
    if partners.empty:
        st.warning("Add at least one partner first.")
    else:
        with st.form("referral_form"):
            partner_code = st.selectbox("Partner Code", partners["partner_code"].tolist())
            customer_name = st.text_input("Customer Name")
            customer_phone = st.text_input("Customer Phone")
            product_interest = st.text_input("Product Interest", placeholder="AC, Refrigerator, Washing Machine, LED etc.")
            branch = st.text_input("Nearest RD Branch")
            sale_value = st.number_input("Sale Value", min_value=0.0, step=1000.0)
            sale_status = st.selectbox("Sale Status", SALE_STATUSES)
            submitted = st.form_submit_button("Save Referral")
        if submitted:
            if customer_name and customer_phone:
                add_referral(partner_code, customer_name, customer_phone, product_interest, branch, sale_value, sale_status)
                st.success("Referral saved successfully.")
            else:
                st.error("Customer name and phone are required.")

elif menu == "Partners":
    st.subheader("Silver Line Partners")
    if not partners.empty:
        st.dataframe(partners, use_container_width=True)
        st.download_button("Download Partners CSV", partners.to_csv(index=False), "silver_line_partners.csv")
    else:
        st.info("No partners registered yet.")

elif menu == "Referrals":
    st.subheader("Referral / Lead Records")
    if not referrals.empty:
        status_filter = st.multiselect("Filter by status", SALE_STATUSES, default=SALE_STATUSES)
        filtered = referrals[referrals["sale_status"].isin(status_filter)]
        st.dataframe(filtered, use_container_width=True)
        st.download_button("Download Referrals CSV", filtered.to_csv(index=False), "silver_line_referrals.csv")
    else:
        st.info("No referrals registered yet.")

elif menu == "Commission Report":
    st.subheader("Commission Report")
    if not referrals.empty:
        report = referrals[referrals["sale_status"]=="Closed Sale"].groupby("partner_code").agg(
            closed_sales=("id","count"),
            total_sales=("sale_value","sum"),
            commission_payable=("commission","sum")
        ).reset_index().sort_values("commission_payable", ascending=False)
        st.dataframe(report, use_container_width=True)
        st.download_button("Download Commission Report", report.to_csv(index=False), "commission_report.csv")
    else:
        st.info("No commission data yet.")
