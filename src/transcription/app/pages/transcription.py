"""
Transcription page for audio upload and session management
"""
import streamlit as st
from datetime import datetime
import time
from typing import Dict, Any

from ..services.database_service import db_service
from ..components import render_upload_form, render_session_card
from ..utils import (
    get_logger, validate_session_data, parse_transcription_text,
    create_text_export, create_download_filename
)
from ..models import SessionFilter

logger = get_logger(__name__)


def render_transcription_page():
    """Render the transcription management page"""
    st.title("🎙️ Transcription Management")
    
    # Main layout
    col1, col2 = st.columns([1.2, 1.8])
    
    with col1:
        render_upload_section()
    
    with col2:
        render_sessions_section()


def render_upload_section():
    """Render the audio upload section"""
    st.subheader("📤 Upload New Session")
    
    # Upload form
    upload_data = render_upload_form()
    
    if upload_data:
        process_uploaded_audio(upload_data)


def process_uploaded_audio(upload_data: Dict[str, Any]):
    """Process uploaded audio file"""
    try:
        # Validate session data
        session_data = {
            'patient_name': upload_data['patient_name'],
            'doctor_name': upload_data['doctor_name'],
            'session_date': upload_data['session_date'],
            'session_notes': upload_data['session_notes']
        }
        
        validation = validate_session_data(session_data)
        if not validation['valid']:
            st.error("Validation failed:")
            for error in validation['errors']:
                st.error(f"• {error}")
            return
        
        # Get uploaded file
        uploaded_file = upload_data['uploaded_file']
        audio_data = uploaded_file.read()
        
        # Validate audio file
        from ..services.transcription_service import transcription_service
        audio_validation = transcription_service.validate_audio_file(
            uploaded_file.name, len(audio_data)
        )
        
        if not audio_validation['valid']:
            st.error(audio_validation['error'])
            return
        
        # Show processing status
        with st.container():
            st.info("🔄 Processing your audio file...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Update progress
            for i in range(100):
                progress_bar.progress(i / 100)
                if i < 20:
                    status_text.text("Initializing transcription...")
                elif i < 60:
                    status_text.text("Processing audio segments...")
                elif i < 90:
                    status_text.text("Analyzing speaker patterns...")
                else:
                    status_text.text("Finalizing transcription...")
                time.sleep(0.05)
            
            # Process the audio
            result = transcription_service.process_audio_file(
                audio_data=audio_data,
                audio_filename=uploaded_file.name,
                session_details=session_data,
                model_size=upload_data['model_size']
            )
            
            progress_bar.progress(100)
            
            if result['success']:
                status_text.text("✅ Transcription completed successfully!")
                st.success(f"Audio file processed successfully! Session ID: {result.get('session', {}).get('id', 'N/A')}")
                
                # Store session in session state for immediate viewing
                if result.get('session'):
                    st.session_state.selected_session = result['session']['id']
                
                time.sleep(2)
                st.rerun()
            else:
                status_text.text("❌ Transcription failed")
                st.error(f"Processing failed: {result.get('error', 'Unknown error')}")
                
                if result.get('session_id'):
                    st.info(f"Session {result['session_id']} was created but processing failed. You can try again later.")
    
    except Exception as e:
        logger.error(f"Error processing uploaded audio: {str(e)}")
        st.error(f"An unexpected error occurred: {str(e)}")


def render_sessions_section():
    """Render the sessions management section"""
    st.subheader("📋 Recent Sessions")
    
    # Get filtered sessions (simplified for now)
    try:
        session_filter = SessionFilter(limit=20)
        sessions = db_service.get_sessions(session_filter)
        
        if sessions:
            for session in sessions:
                session_dict = session.to_dict()
                render_session_card(session_dict, show_audio=True)
        else:
            st.info("No sessions found.")
    
    except Exception as e:
        logger.error(f"Error rendering sessions section: {str(e)}")
        st.error("Failed to load sessions data")


if __name__ == "__main__":
    render_transcription_page() 