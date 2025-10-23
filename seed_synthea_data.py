# ----------------------------------------------------------
# seed_synthea_data.py
# Load Synthea CSVs into syntheaDB.patients
# ----------------------------------------------------------
import csv
from datetime import datetime, date
from pymongo import MongoClient
from bson import ObjectId
from collections import defaultdict
import os

CSV_DIR = os.path.join("data", "synthea_csv")

# --- Helpers ---
def years_between(dob_str):
    try:
        dob = datetime.strptime(dob_str[:10], "%Y-%m-%d").date()
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except:
        return None

def title_case_name(given, family):
    name = f"{(given or '').strip()} {(family or '').strip()}".strip()
    return name.title() if name else "Unknown"

def gender_map(g):
    g = (g or "").lower()
    if "male" in g: return "Male"
    if "female" in g: return "Female"
    return "Other"

# --- Providers ---
providers = {}
prov_path = os.path.join(CSV_DIR, "providers.csv")
if os.path.exists(prov_path):
    with open(prov_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            providers[row.get("Id") or row.get("ID")] = row.get("NAME") or "Clinic GP"

# --- Conditions ---
conditions_by_patient = defaultdict(list)
cond_path = os.path.join(CSV_DIR, "conditions.csv")
if os.path.exists(cond_path):
    with open(cond_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row.get("PATIENT") or row.get("Id")
            desc = row.get("DESCRIPTION") or "General Checkup"
            if pid:
                conditions_by_patient[pid].append(desc)

# --- Encounters → Appointments ---
encounters_by_patient = defaultdict(list)
enc_path = os.path.join(CSV_DIR, "encounters.csv")
if os.path.exists(enc_path):
    with open(enc_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row.get("PATIENT")
            date_str = (row.get("START") or "2024-01-01")[:10]
            doctor = providers.get(row.get("PROVIDER"), "Dr. Smith")
            reason = row.get("REASONDESCRIPTION") or row.get("CLASS") or "Consultation"
            if pid:
                encounters_by_patient[pid].append({
                    "_id": ObjectId(),
                    "doctor": doctor,
                    "date": date_str,
                    "notes": reason,
                    "status": "completed"
                })

# --- Medications → Prescriptions ---
meds_by_patient = defaultdict(list)
med_path = os.path.join(CSV_DIR, "medications.csv")
if os.path.exists(med_path):
    with open(med_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row.get("PATIENT")
            name = row.get("DESCRIPTION") or row.get("CODE") or "Medication"
            start = (row.get("START") or "")[:10]
            stop = (row.get("STOP") or "")[:10]
            if pid:
                meds_by_patient[pid].append({
                    "_id": ObjectId(),
                    "name": name,
                    "start": start,
                    "stop": stop,
                    "status": "active" if not stop else "completed"
                })

# --- CarePlans ---
careplans_by_patient = defaultdict(list)
cp_path = os.path.join(CSV_DIR, "careplans.csv")
if os.path.exists(cp_path):
    with open(cp_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row.get("PATIENT")
            desc = row.get("DESCRIPTION") or row.get("CATEGORY") or "Care plan"
            start = (row.get("START") or "")[:10]
            stop = (row.get("STOP") or "")[:10]
            if pid:
                careplans_by_patient[pid].append({
                    "_id": ObjectId(),
                    "description": desc,
                    "start": start,
                    "stop": stop
                })

# --- Connect to Mongo ---
client = MongoClient("mongodb://127.0.0.1:27017")
db = client["syntheaDB"]            # <--- using new database name
patients_col = db["patients"]

print("⚠️ Dropping existing patients collection in syntheaDB...")
patients_col.drop()

# --- Insert Patients ---
pat_path = os.path.join(CSV_DIR, "patients.csv")
to_insert = []
with open(pat_path, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        pid = row.get("Id") or row.get("ID")
        name = title_case_name(row.get("FIRST"), row.get("LAST"))
        age = years_between(row.get("BIRTHDATE"))
        gender = gender_map(row.get("GENDER"))

        patient = {
            "name": name,
            "age": age or 40,
            "gender": gender,
            "condition": conditions_by_patient.get(pid, ["Check-up"])[0],
            "image_url": None,
            "appointments": encounters_by_patient.get(pid, []),
            "prescriptions": meds_by_patient.get(pid, []),
            "careplans": careplans_by_patient.get(pid, [])
        }
        to_insert.append(patient)

if to_insert:
    patients_col.insert_many(to_insert)
    print(f"✅ Inserted {len(to_insert)} patients into syntheaDB.patients")
else:
    print("❌ No patients found — check CSV folder paths.")
