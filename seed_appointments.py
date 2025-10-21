from pymongo import MongoClient
from bson import ObjectId
import random
from datetime import datetime, timedelta

# -----------------------------
# Connect to your existing DB
# -----------------------------
client = MongoClient("mongodb://127.0.0.1:27017")
db = client.healthcareDB
patients = db.patients

# -----------------------------
# Appointment Templates
# -----------------------------
doctors = ["Dr. Smith", "Dr. Adams", "Dr. Lee", "Dr. Patel", "Dr. Brown", "Dr. Taylor", "Dr. Garcia"]
statuses = ["scheduled", "completed", "cancelled"]
notes_examples = [
    "Routine check-up",
    "Follow-up for hypertension management",
    "Discuss lab results",
    "Vaccination appointment",
    "Review medication plan",
    "Physical examination",
    "Post-operative review",
    "Asthma monitoring visit"
]

# -----------------------------
# Generate appointments
# -----------------------------
def random_date():
    """Generate a random date within ±90 days from today."""
    start_date = datetime.now() - timedelta(days=random.randint(0, 90))
    return start_date.strftime("%Y-%m-%d")

count = 0
for patient in patients.find():
    # Generate between 1 and 3 appointments per patient
    new_appointments = []
    for i in range(random.randint(1, 3)):
        new_appointments.append({
            "_id": ObjectId(),
            "date": random_date(),
            "doctor": random.choice(doctors),
            "notes": random.choice(notes_examples),
            "status": random.choice(statuses)
        })
    
    # Push to DB
    patients.update_one(
        {"_id": patient["_id"]},
        {"$set": {"appointments": new_appointments}}
    )
    count += 1

print(f"✅ Added random appointments for {count} patients.")
