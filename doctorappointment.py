from pymongo import MongoClient
from datetime import datetime
import re

# MongoDB connection
uri = "mongodb+srv://MayankRathore:Mk01092004@cluster0.rawu8tm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri)

db = client["Health_status_shower"]
collection = db["Doctor"]


def existing_user(email):
    """
    Checks if a doctor exists in the registry by email and returns their doctor_id.
    """
    email = email.strip()
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        raise ValueError("📧 Invalid email format.")

    existing = collection.find_one({'email': email})
    if existing:
        doctor_id = existing.get("doctor_id") or existing.get("Doctor_id")
        return str(doctor_id)
    return None


def get_appointments(D_id, choice):
    """
    Retrieves appointments for a specific doctor from the Appointment collection.
    """
    if not D_id:
        return {"error": "Doctor ID not found.", "appointments": []}

    appointment_col = db["Appointment"]
    # Ensure matching format to your booking system date storage (e.g., YYYY-MM-DD)
    today = datetime.today().strftime("%Y-%m-%d")

    appointments_list = []

    # Query using database key fallbacks
    if choice == "1":
        cursor = appointment_col.find({
            "$and": [
                {"$or": [{"Doctor_id": D_id}, {"doctor_id": D_id}]},
                {"$or": [{"Date": today}, {"date": today}]}
            ]
        })
        label = f"Appointments for today ({today})"
    elif choice == "2":
        cursor = appointment_col.find({
            "$and": [
                {"$or": [{"Doctor_id": D_id}, {"doctor_id": D_id}]},
                {"$or": [{"Date": {"$gt": today}}, {"date": {"$gt": today}}]}
            ]
        })
        label = "Upcoming Schedule"
    else:
        return {"error": "Invalid choice parameters.", "appointments": []}

    # Extracting the correct keys from the Appointment records
    for appt in cursor:
        # Check 'slot' first, then look for 'Time_slot' or 'time_slot' as backups
        time_value = appt.get("slot") or appt.get("slot") or appt.get("slot") or "Not Specified"
        date_value = appt.get("Date") or appt.get("date") or "No Date"
        patient_value = appt.get("Patient_id") or appt.get("patient_id") or "Unknown"

        appointments_list.append({
            "Patient_id": patient_value,
            "Date": date_value,
            "slot": time_value
        })

    return {
        "label": label,
        "appointments": appointments_list
    }