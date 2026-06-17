from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId

# Centralized MongoDB Cluster Connection Configuration
uri = "mongodb+srv://MayankRathore:Mk01092004@cluster0.rawu8tm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri)
db = client["Health_status_shower"]

# Plain text Master Key verification variable
ADMIN_MASTER_KEY = "ADMIN123"


def register_admin(email, name, provided_key):
    """Registers a new system administrator into the 'Admin' collection."""
    if provided_key != ADMIN_MASTER_KEY:
        raise ValueError("❌ Incorrect Master Security Key. Registration Denied.")

    admin_col = db["Admin"]
    email_clean = email.strip().lower()

    if admin_col.find_one({"email": email_clean}):
        raise ValueError("❌ An Administrative account with this email already exists.")

    admin_document = {
        "email": email_clean,
        "name": name.strip(),
        "role": "admin",
        "created_at": datetime.now()
    }
    admin_col.insert_one(admin_document)
    return admin_document


def verify_admin_login(email, provided_key):
    """Validates administrative credentials using the master key assignment."""
    if provided_key != ADMIN_MASTER_KEY:
        return None
    email_clean = email.strip().lower()
    return db["Admin"].find_one({"email": email_clean})


def _calculate_next_doctor_id():
    """Scans the database directory to compute the next incremental string identifier."""
    doctor_col = db["Doctor"]
    all_doctors = list(doctor_col.find({}))

    max_num = 0
    for doc in all_doctors:
        id_val = doc.get("doctor_id")
        if id_val and isinstance(id_val, str) and id_val.startswith("DOC"):
            try:
                num_part = int(id_val[3:])
                if num_part > max_num:
                    max_num = num_part
            except ValueError:
                continue

    return f"DOC{max_num + 1:03d}"


def add_new_doctor(name, email, specialization, availability="Mon-Fri", phone="0000000000", selected_times=None):
    """Onboards a physician profile into the 'Doctor' collection and auto-generates hourly slots."""
    if selected_times is None:
        selected_times = []

    doctor_col = db["Doctor"]
    email_clean = email.strip().lower()

    if doctor_col.find_one({"email": email_clean}):
        raise ValueError("❌ A doctor profile with this email address is already verified.")

    generated_id = _calculate_next_doctor_id()
    formatted_name = f"Dr. {name.replace('Dr. ', '').strip()}"
    timestamp_now = datetime.utcnow()

    # 1. Root Doctor Collection Schema Form
    doctor_document = {
        "email": email_clean,
        "availability": availability.strip(),
        "created_at": timestamp_now,
        "doctor_id": generated_id,
        "experience_years": 15,
        "name": formatted_name,
        "phone": phone.strip(),
        "qualification": "MBBS, MD",
        "specialization": specialization.strip(),
        "updated_at": None
    }
    doctor_col.insert_one(doctor_document)

    # Generate sub-collection weekday mappings
    _initialize_slots_for_doctor(email_clean, generated_id, formatted_name, availability, selected_times, timestamp_now)
    return generated_id


def update_doctor_profile(doctor_id, name, email, specialization, availability, phone, selected_times=None):
    """Updates an existing doctor record and regenerates/syncs availability matrices."""
    if selected_times is None:
        selected_times = []

    doctor_col = db["Doctor"]
    existing_doc = doctor_col.find_one({"doctor_id": doctor_id})
    if not existing_doc:
        return False

    old_email = existing_doc.get("email")
    email_clean = email.strip().lower()
    formatted_name = f"Dr. {name.replace('Dr. ', '').strip()}"
    timestamp_now = datetime.utcnow()

    # Update root doctor collection document
    doctor_col.update_one(
        {"doctor_id": doctor_id},
        {"$set": {
            "name": formatted_name,
            "email": email_clean,
            "specialization": specialization.strip(),
            "availability": availability.strip(),
            "phone": phone.strip(),
            "updated_at": timestamp_now
        }}
    )

    # Purge old availability matrices across all week tables
    all_weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for day in all_weekdays:
        db[f"Availability_{day}"].delete_many({"$or": [{"email": old_email}, {"Doctor_id": doctor_id}]})

    # Re-initialize updated slot records
    _initialize_slots_for_doctor(email_clean, doctor_id, formatted_name, availability, selected_times, timestamp_now)
    return True


def _initialize_slots_for_doctor(email_clean, doctor_id, formatted_name, availability, selected_times, timestamp):
    """Helper method to construct availability slot mapping forms matching your verified layout schema."""
    days_to_initialize = []
    avail_lower = availability.lower()

    if "mon-fri" in avail_lower:
        days_to_initialize.extend(["monday", "tuesday", "wednesday", "thursday", "friday"])
    elif "mon-sat" in avail_lower:
        days_to_initialize.extend(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"])
    elif "tue-sat" in avail_lower:
        days_to_initialize.extend(["tuesday", "wednesday", "thursday", "friday", "saturday"])
    else:
        all_weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for d in all_weekdays:
            if d[:3] in avail_lower:
                days_to_initialize.append(d)

    if not days_to_initialize:
        days_to_initialize = ["monday"]

    all_possible_slots = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30"]

    for day in days_to_initialize:
        collection_name = f"Availability_{day}"
        slot_matrix_doc = {
            "email": email_clean,
            "09:00": "available" if "09:00" in selected_times else "unavailable",
            "09:30": "available" if "09:30" in selected_times else "unavailable",
            "10:00": "available" if "10:00" in selected_times else "unavailable",
            "10:30": "available" if "10:30" in selected_times else "unavailable",
            "11:00": "available" if "11:00" in selected_times else "unavailable",
            "11:30": "available" if "11:30" in selected_times else "unavailable",
            "12:00": "available" if "12:00" in selected_times else "unavailable",
            "12:30": "available" if "12:30" in selected_times else "unavailable",
            "13:00": "available" if "13:00" in selected_times else "unavailable",
            "13:30": "available" if "13:30" in selected_times else "unavailable",
            "Created_at": timestamp,
            "Doctor_id": doctor_id,
            "Name": formatted_name,
            "Updated_at": None
        }
        db[collection_name].insert_one(slot_matrix_doc)


def delete_doctor_by_id(doctor_id):
    """Completely purges a physician from the Doctor table and clears out week tracking slots."""
    doctor_col = db["Doctor"]
    doctor = doctor_col.find_one({"doctor_id": doctor_id})
    if not doctor:
        return False

    email_target = doctor.get("email")
    doctor_col.delete_one({"_id": doctor["_id"]})

    all_weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for day in all_weekdays:
        db[f"Availability_{day}"].delete_many({"$or": [{"email": email_target}, {"Doctor_id": doctor_id}]})
    return True


def update_patient_profile(patient_id, name, email, phone, age, gender):
    """Updates demographic records stored within the main Customer database table collection."""
    try:
        db["Customer"].update_one(
            {"_id": ObjectId(patient_id)},
            {"$set": {
                "name": name.strip(),
                "Name": name.strip(),
                "email": email.strip().lower(),
                "Email": email.strip().lower(),
                "phone": phone.strip(),
                "Phone": phone.strip(),
                "age": int(age),
                "Age": int(age),
                "gender": gender.strip(),
                "Gender": gender.strip()
            }}
        )
        return True
    except Exception:
        return False


def delete_patient_by_id(patient_id):
    """Removes a targeted customer document account entry using its explicit object ID mapping reference."""
    try:
        result = db["Customer"].delete_one({"_id": ObjectId(patient_id)})
        return result.deleted_count > 0
    except Exception:
        return False


def get_all_patients():
    """Retrieves all records from the 'Customer' collection."""
    patients = list(db["Customer"].find({}))
    for p in patients:
        p['_id_str'] = str(p['_id'])  # Pre-convert ObjectId to plain text string map key for HTML safety
    return patients


def get_all_doctors():
    """Retrieves all records from the 'Doctor' collection."""
    return list(db["Doctor"].find({}))