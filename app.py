import streamlit as st
import pandas as pd
import sqlite3
import requests
import os
from datetime import datetime
from google import genai

# --- 1. ตั้งค่าระบบและ KEY ---
st.set_page_config(page_title="Work & Task Tracker with AI Secretary", layout="wide")

GEMINI_API_KEY = "AQ.Ab8RN6JtrS3bX1R4US4632720LzcA0KM0RgnMnWhV6jaDCd-Kg"
LINE_CHANNEL_ACCESS_TOKEN = "tczZhOEGhupttNJGtkFywMJDNsgTO5Wib99thpNy+ORanz1nyKP1roZw4HNTwu/sStmF4FO/WILjtMMXLRwqvjBs1TYHgSVgNnNdtIu7MrABP7SdLLYWZ+xtlosdlmE654odeJ0JDr/Y2uwFd9/hDQdB04t89/1O/w1cDnyilFU="
LINE_RECEIVER_ID = "U87c3ee67a45f19e3539bbb0963aba4c8"

client = genai.Client(api_key=GEMINI_API_KEY)

# สร้างโฟลเดอร์สำหรับเก็บรูปภาพ
UPLOAD_FOLDER = "uploaded_images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- 2. สร้างและจัดการฐานข้อมูล SQLite ---
def init_db():
    conn = sqlite3.connect("company_work.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT,
                    fullname TEXT,
                    department TEXT,
                    role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT,
                    department TEXT,
                    assignee_username TEXT,
                    due_date TEXT,
                    status TEXT,
                    progress_note TEXT,
                    image_path TEXT,
                    last_updated TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect("company_work.db")

# --- 3. ฟังก์ชันส่ง LINE ---
def send_line_push(message_text):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "to": LINE_RECEIVER_ID,
        "messages": [{"type": "text", "text": message_text}]
    }
    res = requests.post(url, headers=headers, json=payload)
    return res.status_code == 200

# --- 4. จัดการ Session ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

# ==================== หน้าต่าง LOGIN / REGISTER ====================
if not st.session_state.logged_in:
    st.title("🏢 ระบบบริหารงานก่อสร้าง & AI เลขาติดตามงาน")
    
    tab_login, tab_reg = st.tabs(["🔑 เข้าสู่ระบบ (Login)", "📝 สมัครสมาชิก (Register)"])
    
    with tab_login:
        st.subheader("เข้าสู่ระบบ")
        login_user = st.text_input("ชื่อผู้ใช้ (Username)")
        login_pass = st.text_input("รหัสผ่าน (Password)", type="password")
        if st.button("เข้าสู่ระบบ", use_container_width=True):
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT username, fullname, department, role FROM users WHERE username=? AND password=?", (login_user, login_pass))
            user_data = c.fetchone()
            conn.close()
            
            if user_data:
                st.session_state.logged_in = True
                st.session_state.user = {
                    "username": user_data[0],
                    "fullname": user_data[1],
                    "department": user_data[2],
                    "role": user_data[3]
                }
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    with tab_reg:
        st.subheader("สร้างบัญชีผู้ใช้งานใหม่")
        new_user = st.text_input("สร้างชื่อผู้ใช้ (Username)", key="reg_user")
        new_pass = st.text_input("สร้างรหัสผ่าน (Password)", type="password", key="reg_pass")
        new_name = st.text_input("ชื่อ - นามสกุลจริง")
        new_dept = st.selectbox("แผนก", ["จัดซื้อจัดจ้าง", "ควบคุมคุณภาพ", "บัญชีและการเงิน", "สนับสนุนโครงการ", "ปลูกศิลป์/Landscape", "การตลาด/สื่อสารองค์กร", "Executive Office"])
        new_role = st.selectbox("บทบาท (Role)", ["พนักงาน (Employee)", "หัวหน้า/ผู้บริหาร (Manager)"])
        
        if st.button("ลงทะเบียน", use_container_width=True):
            if new_user and new_pass and new_name:
                try:
                    conn = get_db_connection()
                    c = conn.cursor()
                    role_code = "Manager" if "หัวหน้า" in new_role else "Employee"
                    c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", (new_user, new_pass, new_name, new_dept, role_code))
                    conn.commit()
                    conn.close()
                    st.success("ลงทะเบียนสำเร็จ! กรุณาสลับไปแท็บเข้าสู่ระบบ")
                except sqlite3.IntegrityError:
                    st.error("ชื่อผู้ใช้นี้ถูกใช้งานแล้ว กรุณาตั้งชื่ออื่น")
            else:
                st.warning("กรุณากรอกข้อมูลให้ครบทุกช่อง")

# ==================== หน้าต่างหลัง LOGIN ====================
else:
    user = st.session_state.user
    
    with st.sidebar:
        st.write(f"👤 **ผู้ใช้งาน:** {user['fullname']}")
        st.write(f"🏢 **แผนก:** {user['department']}")
        st.write(f"🎖️ **ระดับ:** {'👑 หัวหน้า / ผู้บริหาร' if user['role'] == 'Manager' else '🛠️ พนักงาน'}")
        if st.button("ออกจากระบบ (Logout)"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()

    # -------------------------------------------------------------
    # 📌 หน้าของ "พนักงาน" (Employee)
    # -------------------------------------------------------------
    if user['role'] == "Employee":
        st.title(f"🛠️ หน้าส่งงานและอัปเดตความคืบหน้า - คุณ {user['fullname']}")
        
        tab_my_tasks, tab_report_new = st.tabs(["📋 รายการงานของฉัน & อัปเดตงาน", "➕ ส่งรายงาน/สร้างงานใหม่ด้วยตนเอง"])
        
        # แท็บ 1: ดูงานและอัปเดตงานที่มีอยู่
        with tab_my_tasks:
            conn = get_db_connection()
            my_tasks = pd.read_sql_query("SELECT * FROM tasks WHERE assignee_username=?", conn, params=(user['username'],))
            conn.close()
            
            if my_tasks.empty:
                st.info("💡 ยังไม่มีงานที่หัวหน้ามอบหมาย คุณสามารถไปที่แท็บ '➕ ส่งรายงาน/สร้างงานใหม่ด้วยตนเอง' เพื่อส่งงานได้ทันที")
            else:
                st.dataframe(my_tasks[['task_id', 'task_name', 'due_date', 'status', 'progress_note', 'last_updated']], use_container_width=True)
                
                st.divider()
                st.subheader("✍️ อัปเดตความคืบหน้าและแนบภาพ")
                with st.form("update_task_form"):
                    task_options = {f"#{row['task_id']} - {row['task_name']}": row['task_id'] for _, row in my_tasks.iterrows()}
                    selected_task_label = st.selectbox("เลือกงานที่ต้องการอัปเดต", list(task_options.keys()))
                    selected_task_id = task_options[selected_task_label]
                    
                    new_status = st.selectbox("สถานะปัจจุบัน", ["In Progress (กำลังทำ)", "Pending (รอดำเนินการ/ติดขัด)", "Completed (เสร็จสิ้น)"])
                    progress_text = st.text_area("คำอธิบายความคืบหน้าล่าสุด (เช่น ตรวจสอบผนังเสร็จแล้ว กำลังรอเอกสารเซ็น)")
                    uploaded_img = st.file_uploader("แนบรูปภาพหน้างาน / เอกสารความคืบหน้า (JPG, PNG)", type=["jpg", "png", "jpeg"])
                    
                    if st.form_submit_button("บันทึกการอัปเดต"):
                        status_clean = new_status.split(" ")[0]
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                        
                        img_path = None
                        if uploaded_img:
                            img_filename = f"task_{selected_task_id}_{int(datetime.now().timestamp())}.png"
                            img_path = os.path.join(UPLOAD_FOLDER, img_filename)
                            with open(img_path, "wb") as f:
                                f.write(uploaded_img.getbuffer())
                        
                        conn = get_db_connection()
                        c = conn.cursor()
                        if img_path:
                            c.execute("UPDATE tasks SET status=?, progress_note=?, image_path=?, last_updated=? WHERE task_id=?", 
                                      (status_clean, progress_text, img_path, now_str, selected_task_id))
                        else:
                            c.execute("UPDATE tasks SET status=?, progress_note=?, last_updated=? WHERE task_id=?", 
                                      (status_clean, progress_text, now_str, selected_task_id))
                        conn.commit()
                        conn.close()
                        st.success("✅ อัปเดตข้อมูลและความคืบหน้าเรียบร้อยแล้ว!")
                        st.rerun()

        # แท็บ 2: พนักงานส่งรายงานงานใหม่เอง
        with tab_report_new:
            st.subheader("➕ ส่งรายงานความคืบหน้างานใหม่")
            with st.form("new_self_task_form"):
                new_title = st.text_input("ชื่องาน / รายการที่กำลังทำ")
                new_due = st.date_input("กำหนดส่ง / วันที่คาดว่าจะเสร็จ")
                new_status_self = st.selectbox("สถานะเริ่มต้น", ["In Progress", "Pending", "Completed"])
                new_desc = st.text_area("คำอธิบายรายละเอียดงาน / ความคืบหน้าหน้างาน")
                new_img = st.file_uploader("แนบรูปภาพหน้างานจริง", type=["jpg", "png", "jpeg"], key="self_img")
                
                if st.form_submit_button("ส่งรายงานให้หัวหน้า"):
                    if new_title:
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                        img_path = None
                        if new_img:
                            img_filename = f"new_{user['username']}_{int(datetime.now().timestamp())}.png"
                            img_path = os.path.join(UPLOAD_FOLDER, img_filename)
                            with open(img_path, "wb") as f:
                                f.write(new_img.getbuffer())
                                
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("INSERT INTO tasks (task_name, department, assignee_username, due_date, status, progress_note, image_path, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                  (new_title, user['department'], user['username'], str(new_due), new_status_self, new_desc, img_path, now_str))
                        conn.commit()
                        conn.close()
                        st.success("✅ ส่งรายงานงานใหม่เข้าสู่ระบบเรียบร้อยแล้ว!")
                        st.rerun()
                    else:
                        st.error("กรุณากรอกชื่องาน")

    # -------------------------------------------------------------
    # 📌 หน้าของ "หัวหน้า" (Manager)
    # -------------------------------------------------------------
    elif user['role'] == "Manager":
        st.title("👑 แดชบอร์ดผู้บริหาร & AI เลขาติดตามงาน")
        
        conn = get_db_connection()
        all_tasks = pd.read_sql_query("""
            SELECT t.task_id, t.task_name, t.department, u.fullname as assignee, t.due_date, t.status, t.progress_note, t.image_path, t.last_updated
            FROM tasks t
            LEFT JOIN users u ON t.assignee_username = u.username
        """, conn)
        
        employees = pd.read_sql_query("SELECT username, fullname, department FROM users WHERE role='Employee'", conn)
        conn.close()

        tab_overview, tab_create, tab_ai = st.tabs(["📊 ภาพรวมงาน & รูปภาพหน้างาน", "➕ มอบหมายงานใหม่", "🤖 AI เลขาสรุปและส่ง LINE"])
        
        # แท็บ 1: ภาพรวมงานและดูรูปแนบ
        with tab_overview:
            st.subheader("ภาพรวมสถานะงานทั้งหมด")
            if all_tasks.empty:
                st.info("ยังไม่มีข้อมูลงานในระบบ")
            else:
                st.dataframe(all_tasks[['task_id', 'task_name', 'department', 'assignee', 'due_date', 'status', 'progress_note', 'last_updated']], use_container_width=True)
                
                st.divider()
                st.subheader("🖼️ ตรวจสอบรูปภาพหน้างานและความคืบหน้าล่าสุด")
                tasks_with_images = all_tasks[all_tasks['image_path'].notnull()]
                if tasks_with_images.empty:
                    st.info("ยังไม่มีพนักงานแนบรูปภาพความคืบหน้าเข้ามา")
                else:
                    cols = st.columns(3)
                    for idx, row in tasks_with_images.iterrows():
                        col = cols[idx % 3]
                        with col:
                            if os.path.exists(str(row['image_path'])):
                                st.image(row['image_path'], caption=f"งาน #{row['task_id']}: {row['task_name']}", use_container_width=True)
                                st.caption(f"👤 ผู้ส่ง: {row['assignee']} ({row['department']})")
                                st.caption(f"📝 ความคืบหน้า: {row['progress_note']}")
                                st.caption(f"🕒 อัปเดต: {row['last_updated']}")

        # แท็บ 2: มอบหมายงาน
        with tab_create:
            st.subheader("สร้างงานและมอบหมายให้พนักงาน")
            if employees.empty:
                st.warning("ยังไม่มีพนักงานสมัครสมาชิกในระบบ")
            else:
                with st.form("assign_form"):
                    task_title = st.text_input("ชื่องาน / รายละเอียดสั้นๆ")
                    emp_choices = {f"{row['fullname']} ({row['department']})": row['username'] for _, row in employees.iterrows()}
                    selected_emp_name = st.selectbox("มอบหมายให้", list(emp_choices.keys()))
                    assigned_username = emp_choices[selected_emp_name]
                    
                    emp_dept = employees[employees['username'] == assigned_username]['department'].values[0]
                    due = st.date_input("กำหนดส่ง (Due Date)")
                    
                    if st.form_submit_button("บันทึกและมอบหมายงาน"):
                        if task_title:
                            conn = get_db_connection()
                            c = conn.cursor()
                            c.execute("INSERT INTO tasks (task_name, department, assignee_username, due_date, status, progress_note, image_path, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                      (task_title, emp_dept, assigned_username, str(due), "Pending", "รอดำเนินการ", None, datetime.now().strftime("%Y-%m-%d %H:%M")))
                            conn.commit()
                            conn.close()
                            st.success(f"มอบหมายงานให้ {selected_emp_name} เรียบร้อยแล้ว!")
                            st.rerun()
                        else:
                            st.error("กรุณากรอกชื่องาน")

        # แท็บ 3: AI เลขา
        with tab_ai:
            st.subheader("สรุปความคืบหน้างานรายบุคคลด้วย AI")
            
            if st.button("✨ ให้ AI เลขาวิเคราะห์และสรุปงานเดี๋ยวนี้", type="primary"):
                if all_tasks.empty:
                    st.warning("ไม่มีงานให้วิเคราะห์")
                else:
                    with st.spinner("AI เลขากำลังอ่านข้อมูลและวิเคราะห์งานของทุกคน..."):
                        today_str = datetime.now().strftime("%Y-%m-%d")
                        ai_prompt = f"""
                        คุณเป็นเลขานุการ AI ระดับสูงของผู้บริหารธุรกิจก่อสร้างและอสังหาริมทรัพย์
                        วันนี้คือวันที่: {today_str}

                        นี่คือข้อมูลงานและการอัปเดตล่าสุดของพนักงานแต่ละคน:
                        {all_tasks[['task_name', 'department', 'assignee', 'due_date', 'status', 'progress_note']].to_string(index=False)}

                        หน้าที่ของคุณ:
                        1. สรุปภาพรวมว่า 'ใครกำลังทำอะไรอยู่' และมีความคืบหน้าตาม Note อย่างไรบ้าง
                        2. ชี้เป้างานที่ 'เลยกำหนด (Overdue)' หรืองานที่ดูเหมือนจะติดขัด
                        3. ให้ข้อเสนอแนะ 1-2 ข้อสำหรับผู้บริหารว่าควรโฟกัสหรือสั่งการเรื่องใดก่อน
                        จัดหมวดหมู่อ่านง่าย ตกแต่งด้วย Emoji ให้สวยงามและเป็นมืออาชีพ
                        """
                        
                        response = client.models.generate_content(
                            model="gemini-3.6-flash",
                            contents=ai_prompt
                        )
                        st.session_state.ai_summary = response.text
            
            if "ai_summary" in st.session_state:
                st.markdown(st.session_state.ai_summary)
                st.divider()
                if st.button("🚀 ยิงข้อความเข้า LINE ทันที"):
                    success = send_line_push(st.session_state.ai_summary)
                    if success:
                        st.success("✅ ส่งข้อความสรุปเข้า LINE ผู้บริหารเรียบร้อยแล้ว!")
                    else:
                        st.error("❌ ไม่สามารถส่ง LINE ได้ กรุณาตรวจสอบ Token")