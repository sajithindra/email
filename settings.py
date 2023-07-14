from pymongo import MongoClient

PORT = 8000
HOST = "0.0.0.0"

DATABASE_URL = f"mongodb://docker:mongopw@localhost:55000"

client = MongoClient(DATABASE_URL)
