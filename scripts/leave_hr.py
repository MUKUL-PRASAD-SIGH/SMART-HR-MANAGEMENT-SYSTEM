# leave_hr.py
import streamlit as st
from db import connect_db
from streamlit_option_menu import option_menu

def approve_leave_page():
    st.subheader("Approve / Reject Leave Requests")
    con = connect_db()
    cur = con.cursor()
    try:
        cur.execute("""
            SELECT lr.user_id, u.name, lr.start_date, lr.end_date, lr.reason, lr.status
            FROM leave_requests lr
            JOIN users u ON lr.user_id = u.id
            WHERE lr.status = 'pending'
        """)
        requests = cur.fetchall()

        if requests:
            for index, request in enumerate(requests):
                user_id, name, from_date, to_date, reason, status = request
                with st.expander(f"Request from {name} ({from_date} to {to_date})"):
                    st.write(f"**Reason:** {reason}")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Approve", key=f"approve_{index}"):
                            cur.execute("""
                                UPDATE leave_requests 
                                SET status = 'approved' 
                                WHERE user_id = %s AND start_date = %s AND end_date = %s
                            """, (user_id, from_date, to_date))
                            con.commit()
                            st.success("Leave Approved!")
                            st.rerun()
                    with col2:
                        if st.button("❌ Reject", key=f"reject_{index}"):
                            cur.execute("""
                                UPDATE leave_requests 
                                SET status = 'rejected' 
                                WHERE user_id = %s AND start_date = %s AND end_date = %s
                            """, (user_id, from_date, to_date))
                            con.commit()
                            st.error("Leave Rejected!")
                            st.rerun()
        else:
            st.info("No pending leave requests.")
    except Exception as e:
        st.error(f"Error: {e}")
    finally:
        cur.close()
        con.close()


def employee_details_page():
    st.subheader("Employee Details")
    con = None
    cur = None
    try:
        # Connect to database
        con = connect_db()
        if not con:
            st.error("Failed to connect to database")
            return
            
        cur = con.cursor()
        
        # Get all employees from users table
        cur.execute("""
            SELECT id, name, gmail, role 
            FROM users 
            WHERE role = 'employee' OR role = 'hr'
            ORDER BY name
        """)

        employees = cur.fetchall()
        
        if not employees:
            st.info("No employees found in the database.")
            return

        for emp in employees:
            user_id = emp['id']
            
            # Count approved leaves for this user
            leave_count = 0
            try:
                cur.execute("""
                    SELECT COUNT(*) as count 
                    FROM leave_requests 
                    WHERE user_id = %s AND status = 'approved'
                """, (user_id,))
                result = cur.fetchone()
                leave_count = result['count'] if result else 0
            except Exception as e:
                st.warning(f"Could not fetch leave count for user {user_id}: {e}")

            # Display employee card
            st.markdown(
                f"""
                <div style='
                    background-color: #262525; 
                    padding: 15px; 
                    border-radius: 10px; 
                    margin-bottom: 15px;
                    border: 2px solid #F7F7F7;
                '>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div>
                        <h4 style='margin: 0 0 10px 0;'>{emp['name']} <span style='font-size: 0.9em; color: #888;'>({emp['role'].title()})</span></h4>
                        <p style='margin: 5px 0;'><b>🆔 ID:</b> {emp['id']}</p>
                        <p style='margin: 5px 0;'><b>📧 Email:</b> {emp['gmail']}</p>
                    </div>
                    <div style='text-align: right;'>
                        <div style='background-color: #333; padding: 5px 10px; border-radius: 15px; display: inline-block;'>
                            <b>📝 Leaves:</b> {leave_count}
                        </div>
                    </div>
                </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    except Exception as e:
        st.error(f"Database error: {str(e)}")
        import traceback
        st.text(traceback.format_exc())
        
    finally:
        if cur:
            try:
                cur.close()
            except:
                pass
        if con:
            try:
                con.close()
            except:
                pass


def hr_leave_page():
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
                    menu_title='HR Portal',
                    options=[
                        'Approve/Reject Leave', 
                        'Employee Details', 
                        'Email', 
                        'Logout'
                    ],
                    icons=['check2-square', 'people', 'envelope', 'box-arrow-left'],
                    menu_icon='briefcase',
                    default_index=0,
                    styles={
                        "container": {"padding": "5!important", "background-color": '#000'},
                        "icon": {"color": "white", "font-size": "23px"},
                        "nav-link": {"color": "white", "font-size": "20px", "--hover-color": "#3363b0"},
                        "nav-link-selected": {"background-color": "#3363b0"},
                    }
                )

            if app == "Approve/Reject Leave":
                approve_leave_page()
            elif app == "Employee Details":
                employee_details_page()
            elif app == "Email":
                from gmail_reader import read_emails, display_emails
                from email_classifier import classify_emails_with_gemini
                import time

                st.title("📬 Email Dashboard")
                
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
                st.rerun()

    app = MultiApp()
    app.run()
