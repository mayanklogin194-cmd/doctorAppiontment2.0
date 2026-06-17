# MultipleFiles/Appointment.py (Updated for Date-based booking)
from pymongo import MongoClient
from datetime import datetime
import calendar
import re

# MongoDB connection
uri = "mongodb+srv://MayankRathore:Mk01092004@cluster0.rawu8tm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri)
db = client["Health_status_shower"]

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Expand "Mon-Fri" etc
def expand_day_range(day_range):
    parts = day_range.split("-")
    if len(parts) == 1:
        return [parts[0]]
    start, end = parts
    start_idx = DAYS.index(start)
    end_idx = DAYS.index(end)
    if start_idx <= end_idx:
        return DAYS[start_idx:end_idx + 1]
    else:
        return DAYS[start_idx:] + DAYS[:end_idx + 1]

# --- Step 1: Get specializations ---
def get_specializations_for_web():
    return db["Doctor"].distinct("specialization")

# --- Step 2: Get doctors for specialization ---
def get_doctors_for_web(selected_spec):
    return list(db["Doctor"].find({"specialization": selected_spec}))

# --- Step 3: Get valid dates for a doctor (this month only) ---
def get_valid_dates_for_doctor(availability_text):
    today = datetime.now().date()
    year, month = today.year, today.month
    days_in_month = calendar.monthrange(year, month)[1]

    # Expand availability text (e.g. "Mon-Fri,Sat")
    available_days = []
    for part in re.split(r"[,\s]+", availability_text.strip()):
        if "-" in part:
            available_days.extend(expand_day_range(part))
        elif part in DAYS:
            available_days.append(part)

    valid_dates = []
    for d in range(today.day, days_in_month + 1):
        date_obj = datetime(year, month, d).date()
        if date_obj.strftime("%a") in available_days:
            valid_dates.append(date_obj.strftime("%Y-%m-%d"))
    return valid_dates

# --- Step 4: Get available slots (merge Availability + Appointment) ---
def get_available_slots_web(doctor_id, chosen_date):
    weekday_short = datetime.strptime(chosen_date, "%Y-%m-%d").strftime("%a").lower()

    # Find correct collection (Availability_mon / Availability_monday etc.)
    target_col = None
    for col in db.list_collection_names():
        if f"availability_{weekday_short}" in col.lower():
            target_col = col
            break
    if not target_col:
        return []

    availability_col = db[target_col]

    doctor_data = availability_col.find_one({"Doctor_id": doctor_id}) or \
                  availability_col.find_one({"doctor_id": doctor_id})
    if not doctor_data:
        return []

    # Get booked slots for this doctor on that date
    appointment_col = db["Appointment"]
    booked = set(
        appt["Slot"] for appt in appointment_col.find({
            "Doctor_id": doctor_id,
            "Date": chosen_date
        })
    )

    # Filter available slots
    available_slots = []
    for time, status in doctor_data.items():
        if re.match(r"^\d{2}:\d{2}$", time) and status == "available" and time not in booked:
            available_slots.append(time)
    return sorted(available_slots)

# --- Step 5: Book appointment ---
def book_appointment_web(patient_id, doctor_id, doctor_name, chosen_date, selected_slot):
    appointment_col = db["Appointment"]

    # Double-check if slot already booked
    already = appointment_col.find_one({
        "Doctor_id": doctor_id,
        "Date": chosen_date,
        "Slot": selected_slot
    })
    if already:
        raise ValueError("Slot already booked.")

    appointment_col.insert_one({
        "Doctor_id": doctor_id,
        "Doctor_name": doctor_name,
        "Patient_id": patient_id,
        "Slot": selected_slot,
        "Date": chosen_date,
        "Created_at": datetime.now()
    })
    return True
