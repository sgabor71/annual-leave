import streamlit as st
import pymongo
import bcrypt
import datetime
from bson.objectid import ObjectId
from pymongo.errors import PyMongoError

# Database connection
@st.cache_resource
def get_mongo_connection():
    client = pymongo.MongoClient(st.secrets["mongo_uri"])
    return client["leave_tracker"]

db = get_mongo_connection()
users_collection = db["users"]
leaves_collection = db["leaves"]

# Hash password securely
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def verify_password(password, hashed_password):
    return bcrypt.checkpw(password.encode(), hashed_password)

# User authentication
def authenticate_user(username, password):
    user = users_collection.find_one({"username": username})
    if user and verify_password(password, user["password"]):
        return user
    return None

# Retrieve user settings
def get_user_settings(user_id):
    try:
        return users_collection.find_one({"_id": ObjectId(user_id)})
    except PyMongoError as e:
        st.error(f"Database error: {e}")
        return None

# Calculate remaining leave hours
def calculate_leave_hours(user_id):
    today = datetime.datetime.utcnow()
    start_of_year = datetime.datetime(today.year, 1, 1)
    leaves = leaves_collection.find({"user_id": user_id, "date": {"$gte": start_of_year}})
    used_hours = sum(leave["hours"] for leave in leaves)
    settings = get_user_settings(user_id)
    if settings:
        return settings["annual_leave_hours"] - used_hours
    return 0

# Check for leave overlap
def check_overlap(user_id, start_date, end_date):
    return leaves_collection.count_documents({
        "user_id": user_id,
        "$or": [
            {"start_date": {"$lte": end_date}, "end_date": {"$gte": start_date}}
        ]
    }) > 0

# Request leave
def request_leave(user_id, start_date, end_date, hours):
    if check_overlap(user_id, start_date, end_date):
        return "Leave request overlaps with an existing leave."
    
    remaining_hours = calculate_leave_hours(user_id)
    if remaining_hours < hours:
        return "Not enough leave balance."
    
    try:
        leaves_collection.insert_one({
            "user_id": user_id,
            "start_date": start_date,
            "end_date": end_date,
            "hours": hours,
        })
        return "Leave request submitted."
    except PyMongoError as e:
        return f"Database error: {e}"

# Logout
def logout():
    st.session_state.clear()
    st.success("Logged out successfully.")

# Streamlit UI
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = authenticate_user(username, password)
        if user:
            st.session_state.authenticated = True
            st.session_state.user_id = str(user["_id"])
            st.success("Login successful!")
        else:
            st.error("Invalid credentials.")
else:
    st.write("Welcome!")
    if st.button("Logout"):
        logout()
