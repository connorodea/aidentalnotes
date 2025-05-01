"""
streamlit_app.py - Streamlit Frontend for AI Dental Note Generator

This module provides a simple Streamlit-based UI for the MVP version
of the AI Dental Note Generator.
"""
import os
import json
import requests
import streamlit as st
from datetime import datetime
import base64
import tempfile
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
APP_NAME = "AI Dental Note Generator"
APP_TAGLINE = "Convert voice or text into structured SOAP-format dental notes"
COMPANY_NAME = "AIDentalNotes.com"

# Page config
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #2C3E50;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: 500;
        color: #34495E;
    }
    .note-container {
        background-color: #F8F9FA;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #E9ECEF;
    }
    .soap-section {
        margin-bottom: 15px;
    }
    .soap-header {
        font-weight: 600;
        color: #2C3E50;
    }
    .footer {
        text-align: center;
        margin-top: 100px;
        color: #7F8C8D;
    }
    .stButton>button {
        background-color: #3498DB;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

def check_api_health():
    """Check if the API is reachable and healthy."""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        return response.status_code == 200
    except:
        return False

def login_page():
    """Display login page and handle authentication."""
    st.markdown(f'<h1 class="main-header">{APP_NAME}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-header">{APP_TAGLINE}</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        login_button = st.button("Login")
        
        if login_button:
            # In a real app, you would authenticate with your backend
            # For now, just check if the fields are non-empty
            if email and password:
                # This is a placeholder for actual authentication
                # In reality, you'd call your API's login endpoint
                jwt_token = "sample_token_for_demo"
                st.session_state['logged_in'] = True
                st.session_state['jwt_token'] = jwt_token
                st.session_state['email'] = email
                st.session_state['plan'] = "starter"  # Default plan for demo
                st.rerun()
            else:
                st.error("Please enter your email and password")

    with col2:
        st.subheader("Don't have an account?")
        st.write("Sign up for a free trial and experience the power of AI-assisted dental note generation.")
        st.markdown("""
        ✅ No credit card required<br>
        ✅ 7-day free trial<br>
        ✅ Cancel anytime
        """, unsafe_allow_html=True)
        if st.button("Start Free Trial"):
            st.write("In a production app, this would redirect to your signup page or Stripe checkout.")

def main_app():
    """Display the main application UI for logged-in users."""
    # Sidebar
    with st.sidebar:
        st.markdown(f'<h2 class="sub-header">{APP_NAME}</h2>', unsafe_allow_html=True)
        st.write(f"Logged in as: {st.session_state['email']}")
        st.write(f"Plan: {st.session_state['plan'].capitalize()}")
        
        # Usage info (placeholder)
        st.progress(45)
        st.write("45/100 notes used this month")
        
        st.markdown("---")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
    
    # Main content
    st.markdown(f'<h1 class="main-header">Generate Dental Notes</h1>', unsafe_allow_html=True)
    
    # Tabs for input methods
    tab1, tab2 = st.tabs(["Voice Input", "Text Input"])
    
    with tab1:
        st.subheader("Upload Audio Recording")
        audio_file = st.file_uploader("Upload an audio file (WAV or MP3)", type=["wav", "mp3"])
        
        st.write("Or record directly:")
        audio_recording = st.audio_recorder()
        
        # Add diarization option
        use_diarization = st.checkbox("Enable speaker identification (for multiple speakers)", value=False)
        st.info("Enable speaker identification if your recording includes both patient and dentist voices.")
        
        if st.button("Generate Note from Audio"):
            if audio_file:
                # Process uploaded file
                with st.spinner("Transcribing audio and generating note..."):
                    try:
                        # Call API with audio file
                        headers = {"Authorization": f"Bearer {st.session_state['jwt_token']}"}
                        files = {"audio_file": audio_file.getvalue()}
                        data = {"use_diarization": use_diarization}
                        
                        response = requests.post(
                            f"{API_BASE_URL}/generate_note_from_audio",
                            headers=headers,
                            files=files,
                            data=data
                        )
                        
                        if response.status_code == 200:
                            note_data = response.json()
                            st.session_state['current_note'] = note_data['soap_note']
                            st.success("Note generated successfully!")
                        else:
                            st.error(f"Error: {response.text}")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
            
            elif audio_recording:
                # Process recorded audio
                with st.spinner("Transcribing audio and generating note..."):
                    try:
                        # Call API with recorded audio
                        headers = {"Authorization": f"Bearer {st.session_state['jwt_token']}"}
                        files = {"audio_file": audio_recording}
                        data = {"use_diarization": use_diarization}
                        
                        response = requests.post(
                            f"{API_BASE_URL}/generate_note_from_audio",
                            headers=headers,
                            files=files,
                            data=data
                        )
                        
                        if response.status_code == 200:
                            note_data = response.json()
                            st.session_state['current_note'] = note_data['soap_note']
                            st.success("Note generated successfully!")
                        else:
                            error_msg = response.text
                            try:
                                error_data = response.json()
                                if 'detail' in error_data:
                                    error_msg = error_data['detail']
                            except:
                                pass
                            st.error(f"Error: {error_msg}")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
            else:
                st.warning("Please upload or record an audio file first")
    
    with tab2:
        st.subheader("Enter Text")
        text_input = st.text_area("Enter your dental notes here", height=200)
        
        if st.button("Generate Note from Text"):
            if text_input:
                with st.spinner("Generating SOAP note..."):
                    try:
                        # Call API with text
                        headers = {
                            "Authorization": f"Bearer {st.session_state['jwt_token']}",
                            "Content-Type": "application/json"
                        }
                        data = {"text": text_input}
                        response = requests.post(
                            f"{API_BASE_URL}/generate_note",
                            headers=headers,
                            json=data
                        )
                        
                        if response.status_code == 200:
                            note_data = response.json()
                            st.session_state['current_note'] = note_data['soap_note']
                            st.success("Note generated successfully!")
                        else:
                            st.error(f"Error: {response.text}")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
            else:
                st.warning("Please enter some text first")
    
    # Display generated note
    if 'current_note' in st.session_state:
        st.markdown("---")
        st.markdown('<h2 class="sub-header">Generated SOAP Note</h2>', unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="note-container">', unsafe_allow_html=True)
            st.markdown(st.session_state['current_note'])
            st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Copy to Clipboard"):
                # This doesn't actually work in Streamlit directly,
                # but in a real app you'd use JS for this
                st.info("In a production app, this would copy the note to clipboard")
        
        with col2:
            if st.download_button(
                label="Download as Text",
                data=st.session_state['current_note'],
                file_name=f"dental_note_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            ):
                pass
        
        with col3:
            if st.button("New Note"):
                if 'current_note' in st.session_state:
                    del st.session_state['current_note']
                st.rerun()

def main():
    """Main entry point for the Streamlit app."""
    # Check if API is healthy
    api_healthy = check_api_health()
    
    # Initialize session state if needed
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    
    # Show login or main app based on authentication status
    if not st.session_state['logged_in']:
        login_page()
    else:
        if not api_healthy:
            st.error("⚠️ API service is unavailable. Please try again later.")
        main_app()
    
    # Footer
    st.markdown(f"""
    <div class="footer">
        <p>© {datetime.now().year} {COMPANY_NAME}. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
