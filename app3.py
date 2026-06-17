import streamlit as st
import pandas as pd
import json, os, hashlib
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Placement Report System", page_icon="🎓", layout="wide")

# ─── CONSTANTS ──────────────────────────────────────────────────────────────────
USERS_FILE            = "users.json"
ADMINS_FILE           = "admins.json"
DATA_FILE             = "data.json"
SUPER_ADMIN_USER      = "jatin_123"
SUPER_ADMIN_PASS_HASH = hashlib.sha256("jatin@123".encode()).hexdigest()

SCHOOL_OPTIONS       = ["SAHS","SAS","SBS","SBSR","SDAP","SET","SHSS","SMFE","SOE","SSCSE"]
PROGRAM_OPTIONS      = ["MSc","BSc","MBA","BTech","BPT","MPT","BBA","MCom","BA","MA"]
PARTICIPATION_ROUNDS = ["Round 1","Round 2","Round 3","Round 4","Round 5"]

# ─── PERSISTENCE HELPERS ────────────────────────────────────────────────────────
def hash_password(pw): return hashlib.sha256(pw.encode()).hexdigest()

def _load(path):
    if os.path.exists(path):
        with open(path, "r") as f: return json.load(f)
    return {}

def _save(path, obj):
    with open(path, "w") as f: json.dump(obj, f, indent=2, default=str)

def load_users():   return _load(USERS_FILE)
def save_users(u):  _save(USERS_FILE, u)
def load_admins():  return _load(ADMINS_FILE)
def save_admins(a): _save(ADMINS_FILE, a)
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f: return json.load(f)
    return []
def save_data(d): _save(DATA_FILE, d)

def is_super_admin(): return st.session_state.get("username") == SUPER_ADMIN_USER

# ─── GOOGLE SHEETS ──────────────────────────────────────────────────────────────
def get_google_sheet():
    try:
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]),
            scopes=["https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"])
        client = gspread.authorize(creds)
        sh = client.open_by_key(st.secrets["google_sheet"]["sheet_id"])
        try:    return sh.worksheet("PlacementData")
        except: return sh.add_worksheet(title="PlacementData", rows=1000, cols=50)
    except: return None

def push_row_to_sheet(row):
    ws = get_google_sheet()
    if not ws: return
    try:
        existing = ws.get_all_values()
        headers  = list(row.keys())
        if not existing: ws.append_row(headers)
        ws.append_row([str(row.get(h,"")) for h in headers])
    except Exception as e:
        st.warning(f"Sheet push failed: {e}")

def sync_all_to_sheet(data):
    ws = get_google_sheet()
    if not ws or not data: return False
    try:
        df = pd.DataFrame(data)
        ws.clear()
        ws.update([df.columns.tolist()] + df.values.tolist())
        return True
    except Exception as e:
        st.warning(f"Sheet sync failed: {e}")
        return False

def df_to_excel_bytes(df):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Report")
    return buf.getvalue()

# ─── SESSION STATE ───────────────────────────────────────────────────────────────
for k, v in {"logged_in": False, "role": None, "username": None,
              "page": "login", "edit_row_idx": None, "login_role": "Manager"}.items():
    if k not in st.session_state: st.session_state[k] = v

# ─── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.main-header{background:linear-gradient(135deg,#1e3a5f,#2d6a9f);color:white;
  padding:1.5rem 2rem;border-radius:12px;margin-bottom:1.5rem;text-align:center;}
.main-header h1{margin:0;font-size:2rem;}
.main-header p{margin:.3rem 0 0;opacity:.85;}
.metric-box{background:linear-gradient(135deg,#f0f6ff,#e8f0fe);border-radius:10px;
  padding:1rem;text-align:center;border:1px solid #c5d8f5;}
.metric-box h3{margin:0;color:#1e3a5f;font-size:2rem;}
.metric-box p{margin:0;color:#5a7fa5;font-size:.85rem;}
div[data-testid="stButton"]>button{border-radius:8px;font-weight:600;}
</style>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════════════════════
def page_login():
    st.markdown('<div class="main-header"><h1>🎓 Placement Report System</h1><p>Login to continue</p></div>', unsafe_allow_html=True)
    _, col, _ = st.columns([1,1.2,1])
    with col:
        st.markdown("### 👤 Login As")
        r1, r2 = st.columns(2)
        with r1:
            if st.button("🔑 Admin", use_container_width=True,
                         type="primary" if st.session_state.login_role=="Admin" else "secondary"):
                st.session_state.login_role = "Admin"; st.rerun()
        with r2:
            if st.button("👥 Manager", use_container_width=True,
                         type="primary" if st.session_state.login_role=="Manager" else "secondary"):
                st.session_state.login_role = "Manager"; st.rerun()

        st.markdown(f"**Logging in as: {st.session_state.login_role}**")
        st.divider()
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("🚀 Login", use_container_width=True, type="primary"):
            if not username or not password:
                st.error("Please fill both fields."); return
            if st.session_state.login_role == "Admin":
                if username == SUPER_ADMIN_USER and hash_password(password) == SUPER_ADMIN_PASS_HASH:
                    st.session_state.update(logged_in=True, role="super_admin", username=username, page="admin_home"); st.rerun()
                else:
                    admins = load_admins()
                    if username in admins and admins[username]["password"] == hash_password(password):
                        st.session_state.update(logged_in=True, role="admin", username=username, page="admin_home"); st.rerun()
                    else:
                        st.error("❌ Invalid admin credentials.")
            else:
                users = load_users()
                if username in users and users[username]["password"] == hash_password(password):
                    st.session_state.update(logged_in=True, role="manager", username=username, page="manager_home"); st.rerun()
                else:
                    st.error("❌ Invalid manager credentials.")

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    role = st.session_state.role
    label = {"super_admin":"Super Admin","admin":"Admin","manager":"Manager"}.get(role, role)
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown(f"Role: **{label}**")
        st.divider()
        if role in ("super_admin","admin"):
            for pg, icon, txt in [("admin_home","🏠","Dashboard"),
                                   ("manage_managers","👥","Manage Managers"),
                                   ("admin_reports","📋","All Reports")]:
                if st.button(f"{icon} {txt}", use_container_width=True):
                    st.session_state.page = pg; st.rerun()
            if role == "super_admin":
                if st.button("🔑 Manage Admins", use_container_width=True):
                    st.session_state.page = "manage_admins"; st.rerun()
            if st.button("☁️ Sync to Google Sheet", use_container_width=True):
                data = load_data()
                if sync_all_to_sheet(data): st.success("✅ Synced!")
                else: st.info("ℹ️ Configure Google Sheets secrets to enable sync.")
        else:
            for pg, icon, txt in [("manager_home","🏠","Home"),
                                   ("data_entry","➕","New Entry"),
                                   ("preview","📋","My Reports")]:
                if st.button(f"{icon} {txt}", use_container_width=True):
                    st.session_state.page = pg; st.rerun()
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
def page_admin_home():
    label = "Super Admin" if is_super_admin() else "Admin"
    st.markdown(f'<div class="main-header"><h1>🏠 {label} Dashboard</h1><p>Overview of all placement data</p></div>', unsafe_allow_html=True)
    data = load_data(); users = load_users()
    df = pd.DataFrame(data) if data else pd.DataFrame()
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(f'<div class="metric-box"><h3>{len(users)}</h3><p>Managers</p></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-box"><h3>{len(df)}</h3><p>Total Entries</p></div>', unsafe_allow_html=True)
    with c3:
        sel = int(df["Final Selection"].sum()) if not df.empty and "Final Selection" in df.columns else 0
        st.markdown(f'<div class="metric-box"><h3>{sel}</h3><p>Total Selections</p></div>', unsafe_allow_html=True)
    with c4:
        co = df["Company Name"].nunique() if not df.empty and "Company Name" in df.columns else 0
        st.markdown(f'<div class="metric-box"><h3>{co}</h3><p>Companies</p></div>', unsafe_allow_html=True)
    if not df.empty:
        st.divider(); st.subheader("📊 Recent Entries")
        st.dataframe(df.tail(10), use_container_width=True, hide_index=True)
        st.divider()
        c1,c2 = st.columns(2)
        with c1: st.download_button("⬇️ Download All (Excel)", df_to_excel_bytes(df),
            file_name="all_placement_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)
        with c2:
            if st.button("☁️ Sync All to Google Sheet", use_container_width=True, type="primary"):
                if sync_all_to_sheet(data): st.success("✅ Synced!")
                else: st.info("ℹ️ Add Google Sheets credentials in secrets.toml")

# ═══════════════════════════════════════════════════════════════════════════════
# MANAGE MANAGERS  (super_admin + admin)
# ═══════════════════════════════════════════════════════════════════════════════
def _user_manager_ui(users, label_singular, save_fn, reserved_names):
    st.subheader(f"➕ Add New {label_singular}")
    with st.form(f"add_{label_singular}_form"):
        c1,c2,c3 = st.columns(3)
        with c1: nu = st.text_input("Username")
        with c2: nn = st.text_input("Full Name")
        with c3: np_ = st.text_input("Password", type="password")
        if st.form_submit_button(f"Add {label_singular}", type="primary", use_container_width=True):
            if not nu or not nn or not np_:
                st.error("All fields required.")
            elif nu in users or nu in reserved_names:
                st.error("Username already exists!")
            else:
                users[nu] = {"name": nn, "password": hash_password(np_)}
                save_fn(users); st.success(f"✅ {label_singular} '{nn}' added!"); st.rerun()

    st.subheader(f"📋 Current {label_singular}s")
    if not users:
        st.info(f"No {label_singular.lower()}s yet.")
    else:
        for uname, udata in list(users.items()):
            c1,c2,c3,c4 = st.columns([2,2,1,1])
            with c1: st.write(f"**{udata['name']}**")
            with c2: st.write(f"`{uname}`")
            with c3:
                with st.popover("🔑 Change PW"):
                    pw2 = st.text_input("New PW", type="password", key=f"pw_{label_singular}_{uname}")
                    if st.button("Update", key=f"upd_{label_singular}_{uname}"):
                        if pw2:
                            users[uname]["password"] = hash_password(pw2)
                            save_fn(users); st.success("Updated!"); st.rerun()
            with c4:
                if st.button("🗑️ Remove", key=f"del_{label_singular}_{uname}"):
                    del users[uname]; save_fn(users); st.success(f"Removed {uname}"); st.rerun()
            st.divider()

def page_manage_managers():
    st.markdown('<div class="main-header"><h1>👥 Manage Managers</h1></div>', unsafe_allow_html=True)
    users = load_users()
    admins = load_admins()
    reserved = set(admins.keys()) | {SUPER_ADMIN_USER}
    _user_manager_ui(users, "Manager", save_users, reserved)

def page_manage_admins():
    st.markdown('<div class="main-header"><h1>🔑 Manage Admins</h1><p>Only Super Admin can add/remove admins</p></div>', unsafe_allow_html=True)
    admins = load_admins()
    users  = load_users()
    reserved = set(users.keys()) | {SUPER_ADMIN_USER}
    _user_manager_ui(admins, "Admin", save_admins, reserved)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA ENTRY FORM
# ═══════════════════════════════════════════════════════════════════════════════
def data_entry_form(prefill=None, edit_idx=None):
    p = prefill or {}
    is_edit = edit_idx is not None
    st.markdown(f'<div class="main-header"><h1>{"✏️ Edit Entry" if is_edit else "➕ New Data Entry"}</h1></div>', unsafe_allow_html=True)

    with st.form("entry_form"):
        # ── Basic info ───────────────────────────────────────────────────────
        st.subheader("👤 Basic Information")
        c1,c2 = st.columns(2)
        with c1: manager_name = st.text_input("Manager Name *", value=p.get("Manager Name", st.session_state.username))
        with c2:
            fd_val = datetime.strptime(p["Floated Date"],"%Y-%m-%d").date() if p.get("Floated Date") else date.today()
            floated_date = st.date_input("Floated Date *", value=fd_val)

        c1,c2,c3 = st.columns(3)
        with c1:
            fb_opts = ["Superset","Google Form"]
            floated_by = st.selectbox("Floated By *", fb_opts, index=fb_opts.index(p["Floated By"]) if p.get("Floated By") in fb_opts else 0)
        with c2:
            ot_opts = ["Full Time","Intern cum PPO","Only Internship"]
            opp_type = st.selectbox("Opportunity Type *", ot_opts, index=ot_opts.index(p["Opportunity Type"]) if p.get("Opportunity Type") in ot_opts else 0)
        with c3:
            bt_opts = ["2025-2026","2026-2027","2027-2028"]
            batch = st.selectbox("Batch *", bt_opts, index=bt_opts.index(p["Batch"]) if p.get("Batch") in bt_opts else 0)

        # ── Company ──────────────────────────────────────────────────────────
        st.subheader("🏢 Company Details")
        c1,c2,c3 = st.columns(3)
        with c1: company_name   = st.text_input("Company Name *",  value=p.get("Company Name",""))
        with c2:
            cn_opts = ["Core","Non-Core"]
            core_noncore = st.selectbox("Core / Non-Core *", cn_opts, index=cn_opts.index(p["Core/Non-Core"]) if p.get("Core/Non-Core") in cn_opts else 0)
        with c3: company_domain = st.text_input("Company Domain",  value=p.get("Company Domain",""))

        c1,c2 = st.columns(2)
        with c1: job_profile   = st.text_input("Job Profile",  value=p.get("Job Profile",""))
        with c2: job_location  = st.text_input("Job Location", value=p.get("Job Location",""))

        # ── School, Program, Specialization ──────────────────────────────────
        st.subheader("🏫 School, Program & Specialization")
        def_schools  = [s.strip() for s in p["School"].split(",")]  if p.get("School")  else []
        def_programs = [s.strip() for s in p["Program"].split(",")] if p.get("Program") else []
        c1,c2,c3 = st.columns(3)
        with c1:
            schools = st.multiselect("School *", SCHOOL_OPTIONS,
                default=[s for s in def_schools if s in SCHOOL_OPTIONS])
        with c2:
            programs = st.multiselect("Program *", PROGRAM_OPTIONS,
                default=[s for s in def_programs if s in PROGRAM_OPTIONS])
        with c3:
            specialization = st.text_input("Specialization", value=p.get("Specialization",""))

        # ── CTC & Status ─────────────────────────────────────────────────────
        st.subheader("💰 CTC & Status")
        c1,c2,c3,c4 = st.columns(4)
        with c1:
            try:    ctc_val = float(str(p.get("CTC (LPA)","0")).replace(" LPA","").strip())
            except: ctc_val = 0.0
            ctc = st.number_input("CTC (LPA) *", min_value=0.0, step=0.1, value=ctc_val, format="%.2f")
        with c2:
            cs_opts = ["In Process","Cancelled","Hold","Completed","Postponed"]
            company_status = st.selectbox("Company Status *", cs_opts, index=cs_opts.index(p["Company Current Status"]) if p.get("Company Current Status") in cs_opts else 0)
        with c3:
            no_positions = st.number_input("No. of Positions", min_value=0, step=1, value=int(p.get("No. of Positions",0) or 0))
        with c4:
            no_registrations = st.number_input("No. of Registrations", min_value=0, step=1, value=int(p.get("No. of Registrations",0) or 0))

        id_val = datetime.strptime(p["Interview Date"],"%Y-%m-%d").date() if p.get("Interview Date") else date.today()
        interview_date = st.date_input("Interview Date", value=id_val)

        # ── Participations ───────────────────────────────────────────────────
        st.subheader("📊 Participations & Shortlistings")
        participations = {}
        cols5 = st.columns(5)
        for i, rnd in enumerate(PARTICIPATION_ROUNDS):
            with cols5[i]:
                k = f"Participation {rnd}"
                participations[k] = st.number_input(f"Part. {rnd}", min_value=0, step=1,
                    value=int(p.get(k,0) or 0), key=f"part_{i}")
        shortlistings = {}
        cols5b = st.columns(5)
        for i, rnd in enumerate(PARTICIPATION_ROUNDS):
            with cols5b[i]:
                k = f"Shortlisting {rnd}"
                shortlistings[k] = st.number_input(f"Short. {rnd}", min_value=0, step=1,
                    value=int(p.get(k,0) or 0), key=f"short_{i}")

        # ── Selections & Offers ──────────────────────────────────────────────
        st.subheader("🏆 Selections & Offers")
        c1,c2,c3,c4 = st.columns(4)
        with c1:
            se_opts = ["Yes","No"]
            sel_email = st.selectbox("Selection Confirmation Email *", se_opts,
                index=se_opts.index(p["Selection Confirmation Email"]) if p.get("Selection Confirmation Email") in se_opts else 1)
        with c2:
            final_selection = st.number_input("Final Selection", min_value=0, step=1, value=int(p.get("Final Selection",0) or 0))
        with c3:
            offer_received  = st.number_input("Offer Letters Received", min_value=0, step=1, value=int(p.get("Offer Letters Received",0) or 0))
        with c4:
            candidates_joined = st.number_input("Candidates Joined", min_value=0, step=1, value=int(p.get("Candidates Joined",0) or 0))

        # NOTE: Offer Letters Pending is auto-calculated silently and saved to Excel only

        remarks = st.text_area("Remarks", value=p.get("Remarks",""), height=100)
        submitted = st.form_submit_button("💾 Update Entry" if is_edit else "💾 Submit Entry",
            type="primary", use_container_width=True)

    if submitted:
        if not manager_name or not company_name or not schools or not programs:
            st.error("Please fill all required (*) fields."); return
        offer_pending = max(0, final_selection - offer_received)
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
            "Offer Letters Pending": offer_pending,   # silently stored + in Excel
            "Candidates Joined": candidates_joined,
            "Remarks": remarks,
            "Submitted By": st.session_state.username,
            "Submitted At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        data = load_data()
        if is_edit:
            data[edit_idx] = row
            st.success("✅ Entry updated!")
        else:
            data.append(row)
            push_row_to_sheet(row)
            st.success("✅ Entry submitted!")
        save_data(data)
        st.session_state.page = "preview"
        st.session_state.edit_row_idx = None
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# PREVIEW / REPORTS  — full interactive table with inline edit/delete buttons
# ═══════════════════════════════════════════════════════════════════════════════
def page_preview(admin_view=False):
    title = "📋 All Reports" if admin_view else "📋 My Reports"
    st.markdown(f'<div class="main-header"><h1>{title}</h1></div>', unsafe_allow_html=True)

    data = load_data()
    if not data:
        st.info("No data found yet."); return

    df = pd.DataFrame(data)

    if not admin_view:
        df = df[df["Submitted By"] == st.session_state.username].reset_index(drop=True)
        if df.empty:
            st.info("No entries yet.")
            if st.button("➕ Add New Entry", type="primary"):
                st.session_state.page = "data_entry"; st.rerun()
            return

    # ── FILTERS ───────────────────────────────────────────────────────────────
    with st.expander("🔍 Filter Data", expanded=False):
        st.markdown("**Text Search**")
        t1,t2,t3,t4 = st.columns(4)
        with t1: f_company  = st.text_input("Company Name")
        with t2: f_domain   = st.text_input("Company Domain")
        with t3: f_profile  = st.text_input("Job Profile")
        with t4: f_location = st.text_input("Job Location")

        t5,t6,t7,t8 = st.columns(4)
        with t5: f_mgr_name = st.text_input("Manager Name")
        with t6: f_spec     = st.text_input("Specialization")
        with t7: f_school   = st.text_input("School contains")
        with t8: f_program  = st.text_input("Program contains")

        t9,_,__,___ = st.columns(4)
        with t9: f_remarks = st.text_input("Remarks contains")

        st.markdown("**Dropdown Filters**")
        d1,d2,d3,d4 = st.columns(4)
        with d1: f_status    = st.selectbox("Company Status",   ["All","In Process","Cancelled","Hold","Completed","Postponed"])
        with d2: f_batch     = st.selectbox("Batch",            ["All","2025-2026","2026-2027","2027-2028"])
        with d3: f_floated_by = st.selectbox("Floated By",      ["All","Superset","Google Form"])
        with d4: f_opp_type  = st.selectbox("Opportunity Type", ["All","Full Time","Intern cum PPO","Only Internship"])

        d5,d6,d7,d8 = st.columns(4)
        with d5: f_core      = st.selectbox("Core/Non-Core",    ["All","Core","Non-Core"])
        with d6: f_sel_email = st.selectbox("Selection Email",  ["All","Yes","No"])
        with d7: f_submitted_by = st.selectbox("Submitted By",
            ["All"] + sorted(df["Submitted By"].unique().tolist())) if admin_view else st.empty()
        with d8: pass

        st.markdown("**Date Filters**")
        dr1,dr2,dr3,dr4 = st.columns(4)
        with dr1: f_fd_from = st.date_input("Floated Date From",   value=None, key="fdf")
        with dr2: f_fd_to   = st.date_input("Floated Date To",     value=None, key="fdt")
        with dr3: f_id_from = st.date_input("Interview Date From", value=None, key="idf")
        with dr4: f_id_to   = st.date_input("Interview Date To",   value=None, key="idt")

        st.markdown("**Number Range Filters**")
        nr1,nr2,nr3,nr4 = st.columns(4)
        with nr1: f_pos_min = st.number_input("Min Positions",    min_value=0, value=0,     step=1)
        with nr2: f_pos_max = st.number_input("Max Positions",    min_value=0, value=99999, step=1)
        with nr3: f_sel_min = st.number_input("Min Selections",   min_value=0, value=0,     step=1)
        with nr4: f_sel_max = st.number_input("Max Selections",   min_value=0, value=99999, step=1)

    # ── Apply Filters ─────────────────────────────────────────────────────────
    flt = df.copy()
    if f_company:   flt = flt[flt["Company Name"].str.contains(f_company, case=False, na=False)]
    if f_domain:    flt = flt[flt["Company Domain"].str.contains(f_domain, case=False, na=False)]
    if f_profile:   flt = flt[flt["Job Profile"].str.contains(f_profile, case=False, na=False)]
    if f_location:  flt = flt[flt["Job Location"].str.contains(f_location, case=False, na=False)]
    if f_mgr_name:  flt = flt[flt["Manager Name"].str.contains(f_mgr_name, case=False, na=False)]
    if f_spec:      flt = flt[flt["Specialization"].str.contains(f_spec, case=False, na=False)]
    if f_school:    flt = flt[flt["School"].str.contains(f_school, case=False, na=False)]
    if f_program:   flt = flt[flt["Program"].str.contains(f_program, case=False, na=False)]
    if f_remarks:   flt = flt[flt["Remarks"].str.contains(f_remarks, case=False, na=False)]
    if f_status    != "All": flt = flt[flt["Company Current Status"] == f_status]
    if f_batch     != "All": flt = flt[flt["Batch"] == f_batch]
    if f_floated_by!= "All": flt = flt[flt["Floated By"] == f_floated_by]
    if f_opp_type  != "All": flt = flt[flt["Opportunity Type"] == f_opp_type]
    if f_core      != "All": flt = flt[flt["Core/Non-Core"] == f_core]
    if f_sel_email != "All": flt = flt[flt["Selection Confirmation Email"] == f_sel_email]
    if admin_view and isinstance(f_submitted_by, str) and f_submitted_by != "All":
        flt = flt[flt["Submitted By"] == f_submitted_by]
    if f_fd_from and "Floated Date" in flt.columns:
        flt = flt[pd.to_datetime(flt["Floated Date"],errors="coerce") >= pd.Timestamp(f_fd_from)]
    if f_fd_to and "Floated Date" in flt.columns:
        flt = flt[pd.to_datetime(flt["Floated Date"],errors="coerce") <= pd.Timestamp(f_fd_to)]
    if f_id_from and "Interview Date" in flt.columns:
        flt = flt[pd.to_datetime(flt["Interview Date"],errors="coerce") >= pd.Timestamp(f_id_from)]
    if f_id_to and "Interview Date" in flt.columns:
        flt = flt[pd.to_datetime(flt["Interview Date"],errors="coerce") <= pd.Timestamp(f_id_to)]
    if "No. of Positions" in flt.columns:
        flt = flt[pd.to_numeric(flt["No. of Positions"],errors="coerce").fillna(0).between(f_pos_min,f_pos_max)]
    if "Final Selection" in flt.columns:
        flt = flt[pd.to_numeric(flt["Final Selection"],errors="coerce").fillna(0).between(f_sel_min,f_sel_max)]

    # preserve original data.json indices for edit/delete
    flt = flt.reset_index(drop=False).rename(columns={"index":"_orig_idx"})
    display_df = flt.drop(columns=["_orig_idx"], errors="ignore")

    st.markdown(f"**{len(flt)} entries found**")
    st.download_button("⬇️ Download as Excel", df_to_excel_bytes(display_df),
        file_name=f"placement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.divider()

    if flt.empty:
        st.info("No entries match the filters."); return

    # ── Manager can edit/delete; admin/super_admin: read-only ────────────────
    can_modify = (st.session_state.role == "manager")

    # ── Build interactive rows ────────────────────────────────────────────────
    st.markdown("#### 📊 Data Table")
    if can_modify:
        st.caption("Expand any row to see all details and use ✏️ Edit or 🗑️ Delete buttons.")
    else:
        st.caption("Read-only view. Scroll right to see all columns.")

    # Full scrollable table at top
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=420)

    if not can_modify:
        return  # admins only see the table, no edit/delete

    st.divider()
    st.markdown("#### ✏️ Edit or Delete your entries")

    for _, row in flt.iterrows():
        orig_i  = int(row["_orig_idx"])
        company = row.get("Company Name","—")
        fdate   = row.get("Floated Date","—")
        status  = row.get("Company Current Status","—")
        batch_v = row.get("Batch","—")

        with st.expander(f"📌 {company}  |  {fdate}  |  {batch_v}  |  {status}"):
            # All columns in 3-col grid
            items = [(k, v) for k, v in row.items() if k != "_orig_idx"]
            for chunk in [items[i:i+3] for i in range(0,len(items),3)]:
                cols = st.columns(3)
                for ci,(k,v) in enumerate(chunk):
                    with cols[ci]:
                        st.markdown(f"**{k}**")
                        st.write(str(v) if v not in [None,""] else "—")
            st.markdown("")
            ec, dc = st.columns(2)
            with ec:
                if st.button("✏️ Edit", key=f"edit_{orig_i}", use_container_width=True, type="primary"):
                    st.session_state.edit_row_idx = orig_i
                    st.session_state.page = "edit_entry"; st.rerun()
            with dc:
                if st.button("🗑️ Delete", key=f"del_{orig_i}", use_container_width=True):
                    all_data = load_data(); all_data.pop(orig_i)
                    save_data(all_data); st.success("Entry deleted."); st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# MANAGER HOME
# ═══════════════════════════════════════════════════════════════════════════════
def page_manager_home():
    uname = st.session_state.username
    name  = load_users().get(uname,{}).get("name", uname)
    st.markdown(f'<div class="main-header"><h1>👋 Welcome, {name}!</h1><p>Placement Data Entry Portal</p></div>', unsafe_allow_html=True)
    data = load_data()
    my   = [r for r in data if r.get("Submitted By") == uname]
    c1,c2,c3 = st.columns(3)
    with c1: st.markdown(f'<div class="metric-box"><h3>{len(my)}</h3><p>My Total Entries</p></div>', unsafe_allow_html=True)
    with c2:
        sel = sum(int(r.get("Final Selection",0) or 0) for r in my)
        st.markdown(f'<div class="metric-box"><h3>{sel}</h3><p>Total Selections</p></div>', unsafe_allow_html=True)
    with c3:
        co = len(set(r.get("Company Name","") for r in my))
        st.markdown(f'<div class="metric-box"><h3>{co}</h3><p>Companies</p></div>', unsafe_allow_html=True)
    st.divider()
    c1,c2 = st.columns(2)
    with c1:
        if st.button("➕ New Data Entry", use_container_width=True, type="primary"):
            st.session_state.page = "data_entry"; st.rerun()
    with c2:
        if st.button("📋 View My Reports", use_container_width=True):
            st.session_state.page = "preview"; st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    if not st.session_state.logged_in:
        page_login(); return
    render_sidebar()
    pg   = st.session_state.page
    role = st.session_state.role
    if   pg == "admin_home":       page_admin_home()
    elif pg == "manage_managers":  page_manage_managers()
    elif pg == "manage_admins":
        if role == "super_admin":  page_manage_admins()
        else: st.error("Access denied.")
    elif pg == "admin_reports":    page_preview(admin_view=True)
    elif pg == "manager_home":     page_manager_home()
    elif pg == "data_entry":       data_entry_form()
    elif pg == "edit_entry":
        idx = st.session_state.edit_row_idx
        if idx is not None:
            d = load_data(); data_entry_form(prefill=d[idx], edit_idx=idx)
        else:
            st.session_state.page = "preview"; st.rerun()
    elif pg == "preview":
        page_preview(admin_view=(role in ("admin","super_admin")))

main()
