import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
import time
from db import connect_db

# Store OTPs temporarily (in production, use Redis or database with TTL)
otp_storage = {}

def generate_otp(email: str) -> str:
    """Generate a 6-digit OTP and store it with timestamp"""
    otp = str(random.randint(100000, 999999))
    otp_storage[email] = {
        'otp': otp,
        'timestamp': time.time(),
        'verified': False
    }
    return otp

def send_otp_email(receiver_email: str, otp: str):
    """Send OTP to user's email"""
    # Load email configuration from environment variables
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    sender_email = os.getenv('EMAIL_SENDER')
    sender_password = os.getenv('EMAIL_PASSWORD')
    
    if not all([sender_email, sender_password]):
        raise ValueError("Email configuration is missing. Please check your .env file.")

    # Create message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "Your OTP for HR Management System"
    
    body = f"""
    <h2>Your One-Time Password (OTP)</h2>
    <p>Your OTP for HR Management System is: <strong>{otp}</strong></p>
    <p>This OTP is valid for 10 minutes.</p>
    <p>If you didn't request this, please ignore this email.</p>
    """
    
    msg.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send OTP: {e}")
        return False

def verify_otp(email: str, user_otp: str) -> bool:
    """Verify if the provided OTP is correct and not expired"""
    OTP_VALIDITY = 600  # 10 minutes in seconds
    
    if email not in otp_storage:
        return False
        
    stored_otp = otp_storage[email]
    
    # Check if OTP is expired
    if (time.time() - stored_otp['timestamp']) > OTP_VALIDITY:
        del otp_storage[email]
        return False
    
    # Check if OTP matches
    if stored_otp['otp'] == user_otp:
        stored_otp['verified'] = True
        return True
    
    return False

def is_email_verified(email: str) -> bool:
    """Check if email has been verified with OTP"""
    return otp_storage.get(email, {}).get('verified', False)

def clear_otp(email: str):
    """Clear OTP data after verification"""
    if email in otp_storage:
        del otp_storage[email]
