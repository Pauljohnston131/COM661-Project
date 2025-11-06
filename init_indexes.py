from pymongo import MongoClient

client = MongoClient("mongodb://127.0.0.1:27017")
db = client["syntheaDB"]
patients = db["patients"]

patients.create_index([("location", "2dsphere")])
print("Created 2dsphere index on 'location' field.")
