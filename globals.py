from pymongo import MongoClient
import os

secret_key = os.environ.get('SECRET_KEY', 'mysecret')

client = MongoClient(os.environ.get('MONGO_URI', 'mongodb://localhost:27017/'))
db_name = os.environ.get('MONGO_DB', 'syntheaDB')
db = client[db_name]
