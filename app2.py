import streamlit as st
import pandas as pd
import json
import os
import hashlib
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Placement Report System",
    page_icon="🎓",
    layout="wide"
)

# ─── CONSTANTS ──────────────────────────────────────────────────────────────────
USERS_FILE = "users.json"
DATA_FILE  = "data.json"
ADMIN_USER = "jatin_123"
ADMIN_PASS_HASH = hashlib.sha256("jatin@123".encode()).hexdigest()

SCHOOL_OPTIONS = ["SAHS","SAS","SBS","SBSR","SDAP","SET","SHSS","SMFE","SOE","SSCSE"]
PROGRAM_OPTIONS = ["MSc","BSc","MBA","BTech","BPT","MPT","BBA","MCom","BA","MA"]
PARTICIPATION_ROUNDS = ["Round 1","Round 2","Round 3","Round 4","Round 5"]

# ─── HELPERS ────────────────────────────────────────────────────────────────────
def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def load_users() -> dict:
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def load_data() -> list:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_data(data: list):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

def get_google_sheet():
    """Connect to Google Sheets using service account from secrets."""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet_id = st.secrets["google_sheet"]["sheet_id"]
        sh = client.open_by_key(sheet_id)
        try:
            worksheet = sh.worksheet("PlacementData")
        except:
            worksheet = sh.add_worksheet(title="PlacementData", rows=1000, cols=30)
        return worksheet
    except Exception as e:
        return None

def push_row_to_sheet(row: dict):
    """Append a single row to Google Sheet."""
    ws = get_google_sheet()
    if ws is None:
        return False
    try:
        existing = ws.get_all_values()
        headers = list(row.keys())
        if not existing:
            ws.append_row(headers)
        ws.append_row([str(row.get(h, "")) for h in headers])
        return True
    except Exception as e:
        st.warning(f"Google Sheet push failed: {e}")
        return False

def sync_all_to_sheet(data: list):
    """Full sync – rewrites entire sheet."""
    ws = get_google_sheet()
    if ws is None or not data:
        return False
    try:
        df = pd.DataFrame(data)
        ws.clear()
        ws.update([df.columns.tolist()] + df.values.tolist())
        return True
    except Exception as e:
        st.warning(f"Google Sheet sync failed: {e}")
        return False

def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
    return buf.getvalue()

# ─── SESSION STATE ───────────────────────────────────────────────────────────────
def init_session():
    defaults = {
        "logged_in": False,
        "role": None,          # "admin" | "manager"
        "username": None,
        "page": "login",       # login | admin_home | manager_home | data_entry | preview
        "edit_row_idx": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ─── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .main-header h1 { margin: 0; font-size: 2rem; }
    .main-header p  { margin: 0.3rem 0 0; opacity: 0.85; }

    .card {
        background: white;
        border: 1px solid #e0e7ef;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    .metric-box {
        background: linear-gradient(135deg, #f0f6ff, #e8f0fe);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        border: 1px solid #c5d8f5;
    }
    .metric-box h3 { margin: 0; color: #1e3a5f; font-size: 2rem; }
    .metric-box p  { margin: 0; color: #5a7fa5; font-size: 0.85rem; }

    div[data-testid="stButton"] > button {
        border-radius: 8px;
        font-weight: 600;
    }
    .stDataFrame { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ═══════════════════════════════════════════════════════════════════════════════
def page_login():
    st.markdown("""
    <div class="main-header">
        <h1>🎓 Placement Report System</h1>
        <p>Login to continue</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        # ── Role selector ────────────────────────────────────────────────────
        st.markdown("### 👤 Login As")
        role_col1, role_col2 = st.columns(2)

        if "login_role" not in st.session_state:
            st.session_state.login_role = "Manager"

        with role_col1:
            admin_style = "primary" if st.session_state.login_role == "Admin" else "secondary"
            if st.button("🔑 Admin", use_container_width=True, type=admin_style):
                st.session_state.login_role = "Admin"
                st.rerun()
        with role_col2:
            mgr_style = "primary" if st.session_state.login_role == "Manager" else "secondary"
            if st.button("👥 Manager", use_container_width=True, type=mgr_style):
                st.session_state.login_role = "Manager"
                st.rerun()

        st.markdown(f"**Logging in as: {st.session_state.login_role}**")
        st.divider()

        # ── Credentials ──────────────────────────────────────────────────────
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password", placeholder="Enter password")

        if st.button("🚀 Login", use_container_width=True, type="primary"):
            if not username or not password:
                st.error("Please enter username and password.")
                return

            if st.session_state.login_role == "Admin":
                if username == ADMIN_USER and hash_password(password) == ADMIN_PASS_HASH:
                    st.session_state.logged_in = True
                    st.session_state.role = "admin"
                    st.session_state.username = username
                    st.session_state.page = "admin_home"
                    st.rerun()
                else:
                    st.error("❌ Invalid admin credentials.")
            else:
                users = load_users()
                if username in users and users[username]["password"] == hash_password(password):
                    st.session_state.logged_in = True
                    st.session_state.role = "manager"
                    st.session_state.username = username
                    st.session_state.page = "manager_home"
                    st.rerun()
                else:
                    st.error("❌ Invalid manager credentials.")

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown(f"Role: **{'Admin' if st.session_state.role == 'admin' else 'Manager'}**")
        st.divider()

        if st.session_state.role == "admin":
            if st.button("🏠 Dashboard", use_container_width=True):
                st.session_state.page = "admin_home"
                st.rerun()
            if st.button("👥 Manage Managers", use_container_width=True):
                st.session_state.page = "manage_managers"
                st.rerun()
            if st.button("📋 All Reports", use_container_width=True):
                st.session_state.page = "admin_reports"
                st.rerun()
            if st.button("☁️ Sync to Google Sheet", use_container_width=True):
                data = load_data()
                if sync_all_to_sheet(data):
                    st.success("✅ Synced!")
                else:
                    st.info("ℹ️ Configure Google Sheets in secrets to enable sync.")
        else:
            if st.button("🏠 Home", use_container_width=True):
                st.session_state.page = "manager_home"
                st.rerun()
            if st.button("➕ New Entry", use_container_width=True):
                st.session_state.page = "data_entry"
                st.rerun()
            if st.button("📋 My Reports", use_container_width=True):
                st.session_state.page = "preview"
                st.rerun()

        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN – DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
def page_admin_home():
    st.markdown('<div class="main-header"><h1>🏠 Admin Dashboard</h1><p>Overview of all placement data</p></div>', unsafe_allow_html=True)
    data  = load_data()
    users = load_users()
    df    = pd.DataFrame(data) if data else pd.DataFrame()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-box"><h3>{len(users)}</h3><p>Total Managers</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-box"><h3>{len(df)}</h3><p>Total Entries</p></div>', unsafe_allow_html=True)
    with c3:
        total_sel = int(df["Final Selection"].sum()) if not df.empty and "Final Selection" in df.columns else 0
        st.markdown(f'<div class="metric-box"><h3>{total_sel}</h3><p>Total Selections</p></div>', unsafe_allow_html=True)
    with c4:
        companies = df["Company Name"].nunique() if not df.empty and "Company Name" in df.columns else 0
        st.markdown(f'<div class="metric-box"><h3>{companies}</h3><p>Companies</p></div>', unsafe_allow_html=True)

    if not df.empty:
        st.markdown("---")
        st.subheader("📊 Recent Entries")
        st.dataframe(df.tail(10), use_container_width=True, hide_index=True)

        st.markdown("---")
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            excel_bytes = df_to_excel_bytes(df)
            st.download_button("⬇️ Download All Data (Excel)", excel_bytes,
                               file_name="all_placement_data.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
        with col_dl2:
            if st.button("☁️ Sync All to Google Sheet", use_container_width=True, type="primary"):
                if sync_all_to_sheet(data):
                    st.success("✅ Synced successfully!")
                else:
                    st.info("ℹ️ Add Google Sheets credentials in secrets.toml to enable sync.")

# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN – MANAGE MANAGERS
# ═══════════════════════════════════════════════════════════════════════════════
def page_manage_managers():
    st.markdown('<div class="main-header"><h1>👥 Manage Managers</h1></div>', unsafe_allow_html=True)
    users = load_users()

    # Add new manager
    st.subheader("➕ Add New Manager")
    with st.form("add_manager_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_user = st.text_input("Username", placeholder="e.g. manager_rahul")
        with col2:
            new_name = st.text_input("Full Name", placeholder="e.g. Rahul Sharma")
        with col3:
            new_pass = st.text_input("Password", type="password", placeholder="Set password")
        submitted = st.form_submit_button("Add Manager", type="primary", use_container_width=True)
        if submitted:
            if not new_user or not new_name or not new_pass:
                st.error("All fields are required.")
            elif new_user in users or new_user == ADMIN_USER:
                st.error("Username already exists!")
            else:
                users[new_user] = {"name": new_name, "password": hash_password(new_pass)}
                save_users(users)
                st.success(f"✅ Manager '{new_name}' added with username '{new_user}'")
                st.rerun()

    # List managers
    st.subheader("📋 Current Managers")
    if not users:
        st.info("No managers added yet.")
    else:
        for uname, udata in users.items():
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            with col1:
                st.write(f"**{udata['name']}**")
            with col2:
                st.write(f"`{uname}`")
            with col3:
                with st.popover("🔑 Change Password"):
                    new_pw = st.text_input("New password", type="password", key=f"pw_{uname}")
                    if st.button("Update", key=f"upd_{uname}"):
                        if new_pw:
                            users[uname]["password"] = hash_password(new_pw)
                            save_users(users)
                            st.success("Updated!")
                            st.rerun()
            with col4:
                if st.button("🗑️ Remove", key=f"del_{uname}"):
                    del users[uname]
                    save_users(users)
                    st.success(f"Removed {uname}")
                    st.rerun()
            st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# DATA ENTRY FORM
# ═══════════════════════════════════════════════════════════════════════════════
def data_entry_form(prefill: dict = None, edit_idx: int = None):
    """Renders the data entry form. If prefill provided, used for editing."""
    p = prefill or {}
    is_edit = edit_idx is not None

    st.markdown(f'<div class="main-header"><h1>{"✏️ Edit Entry" if is_edit else "➕ New Data Entry"}</h1></div>', unsafe_allow_html=True)

    with st.form("entry_form"):
        st.subheader("👤 Basic Information")
        c1, c2 = st.columns(2)
        with c1:
            manager_name = st.text_input("Manager Name *", value=p.get("Manager Name", st.session_state.username))
        with c2:
            floated_date = st.date_input("Floated Date *",
                value=datetime.strptime(p["Floated Date"], "%Y-%m-%d").date() if p.get("Floated Date") else date.today())

        c1, c2, c3 = st.columns(3)
        with c1:
            floated_by = st.selectbox("Floated By *",
                ["Superset", "Google Form"],
                index=["Superset","Google Form"].index(p["Floated By"]) if p.get("Floated By") else 0)
        with c2:
            opp_type = st.selectbox("Opportunity Type *",
                ["Full Time","Intern cum PPO","Only Internship"],
                index=["Full Time","Intern cum PPO","Only Internship"].index(p["Opportunity Type"]) if p.get("Opportunity Type") else 0)
        with c3:
            batch = st.selectbox("Batch *",
                ["2025-2026","2026-2027","2027-2028"],
                index=["2025-2026","2026-2027","2027-2028"].index(p["Batch"]) if p.get("Batch") else 0)

        st.subheader("🏢 Company Details")
        c1, c2, c3 = st.columns(3)
        with c1:
            company_name = st.text_input("Company Name *", value=p.get("Company Name", ""))
        with c2:
            core_noncore = st.selectbox("Core / Non-Core *",
                ["Core","Non-Core"],
                index=["Core","Non-Core"].index(p["Core/Non-Core"]) if p.get("Core/Non-Core") else 0)
        with c3:
            company_domain = st.text_input("Company Domain", value=p.get("Company Domain", ""))

        c1, c2, c3 = st.columns(3)
        with c1:
            job_profile  = st.text_input("Job Profile", value=p.get("Job Profile", ""))
        with c2:
            job_location = st.text_input("Job Location", value=p.get("Job Location", ""))
        with c3:
            specialization = st.text_input("Specialization", value=p.get("Specialization", ""))

        # Schools (multi-select)
        st.subheader("🏫 School & Program")
        default_schools = [s.strip() for s in p["School"].split(",")] if p.get("School") else []
        schools = st.multiselect("School (select all applicable) *",
            SCHOOL_OPTIONS, default=[s for s in default_schools if s in SCHOOL_OPTIONS])

        default_programs = [s.strip() for s in p["Program"].split(",")] if p.get("Program") else []
        programs = st.multiselect("Program (select all applicable) *",
            PROGRAM_OPTIONS, default=[s for s in default_programs if s in PROGRAM_OPTIONS])

        # CTC & Status
        st.subheader("💰 CTC & Status")
        c1, c2, c3 = st.columns(3)
        with c1:
            ctc = st.number_input("CTC (LPA) *", min_value=0.0, step=0.1,
                value=float(p["CTC (LPA)"].replace(" LPA","")) if p.get("CTC (LPA)") else 0.0,
                format="%.2f")
        with c2:
            company_status = st.selectbox("Company Current Status *",
                ["In Process","Cancelled","Hold","Completed","Postponed"],
                index=["In Process","Cancelled","Hold","Completed","Postponed"].index(p["Company Current Status"]) if p.get("Company Current Status") else 0)
        with c3:
            no_positions = st.number_input("No. of Positions", min_value=0, step=1,
                value=int(p.get("No. of Positions", 0) or 0))

        c1, c2 = st.columns(2)
        with c1:
            no_registrations = st.number_input("No. of Registrations", min_value=0, step=1,
                value=int(p.get("No. of Registrations", 0) or 0))
        with c2:
            interview_date = st.date_input("Interview Date",
                value=datetime.strptime(p["Interview Date"], "%Y-%m-%d").date() if p.get("Interview Date") else date.today())

        # Participations
        st.subheader("📊 Rounds & Shortlistings")
        c_cols = st.columns(5)
        participations = {}
        for i, rnd in enumerate(PARTICIPATION_ROUNDS):
            with c_cols[i]:
                pkey = f"Participation {rnd}"
                participations[pkey] = st.number_input(f"Part. {rnd}", min_value=0, step=1,
                    value=int(p.get(pkey, 0) or 0), key=f"part_{i}")

        c_cols2 = st.columns(5)
        shortlistings = {}
        for i, rnd in enumerate(PARTICIPATION_ROUNDS):
            with c_cols2[i]:
                skey = f"Shortlisting {rnd}"
                shortlistings[skey] = st.number_input(f"Short. {rnd}", min_value=0, step=1,
                    value=int(p.get(skey, 0) or 0), key=f"short_{i}")

        # Selections & Offer Letters
        st.subheader("🏆 Selections & Offers")
        c1, c2, c3 = st.columns(3)
        with c1:
            sel_email = st.selectbox("Selection Confirmation Email Received *",
                ["Yes","No"],
                index=["Yes","No"].index(p["Selection Confirmation Email"]) if p.get("Selection Confirmation Email") else 1)
        with c2:
            final_selection = st.number_input("Final Selection", min_value=0, step=1,
                value=int(p.get("Final Selection", 0) or 0))
        with c3:
            offer_received = st.number_input("Offer Letters Received", min_value=0, step=1,
                value=int(p.get("Offer Letters Received", 0) or 0))

        offer_pending_calc = max(0, final_selection - offer_received)
        st.info(f"📌 Offer Letters Pending (auto-calculated): **{offer_pending_calc}**")

        candidates_joined = st.number_input("No. of Candidates Joined", min_value=0, step=1,
            value=int(p.get("Candidates Joined", 0) or 0))

        remarks = st.text_area("Remarks", value=p.get("Remarks", ""), height=100)

        submitted = st.form_submit_button(
            "💾 Update Entry" if is_edit else "💾 Submit Entry",
            type="primary", use_container_width=True)

    if submitted:
        if not manager_name or not company_name or not schools or not programs:
            st.error("Please fill all required (*) fields.")
            return

        row = {
            "Manager Name": manager_name,
            "Floated Date": str(floated_date),
            "Floated By": floated_by,
            "Opportunity Type": opp_type,
            "Batch": batch,
            "Company Name": company_name,
            "Core/Non-Core": core_noncore,
            "Company Domain": company_domain,
            "Job Profile": job_profile,
            "Job Location": job_location,
            "School": ", ".join(schools),
            "Program": ", ".join(programs),
            "Specialization": specialization,
            "CTC (LPA)": f"{ctc:.2f} LPA",
            "Company Current Status": company_status,
            "No. of Positions": no_positions,
            "No. of Registrations": no_registrations,
            "Interview Date": str(interview_date),
            **participations,
            **shortlistings,
            "Selection Confirmation Email": sel_email,
            "Final Selection": final_selection,
            "Offer Letters Received": offer_received,
            "Offer Letters Pending": offer_pending_calc,
            "Candidates Joined": candidates_joined,
            "Remarks": remarks,
            "Submitted By": st.session_state.username,
            "Submitted At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        data = load_data()
        if is_edit:
            data[edit_idx] = row
            st.success("✅ Entry updated successfully!")
        else:
            data.append(row)
            push_row_to_sheet(row)
            st.success("✅ Entry submitted successfully!")

        save_data(data)
        st.session_state.page = "preview"
        st.session_state.edit_row_idx = None
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# PREVIEW / MY REPORTS
# ═══════════════════════════════════════════════════════════════════════════════
def page_preview(admin_view: bool = False):
    st.markdown(f'<div class="main-header"><h1>{"📋 All Reports" if admin_view else "📋 My Reports"}</h1></div>', unsafe_allow_html=True)

    data = load_data()
    if not data:
        st.info("No data found.")
        return

    df = pd.DataFrame(data)

    if not admin_view:
        df = df[df["Submitted By"] == st.session_state.username].reset_index(drop=True)
        if df.empty:
            st.info("You haven't submitted any entries yet.")
            if st.button("➕ Add New Entry", type="primary"):
                st.session_state.page = "data_entry"
                st.rerun()
            return

    # ── ALL-COLUMN FILTERS ────────────────────────────────────────────────────
    with st.expander("🔍 Filter Data", expanded=False):
        st.markdown("**Text Search Filters**")
        t1, t2, t3, t4 = st.columns(4)
        with t1:
            f_company     = st.text_input("Company Name")
        with t2:
            f_domain      = st.text_input("Company Domain")
        with t3:
            f_profile     = st.text_input("Job Profile")
        with t4:
            f_location    = st.text_input("Job Location")

        t5, t6, t7, t8 = st.columns(4)
        with t5:
            f_manager_name = st.text_input("Manager Name")
        with t6:
            f_spec        = st.text_input("Specialization")
        with t7:
            f_remarks     = st.text_input("Remarks contains")
        with t8:
            f_school      = st.text_input("School contains")

        st.markdown("**Dropdown Filters**")
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            f_status = st.selectbox("Company Status", ["All","In Process","Cancelled","Hold","Completed","Postponed"])
        with d2:
            f_batch  = st.selectbox("Batch", ["All","2025-2026","2026-2027","2027-2028"])
        with d3:
            f_floated_by = st.selectbox("Floated By", ["All","Superset","Google Form"])
        with d4:
            f_opp_type = st.selectbox("Opportunity Type", ["All","Full Time","Intern cum PPO","Only Internship"])

        d5, d6, d7, d8 = st.columns(4)
        with d5:
            f_core = st.selectbox("Core/Non-Core", ["All","Core","Non-Core"])
        with d6:
            f_sel_email = st.selectbox("Selection Email Received", ["All","Yes","No"])
        with d7:
            f_program = st.text_input("Program contains")
        with d8:
            if admin_view:
                mgr_list = ["All"] + sorted(df["Submitted By"].unique().tolist())
                f_mgr = st.selectbox("Submitted By (Manager)", mgr_list)
            else:
                f_mgr = "All"

        st.markdown("**Date Filters**")
        dt1, dt2, dt3, dt4 = st.columns(4)
        with dt1:
            f_floated_date_from = st.date_input("Floated Date From", value=None, key="fdf")
        with dt2:
            f_floated_date_to   = st.date_input("Floated Date To",   value=None, key="fdt")
        with dt3:
            f_interview_from    = st.date_input("Interview Date From", value=None, key="idf")
        with dt4:
            f_interview_to      = st.date_input("Interview Date To",   value=None, key="idt")

        st.markdown("**Number Range Filters**")
        n1, n2, n3, n4 = st.columns(4)
        with n1:
            f_pos_min = st.number_input("Min Positions", min_value=0, value=0, step=1)
        with n2:
            f_pos_max = st.number_input("Max Positions", min_value=0, value=99999, step=1)
        with n3:
            f_sel_min = st.number_input("Min Final Selections", min_value=0, value=0, step=1)
        with n4:
            f_sel_max = st.number_input("Max Final Selections", min_value=0, value=99999, step=1)

    # ── Apply Filters ─────────────────────────────────────────────────────────
    filtered = df.copy()

    # text filters
    if f_company:
        filtered = filtered[filtered["Company Name"].str.contains(f_company, case=False, na=False)]
    if f_domain:
        filtered = filtered[filtered["Company Domain"].str.contains(f_domain, case=False, na=False)]
    if f_profile:
        filtered = filtered[filtered["Job Profile"].str.contains(f_profile, case=False, na=False)]
    if f_location:
        filtered = filtered[filtered["Job Location"].str.contains(f_location, case=False, na=False)]
    if f_manager_name:
        filtered = filtered[filtered["Manager Name"].str.contains(f_manager_name, case=False, na=False)]
    if f_spec:
        filtered = filtered[filtered["Specialization"].str.contains(f_spec, case=False, na=False)]
    if f_remarks:
        filtered = filtered[filtered["Remarks"].str.contains(f_remarks, case=False, na=False)]
    if f_school:
        filtered = filtered[filtered["School"].str.contains(f_school, case=False, na=False)]
    if f_program:
        filtered = filtered[filtered["Program"].str.contains(f_program, case=False, na=False)]

    # dropdown filters
    if f_status    != "All": filtered = filtered[filtered["Company Current Status"] == f_status]
    if f_batch     != "All": filtered = filtered[filtered["Batch"] == f_batch]
    if f_floated_by != "All": filtered = filtered[filtered["Floated By"] == f_floated_by]
    if f_opp_type  != "All": filtered = filtered[filtered["Opportunity Type"] == f_opp_type]
    if f_core      != "All": filtered = filtered[filtered["Core/Non-Core"] == f_core]
    if f_sel_email != "All": filtered = filtered[filtered["Selection Confirmation Email"] == f_sel_email]
    if f_mgr       != "All": filtered = filtered[filtered["Submitted By"] == f_mgr]

    # date filters
    if f_floated_date_from and "Floated Date" in filtered.columns:
        filtered = filtered[pd.to_datetime(filtered["Floated Date"], errors="coerce") >= pd.Timestamp(f_floated_date_from)]
    if f_floated_date_to and "Floated Date" in filtered.columns:
        filtered = filtered[pd.to_datetime(filtered["Floated Date"], errors="coerce") <= pd.Timestamp(f_floated_date_to)]
    if f_interview_from and "Interview Date" in filtered.columns:
        filtered = filtered[pd.to_datetime(filtered["Interview Date"], errors="coerce") >= pd.Timestamp(f_interview_from)]
    if f_interview_to and "Interview Date" in filtered.columns:
        filtered = filtered[pd.to_datetime(filtered["Interview Date"], errors="coerce") <= pd.Timestamp(f_interview_to)]

    # number filters
    if "No. of Positions" in filtered.columns:
        filtered = filtered[pd.to_numeric(filtered["No. of Positions"], errors="coerce").fillna(0).between(f_pos_min, f_pos_max)]
    if "Final Selection" in filtered.columns:
        filtered = filtered[pd.to_numeric(filtered["Final Selection"], errors="coerce").fillna(0).between(f_sel_min, f_sel_max)]

    filtered = filtered.reset_index(drop=False).rename(columns={"index": "_orig_idx"})

    st.markdown(f"**{len(filtered)} entries found**")

    # ── Download ──────────────────────────────────────────────────────────────
    display_df = filtered.drop(columns=["_orig_idx"], errors="ignore")
    excel_bytes = df_to_excel_bytes(display_df)
    st.download_button("⬇️ Download as Excel", excel_bytes,
        file_name=f"placement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.divider()

    # ── Full-width table (Excel-style) with Edit per row ─────────────────────
    if filtered.empty:
        st.info("No entries match the filters.")
        return

    # Show full dataframe table (scrollable, all columns)
    st.markdown("#### 📊 Data Table (all columns)")
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)

    st.divider()
    st.markdown("#### ✏️ Edit / Delete Entries")
    st.caption("Click Edit on any row below to modify it.")

    for display_i, row in filtered.iterrows():
        orig_i = int(row["_orig_idx"])
        label = f"📌 {row.get('Company Name','—')}  |  {row.get('Floated Date','—')}  |  {row.get('Batch','—')}  |  {row.get('Company Current Status','—')}"
        with st.expander(label):
            # Show ALL columns in a clean 3-column grid
            items = [(k, v) for k, v in row.items() if k != "_orig_idx"]
            num_cols = 3
            rows_grid = [items[i:i+num_cols] for i in range(0, len(items), num_cols)]
            for row_chunk in rows_grid:
                cols = st.columns(num_cols)
                for ci, (k, v) in enumerate(row_chunk):
                    with cols[ci]:
                        st.markdown(f"**{k}**")
                        st.write(v if v not in [None, ""] else "—")

            st.markdown("")
            edit_col, del_col = st.columns([1, 1])
            with edit_col:
                if st.button("✏️ Edit this entry", key=f"edit_{orig_i}_{display_i}"):
                    st.session_state.edit_row_idx = orig_i
                    st.session_state.page = "edit_entry"
                    st.rerun()
            if admin_view:
                with del_col:
                    if st.button("🗑️ Delete", key=f"del_{orig_i}_{display_i}"):
                        data_all = load_data()
                        data_all.pop(orig_i)
                        save_data(data_all)
                        st.success("Deleted.")
                        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# MANAGER HOME
# ═══════════════════════════════════════════════════════════════════════════════
def page_manager_home():
    users = load_users()
    uname = st.session_state.username
    name  = users.get(uname, {}).get("name", uname)

    st.markdown(f'<div class="main-header"><h1>👋 Welcome, {name}!</h1><p>Placement Data Entry Portal</p></div>', unsafe_allow_html=True)

    data = load_data()
    my_entries = [r for r in data if r.get("Submitted By") == uname]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="metric-box"><h3>{len(my_entries)}</h3><p>My Total Entries</p></div>', unsafe_allow_html=True)
    with c2:
        sel = sum(int(r.get("Final Selection", 0) or 0) for r in my_entries)
        st.markdown(f'<div class="metric-box"><h3>{sel}</h3><p>Total Selections</p></div>', unsafe_allow_html=True)
    with c3:
        companies = len(set(r.get("Company Name","") for r in my_entries))
        st.markdown(f'<div class="metric-box"><h3>{companies}</h3><p>Companies</p></div>', unsafe_allow_html=True)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ New Data Entry", use_container_width=True, type="primary"):
            st.session_state.page = "data_entry"
            st.rerun()
    with col2:
        if st.button("📋 View My Reports", use_container_width=True):
            st.session_state.page = "preview"
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    if not st.session_state.logged_in:
        page_login()
        return

    render_sidebar()
    page = st.session_state.page

    if page == "admin_home":
        page_admin_home()
    elif page == "manage_managers":
        page_manage_managers()
    elif page == "admin_reports":
        page_preview(admin_view=True)
    elif page == "manager_home":
        page_manager_home()
    elif page == "data_entry":
        data_entry_form()
    elif page == "edit_entry":
        idx = st.session_state.edit_row_idx
        if idx is not None:
            data = load_data()
            data_entry_form(prefill=data[idx], edit_idx=idx)
        else:
            st.session_state.page = "preview"
            st.rerun()
    elif page == "preview":
        is_admin = st.session_state.role == "admin"
        page_preview(admin_view=is_admin)

main()
