import csv
from datetime import datetime, date
from pymongo import MongoClient
from bson import ObjectId
from collections import defaultdict
import os
import re

CSV_DIR = os.path.join("data", "synthea_csv")

def years_between(dob_str):
    """Calculate age in years from birthdate string."""
    try:
        dob = datetime.strptime(dob_str[:10], "%Y-%m-%d").date()
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except:
        return None


def title_case_name(given, family):
    """Format and clean full name (remove digits)."""
    name = f"{(given or '').strip()} {(family or '').strip()}".strip()
    name = re.sub(r"\d+", "", name).strip()
    return name.title() if name else None


def clean_doctor_name(name):
    """Remove digits and ensure title case for doctor names."""
    if not name:
        return "Clinic GP"
    name = re.sub(r"\d+", "", name).strip()
    if not re.match(r"^(Dr\.|Clinic)", name, re.IGNORECASE):
        name = "Dr. " + name
    return name.title()


def clean_date(d):
    """Ensure valid ISO-like date string."""
    try:
        return datetime.strptime(d[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        return "Unknown"


def age_group(age):
    """Group patients into age bands."""
    if age is None:
        return "Unknown"
    if age < 18:
        return "Child"
    elif age < 40:
        return "Adult"
    elif age < 65:
        return "Middle-aged"
    else:
        return "Senior"

providers = {}
prov_path = os.path.join(CSV_DIR, "providers.csv")
if os.path.exists(prov_path):
    with open(prov_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw_name = row.get("NAME") or "Clinic GP"
            providers[row.get("Id") or row.get("ID")] = clean_doctor_name(raw_name)

conditions_by_patient = defaultdict(list)
cond_path = os.path.join(CSV_DIR, "conditions.csv")
if os.path.exists(cond_path):
    with open(cond_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row.get("PATIENT") or row.get("Id")
            desc = row.get("DESCRIPTION") or "General Checkup"
            if pid:
                desc = re.sub(r"\(.*?\)", "", desc).strip().title()
                conditions_by_patient[pid].append(desc)

encounters_by_patient = defaultdict(list)
enc_path = os.path.join(CSV_DIR, "encounters.csv")
if os.path.exists(enc_path):
    with open(enc_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row.get("PATIENT")
            date_str = clean_date(row.get("START") or "2024-01-01")
            doctor = clean_doctor_name(providers.get(row.get("PROVIDER"), "Dr. Smith"))
            reason = row.get("REASONDESCRIPTION") or row.get("CLASS") or "Consultation"
            if pid:
                encounters_by_patient[pid].append({
                    "_id": ObjectId(),
                    "doctor": doctor,
                    "date": date_str,
                    "notes": reason,
                    "status": "completed"
                })

meds_by_patient = defaultdict(list)
med_path = os.path.join(CSV_DIR, "medications.csv")
if os.path.exists(med_path):
    with open(med_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row.get("PATIENT")
            name = row.get("DESCRIPTION") or row.get("CODE") or "Medication"
            start = clean_date(row.get("START") or "")
            stop = clean_date(row.get("STOP") or "")
            if pid:
                meds_by_patient[pid].append({
                    "_id": ObjectId(),
                    "name": name.strip().title(),
                    "start": start,
                    "stop": stop,
                    "status": "active" if stop == "Unknown" else "completed"
                })

careplans_by_patient = defaultdict(list)
cp_path = os.path.join(CSV_DIR, "careplans.csv")
if os.path.exists(cp_path):
    with open(cp_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row.get("PATIENT")
            desc = row.get("DESCRIPTION") or row.get("CATEGORY") or "Care plan"
            start = clean_date(row.get("START") or "")
            stop = clean_date(row.get("STOP") or "")
            if pid:
                careplans_by_patient[pid].append({
                    "_id": ObjectId(),
                    "description": desc.strip().title(),
                    "start": start,
                    "stop": stop
                })

client = MongoClient("mongodb://127.0.0.1:27017")
db = client["syntheaDB"]
patients_col = db["patients"]

print("Dropping existing patients collection in syntheaDB...")
patients_col.drop()

pat_path = os.path.join(CSV_DIR, "patients.csv")
to_insert = []

with open(pat_path, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        pid = row.get("Id") or row.get("ID")
        name = title_case_name(row.get("FIRST"), row.get("LAST"))
        age = years_between(row.get("BIRTHDATE"))

        if not name or not age:
            continue

        condition = conditions_by_patient.get(pid, ["Check-up"])[0]
        condition = re.sub(r"\(.*?\)", "", condition).strip().title()

        patient = {
            "name": name,
            "age": age,
            "age_group": age_group(age),
            "condition": condition,
            "image_url": None,
            "appointments": encounters_by_patient.get(pid, []),
            "prescriptions": meds_by_patient.get(pid, []),
            "careplans": careplans_by_patient.get(pid, []),
            "last_updated": datetime.utcnow().isoformat()
        }
        to_insert.append(patient)

if to_insert:
    patients_col.insert_many(to_insert)
    print(f"Inserted {len(to_insert)} cleaned patients into syntheaDB.patients")
    sample = to_insert[0]
    print("\nSample patient preview:")
    print(f"Name: {sample['name']}, Age: {sample['age']} ({sample['age_group']})")
    print(f"Condition: {sample['condition']}")
    print(f"Appointments: {len(sample['appointments'])}, "
          f"Prescriptions: {len(sample['prescriptions'])}, "
          f"Careplans: {len(sample['careplans'])}")
else:
    print("No patients found — check CSV folder paths or data quality.")
