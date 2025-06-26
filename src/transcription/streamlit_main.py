"""
Simple Streamlit entry point for MedTranscribe
This file avoids all circular imports by using absolute imports and lazy loading
"""
import streamlit as st
import sys
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Configure Streamlit first
st.set_page_config(
    page_title="MedTranscribe - AI Medical Transcription",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
.main > div {
    padding-top: 2rem;
}

.stAlert {
    margin-top: 1rem;
}

.metric-container {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #007bff;
}

.chat-container {
    background-color: #f0f0f0;
    padding: 20px;
    border-radius: 10px;
    height: 60vh;
    overflow-y: auto;
    background-image: 
        radial-gradient(circle at 20px 80px, #e8e8e8 1px, transparent 1px),
        radial-gradient(circle at 80px 20px, #e8e8e8 1px, transparent 1px);
    background-size: 100px 100px;
}

/* Hide Streamlit style */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)


def process_uploaded_audio(upload_data: Dict[str, Any]):
    """Process uploaded audio file using transcription service"""
    try:
        # Validate session data
        session_data = {
            'patient_name': upload_data['patient_name'],
            'doctor_name': upload_data['doctor_name'],
            'session_date': upload_data['session_date'],
            'session_notes': upload_data['session_notes']
        }
        
        # Basic validation
        if not session_data['patient_name'] or not session_data['doctor_name']:
            st.error("Patient name and doctor name are required.")
            return
        
        # Get uploaded file
        uploaded_file = upload_data['uploaded_file']
        audio_data = uploaded_file.read()
        
        # Check file size
        max_size_mb = 100
        if len(audio_data) > max_size_mb * 1024 * 1024:
            st.error(f"File too large. Maximum size: {max_size_mb}MB")
            return
        
        # Show processing status
        with st.container():
            st.info("🔄 Processing your audio file...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Update progress simulation
            for i in range(100):
                progress_bar.progress(i / 100)
                if i < 20:
                    status_text.text("Initializing transcription...")
                elif i < 40:
                    status_text.text("Loading AI model...")
                elif i < 70:
                    status_text.text("Processing audio segments...")
                elif i < 90:
                    status_text.text("Analyzing speaker patterns...")
                else:
                    status_text.text("Finalizing transcription...")
                time.sleep(0.03)
            
            # Import and use transcription service
            try:
                from app.services.transcription_service import transcription_service
                
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
                    
                    # Show some results
                    if result.get('session'):
                        session = result['session']
                        st.subheader("📋 Session Created")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Patient:** {session.get('patient_name')}")
                            st.write(f"**Doctor:** {session.get('doctor_name')}")
                        with col2:
                            st.write(f"**Date:** {session.get('session_date')}")
                            st.write(f"**Status:** {session.get('status', 'Unknown')}")
                    
                    time.sleep(2)
                    st.rerun()
                else:
                    status_text.text("❌ Transcription failed")
                    st.error(f"Processing failed: {result.get('error', 'Unknown error')}")
                    
                    if result.get('session_id'):
                        st.info(f"Session {result['session_id']} was created but processing failed. You can try again later.")
            
            except ImportError as e:
                st.error("Transcription service not available. Please check system configuration.")
                st.code(f"Import error: {str(e)}")
            except Exception as e:
                st.error(f"Processing error: {str(e)}")
    
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")


def render_sidebar():
    """Render application sidebar"""
    with st.sidebar:
        st.title("🏥 MedTranscribe")
        st.markdown("*AI-Powered Medical Transcription*")
        
        st.divider()
        
        # Navigation
        page = st.selectbox(
            "📍 Navigate",
            options=["Dashboard", "Transcription"],
            index=0,
            key="navigation"
        )
        
        st.divider()
        
        # App info
        st.markdown("### ℹ️ About")
        st.markdown("""
        **MedTranscribe** is an AI-powered medical transcription system that:
        
        • 🎙️ Transcribes medical conversations
        • 🤖 Identifies speakers automatically  
        • 💾 Stores sessions securely
        • 📊 Provides conversation analytics
        """)
        
        st.divider()
        
        # System status
        st.markdown("### 📊 System Status")
        try:
            # Import database service directly
            from app.services.database_service import db_service
            stats = db_service.get_stats()
            st.metric("Total Sessions", stats.get('total_sessions', 0))
            st.metric("This Month", stats.get('this_month', 0))
            st.success("🟢 System Online")
        except Exception as e:
            st.error("🔴 Database Error")
            st.caption(f"Error: {str(e)}")
        
        return page


def render_simple_dashboard():
    """Simple dashboard implementation"""
    st.title("🏥 MedTranscribe Dashboard")
    
    try:
        # Import services directly
        from app.services.database_service import db_service
        from app.models import SessionFilter
        
        # Get statistics
        stats = db_service.get_stats()
        
        # Stats cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Total Sessions", stats.get('total_sessions', 0))
        
        with col2:
            st.metric("📅 This Month", stats.get('this_month', 0))
        
        with col3:
            st.metric("🎯 Avg Confidence", f"{stats.get('avg_confidence', 0)}%")
        
        with col4:
            st.metric("⏱️ Total Hours", f"{stats.get('total_duration_hours', 0)}h")
        
        st.divider()
        
        # Recent sessions
        st.subheader("📋 Recent Sessions")
        
        # Get recent sessions
        session_filter = SessionFilter(limit=10)
        recent_sessions = db_service.get_sessions(session_filter)
        
        if recent_sessions:
            for session in recent_sessions:
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.markdown(f"**{session.patient_name}**")
                        st.markdown(f"Dr. {session.doctor_name}")
                    
                    with col2:
                        st.markdown(f"📅 {session.session_date}")
                        if session.duration:
                            duration_str = f"{int(session.duration // 60):02d}:{int(session.duration % 60):02d}"
                            st.markdown(f"⏰ {duration_str}")
                    
                    with col3:
                        status_colors = {
                            'completed': '🟢',
                            'processing': '🟡', 
                            'pending': '🔴',
                            'error': '❌'
                        }
                        status = session.status.value if hasattr(session.status, 'value') else str(session.status)
                        st.markdown(f"{status_colors.get(status, '⚪')} {status.title()}")
                    
                    st.divider()
        else:
            st.info("No sessions found. Upload your first audio file to get started!")
    
    except Exception as e:
        st.error(f"Failed to load dashboard data: {str(e)}")


def render_simple_transcription():
    """Simple transcription implementation"""
    st.title("🎙️ Transcription Management")
    
    # Main layout
    col1, col2 = st.columns([1.2, 1.8])
    
    with col1:
        st.subheader("📤 Upload New Session")
        
        # Simple upload form
        with st.form("upload_form", clear_on_submit=True):
            patient_name = st.text_input("Patient Name*", placeholder="Enter patient name")
            doctor_name = st.text_input("Doctor Name*", placeholder="Enter doctor name")
            session_date = st.date_input("Session Date*")
            
            model_size = st.selectbox("Model Size", 
                                    options=["tiny", "base", "small", "medium", "large"],
                                    index=1,
                                    help="Larger models are more accurate but slower")
            
            uploaded_file = st.file_uploader(
                "Upload Audio File*",
                type=['mp3', 'wav', 'm4a', 'mp4'],
                help="Maximum file size: 100MB"
            )
            
            session_notes = st.text_area("Session Notes", placeholder="Optional notes")
            
            submit_button = st.form_submit_button("🚀 Start Transcription", type="primary")
            
            if submit_button:
                if not all([patient_name, doctor_name, uploaded_file]):
                    st.error("Please fill in all required fields and upload an audio file.")
                else:
                    # Process the uploaded audio file
                    # Convert date to string properly
                    session_date_str = session_date.isoformat() if hasattr(session_date, 'isoformat') else str(session_date)
                    
                    process_uploaded_audio({
                        'patient_name': patient_name,
                        'doctor_name': doctor_name,
                        'session_date': session_date_str,
                        'session_notes': session_notes,
                        'model_size': model_size,
                        'uploaded_file': uploaded_file
                    })
    
    with col2:
        st.subheader("📋 Recent Sessions")
        
        try:
            from app.services.database_service import db_service
            from app.models import SessionFilter
            
            session_filter = SessionFilter(limit=20)
            sessions = db_service.get_sessions(session_filter)
            
            if sessions:
                for session in sessions:
                    with st.container():
                        col1, col2, col3 = st.columns([3, 2, 1])
                        
                        with col1:
                            st.markdown(f"**{session.patient_name}**")
                            st.markdown(f"Dr. {session.doctor_name}")
                        
                        with col2:
                            st.markdown(f"📅 {session.session_date}")
                            if hasattr(session, 'duration') and session.duration:
                                duration_str = f"{int(session.duration // 60):02d}:{int(session.duration % 60):02d}"
                                st.markdown(f"⏰ {duration_str}")
                        
                        with col3:
                            status = session.status.value if hasattr(session.status, 'value') else str(session.status)
                            status_colors = {
                                'completed': '🟢',
                                'processing': '🟡', 
                                'pending': '🔴',
                                'error': '❌'
                            }
                            st.markdown(f"{status_colors.get(status, '⚪')} {status.title()}")
                        
                        # Use enhanced session details component
                        try:
                            from app.components.ui_components import render_enhanced_session_details
                            render_enhanced_session_details(session)
                        except ImportError:
                            # Fallback to simple details
                            import time
                            unique_suffix = f"{session.id}_{int(time.time() * 1000)}"
                            
                            if st.button(f"View Details", key=f"view_transcription_{unique_suffix}"):
                                st.session_state.selected_session = session.id
                                st.rerun()
                            
                            # Show session details if selected
                            if hasattr(st.session_state, 'selected_session') and st.session_state.selected_session == session.id:
                                with st.expander(f"Session Details - {session.patient_name}", expanded=True):
                                    st.write(f"**Patient:** {session.patient_name}")
                                    st.write(f"**Doctor:** {session.doctor_name}")
                                    st.write(f"**Date:** {session.session_date}")
                                    st.write(f"**Status:** {status.title()}")
                                    if hasattr(session, 'session_notes') and session.session_notes:
                                        st.write(f"**Notes:** {session.session_notes}")
                                    
                                    # Try to get transcription
                                    try:
                                        transcription = db_service.get_transcription_by_session_id(session.id)
                                        if transcription and transcription.transcription_text:
                                            st.subheader("💬 Transcription")
                                            st.text_area("Conversation", transcription.transcription_text, height=300, key=f"transcription_text_{unique_suffix}")
                                            
                                            # Download button
                                            st.download_button(
                                                label="📥 Download Transcript",
                                                data=transcription.transcription_text,
                                                file_name=f"transcript_{session.patient_name}_{session.session_date}.txt",
                                                mime="text/plain",
                                                key=f"download_file_{unique_suffix}"
                                            )
                                        else:
                                            st.info("No transcription available yet.")
                                    except:
                                        st.info("Transcription data not available.")
                                    
                                    if st.button("🔙 Close Details", key=f"close_details_{unique_suffix}"):
                                        if hasattr(st.session_state, 'selected_session'):
                                            delattr(st.session_state, 'selected_session')
                                    st.rerun()
                        
                        st.divider()
            else:
                st.info("No sessions found.")
        
        except Exception as e:
            st.error(f"Failed to load sessions: {str(e)}")


def main():
    """Main application function"""
    try:
        # Initialize logging
        import logging
        logging.basicConfig(level=logging.INFO)
        
        # Render sidebar and get selected page
        selected_page = render_sidebar()
        
        # Route to appropriate page
        if selected_page == "Dashboard":
            render_simple_dashboard()
        elif selected_page == "Transcription":
            render_simple_transcription()
        else:
            render_simple_dashboard()
    
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.info("Please refresh the page or contact support if the error persists.")


if __name__ == "__main__":
    main() 