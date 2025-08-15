import streamlit as st
from streamlit_option_menu import option_menu
from db import connect_db
import datetime

def request_leave_page():
    st.header("Request Leave")

    # Get logged-in user info
    user_id = st.session_state.user_id
    name = st.session_state.user_name

    # Leave form
    with st.form("leave_form"):
        from_date = st.date_input("From Date", min_value=datetime.date.today())
        to_date = st.date_input("To Date", min_value=from_date)
        reason = st.text_area("Reason for Leave")

        submit = st.form_submit_button("Submit Leave Request")

    if submit:
        conn = connect_db()         
        cursor = conn.cursor() 

        try:
            cursor.execute(
                "INSERT INTO leave_requests (user_id, name, from_date, to_date, reason, status) VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, name, from_date, to_date, reason, "Pending")
            )
            conn.commit()
            st.success("Leave request submitted successfully.")
        except Exception as e:
            st.error(f"Error submitting request: {e}")
        finally:
            cursor.close()
            conn.close()

def leave_status_page():
    st.subheader("📋 Your Leave Status")

    if "user_id" not in st.session_state:
        st.warning("Please log in to view your leave status.")
        return

    try:
        con = connect_db()
        cur = con.cursor()

        query = """
            SELECT from_date, to_date, reason, status
            FROM leave_requests
            WHERE user_id = %s
            ORDER BY from_date DESC
        """
        cur.execute(query, (st.session_state.user_id,))
        leaves = cur.fetchall()

        if not leaves:
            st.info("You have not submitted any leave requests yet.")
        else:
            for leave in leaves:
                from_date, to_date, reason, status = leave

                status_icon = {
                    "Pending": "🟡",
                    "Approved": "✅",
                    "Rejected": "❌"
                }.get(status, "❓")

                st.markdown(f"""
                <div style='border:1px solid #ddd; padding:10px; margin-bottom:10px; border-radius:10px;'>
                    <b>📅 From:</b> {from_date} to {to_date}  
                    <br><b>📝 Reason:</b> {reason}  
                    <br><b>📍 Status:</b> {status_icon} <b>{status}</b>
                </div>
                """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error: {e}")
    finally:
        cur.close()
        con.close()

def leave_history_page():
    st.subheader("📜 Leave History (Approved Only)")
    
    try:
        con = connect_db()
        cur = con.cursor()

        query = """
            SELECT from_date, to_date, reason, status
            FROM leave_requests
            WHERE user_id = %s AND status = 'Approved'
            ORDER BY from_date DESC
        """
        cur.execute(query, (st.session_state.user_id,))
        leaves = cur.fetchall()

        if leaves:
            for leave in leaves:
                st.markdown(
                    f"""
                    🟢 **{leave[0]} to {leave[1]}**  
                    ✏️ **Reason:** {leave[2]}  
                    ✅ **Status:** {leave[3]}
                    ---
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No approved leave history found.")

    except Exception as e:
        st.error(f"Something went wrong: {e}")

    finally:
        if cur: cur.close()
        if con: con.close()

def resign_page():
    st.subheader("Resign Request")
    if st.button("Submit Resignation"):
        st.success("Resignation submitted successfully!")  # Replace with DB logic if needed

def employee_leave_page():
    class MultiApp:
        def __init__(self):
            self.apps = []

        def add_app(self, title, func):
            self.apps.append({
                "title": title,
                "function": func
            })

        def run(self):
            with st.sidebar:
                app = option_menu(
                    menu_title="Employee Portal",
                    options=["Request Leave", "Leave Status", "Leave History", "Take Resign","Email", "Logout"],
                    icons=["file-earmark-plus", "clipboard2-check", "clock-history", "person-x","envelope", "box-arrow-left"],
                    menu_icon="person-fill",
                    default_index=0,
                    styles={
                        "container": {"padding": "5!important", "background-color": '#000'},
                        "icon": {"color": "white", "font-size": "23px"},
                        "nav-link": {"color": "white", "font-size": "20px", "--hover-color": "#3363b0"},
                        "nav-link-selected": {"background-color": "#3363b0"},
                    }
                )

            if app == "Request Leave":
                request_leave_page()
            elif app == "Leave Status":
                leave_status_page()
            elif app == "Leave History":
                leave_history_page()
            elif app == "Take Resign":
                resign_page()
            elif app == "Email":
                from gmail_reader import read_emails, display_emails
                from email_classifier import classify_emails_with_gemini
                import time

                st.title("📬 Employee Email Dashboard")
                
                # Add a refresh button
                if st.button("🔄 Refresh Emails"):
                    st.rerun()
                
                # Show loading spinner while fetching emails
                with st.spinner("Fetching your emails..."):
                    emails = read_emails(max_results=15)
                
                if not emails:
                    st.warning("No emails found or there was an error fetching your emails.")
                else:
                    # Display emails in a tabbed interface
                    tab1, tab2 = st.tabs(["📧 All Emails", "🔍 Smart Classification"])
                    
                    with tab1:
                        st.subheader("Your Inbox")
                        display_emails(emails)
                    
                    with tab2:
                        st.subheader("Smart Email Classification")
                        st.info("Classifying emails using AI...")
                        try:
                            with st.spinner("Analyzing emails with Gemini AI..."):
                                result = classify_emails_with_gemini(emails)
                            
                            if result:
                                category_emojis = {
                                    "Important": "🚨",
                                    "General": "📂",
                                    "Spam": "📢"
                                }

                                # Rename categories
                                renamed_result = {
                                    "Important": result.get("Important", []),
                                    "General": result.get("General", []),
                                    "Spam": result.get("Spam", [])
                                }

                                for category in ["Important", "General", "Spam"]:
                                    with st.expander(f"{category_emojis[category]} {category} Emails", expanded=True):
                                        if renamed_result[category]:
                                            for mail in renamed_result[category]:
                                                st.write(f"➡️ {mail}")
                                        else:
                                            st.info("No emails in this category.")
                            else:
                                st.error("Failed to classify emails. Please try again later.")
                        except Exception as e:
                            st.error(f"An error occurred during email classification: {str(e)}")
            elif app == "Logout":
                st.session_state.logged_in = False
                st.session_state.user_id = None
                st.session_state.user_role = None
                st.experimental_rerun()

    app = MultiApp()
    app.run()
