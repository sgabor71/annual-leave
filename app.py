import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
import bcrypt  # Import bcrypt for password hashing
from bson.objectid import ObjectId

# MongoDB connection setup
def get_mongo_connection():
    # Get connection string from Streamlit secrets
    connection_string = st.secrets["mongo"]["connection_string"]
    client = MongoClient(connection_string)
    db = client.leave_tracker
    return db

# Initialize MongoDB collections
def init_db():
    try:
        db = get_mongo_connection()
        # Check if collections exist, if not create them
        if "users" not in db.list_collection_names():
            db.create_collection("users")
        if "leaves" not in db.list_collection_names():
            db.create_collection("leaves")
        if "settings" not in db.list_collection_names():
            db.create_collection("settings")
        return True
    except Exception as e:
        st.error(f"Database initialization error: {e}")
        return False

# Helper functions for MongoDB operations
def create_user(username, password):
    # Hash the password using bcrypt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    db = get_mongo_connection()
    
    # Check if username already exists
    if db.users.find_one({"username": username}):
        st.error("Username already exists. Please choose a different username.")
        return False
    
    try:
        # Insert new user
        user_id = db.users.insert_one({
            "username": username,
            "password": hashed_password  # Store the hashed password
        }).inserted_id
        
        # Create default settings for the user
        db.settings.insert_one({
            "user_id": str(user_id),
            "mon_hours": 7.5,
            "tue_hours": 0,
            "wed_hours": 10.5,
            "thu_hours": 11.5,
            "fri_hours": 8.5,
            "sat_hours": 0,
            "sun_hours": 0,
            "leave_balance": 307.5  # Updated default leave balance
        })
        
        return True
    except Exception as e:
        st.error(f"Error creating user: {e}")
        return False

def verify_password(password, hashed_password):
    # Convert the hashed password to bytes if it's a string
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    # Verify the password against the hashed password
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)

def get_user_settings(user_id):
    db = get_mongo_connection()
    settings = db.settings.find_one({"user_id": str(user_id)})
    
    if not settings:
        # Create default settings if not found
        settings = {
            "user_id": str(user_id),
            "mon_hours": 7.5,
            "tue_hours": 0,
            "wed_hours": 10.5,
            "thu_hours": 11.5,
            "fri_hours": 8.5,
            "sat_hours": 0,
            "sun_hours": 0,
            "leave_balance": 307.5  # Updated default leave balance
        }
        db.settings.insert_one(settings)
    
    return settings

def update_user_settings(user_id, day, hours):
    db = get_mongo_connection()
    db.settings.update_one(
        {"user_id": str(user_id)},
        {"$set": {f"{day}_hours": hours}}
    )

def update_leave_balance(user_id, new_balance):
    db = get_mongo_connection()
    db.settings.update_one(
        {"user_id": str(user_id)},
        {"$set": {"leave_balance": new_balance}}
    )

def parse_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d')

def format_date(date_obj):
    return date_obj.strftime('%Y-%m-%d')

def calculate_leave_hours(start_date, end_date, user_id):
    settings = get_user_settings(user_id)
    total_hours = 0
    current_date = parse_date(start_date)
    end_date = parse_date(end_date)
    
    while current_date <= end_date:
        day_of_week = current_date.strftime('%a').lower()
        total_hours += settings[f'{day_of_week}_hours']
        current_date += timedelta(days=1)
    
    return total_hours

def check_overlap(user_id, new_start_date, new_end_date):
    db = get_mongo_connection()
    leaves = list(db.leaves.find({"user_id": str(user_id)}))
    
    new_start = parse_date(new_start_date)
    new_end = parse_date(new_end_date)
    
    for leave in leaves:
        existing_start = parse_date(leave['start_date'])
        existing_end = parse_date(leave['end_date'])
        if (new_start <= existing_end) and (new_end >= existing_start):
            return True
    
    return False

# Streamlit App
def main():
    # Custom CSS for styling
    st.markdown(
        """
        <style>
        .stButton button {
            background-color: #4CAF50;
            color: white;
            border-radius: 5px;
            padding: 10px 20px;
            font-size: 16px;
        }
        .stButton button:hover {
            background-color: #45a049;
        }
        .stHeader {
            color: #2E86C1;
        }
        .stSubheader {
            color: #1A5276;
        }
        .stWarning {
            background-color: #F9E79F;
            padding: 10px;
            border-radius: 5px;
        }
        .stSuccess {
            background-color: #D5F5E3;
            padding: 10px;
            border-radius: 5px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("📅 Annual Leave Tracker")

    # Initialize session state
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'delete_leave_id' not in st.session_state:
        st.session_state.delete_leave_id = None
    if 'show_signup' not in st.session_state:
        st.session_state.show_signup = False
    if 'show_delete_confirmation' not in st.session_state:
        st.session_state.show_delete_confirmation = False
    if 'show_delete_account_confirmation' not in st.session_state:
        st.session_state.show_delete_account_confirmation = False
    if 'show_delete_all_confirmation' not in st.session_state:
        st.session_state.show_delete_all_confirmation = False
    if 'show_update_balance_confirmation' not in st.session_state:
        st.session_state.show_update_balance_confirmation = False
    if 'new_balance' not in st.session_state:
        st.session_state.new_balance = None

    # Initialize database
    init_db()

    # Login and Sign-Up Section
    if not st.session_state.user_id:
        st.header("🔐 Login / Sign Up")
        
        if st.session_state.show_signup:
            # Sign-Up Form
            st.subheader("Sign Up")
            new_username = st.text_input("Choose a Username")
            new_password = st.text_input("Choose a Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            if st.button("Create Account"):
                if new_password == confirm_password:
                    if create_user(new_username, new_password):
                        st.success("✅ Account created successfully! Please log in.")
                        st.session_state.show_signup = False
                else:
                    st.error("Passwords do not match. Please try again.")
            
            if st.button("Back to Login"):
                st.session_state.show_signup = False
        else:
            # Login Form
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Login"):
                db = get_mongo_connection()
                user = db.users.find_one({"username": username})
                
                if user and verify_password(password, user['password']):
                    st.session_state.user_id = str(user['_id'])
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            
            if st.button("Sign Up"):
                st.session_state.show_signup = True
        
        # Use st.stop() instead of return
        st.stop()

    # Main Application
    user_id = st.session_state.user_id
    db = get_mongo_connection()
    user_settings = get_user_settings(user_id)

    # Leave Balance Section
    st.subheader("⏳ Remaining Leave Balance")
    st.markdown(f"**Current Balance: {user_settings['leave_balance']} hours**")

    # Add Leave Section
    st.subheader("➕ Add Leave")
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", format="YYYY-MM-DD")
        with col2:
            end_date = st.date_input("End Date", min_value=start_date, format="YYYY-MM-DD")
        
        custom_hours = st.checkbox("Enter custom hours (optional)")
        hours = None
        if custom_hours:
            hours = st.number_input("Enter Hours", min_value=0.0, step=0.5)

        if st.button("Add Leave"):
            start_date_str = format_date(start_date)
            end_date_str = format_date(end_date)
            
            if not hours:
                hours = calculate_leave_hours(start_date_str, end_date_str, user_id)
            
            if float(hours) > user_settings['leave_balance']:
                st.warning("⚠️ Warning: The requested hours exceed your remaining leave balance. Please adjust your request.")
            elif check_overlap(user_id, start_date_str, end_date_str):
                st.warning("⚠️ Overlap detected with existing leave requests.")
                
                # Store the leave request details in session state
                st.session_state.pending_leave_request = {
                    "start_date": start_date_str,
                    "end_date": end_date_str,
                    "hours": hours
                }
                st.session_state.show_overlap_confirmation = True
            else:
                # No overlap, proceed with adding the leave request
                requested_on = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                db.leaves.insert_one({
                    "user_id": str(user_id),
                    "start_date": start_date_str,
                    "end_date": end_date_str,
                    "hours": hours,
                    "requested_on": requested_on
                })
                
                # Update leave balance
                db.settings.update_one(
                    {"user_id": str(user_id)},
                    {"$set": {"leave_balance": user_settings['leave_balance'] - hours}}
                )
                
                st.success("✅ Leave added successfully!")
                st.rerun()

    # Overlap Confirmation Dialog
    if st.session_state.get('show_overlap_confirmation'):
        st.warning("⚠️ Are you sure you want to proceed with the overlapping leave request?")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Proceed", key="proceed_overlap"):
                # Retrieve the pending leave request from session state
                pending_request = st.session_state.pending_leave_request
                requested_on = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Add the leave request to the database
                db.leaves.insert_one({
                    "user_id": str(user_id),
                    "start_date": pending_request["start_date"],
                    "end_date": pending_request["end_date"],
                    "hours": pending_request["hours"],
                    "requested_on": requested_on
                })
                
                # Update leave balance
                db.settings.update_one(
                    {"user_id": str(user_id)},
                    {"$set": {"leave_balance": user_settings['leave_balance'] - pending_request["hours"]}}
                )
                
                # Clear session state
                del st.session_state.pending_leave_request
                del st.session_state.show_overlap_confirmation
                
                st.success("✅ Leave added successfully!")
                st.rerun()
        
        with col_no:
            if st.button("Cancel", key="cancel_overlap"):
                # Clear session state
                del st.session_state.pending_leave_request
                del st.session_state.show_overlap_confirmation
                st.info("❌ Leave request canceled.")
                st.rerun()

    # View Leave History Section
    st.subheader("📋 Leave History")
    leaves = list(db.leaves.find({"user_id": str(user_id)}))
    
    if not leaves:
        st.info("No leave history found.")
    else:
        # Sort leaves by start date (earliest first - ascending order)
        leaves.sort(key=lambda x: parse_date(x['start_date']), reverse=False)
        
        for leave in leaves:
            with st.container():
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"**From:** {leave['start_date']}")
                    st.write(f"**To:** {leave['end_date']}")
                with col2:
                    st.write(f"**Hours:** {leave['hours']}")
                    st.write(f"**Requested on:** {leave['requested_on']}")
                with col3:
                    if st.button("Delete", key=f"delete_{leave['_id']}"):
                        # Store the leave ID and show confirmation dialog
                        st.session_state.delete_leave_id = str(leave['_id'])
                        st.session_state.show_delete_confirmation = True
                st.divider()
    
    # Delete Confirmation Dialog
    if st.session_state.get('show_delete_confirmation') and st.session_state.delete_leave_id:
        leave_to_delete = db.leaves.find_one({"_id": ObjectId(st.session_state.delete_leave_id)})
        
        if leave_to_delete:
            st.warning(f"⚠️ Are you sure you want to delete the leave from {leave_to_delete['start_date']} to {leave_to_delete['end_date']}?")
            col_yes, col_no = st.columns(2)
            
            with col_yes:
                if st.button("Yes, Delete", key="confirm_delete"):
                    # Refund the hours to the leave balance
                    db.settings.update_one(
                        {"user_id": str(user_id)},
                        {"$inc": {"leave_balance": leave_to_delete['hours']}}
                    )
                    
                    # Delete the leave record
                    db.leaves.delete_one({"_id": ObjectId(st.session_state.delete_leave_id)})
                    
                    # Clear session state
                    st.session_state.delete_leave_id = None
                    st.session_state.show_delete_confirmation = False
                    
                    st.success("✅ Leave deleted and hours refunded to your balance.")
                    st.rerun()
            
            with col_no:
                if st.button("Cancel", key="cancel_delete"):
                    # Clear session state
                    st.session_state.delete_leave_id = None
                    st.session_state.show_delete_confirmation = False
                    st.rerun()

    # Settings Section
    st.subheader("⚙️ Settings")
    
    # Update Leave Balance Option
    with st.expander("Update Leave Balance"):
        st.write(f"Current leave balance: **{user_settings['leave_balance']} hours**")
        new_balance = st.number_input("New Leave Balance (hours)", 
                                     min_value=0.0, 
                                     value=float(user_settings['leave_balance']), 
                                     step=0.5)
        
        if st.button("Update Balance"):
            if new_balance != user_settings['leave_balance']:
                # Store new balance in session state and trigger confirmation
                st.session_state.new_balance = new_balance
                st.session_state.show_update_balance_confirmation = True
            else:
                st.info("No change in balance detected.")
    
    # Update Balance Confirmation Dialog
    if st.session_state.get('show_update_balance_confirmation') and st.session_state.new_balance is not None:
        current_balance = user_settings['leave_balance']
        new_balance = st.session_state.new_balance
        difference = new_balance - current_balance
        
        if difference > 0:
            message = f"⚠️ This will **increase** your leave balance by **{difference} hours**."
        else:
            message = f"⚠️ This will **decrease** your leave balance by **{abs(difference)} hours**."
            
        st.warning(f"Are you sure you want to update your leave balance from {current_balance} to {new_balance} hours? {message}")
        
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Yes, Update Balance", key="confirm_update_balance"):
                # Update the leave balance
                update_leave_balance(user_id, new_balance)
                
                # Clear session state
                st.session_state.new_balance = None
                st.session_state.show_update_balance_confirmation = False
                
                st.success("✅ Leave balance updated successfully!")
                st.rerun()
        
        with col_no:
            if st.button("Cancel", key="cancel_update_balance"):
                # Clear session state
                st.session_state.new_balance = None
                st.session_state.show_update_balance_confirmation = False
                st.info("❌ Balance update canceled.")
                st.rerun()
    
    # Working Hours Settings
    with st.expander("Working Hours Settings"):
        st.write("Set your working hours for each day of the week:")
        
        days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for day, day_name in zip(days, day_names):
            col1, col2 = st.columns([1, 3])
            with col1:
                st.write(f"{day_name}:")
            with col2:
                new_hours = st.number_input(f"Hours for {day_name}", min_value=0.0, max_value=24.0, value=float(user_settings[f'{day}_hours']), step=0.5, key=f"hours_{day}")
                if new_hours != user_settings[f'{day}_hours']:
                    update_user_settings(user_id, day, new_hours)
                    st.success(f"✅ {day_name} hours updated.")
                    st.rerun()

    # Danger Zone Section
    with st.expander("Danger Zone"):
        st.warning("⚠️ These actions are irreversible. Proceed with caution.")
        
        # Delete All Leave History
        if st.button("Delete All Leave History", key="delete_all"):
            st.session_state.show_delete_all_confirmation = True
        
        # Delete Account
        if st.button("Delete Account", key="delete_account"):
            st.session_state.show_delete_account_confirmation = True
    
    # Delete All Leave History Confirmation Dialog
    if st.session_state.get('show_delete_all_confirmation'):
        st.warning("⚠️ Are you sure you want to delete ALL leave history? This cannot be undone.")
        col_yes, col_no = st.columns(2)
        
        with col_yes:
            if st.button("Yes, Delete All", key="confirm_delete_all"):
                # Get total hours from all leaves
                total_hours = sum(leave['hours'] for leave in leaves)
                
                # Refund all hours to the leave balance
                db.settings.update_one(
                    {"user_id": str(user_id)},
                    {"$set": {"leave_balance": user_settings['leave_balance'] + total_hours}}
                )
                
                # Delete all leave records for this user
                db.leaves.delete_many({"user_id": str(user_id)})
                
                # Clear session state
                del st.session_state.show_delete_all_confirmation
                
                st.success("✅ All leave history deleted and hours refunded to your balance.")
                st.rerun()
        
        with col_no:
            if st.button("Cancel", key="cancel_delete_all"):
                # Clear session state
                del st.session_state.show_delete_all_confirmation
                st.info("❌ Delete all leave history canceled.")
                st.rerun()
    
    # Delete Account Confirmation Dialog
    if st.session_state.get('show_delete_account_confirmation'):
        st.warning("⚠️ Are you sure you want to delete your account? This will erase all your data, including leave history and settings.")
        col_yes, col_no = st.columns(2)
        
        with col_yes:
            if st.button("Yes, Delete My Account", key="confirm_delete_account"):
                # Delete user, settings, and leave records
                db.users.delete_one({"_id": ObjectId(user_id)})
                db.settings.delete_many({"user_id": str(user_id)})
                db.leaves.delete_many({"user_id": str(user_id)})
                
                # Clear session state
                del st.session_state.user_id
                st.session_state.show_delete_account_confirmation = False
                
                st.success("✅ Account deleted successfully!")
                st.rerun()
        
        with col_no:
            if st.button("Cancel", key="cancel_delete_account"):
                # Clear session state
                st.session_state.show_delete_account_confirmation = False
                st.info("❌ Account deletion canceled.")
                st.rerun()
    
    # Logout
    if st.button("🚪 Logout"):
        del st.session_state.user_id
        st.success("✅ Logged out successfully!")

if __name__ == '__main__':
    main()
