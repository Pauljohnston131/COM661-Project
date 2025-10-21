from pymongo import MongoClient
import bcrypt

# Connect to MongoDB
client = MongoClient("mongodb://127.0.0.1:27017")
db = client.healthcareDB      # select the new database
users = db.users               # select the collection name

# New list of users
user_list = [
    { 
        "name": "Paul Johnston",
        "username": "paul",
        "password": b"paul123",
        "email": "paul.johnston@example.com",
        "admin": True
    },
    { 
        "name": "Bob Smith",
        "username": "bob",
        "password": b"bob123",
        "email": "bob.smith@example.com",
        "admin": False
    },
    { 
        "name": "Carol White",
        "username": "carol",
        "password": b"carol123",
        "email": "carol.white@example.com",
        "admin": False
    },        
    { 
        "name": "David Lee",
        "username": "david",
        "password": b"david123",
        "email": "david.lee@example.com",
        "admin": True
    },
    { 
        "name": "Eva Brown",
        "username": "eva",
        "password": b"eva123",
        "email": "eva.brown@example.com",
        "admin": False
    }
]

# Hash passwords and insert users
for new_user in user_list:
    new_user["password"] = bcrypt.hashpw(new_user["password"], bcrypt.gensalt())
    users.insert_one(new_user)
