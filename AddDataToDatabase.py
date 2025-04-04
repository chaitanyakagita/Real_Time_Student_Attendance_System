import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from dotenv import load_dotenv

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': os.getenv("FIREBASE_DATABASE_URL")
})

ref = db.reference('Students')

data = {
    "11367":
        {
            "name": "Nani",
            "major": "CSE",
            "starting_year": 2021,
            "total_attendance": 10,
            "standing": "T",
            "year": 4,
            "last_attendance_time": "2024-08-20 00:54:34"
        },
    "11368":
        {
            "name": "Elon Musk",
            "major": "CSE",
            "starting_year": 2021,
            "total_attendance": 15,
            "standing": "T",
            "year": 4,
            "last_attendance_time": "2024-08-20 00:54:34"
        },
    "11369":
        {
            "name": "Prabhas",
            "major": "CSE",
            "starting_year": 2021,
            "total_attendance": 10,
            "standing": "T",
            "year": 4,
            "last_attendance_time": "2024-08-20 00:54:34"
        }
}

for key, value in data.items():
    ref.child(key).set(value)