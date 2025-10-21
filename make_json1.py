import random, json, datetime

def generate_dummy_data():
    names = ['Alice', 'Bob', 'Charlie', 'Diana', 'Edward', 'Fiona', 'George', 'Hannah', 'Ian', 'Julia']
    conditions = ['Hypertension', 'Asthma', 'Diabetes', 'Flu', 'Allergy', 'Migraine', 'Arthritis']
    genders = ['Male', 'Female', 'Other']
    patient_list = []

    for i in range(50):
        name = random.choice(names) + " " + random.choice(["Smith", "Brown", "Taylor", "Wilson", "Lee"])
        age = random.randint(20, 85)
        gender = random.choice(genders)
        condition = random.choice(conditions)
        patient = {
            "name": name,
            "age": age,
            "gender": gender,
            "condition": condition,
            "appointments": []
        }
        patient_list.append(patient)
    return patient_list

patients = generate_dummy_data()

with open("patients.json", "w") as fout:
    json.dump(patients, fout, indent=4)

print("✅ Mock patient data generated successfully!")
