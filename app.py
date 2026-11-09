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
