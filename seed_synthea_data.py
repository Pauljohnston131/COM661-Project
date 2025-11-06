import csv
from datetime import datetime, date
from pymongo import MongoClient
from bson import ObjectId
from collections import defaultdict
import os
import re
import random

# paths and setup
CSV_DIR = os.path.join("data", "synthea_csv")

# helper: calculate age
def years_between(dob_str):
    try:
        dob = datetime.strptime(dob_str[:10], "%Y-%m-%d").date()
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except:
        return None

# helper: clean patient name
def title_case_name(given, family):
    name = f"{(given or '').strip()} {(family or '').strip()}".strip()
    name = re.sub(r"\d+", "", name).strip()
    return name.title() if name else None

# helper: clean doctor name
def clean_doctor_name(name):
    if not name:
        return "Clinic GP"
    name = re.sub(r"\d+", "", name).strip()
    if not re.match(r"^(Dr\.|Clinic)", name, re.IGNORECASE):
        name = "Dr. " + name
    return name.title()

# helper: clean date
def clean_date(d):
    try:
        return datetime.strptime(d[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        return "Unknown"

# helper: assign age group
def age_group(age):
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

# load providers
providers = {}
prov_path = os.path.join(CSV_DIR, "providers.csv")
if os.path.exists(prov_path):
    with open(prov_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw_name = row.get("NAME") or "Clinic GP"
            providers[row.get("Id") or row.get("ID")] = clean_doctor_name(raw_name)

# load conditions
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

# load encounters
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

# load medications
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

# load careplans
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

# connect to MongoDB
client = MongoClient("mongodb://127.0.0.1:27017")
db = client["syntheaDB"]
patients_col = db["patients"]

print("Dropping existing patients collection in syntheaDB...")
patients_col.drop()

# sample towns and coordinates
town_boxes = {
    "Belfast": [54.5733, -5.9689, 54.6233, -5.8789],
    "Derry/LondonDerry": [55.0000, -7.3700, 55.0500, -7.2600],
    "Letterkenny": [54.9300, -7.7800, 54.9700, -7.7000],
    "Donegal": [54.6400, -8.1500, 54.6700, -8.1000]
}

# read patients and insert
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
        town = random.choice(list(town_boxes.keys()))
        box = town_boxes[town]
        rand_lat = box[0] + (box[2] - box[0]) * random.random()
        rand_long = box[1] + (box[3] - box[1]) * random.random()

        patient = {
            "name": name,
            "age": age,
            "age_group": age_group(age),
            "condition": condition,
            "town": town,
            "location": {"type": "Point", "coordinates": [rand_long, rand_lat]},
            "image_url": None,
            "appointments": encounters_by_patient.get(pid, []),
            "prescriptions": meds_by_patient.get(pid, []),
            "careplans": careplans_by_patient.get(pid, []),
            "last_updated": datetime.utcnow().isoformat()
        }
        to_insert.append(patient)

# insert into MongoDB
if to_insert:
    patients_col.insert_many(to_insert)
    print(f"Inserted {len(to_insert)} cleaned patients with location data into syntheaDB.patients")
    sample = to_insert[0]
    print("\nSample patient preview:")
    print(f"Name: {sample['name']}, Age: {sample['age']} ({sample['age_group']})")
    print(f"Condition: {sample['condition']}, Town: {sample['town']}")
    print(f"Coordinates: {sample['location']['coordinates']}")
    print(f"Appointments: {len(sample['appointments'])}, "
          f"Prescriptions: {len(sample['prescriptions'])}, "
          f"Careplans: {len(sample['careplans'])}")
else:
    print("No patients found — check CSV folder paths or data quality.")
