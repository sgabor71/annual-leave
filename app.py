from passlib.hash import bcrypt

# Helper functions for MongoDB operations
def create_user(username, password):
    # Hash the password using bcrypt
    hashed_password = bcrypt.hash(password.encode('utf-8'))
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
    return
