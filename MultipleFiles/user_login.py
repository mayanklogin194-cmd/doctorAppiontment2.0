# MultipleFiles/user_login.py (Modified)
from pymongo import MongoClient
from datetime import datetime
import re

# MongoDB connection
uri = "mongodb+srv://MayankRathore:Mk01092004@cluster0.rawu8tm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri)
db = client["Health_status_shower"]
collection = db["Customer"]

def generate_patient_id():
    count = collection.count_documents({})
    return f"PAT{count + 1:03}"

# New function to handle user creation from web form
def create_new_user_web(name, email, contact_number, gender, age, pincode):
    if not name:
        raise ValueError("Name cannot be empty.")
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        raise ValueError("Invalid email format. Use something like user@example.com")
    if not re.match(r'^\+91\d{10}$', contact_number):
        raise ValueError("Please enter a valid Indian contact number (e.g., +911234567890)")
    if not (0 <= age <= 120):
        raise ValueError("Age must be between 0 and 120 years.")

    existing = collection.find_one({'email': email})
    if existing:
        patient_id = str(existing["Patient_id"])
        current_date = existing["current_date"] # Keep original creation date
        updated_date = datetime.now()
    else:
        patient_id = str(generate_patient_id())
        current_date = datetime.now()
        updated_date = None

    user_data = {
        "Patient_id": patient_id,
        "Name": name,
        "email": email,
        "contact_number": contact_number,
        "Gender": gender,
        "Age": age,
        "pincode": pincode,
        "current_date": current_date,
        "update_date": updated_date
    }

    collection.update_one(
        {"email": email},
        {"$set": user_data},
        upsert=True
    )
    return user_data

# Original new_user function (can be removed or kept if needed for other purposes)
def new_user():
    # This function will no longer be called directly by Flask
    pass
