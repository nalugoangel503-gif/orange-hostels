from datetime import datetime
import hashlib
import sqlite3
import models
import streamlit as st

# Initialize the database and default rooms on app load
models.init_db()

# Page configuration
st.set_page_config(
    page_title="Orange Hostels Management System", page_icon="🍊", layout="wide"
)

st.title("🍊 Orange Hostels Management System")
st.markdown(
    "### Kampala University Luweero Campus | Student Portal & Management"
    " Dashboard"
)
st.info(
    "📍 **Hostel Location Background:** Luweero District | Katikamu Town Council"
    " | Butanza Sub-county | Nakyewa Village"
)

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
        status_color = "green" if r[4] == "Available" else "orange"
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
    st.write(
        "Fill in your details below to create your student account in the"
        " system."
    )

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
                    hashed_pwd = hashlib.sha256(
                        password.encode("utf-8")
                    ).hexdigest()
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
                    st.success(
                        f"✅ Student '{full_name}' Registered Successfully!"
                    )
                except sqlite3.IntegrityError:
                    st.error(
                        f"❌ Error: Reg Number '{reg_number}' already exists."
                    )
            else:
                st.warning("Please fill in all required fields.")

# -------------------------------------------------------------
# 3. MAKE ROOM RESERVATION
# -------------------------------------------------------------
elif menu == "🛌 Make Room Reservation":
    st.header("Room Booking Portal")

    reg_no = st.text_input("Enter Your Student Reg Number")

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

        if st.button("Confirm Reservation"):
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
                st.success(
                    "✅ Booking Created Successfully! Status: Pending Payment."
                )
            else:
                st.error(
                    "❌ Error: Student Registration Number not found in the"
                    " system."
                )
    else:
        st.info("No rooms are currently available for booking.")

# -------------------------------------------------------------
# 4. PROCESS PAYMENT
# -------------------------------------------------------------
elif menu == "💳 Process Payment":
    st.header("Booking Payment Verification")

    booking_id = st.text_input("Enter Booking ID")
    amount = st.number_input("Amount Paid (UGX)", min_value=0.0, step=10000.0)
    txn_ref = st.text_input("Mobile Money / Bank Reference Code")
    method = st.selectbox(
        "Payment Method", ["MTN MoMo", "Airtel Money", "Bank Deposit"]
    )

    if st.button("Verify and Complete Payment"):
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
                f"✅ Payment Verified! Booking #{booking_id} is now CONFIRMED."
            )
        except sqlite3.IntegrityError:
            st.error(
                "❌ Error: Payment reference or Booking ID has already been"
                " processed."
            )

# -------------------------------------------------------------
# 5. EMERGENCY SOS DESK
# -------------------------------------------------------------
elif menu == "🚨 Emergency SOS Desk":
    st.header("🚨 Emergency SOS Panic Desk")
    st.warning(
        "Use this interface strictly for urgent medical, security, or safety"
        " alerts."
    )

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

    # Display Active Emergencies
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

    # Revenue Metrics
    cursor.execute("SELECT SUM(amount) FROM payment")
    total_revenue = cursor.fetchone()[0] or 0.0
    st.metric(
        label="Total Revenue Collected", value=f"UGX {total_revenue:,.0f}"
    )

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
import streamlit as st

# --- VISITOR LOG / FEEDBACK SECTION ---
st.sidebar.markdown("---")
st.sidebar.subheader("📝 Visitor Log")
visitor_name = st.sidebar.text_input("Enter your Name / Reg No:")
if st.sidebar.button("Log Visit"):
  if visitor_name:
    st.sidebar.success(
        f"Thank you, {visitor_name}! Your visit has been recorded."
    )
    # You can save this to a list or database table if you want
  else:
    st.sidebar.warning("Please enter a name first.")
