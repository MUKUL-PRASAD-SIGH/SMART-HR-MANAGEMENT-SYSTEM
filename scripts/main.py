# main.py
import streamlit as st
import pymysql
from db import connect_db
from leave_employee import employee_leave_page
import time
from otp_utils import generate_otp, send_otp_email, verify_otp, is_email_verified, clear_otp

#signup
def signup_user(id, gmail, password, role, name):
    con = connect_db()
    cur = con.cursor()
    try:
        # Check if user already exists
        cur.execute("SELECT id FROM users WHERE id = %s OR gmail = %s", (id, gmail))
        if cur.fetchone():
            st.error("User with this ID or email already exists")
            return False
            
        # Send OTP
        otp = generate_otp(gmail)
        if send_otp_email(gmail, otp):
            st.session_state.signup_data = {
                'id': id,
                'gmail': gmail,
                'password': password,
                'role': role.lower(),
                'name': name,
                'otp_sent': True,
                'otp_attempts': 0
            }
            st.success("OTP sent to your email!")
            return True
        else:
            st.error("Failed to send OTP. Please try again.")
            return False
            
    except Exception as e:
        st.error(f"Error during signup: {e}")
        return False
    finally:
        cur.close()
        con.close()
# Login function with enhanced debugging
def login_user(user_id, password):
    print("\n" + "="*50)
    print(f"🔑 Login attempt for user: {user_id}")
    print("="*50)
    
    try:
        # Print environment variables for debugging
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        print("\nEnvironment variables:")
        print(f"DB_HOST: {os.getenv('DB_HOST')}")
        print(f"DB_USER: {os.getenv('DB_USER')}")
        print(f"DB_NAME: {os.getenv('DB_NAME')}")
        
        # Get database connection
        print("\nConnecting to database...")
        con = connect_db()
        if not con:
            print("❌ Failed to connect to database")
            return None
            
        cursor = con.cursor()
        
        # First check if user exists and get their data
        query = "SELECT id, role, name, password FROM users WHERE id = %s"
        print(f"\nExecuting query: {query} with id={user_id}")
        
        cursor.execute(query, (user_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            print(f"❌ No user found with ID: {user_id}")
            
            # Debug: List all users in the database
            print("\nDebug: Listing all users in the database:")
            cursor.execute("SELECT id, name, role FROM users")
            all_users = cursor.fetchall()
            if all_users:
                for user in all_users:
                    print(f"- {user['id']}: {user['name']} ({user['role']})")
            else:
                print("No users found in the database!")
                
            return None
        
        # Print user data (except password for security)
        print(f"\n✅ User found in database:")
        print(f"ID: {user_data['id']}")
        print(f"Name: {user_data['name']}")
        print(f"Role: {user_data['role']}")
        print(f"Stored password: {'*' * len(str(user_data['password']))}")
        print(f"Provided password: {'*' * len(password)}")
        
        # Verify password (in production, use hashed password comparison)
        if user_data['password'] == password:
            print("\n✅ Password matches! Login successful!")
            return (str(user_data['id']), str(user_data['role']), str(user_data['name']))
        else:
            print("\n❌ Password does not match!")
            print(f"Stored password length: {len(str(user_data['password']))}")
            print(f"Provided password length: {len(password)}")
            return None
            
    except Exception as e:
        print(f"\n❌ Error during login: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        try:
            if 'con' in locals() and con:
                con.close()
                print("Database connection closed.")
        except Exception as e:
            print(f"Error closing connection: {e}")
        
        print("\n" + "="*50 + "\n")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    if 'show_login' not in st.session_state:
        st.session_state.show_login = False

    if st.session_state.show_login:
        #Login Form
        st.title("🧠 :blue[Smart] HR Management System")
        st.header("Login to Your Account")

        with st.form("login_form"):
            id = st.text_input("Enter ID", key="login_id")
            password = st.text_input("Password", type="password", key="login_pass")
            submit_login = st.form_submit_button("Submit")

            if submit_login:
                if id and password:
                    user_data = login_user(id, password)
                    print(f"Login attempt - User data: {user_data}")
                    
                    if user_data and len(user_data) >= 3:  # Ensure we have all required fields
                        try:
                            # Clear any existing session state
                            st.session_state.clear()
                            
                            # Set up new session
                            st.session_state.logged_in = True
                            st.session_state.user_id = str(user_data[0])
                            st.session_state.user_role = str(user_data[1]).lower()  # Ensure lowercase
                            st.session_state.user_name = str(user_data[2])
                            
                            print(f"Login successful - Session: {st.session_state}")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error setting up session: {e}")
                            print(f"Session setup error: {e}")
                            st.session_state.clear()  # Clear any partial session data
                            
                    else:
                        error_msg = "Invalid ID or Password. Please try again."
                        if user_data is None:
                            error_msg = "No user found with these credentials."
                        elif len(user_data) < 3:
                            error_msg = "Invalid user data format. Please contact support."
                        st.error(error_msg)
                        print(f"Login failed: {error_msg}")
                        st.session_state.clear()  # Ensure clean state on failed login
                else:
                    st.warning("Please enter both ID and password.")
        if st.button("Back to SignUp"):
            st.session_state.show_login = False

    else:
        # SignUp Form
        st.title("🧠 :blue[Smart] HR Management System")
        st.header("Create New Account!")

        if 'signup_data' in st.session_state and st.session_state.signup_data.get('otp_sent', False):
            # OTP Verification Step
            st.info("Please check your email for the OTP")
            otp = st.text_input("Enter OTP")
            
            if st.button("Verify OTP"):
                if verify_otp(st.session_state.signup_data['gmail'], otp):
                    # OTP verified, complete registration
                    try:
                        con = connect_db()
                        cur = con.cursor()
                        cur.execute(
                            "INSERT INTO users (id, gmail, password, role, name) VALUES (%s, %s, %s, %s, %s)",
                            (
                                st.session_state.signup_data['id'],
                                st.session_state.signup_data['gmail'],
                                st.session_state.signup_data['password'],
                                st.session_state.signup_data['role'],
                                st.session_state.signup_data['name']
                            )
                        )
                        con.commit()
                        st.success("Account created successfully! Please login.")
                        # Clear the signup data and OTP
                        clear_otp(st.session_state.signup_data['gmail'])
                        del st.session_state.signup_data
                        st.rerun()
                    except pymysql.IntegrityError:
                        st.error("This account could not be created. Please try again.")
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        if 'cur' in locals():
                            cur.close()
                        if 'con' in locals():
                            con.close()
                else:
                    st.session_state.signup_data['otp_attempts'] += 1
                    if st.session_state.signup_data['otp_attempts'] >= 3:
                        st.error("Too many failed attempts. Please try signing up again.")
                        clear_otp(st.session_state.signup_data['gmail'])
                        del st.session_state.signup_data
                        st.rerun()
                    else:
                        st.error("Invalid OTP. Please try again.")
            
            if st.button("Resend OTP"):
                otp = generate_otp(st.session_state.signup_data['gmail'])
                if send_otp_email(st.session_state.signup_data['gmail'], otp):
                    st.success("New OTP sent!")
                else:
                    st.error("Failed to resend OTP. Please try again.")
                    
            if st.button("Back to Signup"):
                clear_otp(st.session_state.signup_data['gmail'])
                del st.session_state.signup_data
                st.rerun()
                
        else:
            # Initial Signup Form
            with st.form("signup_form"):
                id = st.text_input("Enter your ID", key="signup_id")
                gmail = st.text_input("Enter Email", key="signup_gmail")
                password = st.text_input("Password", type="password", key="signup_pass")
                confirm_password = st.text_input("Confirm Password", type="password", key="confirm_pass")
                role = st.selectbox("Select Role", ["employee", "hr"], key="signup_role")
                name = st.text_input("Full Name")
                submit_signup = st.form_submit_button("Sign Up")

                if submit_signup:
                    if id and gmail and password and name and confirm_password:
                        if password != confirm_password:
                            st.error("Passwords do not match!")
                        else:
                            signup_user(id, gmail, password, role, name)
                    else:
                        st.warning("Please fill all details...")

        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(":blue[Already have an account?]")

        with col2:
            if st.button("Login"):
                st.session_state.show_login = True


# Initialize session state variables
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = ''
if 'user_id' not in st.session_state:
    st.session_state.user_id = ''

# ROLE-BASED DASHBOARDS
if st.session_state.get('logged_in'):
    if st.session_state.get('user_role') == "employee":
        st.markdown(f"# 👋Welcome :blue[{st.session_state.get('user_name', 'Employee')}]")
        employee_leave_page()
    elif st.session_state.get('user_role') == "hr":
        st.markdown(f"# 👋Welcome :blue[HR - {st.session_state.get('user_name', '')}]")
        import leave_hr
        leave_hr.hr_leave_page()
    else:
        st.error("Invalid user role. Please contact support.")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
