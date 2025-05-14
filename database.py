import sqlite3
import uuid

DB_FILE = "hospital_db.sqlite3"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create patients table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Patients (
            patient_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            contact_number TEXT,
            email TEXT,
            medical_history TEXT
        )
    ''')
    
    # Create doctors table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Doctors (
            doctor_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL
        )
    ''')
    
    # Create appointments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Appointments (
            appointment_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            doctor_id TEXT NOT NULL,
            department TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES Patients (patient_id),
            FOREIGN KEY (doctor_id) REFERENCES Doctors (doctor_id)
        )
    ''')
    
    # Insert sample doctors if table is empty
    cursor.execute("SELECT COUNT(*) FROM Doctors")
    if cursor.fetchone()[0] == 0:
        sample_doctors = [
            ("DOC001", "Dr. Smith", "Cardiology"),
            ("DOC002", "Dr. Johnson", "Neurology"),
            ("DOC003", "Dr. Williams", "Pediatrics"),
            ("DOC004", "Dr. Brown", "Orthopedics"),
            ("DOC005", "Dr. Jones", "Dermatology")
        ]
        cursor.executemany("INSERT INTO Doctors (doctor_id, name, specialization) VALUES (?, ?, ?)", sample_doctors)
    
    conn.commit()
    conn.close()

def book_appointment(name, age, gender, contact_number, email, medical_history, appointment_date, appointment_time):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        patient_id = str(uuid.uuid4())[:8]  # Generate a unique 8-character patient ID
        appointment_id = str(uuid.uuid4())[:8]  # Generate a unique 8-character appointment ID
        
        # Insert new patient record
        cursor.execute("""
            INSERT INTO Patients (patient_id, name, age, gender, contact_number, email, medical_history)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (patient_id, name, age, gender, contact_number, email, medical_history))
        conn.commit()
        
        # Look for doctors with matching specialization
        cursor.execute("""
            SELECT doctor_id, name FROM Doctors
            WHERE specialization = ?
        """, (medical_history,))
        doctors = cursor.fetchall()
        
        if not doctors:
            conn.close()
            return {"error": f"No doctors found with specialization '{medical_history}'"}
        
        selected_doctor = None
        for doctor in doctors:
            doc_id, doc_name = doctor
            cursor.execute("""
                SELECT appointment_id FROM Appointments
                WHERE doctor_id = ? AND date = ? AND time = ?
            """, (doc_id, appointment_date, appointment_time))
            
            if cursor.fetchone() is None:
                selected_doctor = (doc_id, doc_name)
                break
        
        if not selected_doctor:
            conn.close()
            return {"error": "No doctor available at the given time. Please choose another date/time."}
        
        doctor_id, doctor_name = selected_doctor
        
        # Insert appointment
        cursor.execute("""
            INSERT INTO Appointments (appointment_id, patient_id, doctor_id, department, date, time, status)
            VALUES (?, ?, ?, ?, ?, ?, 'Scheduled')
        """, (appointment_id, patient_id, doctor_id, medical_history, appointment_date, appointment_time))
        
        conn.commit()
        return {
            "message": f"Appointment scheduled with Dr. {doctor_name}",
            "patient_id": patient_id,
            "appointment_id": appointment_id,
            "doctor_id": doctor_id,
            "doctor_name": doctor_name
        }
    
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    
    finally:
        conn.close()


def reschedule_appointment(patient_name, old_date, old_time, new_date, new_time):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get the patient_id from the patients table
    cursor.execute("SELECT patient_id FROM Patients WHERE name = ?", (patient_name,))
    patient = cursor.fetchone()

    if not patient:
        conn.close()
        return False

    patient_id = patient[0]

    # Find the appointment based on patient_id, old_date, and old_time
    cursor.execute("""
        SELECT appointment_id FROM Appointments WHERE patient_id = ? AND date = ? AND time = ?
    """, (patient_id, old_date, old_time))

    appointment = cursor.fetchone()

    if not appointment:
        conn.close()
        return False

    appointment_id = appointment[0]

    # Update the appointment with new date and time
    cursor.execute("""
        UPDATE Appointments SET date = ?, time = ? WHERE appointment_id = ?
    """, (new_date, new_time, appointment_id))

    updated = cursor.rowcount  # Check if any row was updated
    conn.commit()
    conn.close()
    
    return updated > 0

def cancel_appointment(patient_name, date, time):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Get the patient_id from the patients table
    cursor.execute("SELECT patient_id FROM Patients WHERE name = ?", (patient_name,))
    patient = cursor.fetchone()

    if not patient:
        conn.close()
        return False

    patient_id = patient[0]

    # Find the appointment matching patient_id, date, and time
    cursor.execute("""
        SELECT appointment_id FROM Appointments WHERE patient_id = ? AND date = ? AND time = ?
    """, (patient_id, date, time))

    appointment = cursor.fetchone()

    if not appointment:
        conn.close()
        return False

    appointment_id = appointment[0]

    # Update appointment status to 'Cancelled' instead of deleting
    cursor.execute("UPDATE Appointments SET status = 'Cancelled' WHERE appointment_id = ?", (appointment_id,))
    
    updated = cursor.rowcount  # Check if any row was updated
    conn.commit()
    conn.close()
    
    return updated > 0

def get_appointments():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.appointment_id, a.patient_id, p.name AS patient_name,
                a.doctor_id, d.name AS doctor_name,
                a.department, a.date, a.time, a.status,
                p.age, p.gender, p.contact_number, p.email, p.medical_history
        FROM Appointments a
        JOIN Patients p ON a.patient_id = p.patient_id
        JOIN Doctors d ON a.doctor_id = d.doctor_id
    """)
    
    rows = cursor.fetchall()
    
    appointments = [{
        "id": row["appointment_id"],
        "patientId": row["patient_id"],
        "patientName": row["patient_name"],
        "doctorId": row["doctor_id"],
        "doctorName": row["doctor_name"],
        "department": row["department"],
        "date": row["date"],
        "time": row["time"],
        "status": row["status"],
        "patientAge": row["age"],
        "patientGender": row["gender"],
        "patientContact": row["contact_number"],
        "patientEmail": row["email"],
        "medicalHistory": row["medical_history"]
    } for row in rows]
    
    conn.close()
    return appointments