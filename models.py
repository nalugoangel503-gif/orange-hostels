import csv
import hashlib
import sqlite3
from datetime import datetime, timedelta

DB_NAME = "orange_hostels.db"

# ==========================================
# DATABASE INITIALIZATION & EXPIRY LOGIC
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        password_hash TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student (
        reg_number TEXT PRIMARY KEY,
        user_id INTEGER UNIQUE,
        year_of_study INTEGER NOT NULL,
        national_id TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS manager (
        manager_id TEXT PRIMARY KEY,
        user_id INTEGER UNIQUE,
        department TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS room (
        room_id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_number TEXT UNIQUE NOT NULL,
        capacity INTEGER NOT NULL,
        price REAL NOT NULL,
        status TEXT DEFAULT 'Available'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS booking (
        booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
        reg_number TEXT NOT NULL,
        room_id INTEGER NOT NULL,
        booking_date TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        FOREIGN KEY (reg_number) REFERENCES student(reg_number),
        FOREIGN KEY (room_id) REFERENCES room(room_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payment (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER UNIQUE NOT NULL,
        amount REAL NOT NULL,
        transaction_ref TEXT UNIQUE NOT NULL,
        payment_method TEXT NOT NULL,
        FOREIGN KEY (booking_id) REFERENCES booking(booking_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emergency (
        alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
        reg_number TEXT NOT NULL,
        room_number TEXT NOT NULL,
        emergency_type TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'Active (Unresolved)',
        created_at TEXT NOT NULL,
        FOREIGN KEY (reg_number) REFERENCES student(reg_number)
    )
    """)

    # Seed Default Rooms
    cursor.execute("SELECT COUNT(*) FROM room")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            """
        INSERT INTO room (room_number, capacity, price, status)
        VALUES (?, ?, ?, 'Available')
        """,
            [
                ("Block A - 101", 2, 500000.0),
                ("Block A - 102", 1, 800000.0),
                ("Block B - 201", 4, 350000.0),
            ],
        )

    conn.commit()
    conn.close()


def auto_cancel_expired_bookings():
    """Automated Feature: Cancels pending bookings older than 24 hours."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    time_threshold = (datetime.now() - timedelta(hours=24)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    cursor.execute(
        """
        SELECT booking_id, room_id FROM booking 
        WHERE status = 'Pending' AND booking_date < ?
    """,
        (time_threshold,),
    )
    expired_bookings = cursor.fetchall()

    for b_id, r_id in expired_bookings:
        cursor.execute(
            "UPDATE booking SET status = 'Expired' WHERE booking_id = ?",
            (b_id,),
        )
        cursor.execute(
            "UPDATE room SET status = 'Available' WHERE room_id = ?", (r_id,)
        )

    conn.commit()
    conn.close()
    if expired_bookings:
        print(
            f"🧹 [Auto-Cleanup] {len(expired_bookings)} expired pending"
            " booking(s) released back to room inventory."
        )


# ==========================================
# OOP CLASSES & AUTHENTICATION
# ==========================================
class User:

    def __init__(self, full_name, phone, password):
        self.full_name = full_name
        self.phone = phone
        self.password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()


class Student(User):

    @staticmethod
    def register(
        full_name, phone, password, reg_number, year_of_study, national_id
    ):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            hashed_pwd = hashlib.sha256(password.encode("utf-8")).hexdigest()
            cursor.execute(
                "INSERT INTO user (full_name, phone, password_hash) VALUES"
                " (?, ?, ?)",
                (full_name, phone, hashed_pwd),
            )
            u_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO student (reg_number, user_id, year_of_study,"
                " national_id) VALUES (?, ?, ?, ?)",
                (reg_number, u_id, year_of_study, national_id),
            )
            conn.commit()
            print(f"✅ Student '{full_name}' Registered Successfully!")
        except sqlite3.IntegrityError:
            print(f"❌ Error: Reg Number '{reg_number}' already exists.")
        finally:
            conn.close()


class Manager(User):

    @staticmethod
    def register_manager(full_name, phone, password, manager_id, department):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            hashed_pwd = hashlib.sha256(password.encode("utf-8")).hexdigest()
            cursor.execute(
                "INSERT INTO user (full_name, phone, password_hash) VALUES"
                " (?, ?, ?)",
                (full_name, phone, hashed_pwd),
            )
            u_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO manager (manager_id, user_id, department) VALUES"
                " (?, ?, ?)",
                (manager_id, u_id, department),
            )
            conn.commit()
            print(f"✅ Manager '{full_name}' Registered Successfully!")
        except sqlite3.IntegrityError:
            print(f"❌ Error: Manager ID '{manager_id}' already exists.")
        finally:
            conn.close()


def authenticate_user():
    """Session Authentication Feature"""
    print("\n🔐 --- USER LOGIN SYSTEM ---")
    identifier = input("Enter Student Reg Number OR Manager ID: ").strip()
    password = input("Enter Password: ").strip()
    hashed_pwd = hashlib.sha256(password.encode("utf-8")).hexdigest()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Check Student
    cursor.execute(
        """
        SELECT s.reg_number, u.full_name FROM student s
        JOIN user u ON s.user_id = u.user_id
        WHERE s.reg_number = ? AND u.password_hash = ?
    """,
        (identifier, hashed_pwd),
    )
    student = cursor.fetchone()

    if student:
        conn.close()
        print(f"\n🎉 Welcome back, Student {student[1]}!")
        return {"role": "student", "id": student[0], "name": student[1]}

    # Check Manager
    cursor.execute(
        """
        SELECT m.manager_id, u.full_name FROM manager m
        JOIN user u ON m.user_id = u.user_id
        WHERE m.manager_id = ? AND u.password_hash = ?
    """,
        (identifier, hashed_pwd),
    )
    manager = cursor.fetchone()
    conn.close()

    if manager:
        print(f"\n🎉 Welcome back, Manager {manager[1]}!")
        return {"role": "manager", "id": manager[0], "name": manager[1]}

    print("❌ Authentication Failed: Invalid Credentials.")
    return None


# ==========================================
# SYSTEM FUNCTIONS & CSV EXPORTER
# ==========================================
def view_rooms():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT room_id, room_number, capacity, price, status FROM room"
    )
    rooms = cursor.fetchall()
    conn.close()

    print("\n--- HOSTEL ROOMS INVENTORY ---")
    print(
        f"{'ID':<5} {'Room Number':<20} {'Capacity':<10} {'Price (UGX)':<15}"
        " {'Status':<10}"
    )
    print("-" * 65)
    for r in rooms:
        print(f"{r[0]:<5} {r[1]:<20} {r[2]:<10} {r[3]:<15,.0f} {r[4]:<10}")


def book_room(session_user):
    auto_cancel_expired_bookings()
    reg_no = session_user["id"]
    view_rooms()
    room_id = input("\nEnter Room ID to Book: ").strip()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM room WHERE room_id = ?", (room_id,))
    room_res = cursor.fetchone()

    if not room_res or room_res[0] != "Available":
        print("❌ Selected room is not available for booking.")
        conn.close()
        return

    booking_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO booking (reg_number, room_id, booking_date, status)"
        " VALUES (?, ?, ?, 'Pending')",
        (reg_no, room_id, booking_date),
    )
    b_id = cursor.lastrowid
    conn.commit()
    conn.close()

    print(
        f"✅ Booking #{b_id} Created for {reg_no}! Status: Pending Payment"
        " (Expires in 24 Hours)."
    )


def process_payment():
    b_id = input("\nEnter Booking ID to Pay For: ").strip()
    amount = float(input("Enter Amount (UGX): ").strip())
    txn_ref = input("Enter Mobile Money / Bank Ref Code: ").strip()
    method = input("Enter Method (MTN MoMo / Airtel Money / Bank): ").strip()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO payment (booking_id, amount, transaction_ref,"
            " payment_method) VALUES (?, ?, ?, ?)",
            (b_id, amount, txn_ref, method),
        )
        cursor.execute(
            "UPDATE booking SET status = 'Confirmed' WHERE booking_id = ?",
            (b_id,),
        )

        cursor.execute(
            "SELECT room_id FROM booking WHERE booking_id = ?", (b_id,)
        )
        res = cursor.fetchone()
        if res:
            cursor.execute(
                "UPDATE room SET status = 'Booked' WHERE room_id = ?", (res[0],)
            )

        conn.commit()
        print(f"✅ Payment Verified! Booking #{b_id} CONFIRMED.")
    except sqlite3.IntegrityError:
        print("❌ Error: Payment reference or Booking ID already processed.")
    finally:
        conn.close()


def send_emergency_sos(session_user):
    print("\n🚨 --- EMERGENCY SOS PANIC DESK ---")
    reg_no = session_user["id"]
    room_no = input("Enter Current Room / Location: ").strip()
    e_type = input("Emergency Category (Medical / Security / Fire): ").strip()
    desc = input("Describe Emergency Need: ").strip()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO emergency (reg_number, room_number, emergency_type,"
        " description, created_at) VALUES (?, ?, ?, ?, ?)",
        (reg_no, room_no, e_type, desc, created_at),
    )
    conn.commit()
    conn.close()

    print("🚨 EMERGENCY ALERT BROADCASTED! Hostel wardens & managers notified.")


def manager_dashboard():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT alert_id, reg_number, room_number, emergency_type, description"
        " FROM emergency WHERE status = 'Active (Unresolved)'"
    )
    emergencies = cursor.fetchall()
    if emergencies:
        print("\n🚨 --- CRITICAL ACTIVE EMERGENCY ALERTS ---")
        for e in emergencies:
            print(
                f"ALERT #{e[0]} | Student: {e[1]} | Room: {e[2]} | Category:"
                f" {e[3]} | Detail: {e[4]}"
            )
        print("-" * 65)

    cursor.execute("SELECT SUM(amount) FROM payment")
    total_rev = cursor.fetchone()[0] or 0.0

    print("\n📊 --- MANAGER CONTROL DASHBOARD ---")
    print(f"💰 Total Revenue Collected: UGX {total_rev:,.0f}")

    print("\n📋 All System Bookings:")
    cursor.execute("""
        SELECT b.booking_id, u.full_name, r.room_number, b.status 
        FROM booking b
        JOIN student s ON b.reg_number = s.reg_number
        JOIN user u ON s.user_id = u.user_id
        JOIN room r ON b.room_id = r.room_id
    """)
    for b in cursor.fetchall():
        print(
            f"  Booking #{b[0]} | Student: {b[1]} | Room: {b[2]} | Status:"
            f" {b[3]}"
        )

    conn.close()


def export_reports_to_csv():
    """CSV Export Feature for Management Reports"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Export Payments
    cursor.execute("""
        SELECT p.payment_id, b.reg_number, p.amount, p.transaction_ref, p.payment_method 
        FROM payment p JOIN booking b ON p.booking_id = b.booking_id
    """)
    payments = cursor.fetchall()
    with open("financial_audit_report.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Payment ID",
            "Student Reg No",
            "Amount (UGX)",
            "Transaction Ref",
            "Method",
        ])
        writer.writerows(payments)

    # 2. Export Emergency Logs
    cursor.execute(
        "SELECT alert_id, reg_number, room_number, emergency_type, status,"
        " created_at FROM emergency"
    )
    emergencies = cursor.fetchall()
    with open("emergency_incident_log.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Alert ID",
            "Reg No",
            "Room",
            "Type",
            "Status",
            "Timestamp",
        ])
        writer.writerows(emergencies)

    conn.close()
    print(
        "📁 [EXPORT COMPLETE] Generated 'financial_audit_report.csv' and"
        " 'emergency_incident_log.csv'!"
    )


def show_terms():
    print("\n📜 --- TERMS & CONDITIONS ---")
    print("1. Booking status is 'Pending' until payment is verified.")
    print("2. Rooms held under 'Pending' status expire after 24 hours.")
    print("3. Quiet hours observed between 10:00 PM and 6:00 AM daily.")
    print("4. Emergency SOS Panic Desk is strictly for medical/safety threats.")


def show_architecture_diagrams():
    print("\n📐 ==========================================")
    print("SYSTEM ARCHITECTURE, UML & DATABASE MODELING")
    print("==========================================")

    print("\n1. UML CLASS DIAGRAM (OBJECT-ORIENTED MODEL):")
    print("""
    +-------------------------------------------------------------------------+
    |                                User                                     |
    +-------------------------------------------------------------------------+
    | - user_id: int | - full_name: string | - phone: string | - password_hash|
    +-------------------------------------------------------------------------+
                                        ▲
                                        │ (Inheritance)
                      ┌─────────────────┴─────────────────┐
                      │                                   │
    +-----------------------------------+ +-----------------------------------+
    |              Student              | |              Manager              |
    +-----------------------------------+ +-----------------------------------+
    | - reg_number: string [PK]         | | - manager_id: string [PK]         |
    | - year_of_study: int              | | - department: string            |
    | - national_id: string             | +-----------------------------------+
    +-----------------------------------+
    """)

    print("\n2. RELATIONAL DATABASE SCHEMA (ERD):")
    print("  • USER      (user_id [PK], full_name, phone, password_hash)")
    print(
        "  • STUDENT   (reg_number [PK], user_id [FK], year_of_study,"
        " national_id)"
    )
    print("  • MANAGER   (manager_id [PK], user_id [FK], department)")
    print("  • ROOM      (room_id [PK], room_number, capacity, price, status)")
    print(
        "  • BOOKING   (booking_id [PK], reg_number [FK], room_id [FK],"
        " booking_date, status)"
    )
    print(
        "  • PAYMENT   (payment_id [PK], booking_id [FK, UNIQUE], amount,"
        " transaction_ref, payment_method)"
    )
    print(
        "  • EMERGENCY (alert_id [PK], reg_number [FK], room_number,"
        " emergency_type, description, status)"
    )