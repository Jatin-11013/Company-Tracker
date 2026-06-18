import streamlit as st
import pandas as pd
import json, os, hashlib
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

st.set_page_config(page_title="Placement Report System", page_icon="🎓", layout="wide")

# ─── CONSTANTS ───────────────────────────────────────────────────────────────
USERS_FILE            = "users.json"
ADMINS_FILE           = "admins.json"
DATA_FILE             = "data.json"
SUPER_ADMIN_USER      = "jatin_123"
SUPER_ADMIN_PASS_HASH = hashlib.sha256("jatin@123".encode()).hexdigest()
SCHOOL_OPTIONS        = ["SAHS","SAS","SBS","SBSR","SDAP","SET","SHSS","SMFE","SOE","SSCSE"]
PROGRAM_OPTIONS       = ["MSc","BSc","MBA","BTech","BPT","MPT","BBA","MCom","BA","MA"]
PARTICIPATION_ROUNDS  = ["Round 1","Round 2","Round 3","Round 4","Round 5"]

# ─── PERSISTENCE ─────────────────────────────────────────────────────────────
def hash_password(pw): return hashlib.sha256(pw.encode()).hexdigest()
def _load(p): return json.load(open(p)) if os.path.exists(p) else {}
def _save(p, o):
    with open(p,"w") as f: json.dump(o, f, indent=2, default=str)
def load_users():   return _load(USERS_FILE)
def save_users(u):  _save(USERS_FILE, u)
def load_admins():  return _load(ADMINS_FILE)
def save_admins(a): _save(ADMINS_FILE, a)
def load_data():    return json.load(open(DATA_FILE)) if os.path.exists(DATA_FILE) else []
def save_data(d):   _save(DATA_FILE, d)
def is_super_admin(): return st.session_state.get("username") == SUPER_ADMIN_USER

# ─── GOOGLE SHEETS ────────────────────────────────────────────────────────────
def get_ws():
    try:
        creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]),
            scopes=["https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"])
        sh = gspread.authorize(creds).open_by_key(st.secrets["google_sheet"]["sheet_id"])
        try: return sh.worksheet("PlacementData")
        except: return sh.add_worksheet("PlacementData", 1000, 50)
    except: return None

def push_row(row):
    ws = get_ws()
    if not ws: return
    try:
        ex = ws.get_all_values(); h = list(row.keys())
        if not ex: ws.append_row(h)
        ws.append_row([str(row.get(k,"")) for k in h])
    except Exception as e: st.warning(f"Sheet push: {e}")

def sync_all(data):
    ws = get_ws()
    if not ws or not data: return False
    try:
        df = pd.DataFrame(data); ws.clear()
        ws.update([df.columns.tolist()] + df.values.tolist()); return True
    except Exception as e: st.warning(f"Sync: {e}"); return False

def excel_bytes(df):
    b = BytesIO()
    with pd.ExcelWriter(b, engine="openpyxl") as w: df.to_excel(w,index=False,sheet_name="Report")
    return b.getvalue()

# ─── SESSION ─────────────────────────────────────────────────────────────────
for k,v in {"logged_in":False,"role":None,"username":None,"page":"login",
            "edit_row_idx":None,"login_role":"Manager","confirm_del":None}.items():
    if k not in st.session_state: st.session_state[k] = v

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""<style>
.main-header{background:linear-gradient(135deg,#1e3a5f,#2d6a9f);color:white;
  padding:1.5rem 2rem;border-radius:12px;margin-bottom:1.5rem;text-align:center;}
.main-header h1{margin:0;font-size:2rem;}
.main-header p{margin:.3rem 0 0;opacity:.85;}
.metric-box{background:linear-gradient(135deg,#f0f6ff,#e8f0fe);border-radius:10px;
  padding:1rem;text-align:center;border:1px solid #c5d8f5;}
.metric-box h3{margin:0;color:#1e3a5f;font-size:2rem;}
.metric-box p{margin:0;color:#5a7fa5;font-size:.85rem;}
div[data-testid="stButton"]>button{border-radius:8px;font-weight:600;}
/* tighten action rows */
.action-row-header{font-size:.72rem;font-weight:700;color:#5a7fa5;
  padding:4px 2px;border-bottom:2px solid #dde4ef;margin-bottom:2px;}
.action-cell{font-size:.82rem;padding:3px 2px;}
</style>""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# LOGIN
# ═════════════════════════════════════════════════════════════════════════════
def page_login():
    st.markdown('<div class="main-header"><h1>🎓 Placement Report System</h1><p>Login to continue</p></div>',
                unsafe_allow_html=True)
    _,col,_ = st.columns([1,1.2,1])
    with col:
        st.markdown("### 👤 Login As")
        a,b = st.columns(2)
        with a:
            if st.button("🔑 Admin", use_container_width=True,
                         type="primary" if st.session_state.login_role=="Admin" else "secondary"):
                st.session_state.login_role="Admin"; st.rerun()
        with b:
            if st.button("👥 Manager", use_container_width=True,
                         type="primary" if st.session_state.login_role=="Manager" else "secondary"):
                st.session_state.login_role="Manager"; st.rerun()
        st.markdown(f"**Logging in as: {st.session_state.login_role}**")
        st.divider()
        user = st.text_input("Username"); pw = st.text_input("Password", type="password")
        if st.button("🚀 Login", use_container_width=True, type="primary"):
            if not user or not pw: st.error("Fill both fields."); return
            if st.session_state.login_role == "Admin":
                if user==SUPER_ADMIN_USER and hash_password(pw)==SUPER_ADMIN_PASS_HASH:
                    st.session_state.update(logged_in=True,role="super_admin",username=user,page="admin_home"); st.rerun()
                else:
                    admins=load_admins()
                    if user in admins and admins[user]["password"]==hash_password(pw):
                        st.session_state.update(logged_in=True,role="admin",username=user,page="admin_home"); st.rerun()
                    else: st.error("❌ Invalid admin credentials.")
            else:
                users=load_users()
                if user in users and users[user]["password"]==hash_password(pw):
                    st.session_state.update(logged_in=True,role="manager",username=user,page="manager_home"); st.rerun()
                else: st.error("❌ Invalid manager credentials.")

# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    role=st.session_state.role
    lbl={"super_admin":"Super Admin","admin":"Admin","manager":"Manager"}.get(role,role)
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown(f"Role: **{lbl}**"); st.divider()
        if role in ("super_admin","admin"):
            for pg,ic,tx in [("admin_home","🏠","Dashboard"),
                              ("manage_managers","👥","Manage Managers"),
                              ("admin_reports","📋","All Reports")]:
                if st.button(f"{ic} {tx}", use_container_width=True):
                    st.session_state.page=pg; st.rerun()
            if role=="super_admin":
                if st.button("🔑 Manage Admins", use_container_width=True):
                    st.session_state.page="manage_admins"; st.rerun()
            if st.button("☁️ Sync Google Sheet", use_container_width=True):
                d=load_data()
                if sync_all(d): st.success("✅ Synced!")
                else: st.info("ℹ️ Configure secrets.toml for Google Sheets.")
        else:
            for pg,ic,tx in [("manager_home","🏠","Home"),
                              ("data_entry","➕","New Entry"),
                              ("preview","📋","My Reports")]:
                if st.button(f"{ic} {tx}", use_container_width=True):
                    st.session_state.page=pg; st.rerun()
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# ADMIN DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
def page_admin_home():
    lbl="Super Admin" if is_super_admin() else "Admin"
    st.markdown(f'<div class="main-header"><h1>🏠 {lbl} Dashboard</h1></div>',unsafe_allow_html=True)
    data=load_data(); users=load_users(); df=pd.DataFrame(data) if data else pd.DataFrame()
    c1,c2,c3,c4=st.columns(4)
    with c1: st.markdown(f'<div class="metric-box"><h3>{len(users)}</h3><p>Managers</p></div>',unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-box"><h3>{len(df)}</h3><p>Total Entries</p></div>',unsafe_allow_html=True)
    with c3:
        s=int(df["Final Selection"].sum()) if not df.empty and "Final Selection" in df.columns else 0
        st.markdown(f'<div class="metric-box"><h3>{s}</h3><p>Total Selections</p></div>',unsafe_allow_html=True)
    with c4:
        c=df["Company Name"].nunique() if not df.empty and "Company Name" in df.columns else 0
        st.markdown(f'<div class="metric-box"><h3>{c}</h3><p>Companies</p></div>',unsafe_allow_html=True)
    if not df.empty:
        st.divider(); st.subheader("📊 Recent Entries")
        st.dataframe(df.tail(10),use_container_width=True,hide_index=True)
        st.divider()
        c1,c2=st.columns(2)
        with c1: st.download_button("⬇️ Download All (Excel)",excel_bytes(df),
            file_name="all_placement_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
        with c2:
            if st.button("☁️ Sync All to Google Sheet",use_container_width=True,type="primary"):
                if sync_all(data): st.success("✅ Synced!")
                else: st.info("ℹ️ Add Google Sheets credentials in secrets.toml")

# ═════════════════════════════════════════════════════════════════════════════
# USER MANAGEMENT (shared logic)
# ═════════════════════════════════════════════════════════════════════════════
def user_mgmt_ui(users, singular, save_fn, reserved):
    st.subheader(f"➕ Add New {singular}")
    with st.form(f"add_{singular}"):
        c1,c2,c3=st.columns(3)
        with c1: nu=st.text_input("Username")
        with c2: nn=st.text_input("Full Name")
        with c3: np_=st.text_input("Password",type="password")
        if st.form_submit_button(f"Add {singular}",type="primary",use_container_width=True):
            if not nu or not nn or not np_: st.error("All fields required.")
            elif nu in users or nu in reserved: st.error("Username already exists!")
            else:
                users[nu]={"name":nn,"password":hash_password(np_)}
                save_fn(users); st.success(f"✅ {singular} '{nn}' added!"); st.rerun()
    st.subheader(f"📋 Current {singular}s")
    if not users: st.info(f"No {singular.lower()}s yet.")
    for uname,ud in list(users.items()):
        c1,c2,c3,c4=st.columns([2,2,1,1])
        with c1: st.write(f"**{ud['name']}**")
        with c2: st.write(f"`{uname}`")
        with c3:
            with st.popover("🔑 Change PW"):
                pw2=st.text_input("New PW",type="password",key=f"pw_{singular}_{uname}")
                if st.button("Update",key=f"upd_{singular}_{uname}"):
                    if pw2: users[uname]["password"]=hash_password(pw2); save_fn(users); st.success("Updated!"); st.rerun()
        with c4:
            if st.button("🗑️ Remove",key=f"rm_{singular}_{uname}"):
                del users[uname]; save_fn(users); st.success(f"Removed {uname}"); st.rerun()
        st.divider()

def page_manage_managers():
    st.markdown('<div class="main-header"><h1>👥 Manage Managers</h1></div>',unsafe_allow_html=True)
    user_mgmt_ui(load_users(),"Manager",save_users,set(load_admins().keys())|{SUPER_ADMIN_USER})

def page_manage_admins():
    st.markdown('<div class="main-header"><h1>🔑 Manage Admins</h1></div>',unsafe_allow_html=True)
    user_mgmt_ui(load_admins(),"Admin",save_admins,set(load_users().keys())|{SUPER_ADMIN_USER})

# ═════════════════════════════════════════════════════════════════════════════
# DATA ENTRY
# ═════════════════════════════════════════════════════════════════════════════
def data_entry_form(prefill=None, edit_idx=None):
    p=prefill or {}; is_edit=edit_idx is not None
    st.markdown(f'<div class="main-header"><h1>{"✏️ Edit Entry" if is_edit else "➕ New Data Entry"}</h1></div>',
                unsafe_allow_html=True)
    with st.form("entry_form"):
        st.subheader("👤 Basic Information")
        c1,c2=st.columns(2)
        with c1: mgr_name=st.text_input("Manager Name *",value=p.get("Manager Name",st.session_state.username))
        with c2:
            fd=datetime.strptime(p["Floated Date"],"%Y-%m-%d").date() if p.get("Floated Date") else date.today()
            floated_date=st.date_input("Floated Date *",value=fd)
        c1,c2,c3=st.columns(3)
        with c1:
            fb=["Superset","Google Form"]
            floated_by=st.selectbox("Floated By *",fb,index=fb.index(p["Floated By"]) if p.get("Floated By") in fb else 0)
        with c2:
            ot=["Full Time","Intern cum PPO","Only Internship"]
            opp_type=st.selectbox("Opportunity Type *",ot,index=ot.index(p["Opportunity Type"]) if p.get("Opportunity Type") in ot else 0)
        with c3:
            bt=["2025-2026","2026-2027","2027-2028"]
            batch=st.selectbox("Batch *",bt,index=bt.index(p["Batch"]) if p.get("Batch") in bt else 0)

        st.subheader("🏢 Company Details")
        c1,c2,c3=st.columns(3)
        with c1: company_name=st.text_input("Company Name *",value=p.get("Company Name",""))
        with c2:
            cn=["Core","Non-Core"]
            core_nc=st.selectbox("Core / Non-Core *",cn,index=cn.index(p["Core/Non-Core"]) if p.get("Core/Non-Core") in cn else 0)
        with c3: company_domain=st.text_input("Company Domain",value=p.get("Company Domain",""))
        c1,c2=st.columns(2)
        with c1: job_profile=st.text_input("Job Profile",value=p.get("Job Profile",""))
        with c2: job_location=st.text_input("Job Location",value=p.get("Job Location",""))

        st.subheader("🏫 School, Program & Specialization")
        ds=[s.strip() for s in p["School"].split(",")]  if p.get("School")  else []
        dp=[s.strip() for s in p["Program"].split(",")] if p.get("Program") else []
        c1,c2,c3=st.columns(3)
        with c1: schools=st.multiselect("School *",SCHOOL_OPTIONS,default=[s for s in ds if s in SCHOOL_OPTIONS])
        with c2: programs=st.multiselect("Program *",PROGRAM_OPTIONS,default=[s for s in dp if s in PROGRAM_OPTIONS])
        with c3: specialization=st.text_input("Specialization",value=p.get("Specialization",""))

        st.subheader("💰 CTC & Status")
        c1,c2,c3,c4=st.columns(4)
        with c1:
            try: cv=float(str(p.get("CTC (LPA)","0")).replace(" LPA","").strip())
            except: cv=0.0
            ctc=st.number_input("CTC (LPA) *",min_value=0.0,step=0.1,value=cv,format="%.2f")
        with c2:
            cs=["In Process","Cancelled","Hold","Completed","Postponed"]
            company_status=st.selectbox("Company Status *",cs,index=cs.index(p["Company Current Status"]) if p.get("Company Current Status") in cs else 0)
        with c3: no_pos=st.number_input("No. of Positions",min_value=0,step=1,value=int(p.get("No. of Positions",0) or 0))
        with c4: no_reg=st.number_input("No. of Registrations",min_value=0,step=1,value=int(p.get("No. of Registrations",0) or 0))
        iv=datetime.strptime(p["Interview Date"],"%Y-%m-%d").date() if p.get("Interview Date") else date.today()
        interview_date=st.date_input("Interview Date",value=iv)

        st.subheader("📊 Participations & Shortlistings")
        parts={}; c5=st.columns(5)
        for i,rnd in enumerate(PARTICIPATION_ROUNDS):
            with c5[i]:
                k=f"Participation {rnd}"
                parts[k]=st.number_input(f"Part. {rnd}",min_value=0,step=1,value=int(p.get(k,0) or 0),key=f"p{i}")
        shorts={}; c5b=st.columns(5)
        for i,rnd in enumerate(PARTICIPATION_ROUNDS):
            with c5b[i]:
                k=f"Shortlisting {rnd}"
                shorts[k]=st.number_input(f"Short. {rnd}",min_value=0,step=1,value=int(p.get(k,0) or 0),key=f"s{i}")

        st.subheader("🏆 Selections & Offers")
        c1,c2,c3,c4=st.columns(4)
        with c1:
            se=["Yes","No"]
            sel_email=st.selectbox("Selection Confirmation Email *",se,
                index=se.index(p["Selection Confirmation Email"]) if p.get("Selection Confirmation Email") in se else 1)
        with c2: final_sel=st.number_input("Final Selection",min_value=0,step=1,value=int(p.get("Final Selection",0) or 0))
        with c3: offer_recv=st.number_input("Offer Letters Received",min_value=0,step=1,value=int(p.get("Offer Letters Received",0) or 0))
        with c4: cand_joined=st.number_input("Candidates Joined",min_value=0,step=1,value=int(p.get("Candidates Joined",0) or 0))
        remarks=st.text_area("Remarks",value=p.get("Remarks",""),height=100)
        submitted=st.form_submit_button("💾 Update Entry" if is_edit else "💾 Submit Entry",
            type="primary",use_container_width=True)

    if submitted:
        if not mgr_name or not company_name or not schools or not programs:
            st.error("Please fill all required (*) fields."); return
        row={
            "Manager Name":mgr_name,"Floated Date":str(floated_date),"Floated By":floated_by,
            "Opportunity Type":opp_type,"Batch":batch,"Company Name":company_name,
            "Core/Non-Core":core_nc,"Company Domain":company_domain,
            "Job Profile":job_profile,"Job Location":job_location,
            "School":", ".join(schools),"Program":", ".join(programs),
            "Specialization":specialization,"CTC (LPA)":f"{ctc:.2f} LPA",
            "Company Current Status":company_status,"No. of Positions":no_pos,
            "No. of Registrations":no_reg,"Interview Date":str(interview_date),
            **parts,**shorts,
            "Selection Confirmation Email":sel_email,"Final Selection":final_sel,
            "Offer Letters Received":offer_recv,
            "Offer Letters Pending":max(0,final_sel-offer_recv),
            "Candidates Joined":cand_joined,"Remarks":remarks,
            "Submitted By":st.session_state.username,
            "Submitted At":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        data=load_data()
        if is_edit: data[edit_idx]=row; st.success("✅ Entry updated!")
        else: data.append(row); push_row(row); st.success("✅ Entry submitted!")
        save_data(data)
        st.session_state.page="preview"; st.session_state.edit_row_idx=None; st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# PREVIEW — combined table with inline Edit / Delete
# ═════════════════════════════════════════════════════════════════════════════
def page_preview(admin_view=False):
    title="📋 All Reports" if admin_view else "📋 My Reports"
    st.markdown(f'<div class="main-header"><h1>{title}</h1></div>',unsafe_allow_html=True)

    data=load_data()
    if not data: st.info("No data found yet."); return
    df=pd.DataFrame(data)

    if not admin_view:
        df=df[df["Submitted By"]==st.session_state.username].reset_index(drop=True)
        if df.empty:
            st.info("No entries yet.")
            if st.button("➕ Add New Entry",type="primary"): st.session_state.page="data_entry"; st.rerun()
            return

    # ── FILTERS ──────────────────────────────────────────────────────────────
    with st.expander("🔍 Filter Data",expanded=False):
        st.markdown("**Text Search**")
        t1,t2,t3,t4=st.columns(4)
        with t1: f_co=st.text_input("Company Name")
        with t2: f_do=st.text_input("Company Domain")
        with t3: f_jp=st.text_input("Job Profile")
        with t4: f_jl=st.text_input("Job Location")
        t5,t6,t7,t8=st.columns(4)
        with t5: f_mn=st.text_input("Manager Name")
        with t6: f_sp=st.text_input("Specialization")
        with t7: f_sc=st.text_input("School contains")
        with t8: f_pr=st.text_input("Program contains")
        t9,_,__,___=st.columns(4)
        with t9: f_re=st.text_input("Remarks contains")
        st.markdown("**Dropdown Filters**")
        d1,d2,d3,d4=st.columns(4)
        with d1: f_st=st.selectbox("Company Status",["All","In Process","Cancelled","Hold","Completed","Postponed"])
        with d2: f_ba=st.selectbox("Batch",["All","2025-2026","2026-2027","2027-2028"])
        with d3: f_fb=st.selectbox("Floated By",["All","Superset","Google Form"])
        with d4: f_ot=st.selectbox("Opportunity Type",["All","Full Time","Intern cum PPO","Only Internship"])
        d5,d6,d7,d8=st.columns(4)
        with d5: f_cn=st.selectbox("Core/Non-Core",["All","Core","Non-Core"])
        with d6: f_se=st.selectbox("Selection Email",["All","Yes","No"])
        with d7:
            if admin_view:
                mgrs=["All"]+sorted(df["Submitted By"].unique().tolist())
                f_sb=st.selectbox("Submitted By",mgrs)
            else: f_sb="All"
        with d8: pass
        st.markdown("**Date Filters**")
        dr1,dr2,dr3,dr4=st.columns(4)
        with dr1: f_fdf=st.date_input("Floated From",value=None,key="fdf")
        with dr2: f_fdt=st.date_input("Floated To",value=None,key="fdt")
        with dr3: f_idf=st.date_input("Interview From",value=None,key="idf")
        with dr4: f_idt=st.date_input("Interview To",value=None,key="idt")
        st.markdown("**Number Filters**")
        nr1,nr2,nr3,nr4=st.columns(4)
        with nr1: f_pmn=st.number_input("Min Positions",min_value=0,value=0,step=1)
        with nr2: f_pmx=st.number_input("Max Positions",min_value=0,value=99999,step=1)
        with nr3: f_smn=st.number_input("Min Selections",min_value=0,value=0,step=1)
        with nr4: f_smx=st.number_input("Max Selections",min_value=0,value=99999,step=1)

    flt=df.copy()
    if f_co: flt=flt[flt["Company Name"].str.contains(f_co,case=False,na=False)]
    if f_do: flt=flt[flt["Company Domain"].str.contains(f_do,case=False,na=False)]
    if f_jp: flt=flt[flt["Job Profile"].str.contains(f_jp,case=False,na=False)]
    if f_jl: flt=flt[flt["Job Location"].str.contains(f_jl,case=False,na=False)]
    if f_mn: flt=flt[flt["Manager Name"].str.contains(f_mn,case=False,na=False)]
    if f_sp: flt=flt[flt["Specialization"].str.contains(f_sp,case=False,na=False)]
    if f_sc: flt=flt[flt["School"].str.contains(f_sc,case=False,na=False)]
    if f_pr: flt=flt[flt["Program"].str.contains(f_pr,case=False,na=False)]
    if f_re: flt=flt[flt["Remarks"].str.contains(f_re,case=False,na=False)]
    if f_st!="All": flt=flt[flt["Company Current Status"]==f_st]
    if f_ba!="All": flt=flt[flt["Batch"]==f_ba]
    if f_fb!="All": flt=flt[flt["Floated By"]==f_fb]
    if f_ot!="All": flt=flt[flt["Opportunity Type"]==f_ot]
    if f_cn!="All": flt=flt[flt["Core/Non-Core"]==f_cn]
    if f_se!="All": flt=flt[flt["Selection Confirmation Email"]==f_se]
    if f_sb!="All": flt=flt[flt["Submitted By"]==f_sb]
    if f_fdf and "Floated Date" in flt.columns:
        flt=flt[pd.to_datetime(flt["Floated Date"],errors="coerce")>=pd.Timestamp(f_fdf)]
    if f_fdt and "Floated Date" in flt.columns:
        flt=flt[pd.to_datetime(flt["Floated Date"],errors="coerce")<=pd.Timestamp(f_fdt)]
    if f_idf and "Interview Date" in flt.columns:
        flt=flt[pd.to_datetime(flt["Interview Date"],errors="coerce")>=pd.Timestamp(f_idf)]
    if f_idt and "Interview Date" in flt.columns:
        flt=flt[pd.to_datetime(flt["Interview Date"],errors="coerce")<=pd.Timestamp(f_idt)]
    if "No. of Positions" in flt.columns:
        flt=flt[pd.to_numeric(flt["No. of Positions"],errors="coerce").fillna(0).between(f_pmn,f_pmx)]
    if "Final Selection" in flt.columns:
        flt=flt[pd.to_numeric(flt["Final Selection"],errors="coerce").fillna(0).between(f_smn,f_smx)]

    flt=flt.reset_index(drop=False).rename(columns={"index":"_oi"})
    disp=flt.drop(columns=["_oi"])

    st.markdown(f"**{len(flt)} entries found**")
    st.download_button("⬇️ Download as Excel",excel_bytes(disp),
        file_name=f"placement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.divider()
    if flt.empty: st.info("No entries match the filters."); return

    can_modify=(st.session_state.role=="manager")

    # ── Delete confirmation popup ─────────────────────────────────────────────
    if st.session_state.confirm_del is not None:
        oi=st.session_state.confirm_del
        all_d=load_data()
        co_name=all_d[oi].get("Company Name","this entry") if oi<len(all_d) else "this entry"
        st.warning(f"⚠️ Delete **{co_name}**? This cannot be undone.")
        ya,na=st.columns(2)
        with ya:
            if st.button("✅ Yes, Delete",type="primary",use_container_width=True):
                all_d.pop(oi); save_data(all_d)
                st.session_state.confirm_del=None; st.success("Deleted!"); st.rerun()
        with na:
            if st.button("❌ Cancel",use_container_width=True):
                st.session_state.confirm_del=None; st.rerun()
        st.divider()

    # ═══════════════════════════════════════════════════════════════════════
    # COMBINED TABLE — all data columns + Edit/Delete at the end of each row
    # Uses st.columns per row (Streamlit's only way to have buttons in a table)
    # ═══════════════════════════════════════════════════════════════════════
    all_data_cols=list(disp.columns)

    # Fixed column widths for the key visible columns
    # We'll show a compact set of cols; user can download Excel for full view
    SHOW_COLS=[
        ("Company Name",       2.0),
        ("Floated Date",       1.2),
        ("Batch",              1.0),
        ("Opportunity Type",   1.4),
        ("Core/Non-Core",      0.9),
        ("CTC (LPA)",          0.9),
        ("Company Current Status", 1.3),
        ("School",             1.5),
        ("Program",            1.2),
        ("Final Selection",    1.0),
        ("Submitted By",       1.1),
    ]
    # keep only cols that exist
    SHOW_COLS=[(c,w) for c,w in SHOW_COLS if c in disp.columns]
    col_names=[c for c,_ in SHOW_COLS]
    col_widths=[w for _,w in SHOW_COLS]

    if can_modify:
        # Add Edit + Delete column widths
        all_widths=col_widths+[0.65, 0.65]
        all_labels=col_names+["Edit","Delete"]
    else:
        all_widths=col_widths
        all_labels=col_names

    # ── Header row ────────────────────────────────────────────────────────────
    header_cols=st.columns(all_widths)
    for hc,lbl in zip(header_cols,all_labels):
        hc.markdown(
            f"<div style='font-size:.72rem;font-weight:700;color:#2d6a9f;"
            f"padding:4px 2px;border-bottom:2px solid #2d6a9f'>{lbl}</div>",
            unsafe_allow_html=True)

    # ── Data rows ─────────────────────────────────────────────────────────────
    for _, row in flt.iterrows():
        oi=int(row["_oi"])
        row_cols=st.columns(all_widths)
        for ci,cname in enumerate(col_names):
            val=str(row.get(cname,"—"))
            # truncate long values so row stays compact
            display_val=val[:28]+"…" if len(val)>28 else val
            row_cols[ci].markdown(
                f"<div style='font-size:.80rem;padding:4px 2px;"
                f"border-bottom:1px solid #eef1f7;line-height:1.3'>"
                f"<span title='{val}'>{display_val}</span></div>",
                unsafe_allow_html=True)
        if can_modify:
            with row_cols[len(col_names)]:
                if st.button("✏️",key=f"ed_{oi}",use_container_width=True,type="primary",
                             help="Edit this entry"):
                    st.session_state.edit_row_idx=oi
                    st.session_state.page="edit_entry"; st.rerun()
            with row_cols[len(col_names)+1]:
                if st.button("🗑️",key=f"dl_{oi}",use_container_width=True,
                             help="Delete this entry"):
                    st.session_state.confirm_del=oi; st.rerun()

    st.markdown("<br>",unsafe_allow_html=True)
    st.caption("💡 Hover over any cell to see full value. Download Excel for all columns.")

# ═════════════════════════════════════════════════════════════════════════════
# MANAGER HOME
# ═════════════════════════════════════════════════════════════════════════════
def page_manager_home():
    uname=st.session_state.username
    name=load_users().get(uname,{}).get("name",uname)
    st.markdown(f'<div class="main-header"><h1>👋 Welcome, {name}!</h1><p>Placement Data Entry Portal</p></div>',
                unsafe_allow_html=True)
    data=load_data(); my=[r for r in data if r.get("Submitted By")==uname]
    c1,c2,c3=st.columns(3)
    with c1: st.markdown(f'<div class="metric-box"><h3>{len(my)}</h3><p>My Total Entries</p></div>',unsafe_allow_html=True)
    with c2:
        s=sum(int(r.get("Final Selection",0) or 0) for r in my)
        st.markdown(f'<div class="metric-box"><h3>{s}</h3><p>Total Selections</p></div>',unsafe_allow_html=True)
    with c3:
        c=len(set(r.get("Company Name","") for r in my))
        st.markdown(f'<div class="metric-box"><h3>{c}</h3><p>Companies</p></div>',unsafe_allow_html=True)
    st.divider()
    c1,c2=st.columns(2)
    with c1:
        if st.button("➕ New Data Entry",use_container_width=True,type="primary"):
            st.session_state.page="data_entry"; st.rerun()
    with c2:
        if st.button("📋 View My Reports",use_container_width=True):
            st.session_state.page="preview"; st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═════════════════════════════════════════════════════════════════════════════
def main():
    if not st.session_state.logged_in: page_login(); return
    render_sidebar()
    pg=st.session_state.page; role=st.session_state.role
    if   pg=="admin_home":       page_admin_home()
    elif pg=="manage_managers":  page_manage_managers()
    elif pg=="manage_admins":
        if role=="super_admin":  page_manage_admins()
        else: st.error("Access denied.")
    elif pg=="admin_reports":    page_preview(admin_view=True)
    elif pg=="manager_home":     page_manager_home()
    elif pg=="data_entry":       data_entry_form()
    elif pg=="edit_entry":
        idx=st.session_state.edit_row_idx
        if idx is not None: data_entry_form(prefill=load_data()[idx],edit_idx=idx)
        else: st.session_state.page="preview"; st.rerun()
    elif pg=="preview":
        page_preview(admin_view=(role in ("admin","super_admin")))

main()
