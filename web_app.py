from datetime import datetime
import hashlib
import sqlite3
import models
import streamlit as st

# --- CLEAN & MINIMAL UI CONFIGURATION ---
st.set_page_config(
    page_title="Orange Hostels System", page_icon="🍊", layout="wide"
)

# Minimal, clean header styling
st.markdown(
    """
    <div style='background-color: #FAFAFA; padding: 20px; border-radius: 8px; border-left: 6px solid #FF7518;'>
        <h2 style='color: #222222; margin: 0;'>🍊 Orange Hostels Management System</h2>
        <p style='color: #555555; margin: 4px 0 0 0; font-size: 15px;'>Kampala University Luweero Campus | Student Accommodation Portal</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")

# Initialize the database and default rooms on app load
models.init_db()

# Sidebar Navigation
menu = st.sidebar.selectbox(
    "Navigation Menu",
    [
        "🏠 Browse Rooms Inventory",
        "📝 Register Student Account",
        "🛌 Make Room Reservation",
        "💳 Process Payment",
        "🚨 Emergency SOS Desk",
        "📊 Manager Control Dashboard",
    ],
)

# Connect to database for queries
conn = sqlite3.connect("orange_hostels.db")
cursor = conn.cursor()

# -------------------------------------------------------------
# 1. BROWSE ROOMS
# -------------------------------------------------------------
if menu == "🏠 Browse Rooms Inventory":
  st.header("Hostel Rooms Inventory")
  st.write("Browse available rooms across our blocks and check their rates.")
  cursor.execute(
      "SELECT room_id, room_number, capacity, price, status FROM room"
  )
  rooms = cursor.fetchall()
  for r in rooms:
    status_color = "green" if r[4] == "Available" else "gray"
    st.markdown(
        f"""
        * **Room Number:** {r[1]}
        * **Capacity:** {r[2]} Student(s)
        * **Price:** UGX {r[3]:,.0f} per semester
        * **Status:** :{status_color}[**{r[4]}**]
        """
    )
    st.divider()

# -------------------------------------------------------------
# 2. REGISTER STUDENT ACCOUNT
# -------------------------------------------------------------
elif menu == "📝 Register Student Account":
  st.header("Student Account Registration")
  with st.form("student_reg_form"):
    full_name = st.text_input("Full Name")
    phone = st.text_input("Phone Number")
    password = st.text_input("Password", type="password")
    reg_number = st.text_input("Registration Number (e.g., 2026/OCT/001)")
    year_of_study = st.number_input(
        "Year of Study", min_value=1, max_value=4, value=1
    )
    national_id = st.text_input("National ID / NIN")
    submitted = st.form_submit_button("Register Student")
    if submitted:
      if full_name and reg_number and password:
        try:
          hashed_pwd = hashlib.sha256(password.encode("utf-8")).hexdigest()
          cursor.execute(
              "INSERT INTO user (full_name, phone, password_hash)"
              " VALUES (?, ?, ?)",
              (full_name, phone, hashed_pwd),
          )
          u_id = cursor.lastrowid
          cursor.execute(
              "INSERT INTO student (reg_number, user_id,"
              " year_of_study, national_id) VALUES (?, ?, ?, ?)",
              (reg_number, u_id, year_of_study, national_id),
          )
          conn.commit()
          st.success(f"✅ Student '{full_name}' Registered Successfully!")
        except sqlite3.IntegrityError:
          st.error(f"❌ Error: Reg Number '{reg_number}' already exists.")
      else:
        st.warning("Please fill in all required fields.")

# -------------------------------------------------------------
# 3. MAKE ROOM RESERVATION
# -------------------------------------------------------------
elif menu == "🛌 Make Room Reservation":
  st.header("Room Booking Portal")
  st.write("Book your room by providing your registered student number.")

  reg_no = st.text_input("Enter Your Student Reg Number")

  # Fetch available rooms
  cursor.execute(
      "SELECT room_id, room_number, price FROM room WHERE status ="
      " 'Available'"
  )
  available_rooms = cursor.fetchall()
  room_options = {
      f"Room {r[1]} (UGX {r[2]:,.0f})": r[0] for r in available_rooms
  }

  if room_options:
    selected_room_label = st.selectbox(
        "Select Available Room", list(room_options.keys())
    )
    selected_room_id = room_options[selected_room_label]

    if st.button("Confirm Reservation Now"):
      if reg_no:
        cursor.execute(
            "SELECT reg_number FROM student WHERE reg_number = ?", (reg_no,)
        )
        if cursor.fetchone():
          booking_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          cursor.execute(
              "INSERT INTO booking (reg_number, room_id, booking_date,"
              " status) VALUES (?, ?, ?, 'Pending')",
              (reg_no, selected_room_id, booking_date),
          )
          conn.commit()
          new_b_id = cursor.lastrowid
          st.success(
              f"✅ Booking Created Successfully! Your Booking ID is"
              f" **#{new_b_id}**. Copy this ID to make your payment."
          )
        else:
          st.error(
              "❌ Error: This Registration Number is not registered yet."
              " Please register first under '📝 Register Student Account'."
          )
      else:
        st.warning("Please enter your student registration number first.")
  else:
    st.info("No rooms are currently available for booking.")
# -------------------------------------------------------------
# 4. PROCESS PAYMENT (FIXED DATABASE ERRORS)
# -------------------------------------------------------------
elif menu == "💳 Process Payment":
  st.header("Booking Payment Verification")
  st.write("Enter your active Booking ID to complete payment matching.")

  cursor.execute(
      "SELECT booking_id, reg_number, room_id FROM booking WHERE status ="
      " 'Pending'"
  )
  pending_bookings = cursor.fetchall()
  if pending_bookings:
    st.info("💡 Pending bookings currently available for testing:")
    for pb in pending_bookings:
      st.write(f"- **Booking ID #{pb[0]}** (Student: {pb[1]})")

  booking_id = st.number_input("Enter Booking ID Number", min_value=1, step=1)
  amount = st.number_input("Amount Paid (UGX)", min_value=0.0, step=10000.0)
  txn_ref = st.text_input("Mobile Money / Bank Reference Code (e.g., TXN12345)")
  method = st.selectbox(
      "Payment Method", ["MTN MoMo", "Airtel Money", "Bank Deposit"]
  )

  if st.button("Verify and Complete Payment"):
    cursor.execute(
        "SELECT booking_id, status FROM booking WHERE booking_id = ?",
        (booking_id,),
    )
    booking_record = cursor.fetchone()

    if booking_record:
      if booking_record[1] == "Confirmed":
        st.warning(
            f"⚠️ Booking #{booking_id} has already been paid and confirmed!"
        )
      else:
        try:
          cursor.execute(
              "INSERT INTO payment (booking_id, amount, transaction_ref,"
              " payment_method) VALUES (?, ?, ?, ?)",
              (booking_id, amount, txn_ref, method),
          )
          cursor.execute(
              "UPDATE booking SET status = 'Confirmed' WHERE booking_id = ?",
              (booking_id,),
          )
          cursor.execute(
              "SELECT room_id FROM booking WHERE booking_id = ?", (booking_id,)
          )
          res = cursor.fetchone()
          if res:
            cursor.execute(
                "UPDATE room SET status = 'Booked' WHERE room_id = ?",
                (res[0],),
            )
            conn.commit()
            st.success(
                f"✅ Payment Verified Successfully! Booking #{booking_id} is"
                " now CONFIRMED."
            )
        except sqlite3.IntegrityError:
          st.error(
              "❌ Error: This transaction reference code has already been"
              " used."
          )
    else:
      st.error(
          f"❌ Error: Booking ID #{booking_id} does not exist in the database."
      )

# -------------------------------------------------------------
# 5. EMERGENCY SOS DESK
# -------------------------------------------------------------
elif menu == "🚨 Emergency SOS Desk":
  st.header("🚨 Emergency SOS Panic Desk")
  sos_reg = st.text_input("Student Registration Number")
  sos_room = st.text_input("Current Room Number / Location")
  sos_type = st.selectbox(
      "Emergency Category", ["Medical", "Security Threat", "Fire Hazard"]
  )
  sos_desc = st.text_area("Brief Description of Emergency")
  if st.button("Broadcast Emergency Alert"):
    if sos_reg and sos_room and sos_desc:
      created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      cursor.execute(
          "INSERT INTO emergency (reg_number, room_number,"
          " emergency_type, description, created_at) VALUES (?, ?, ?,"
          " ?, ?)",
          (sos_reg, sos_room, sos_type, sos_desc, created_at),
      )
      conn.commit()
      st.error(
          "🚨 EMERGENCY ALERT BROADCASTED! Hostel wardens and management"
          " have been notified."
      )
    else:
      st.error("Please fill in all fields before broadcasting.")

# -------------------------------------------------------------
# 6. MANAGER CONTROL DASHBOARD
# -------------------------------------------------------------
elif menu == "📊 Manager Control Dashboard":
  st.header("Manager Control Panel")
  cursor.execute(
      "SELECT alert_id, reg_number, room_number, emergency_type, description"
      " FROM emergency WHERE status = 'Active (Unresolved)'"
  )
  emergencies = cursor.fetchall()
  if emergencies:
    st.error("🚨 CRITICAL ACTIVE EMERGENCIES")
    for e in emergencies:
      st.markdown(
          f"""
            * **Alert ID:** #{e[0]} | **Student:** {e[1]} | **Room:** {e[2]}
            * **Type:** {e[3]}
            * **Details:** {e[4]}
            """
      )
  else:
    st.success("No active emergency alerts at the moment.")

  st.divider()

  cursor.execute("SELECT SUM(amount) FROM payment")
  total_revenue = cursor.fetchone()[0] or 0.0
  st.metric(label="Total Revenue Collected", value=f"UGX {total_revenue:,.0f}")

  st.subheader("All System Bookings")
  cursor.execute("""
        SELECT b.booking_id, u.full_name, r.room_number, b.status 
        FROM booking b 
        JOIN student s ON b.reg_number = s.reg_number 
        JOIN user u ON s.user_id = u.user_id 
        JOIN room r ON b.room_id = r.room_id
    """)
  bookings = cursor.fetchall()
  for b in bookings:
    st.write(
        f"Booking #{b[0]} | Student: {b[1]} | Room: {b[2]} | Status:"
        f" {b[3]}"
    )

conn.close()

# --- VISITOR LOG / FEEDBACK SECTION ---
st.sidebar.markdown("---")
st.sidebar.subheader("📝 Visitor Log")
visitor_name = st.sidebar.text_input("Enter your Name / Reg No:")
if st.sidebar.button("Log Visit"):
  if visitor_name:
    st.sidebar.success(
        f"Thank you, {visitor_name}! Your visit has been recorded."
    )
  else:
    st.sidebar.warning("Please enter a name first.")
  # --- PEER COMMENTS & FEEDBACK SECTION ---
st.markdown("---")
st.header("💬 Coursemate & Panel Feedback")
st.write("Leave your comments, UI suggestions, or testing notes below:")

with st.form("feedback_form"):
  commenter = st.text_input("Your Name / Reg No")
  comment_text = st.text_area("Your Comment or UI Suggestion")
  submit_comment = st.form_submit_button("Submit Comment")

  if submit_comment:
    if commenter and comment_text:
      # You can save this to your database or display it instantly
      st.success(
          f"Thank you {commenter}! Your comment has been recorded for project"
          " review."
      )
      st.info(f'"{comment_text}"')
    else:
      st.warning("Please fill in both your name and comment.")    
