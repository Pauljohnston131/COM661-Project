from pymongo import MongoClient
import bcrypt

client = MongoClient("mongodb://127.0.0.1:27017")
db = client["syntheaDB"]
users = db["users"]

users.delete_many({})

user_list = [
    {"name": "Paul Johnston", "username": "paul", "password": "paul123", "email": "paul.johnston@example.com", "admin": True},
    {"name": "Bob Smith", "username": "bob", "password": "bob123", "email": "bob.smith@example.com", "admin": False},
    {"name": "Carol White", "username": "carol", "password": "carol123", "email": "carol.white@example.com", "admin": False},
    {"name": "David Lee", "username": "david", "password": "david123", "email": "david.lee@example.com", "admin": True},
    {"name": "Eva Brown", "username": "eva", "password": "eva123", "email": "eva.brown@example.com", "admin": False}
]

for user in user_list:
    hashed_pw = bcrypt.hashpw(user["password"].encode("utf-8"), bcrypt.gensalt())
    user["password"] = hashed_pw 
    users.insert_one(user)

print("Users seeded into syntheaDB.users with readable bcrypt strings.")
