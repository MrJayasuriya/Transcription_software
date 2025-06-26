import streamlit as st
import os
import time
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import tempfile
import base64
from main import ContextualTranscriber, RealTimeTranscriber, test_with_existing_file
from database import db
import asyncio
import threading

# Page config
st.set_page_config(
    page_title="MedTranscribe - AI Medical Transcription",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for medical theme
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --medical-blue: #0ea5e9;
        --medical-blue-dark: #0284c7;
        --medical-blue-light: #e0f2fe;
        --success-green: #10b981;
        --warning-yellow: #f59e0b;
        --error-red: #ef4444;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom header styling */
    .main-header {
        background: linear-gradient(90deg, var(--medical-blue) 0%, var(--medical-blue-dark) 100%);
        padding: 1rem 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .header-title {
        font-size: 2rem;
        font-weight: bold;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .header-subtitle {
        font-size: 1rem;
        opacity: 0.9;
        margin-top: 0.5rem;
    }
    
    /* Stat cards */
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        border-left: 4px solid var(--medical-blue);
        margin-bottom: 1rem;
    }
    
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1f2937;
        margin: 0;
    }
    
    .stat-label {
        font-size: 0.875rem;
        color: #6b7280;
        margin-top: 0.25rem;
    }
    
    /* Upload area */
    .upload-area {
        border: 2px dashed #d1d5db;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        background: #f9fafb;
        transition: all 0.3s ease;
    }
    
    .upload-area:hover {
        border-color: var(--medical-blue);
        background: var(--medical-blue-light);
    }
    
    /* WhatsApp-style Chat styling */
    .chat-container {
        max-height: 600px;
        overflow-y: auto;
        padding: 1rem;
        background: #e5ddd5;
        background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23f0f0f0' fill-opacity='0.1'%3E%3Ccircle cx='30' cy='30' r='2'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
        border-radius: 0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    .chat-message {
        margin-bottom: 0.75rem;
        padding: 0.75rem 1rem;
        border-radius: 18px;
        max-width: 75%;
        position: relative;
        word-wrap: break-word;
        box-shadow: 0 1px 0.5px rgba(0, 0, 0, 0.13);
        clear: both;
        display: block;
    }
    
    .doctor-message {
        background: #dcf8c6;
        margin-left: auto;
        margin-right: 0;
        border-bottom-right-radius: 5px;
        float: right;
        clear: both;
    }
    
    .doctor-message::after {
        content: '';
        position: absolute;
        bottom: 0;
        right: -8px;
        width: 0;
        height: 0;
        border: 8px solid transparent;
        border-bottom-color: #dcf8c6;
        border-right: 0;
        border-bottom-right-radius: 3px;
    }
    
    .patient-message {
        background: #ffffff;
        margin-right: auto;
        margin-left: 0;
        border-bottom-left-radius: 5px;
        float: left;
        clear: both;
    }
    
    .patient-message::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: -8px;
        width: 0;
        height: 0;
        border: 8px solid transparent;
        border-bottom-color: #ffffff;
        border-left: 0;
        border-bottom-left-radius: 3px;
    }
    
    .chat-message strong {
        font-size: 0.85rem;
        color: #075e54;
        font-weight: 600;
        margin-bottom: 0.25rem;
        display: block;
    }
    
    .chat-message div:not(.message-time) {
        color: #303030;
        font-size: 0.95rem;
        line-height: 1.4;
        margin: 0.25rem 0;
    }
    
    .message-time {
        font-size: 0.7rem;
        color: #667781;
        text-align: right;
        margin-top: 0.5rem;
        opacity: 0.8;
    }
    
    .chat-container::after {
        content: "";
        display: table;
        clear: both;
    }
    
    /* Status indicators */
    .status-processing {
        color: var(--warning-yellow);
    }
    
    .status-completed {
        color: var(--success-green);
    }
    
    .status-error {
        color: var(--error-red);
    }
    
    /* Progress indicators */
    .progress-step {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 8px;
        background: #f3f4f6;
    }
    
    .progress-step.active {
        background: var(--medical-blue-light);
        color: var(--medical-blue-dark);
    }
    
    .progress-step.completed {
        background: #dcfce7;
        color: var(--success-green);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'selected_session_id' not in st.session_state:
    st.session_state.selected_session_id = None
if 'current_transcription' not in st.session_state:
    st.session_state.current_transcription = None
if 'processing_status' not in st.session_state:
    st.session_state.processing_status = "idle"
if 'filter_doctor' not in st.session_state:
    st.session_state.filter_doctor = ""
if 'filter_patient' not in st.session_state:
    st.session_state.filter_patient = ""

def render_header():
    """Render the main header"""
    st.markdown("""
    <div class="main-header">
        <div class="header-title">
            🏥 MedTranscribe
        </div>
        <div class="header-subtitle">
            AI-Powered Medical Transcription with Smart Speaker Detection
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_stats():
    """Render statistics dashboard"""
    col1, col2, col3, col4 = st.columns(4)
    
    # Get stats from database
    stats = db.get_stats()
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats['total_sessions']}</div>
            <div class="stat-label">📊 Total Sessions</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats['this_month']}</div>
            <div class="stat-label">📅 This Month</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats['total_duration_hours']}h</div>
            <div class="stat-label">⏱️ Total Duration</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats['avg_confidence']}%</div>
            <div class="stat-label">🎯 Accuracy</div>
        </div>
        """, unsafe_allow_html=True)

def render_progress_steps(current_step=0):
    """Render processing progress steps"""
    steps = [
        "🎵 Audio Processing",
        "🎭 Speaker Segmentation", 
        "🔗 Continuity Detection",
        "🤖 AI Context Analysis",
        "🔄 Speaker Mapping",
        "💬 Generating Output"
    ]
    
    progress_html = "<div style='margin: 1rem 0;'>"
    for i, step in enumerate(steps):
        status_class = ""
        if i < current_step:
            status_class = "completed"
        elif i == current_step:
            status_class = "active"
            
        progress_html += f"""
        <div class="progress-step {status_class}">
            {step} {'✅' if i < current_step else '⏳' if i == current_step else '⭕'}
        </div>
        """
    progress_html += "</div>"
    
    st.markdown(progress_html, unsafe_allow_html=True)

def process_transcription(audio_file, session_details, model_size="tiny"):
    """Process transcription with progress updates and database storage"""
    try:
        # Read audio file data
        audio_data = audio_file.read()
        audio_filename = audio_file.name
        
        # Save session to database first
        session_id = db.save_session(
            patient_name=session_details['patient_name'],
            doctor_name=session_details['doctor_name'],
            session_date=session_details['session_date'],
            audio_file_data=audio_data,
            audio_filename=audio_filename,
            session_notes=session_details.get('session_notes', ''),
            model_used=model_size
        )
        
        # Update session status to processing
        db.update_session_status(session_id, 'processing')
        
        # Save uploaded file temporarily for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(audio_data)
            temp_path = tmp_file.name
        
        progress_container = st.container()
        status_container = st.container()
        
        with status_container:
            st.info("🚀 Starting transcription process...")
        
        # Initialize transcriber
        transcriber = ContextualTranscriber(model_size=model_size, audio_file=temp_path)
        
        # Step-by-step processing with UI updates
        steps = [
            "Loading audio file...",
            "Performing initial transcription...", 
            "Detecting speaker segments...",
            "Analyzing conversation context...",
            "Mapping speakers to roles...",
            "Saving to database..."
        ]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, step in enumerate(steps[:-1]):  # All steps except last
            status_text.text(f"Step {i+1}/6: {step}")
            progress_bar.progress((i + 1) / len(steps))
            time.sleep(0.5)  # Simulate processing time
        
        # Actual transcription
        status_text.text(f"Step 6/6: {steps[-1]}")
        chat_content, segments = transcriber.transcribe_with_context(session_id=session_id)
        
        # Clean up
        os.unlink(temp_path)
        
        # Get complete session data
        session_data = db.get_session_by_id(session_id)
        
        status_text.text("✅ Transcription completed successfully!")
        progress_bar.progress(1.0)
        
        return session_data
        
    except Exception as e:
        st.error(f"❌ Transcription failed: {str(e)}")
        if 'session_id' in locals():
            db.update_session_status(session_id, 'error')
        return None

def render_transcription_chat(session_data, context="main", index=0):
    """Render transcription in WhatsApp-style chat format using Streamlit components"""
    if not session_data:
        st.error("❌ No session data available")
        return
    
    # Header with refresh and download buttons
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown("### 💬 Conversation Transcription")
    with col2:
        # Generate unique key with timestamp to avoid duplicates
        import random
        import time
        unique_id = f"{session_data.get('id')}_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        if st.button("🔄 Refresh", key=f"refresh_chat_{unique_id}"):
            st.rerun()
    with col3:
        # Download button will be added after we parse the messages
        download_placeholder = st.empty()
    
    # Debug info (remove this later)
    debug_key = f"debug_{session_data.get('id', 'unknown')}_{int(time.time() * 1000)}"
    if st.checkbox("🔍 Debug Info", key=debug_key):
        st.json({
            'has_transcription_text': bool(session_data.get('transcription_text')),
            'transcription_length': len(session_data.get('transcription_text', '')),
            'session_status': session_data.get('status'),
            'session_id': session_data.get('id')
        })
    
    transcription_text = session_data.get('transcription_text')
    if not transcription_text:
        st.warning("⚠️ No transcription text found. The session may still be processing or failed.")
        
        # Try to get transcription with speakers from database
        transcription_data = db.get_transcription_with_speakers(session_data['id'])
        if transcription_data and transcription_data.get('speakers'):
            st.info("📋 Found speaker segments, displaying those instead...")
            render_speaker_segments_native(transcription_data['speakers'], session_data)
        else:
            st.error("❌ No transcription data found in database.")
        return
    
    # Parse transcription content
    lines = transcription_text.split('\n')
    current_speaker = None
    current_message = ""
    messages = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('=') or line.startswith('📁') or line.startswith('⏰') or line.startswith('🤖'):
            continue
            
        # Detect speaker changes - look for various patterns
        speaker_indicators = ['👨‍⚕️ DOCTOR', '🧑‍🤝‍🧑 PATIENT', 'DOCTOR', 'PATIENT', 'Person 1', 'Person 2']
        is_speaker_line = any(indicator in line.upper() for indicator in [s.upper() for s in speaker_indicators])
        
        if is_speaker_line or '[' in line and ']:' in line:
            # Save previous message
            if current_speaker and current_message:
                is_doctor = any(d in current_speaker.upper() for d in ['DOCTOR', 'DR.'])
                speaker_name = session_data.get('doctor_name', 'Doctor') if is_doctor else session_data.get('patient_name', 'Patient')
                
                messages.append({
                    'speaker': speaker_name,
                    'text': current_message.strip(),
                    'is_doctor': is_doctor,
                    'time': datetime.now().strftime('%H:%M')
                })
            
            # Start new message
            current_speaker = line
            current_message = ""
        elif line.strip() and not line.startswith('📊'):
            # Message content - look for indented content or direct text
            if line.startswith('   ') or current_speaker:
                current_message += line.strip() + " "
    
    # Add final message
    if current_speaker and current_message:
        is_doctor = any(d in current_speaker.upper() for d in ['DOCTOR', 'DR.'])
        speaker_name = session_data.get('doctor_name', 'Doctor') if is_doctor else session_data.get('patient_name', 'Patient')
        
        messages.append({
            'speaker': speaker_name,
            'text': current_message.strip(),
            'is_doctor': is_doctor,
            'time': datetime.now().strftime('%H:%M')
        })
    
    if not messages:
        st.warning("⚠️ No conversation messages found in transcription text.")
        raw_key = f"raw_{session_data.get('id')}_{int(time.time() * 1000)}"
        st.text_area("Raw transcription text:", transcription_text, height=200, key=raw_key)
        
        # Try alternative parsing
        st.markdown("**Attempting alternative display:**")
        st.text(transcription_text)
    else:
        # Generate downloadable text format
        def create_text_conversation():
            text_output = f"""Medical Consultation Transcript
=====================================
Patient: {session_data.get('patient_name', 'Unknown')}
Doctor: {session_data.get('doctor_name', 'Unknown')}
Date: {session_data.get('session_date', 'Unknown')}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Conversation:
=============

"""
            for msg in messages:
                text_output += f"{msg['speaker']}: {msg['text']}\n\n"
            
            return text_output
        
        # Add download button in the placeholder
        with download_placeholder:
            text_content = create_text_conversation()
            st.download_button(
                "📥 Download",
                data=text_content,
                file_name=f"chat_{session_data.get('patient_name', 'patient')}_{session_data.get('session_date', datetime.now().strftime('%Y-%m-%d'))}.txt",
                mime="text/plain",
                help="Download conversation as text file",
                key=f"download_chat_{context}_{session_data.get('id', 'unknown')}_{index}"
            )
        
        # Create chat container with improved WhatsApp styling
        chat_css = """
        <style>
        .whatsapp-chat {
            background: #e5ddd5;
            background-image: linear-gradient(45deg, transparent 40%, rgba(255,255,255,0.1) 50%, transparent 60%);
            padding: 0.75rem;
            border-radius: 10px;
                         max-height: 60vh;
            overflow-y: auto;
            font-family: 'Segoe UI', sans-serif;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border: 1px solid #d1d5db;
        }
        .chat-bubble {
            margin: 6px 0;
            padding: 6px 10px;
            border-radius: 16px;
            max-width: 75%;
            position: relative;
            word-wrap: break-word;
            box-shadow: 0 1px 2px rgba(0,0,0,0.15);
            animation: fadeIn 0.3s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .patient-bubble {
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
            margin-right: 25%;
            border-bottom-left-radius: 4px;
            border: 1px solid #e9ecef;
        }
        .doctor-bubble {
            background: linear-gradient(135deg, #dcf8c6 0%, #c8e6c9 100%);
            margin-left: 25%;
            border-bottom-right-radius: 4px;
            border: 1px solid #a5d6a7;
        }
        .bubble-header {
            font-size: 0.75rem;
            color: #075e54;
            font-weight: 600;
            margin-bottom: 3px;
            text-transform: capitalize;
        }
        .bubble-text {
            color: #303030;
            font-size: 0.85rem;
            line-height: 1.3;
            margin: 2px 0;
        }
        .bubble-time {
            font-size: 0.65rem;
            color: #667781;
            text-align: right;
            margin-top: 3px;
            opacity: 0.7;
            font-style: italic;
        }
        .whatsapp-chat::-webkit-scrollbar {
            width: 6px;
        }
        .whatsapp-chat::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 3px;
        }
        .whatsapp-chat::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 3px;
        }
        .whatsapp-chat::-webkit-scrollbar-thumb:hover {
            background: #a8a8a8;
        }
        </style>
        """
        
        st.markdown(chat_css, unsafe_allow_html=True)
        
        # Render messages using Streamlit components
        st.markdown('<div class="whatsapp-chat">', unsafe_allow_html=True)
        
        for i, msg in enumerate(messages):
            bubble_class = "doctor-bubble" if msg['is_doctor'] else "patient-bubble"
            
            # Create message bubble HTML
            bubble_html = f"""
            <div class="chat-bubble {bubble_class}">
                <div class="bubble-header">{msg['speaker']}</div>
                <div class="bubble-text">{msg['text']}</div>
                <div class="bubble-time">{msg['time']}</div>
            </div>
            """
            
            st.markdown(bubble_html, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Add conversation summary at the bottom
        st.markdown(f"**💬 {len(messages)} messages** • **👥 {len(set(msg['speaker'] for msg in messages))} speakers**")

def render_speaker_segments_native(speakers, session_data):
    """Render speaker segments directly from database using native Streamlit components"""
    # WhatsApp-style CSS
    chat_css = """
    <style>
    .whatsapp-chat {
        background: #e5ddd5;
        padding: 1rem;
        border-radius: 10px;
        max-height: 500px;
        overflow-y: auto;
        font-family: 'Segoe UI', sans-serif;
    }
    .chat-bubble {
        margin: 8px 0;
        padding: 8px 12px;
        border-radius: 18px;
        max-width: 70%;
        position: relative;
        word-wrap: break-word;
        box-shadow: 0 1px 0.5px rgba(0,0,0,0.13);
    }
    .patient-bubble {
        background: #ffffff;
        margin-right: 30%;
        border-bottom-left-radius: 5px;
    }
    .doctor-bubble {
        background: #dcf8c6;
        margin-left: 30%;
        border-bottom-right-radius: 5px;
    }
    .bubble-header {
        font-size: 0.8rem;
        color: #075e54;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .bubble-text {
        color: #303030;
        font-size: 0.9rem;
        line-height: 1.4;
    }
    .bubble-time {
        font-size: 0.7rem;
        color: #667781;
        text-align: right;
        margin-top: 4px;
    }
    </style>
    """
    
    st.markdown(chat_css, unsafe_allow_html=True)
    st.markdown('<div class="whatsapp-chat">', unsafe_allow_html=True)
    
    for speaker in speakers:
        is_doctor = speaker['speaker_type'].upper() in ['DOCTOR', 'DR.']
        speaker_name = session_data.get('doctor_name', 'Doctor') if is_doctor else session_data.get('patient_name', 'Patient')
        
        # Format timestamp
        start_time = int(speaker['start_time'])
        minutes = start_time // 60
        seconds = start_time % 60
        timestamp = f"{minutes:02d}:{seconds:02d}"
        
        bubble_class = "doctor-bubble" if is_doctor else "patient-bubble"
        
        bubble_html = f"""
        <div class="chat-bubble {bubble_class}">
            <div class="bubble-header">{speaker_name}</div>
            <div class="bubble-text">{speaker['text']}</div>
            <div class="bubble-time">{timestamp}</div>
        </div>
        """
        
        st.markdown(bubble_html, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_speaker_segments(speakers, session_data):
    """Legacy function - redirects to native version"""
    render_speaker_segments_native(speakers, session_data)

def get_audio_player_html(audio_data: bytes, audio_filename: str) -> str:
    """Generate HTML for audio player"""
    b64_audio = base64.b64encode(audio_data).decode()
    file_extension = Path(audio_filename).suffix.lower()
    
    # Determine MIME type
    mime_type = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.m4a': 'audio/mp4',
        '.mp4': 'audio/mp4'
    }.get(file_extension, 'audio/mpeg')
    
    return f"""
    <audio controls style="width: 100%; margin: 10px 0;">
        <source src="data:{mime_type};base64,{b64_audio}" type="{mime_type}">
        Your browser does not support the audio element.
    </audio>
    """

def render_session_table_with_filters(context="main"):
    """Render session table with filtering and playback"""
    st.markdown("### 📋 Session Records")
    
    # Filters - Updated layout with date filter
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        doctors = [''] + db.get_doctors()
        selected_doctor = st.selectbox("Filter by Doctor:", doctors, key="filter_doctor_select")
    
    with col2:
        patients = [''] + db.get_patients()
        selected_patient = st.selectbox("Filter by Patient:", patients, key="filter_patient_select")
    
    with col3:
        # Date filter with minimalistic calendar
        date_filter_option = st.selectbox(
            "📅 Filter by Date:",
            ["All Dates", "Today", "Yesterday", "Last 7 days", "Last 30 days", "Custom Date"],
            key="date_filter_select"
        )
        
        selected_date = None
        if date_filter_option == "Custom Date":
            selected_date = st.date_input(
                "Select Date:",
                value=datetime.now().date(),
                key="custom_date_picker"
            )
    
    with col4:
        search_query = st.text_input("🔍 Search sessions:", placeholder="Search by name or notes...")
    
    # Process date filter
    date_filter = None
    if date_filter_option == "Today":
        date_filter = datetime.now().date()
    elif date_filter_option == "Yesterday":
        date_filter = datetime.now().date() - timedelta(days=1)
    elif date_filter_option == "Last 7 days":
        date_filter = "last_7_days"
    elif date_filter_option == "Last 30 days":
        date_filter = "last_30_days"
    elif date_filter_option == "Custom Date" and selected_date:
        date_filter = selected_date
    
    # Show quick date buttons for easy access
    if date_filter_option == "All Dates":
        st.markdown("**📅 Quick Date Access:**")
        
        # Add CSS for better button styling
        st.markdown("""
        <style>
        .date-button {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 8px;
            text-align: center;
            margin: 2px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .date-button:hover {
            background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
            color: white;
            transform: translateY(-1px);
        }
        </style>
        """, unsafe_allow_html=True)
        
        date_cols = st.columns(7)
        
        # Show last 7 days as clickable buttons
        for i, col in enumerate(date_cols):
            date_to_show = datetime.now().date() - timedelta(days=i)
            day_name = date_to_show.strftime('%a')
            is_today = i == 0
            
            with col:
                button_label = f"{'🟢 ' if is_today else ''}{date_to_show.strftime('%d')}\n{date_to_show.strftime('%b')}\n{day_name}"
                if st.button(
                    button_label,
                    key=f"quick_date_{i}",
                    help=f"Sessions from {date_to_show.strftime('%Y-%m-%d')} ({day_name})",
                    use_container_width=True
                ):
                    st.session_state.selected_quick_date = date_to_show
                    st.rerun()
        
        # Use quick date if selected
        if hasattr(st.session_state, 'selected_quick_date'):
            date_filter = st.session_state.selected_quick_date
            col_info, col_clear = st.columns([3, 1])
            with col_info:
                st.info(f"🗓️ Showing sessions from: {date_filter.strftime('%Y-%m-%d')}")
            with col_clear:
                if st.button("❌ Clear", key="clear_quick_date"):
                    if hasattr(st.session_state, 'selected_quick_date'):
                        delattr(st.session_state, 'selected_quick_date')
                    st.rerun()
    
    # Get sessions based on filters
    if search_query:
        sessions = db.search_sessions(search_query, date_filter=date_filter)
    else:
        sessions = db.get_sessions(
            doctor_name=selected_doctor if selected_doctor else None,
            patient_name=selected_patient if selected_patient else None,
            date_filter=date_filter,
            limit=50
        )
    
    if not sessions:
        st.info("📭 No sessions found. Upload an audio file to get started!")
        return
    
    # Session table
    for i, session in enumerate(sessions):
        with st.expander(
            f"🏥 {session['patient_name']} - {session['doctor_name']} "
            f"({datetime.fromisoformat(session['created_at']).strftime('%Y-%m-%d %H:%M')})",
            expanded=(i == 0)  # Expand first session by default
        ):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                # Session details
                st.markdown("**📋 Session Details:**")
                st.markdown(f"**Patient:** {session['patient_name']}")
                st.markdown(f"**Doctor:** {session['doctor_name']}")
                st.markdown(f"**Date:** {session['session_date']}")
                st.markdown(f"**Status:** {'✅ Completed' if session['status'] == 'completed' else '⏳ Processing' if session['status'] == 'processing' else '❌ Error'}")
                
                if session.get('file_size'):
                    file_size_mb = round(session['file_size'] / (1024 * 1024), 2)
                    st.markdown(f"**File Size:** {file_size_mb} MB")
                
                if session.get('confidence_score'):
                    confidence_pct = round(session['confidence_score'] * 100, 1)
                    st.markdown(f"**Accuracy:** {confidence_pct}%")
                
                # Audio player
                if session['status'] == 'completed':
                    st.markdown("**🎵 Audio Playback:**")
                    audio_data = db.get_audio_data(session['id'])
                    if audio_data:
                        audio_html = get_audio_player_html(audio_data, session['audio_filename'])
                        st.markdown(audio_html, unsafe_allow_html=True)
                    
                    # Action buttons
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button(f"👁️ View", key=f"view_{context}_{session['id']}_{i}"):
                            st.session_state.selected_session_id = session['id']
                            st.rerun()
                    
                    with col_btn2:
                        if st.button(f"🗑️ Delete", key=f"delete_{context}_{session['id']}_{i}"):
                            db.delete_session(session['id'])
                            st.success("Session deleted!")
                            st.rerun()
            
            with col2:
                                # Show transcription if this session is selected or if it's the first completed session
                if (st.session_state.selected_session_id == session['id'] or 
                    (i == 0 and session['status'] == 'completed' and not st.session_state.selected_session_id)):
                    
                    session_data = db.get_session_by_id(session['id'])
                    if session_data:
                        render_transcription_chat(session_data, f"{context}_table", i)
                        
                        # Add manual refresh button with unique key
                        import time
                        refresh_key = f"refresh_{session['id']}_{int(time.time() * 1000)}"
                        if st.button(f"🔄 Refresh Transcription", key=refresh_key):
                            st.rerun()
                    else:
                        st.error("❌ Could not load session data from database.")

def render_session_history():
    """Legacy function - redirects to enhanced table"""
    render_session_table_with_filters("dashboard")

def render_live_demo():
    """Render live transcription demo"""
    st.markdown("### 🔴 Live Transcription Demo")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("🎙️ Start Demo", type="primary"):
            st.session_state.demo_active = True
        
        if st.button("⏹️ Stop"):
            st.session_state.demo_active = False
    
    with col1:
        if st.session_state.get('demo_active', False):
            st.success("🔴 Demo recording active")
            
            # Simulate real-time transcription
            demo_messages = [
                ("Patient", "Hi Dr. Johnson, I've been having some chest pain recently."),
                ("Doctor", "I see. Can you describe the pain? When does it occur?"),
                ("Patient", "It's mostly when I exercise or climb stairs. Sharp, stabbing pain."),
                ("Doctor", "How long have you been experiencing this?"),
                ("Patient", "About two weeks now. It's getting worse."),
            ]
            
            chat_placeholder = st.empty()
            
            for i, (speaker, message) in enumerate(demo_messages):
                time.sleep(2)  # Simulate real-time delay
                
                # Build chat history
                chat_html = "<div class='chat-container'>"
                for j in range(i + 1):
                    spk, msg = demo_messages[j]
                    message_class = "doctor-message" if spk == "Doctor" else "patient-message"
                    chat_html += f"""
                    <div class="chat-message {message_class}">
                        <strong>{spk}</strong>
                        <div>{msg}</div>
                        <div class="message-time">{datetime.now().strftime('%H:%M')}</div>
                    </div>
                    """
                chat_html += "</div>"
                
                chat_placeholder.markdown(chat_html, unsafe_allow_html=True)
                
            st.session_state.demo_active = False
        else:
            st.info("Click 'Start Demo' to see live transcription simulation")

def main():
    """Main application"""
    render_header()
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("## 🎛️ Navigation")
        page = st.selectbox(
            "Choose a page:",
            ["📊 Dashboard", "📝 New Transcription", "🔴 Live Demo", "🧪 Test Features"]
        )
        
        st.markdown("---")
        st.markdown("## ⚙️ Settings")
        model_size = st.selectbox("Model Size:", ["tiny", "base", "small", "medium"])
        st.markdown("**Current Model:** `" + model_size + "`")
        
        st.markdown("---")
        st.markdown("## 📈 Quick Stats")
        stats = db.get_stats()
        st.metric("Total Sessions", stats['total_sessions'])
        st.metric("This Month", stats['this_month'])
        st.metric("Avg Accuracy", f"{stats['avg_confidence']}%")
        
        st.markdown("---")
        st.markdown("## 🎯 Quick Actions")
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
        
        if st.button("🗑️ Clear Filters", use_container_width=True):
            st.session_state.selected_session_id = None
            st.rerun()
    
    # Main content based on page selection
    if page == "📊 Dashboard":
        render_stats()
        
        # Better screen utilization with adjusted column ratios
        col1, col2 = st.columns([2.5, 1.5])
        
        with col1:
            render_session_history()
        
        with col2:
            st.markdown("### 🎯 Quick Actions")
            
            if st.button("🆕 New Transcription", type="primary", use_container_width=True):
                st.rerun()
            
            st.markdown("### 📊 Usage Analytics")
            
            # Simple chart if we have data
            sessions = db.get_sessions(limit=100)  # Get recent sessions for analytics
            if sessions:
                # Process dates for chart
                dates = [datetime.fromisoformat(s['created_at']).date() for s in sessions]
                date_counts = pd.Series(dates).value_counts().sort_index()
                
                if len(date_counts) > 0:
                    fig = px.line(x=date_counts.index, y=date_counts.values, 
                                 title="Sessions per Day")
                    fig.update_layout(showlegend=False, height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Not enough data for analytics")
            else:
                st.info("Upload sessions to see analytics")
    
    elif page == "📝 New Transcription":
        # Two-column layout: Upload on left, Session table on right - better screen fit
        col_upload, col_sessions = st.columns([1.2, 1.8])
        
        with col_upload:
            st.markdown("### 🎵 Upload Audio Session")
            
            # Session details form
            with st.form("session_details"):
                patient_name = st.text_input("👤 Patient Name", placeholder="Enter patient name")
                doctor_name = st.text_input("👨‍⚕️ Doctor Name", placeholder="Enter doctor name")
                session_date = st.date_input("📅 Session Date", value=datetime.now().date())
                session_notes = st.text_area("📝 Session Notes (Optional)", placeholder="Add any relevant notes...")
                
                # Model selection
                model_size = st.selectbox("🤖 Model Size:", ["tiny", "base", "small", "medium"], 
                                        help="Larger models are more accurate but slower")
                
                # Audio file upload
                st.markdown("**🎵 Audio File**")
                audio_file = st.file_uploader(
                    "Choose an audio file",
                    type=['mp3', 'wav', 'm4a', 'mp4'],
                    help="Supports MP3, WAV, M4A, and MP4 files up to 100MB"
                )
                
                submit_button = st.form_submit_button("🚀 Start Transcription", type="primary")
            
            if submit_button and audio_file and patient_name and doctor_name:
                session_details = {
                    'patient_name': patient_name,
                    'doctor_name': doctor_name,
                    'session_date': session_date.isoformat(),
                    'session_notes': session_notes
                }
                
                with st.spinner("Processing transcription..."):
                    result = process_transcription(audio_file, session_details, model_size)
                
                if result:
                    st.success("✅ Transcription completed successfully!")
                    st.session_state.selected_session_id = result['id']
                    
                    # Download option
                    if result.get('transcription_text'):
                        st.download_button(
                            "📥 Download Transcription",
                            data=result['transcription_text'],
                            file_name=f"transcription_{patient_name}_{session_date}.txt",
                            mime="text/plain",
                            key=f"download_transcription_result_{result.get('id', 'new')}"
                        )
                    
                    st.rerun()  # Refresh to show new session
            
            elif submit_button:
                st.error("Please fill in all required fields and upload an audio file.")
        
        with col_sessions:
            # Show recent sessions with live transcription on the right
            st.markdown("### 📋 Recent Sessions")
            
            # Get recent sessions
            recent_sessions = db.get_sessions(limit=5)
            
            if recent_sessions:
                # Session selector
                session_options = [
                    f"{s['patient_name']} - {s['doctor_name']} ({datetime.fromisoformat(s['created_at']).strftime('%m/%d %H:%M')})"
                    for s in recent_sessions
                ]
                
                selected_idx = st.selectbox(
                    "Select session to view:",
                    range(len(session_options)),
                    format_func=lambda x: session_options[x],
                    key="session_selector"
                )
                
                selected_session = recent_sessions[selected_idx]
                
                # Session info
                st.markdown(f"**Status:** {'✅ Completed' if selected_session['status'] == 'completed' else '⏳ Processing'}")
                
                # Audio player for completed sessions
                if selected_session['status'] == 'completed':
                    audio_data = db.get_audio_data(selected_session['id'])
                    if audio_data:
                        audio_html = get_audio_player_html(audio_data, selected_session['audio_filename'])
                        st.markdown(audio_html, unsafe_allow_html=True)
                    
                                         # Show transcription
                    session_data = db.get_session_by_id(selected_session['id'])
                    if session_data:
                        render_transcription_chat(session_data, "new_transcription_preview", selected_idx)
                    else:
                        st.error("❌ Could not load session data.")
                else:
                    st.info("Session is still processing...")
            else:
                st.info("No sessions yet. Upload an audio file to get started!")
        
        # Full session table at the bottom
        st.markdown("---")
        render_session_table_with_filters("new_transcription")
    
    elif page == "🔴 Live Demo":
        render_live_demo()
    
    elif page == "🧪 Test Features":
        st.markdown("### 🧪 Test Speaker Detection")
        
        if st.button("Run Speaker Continuity Test"):
            with st.spinner("Running test..."):
                # Capture test output
                test_output = []
                
                # Redirect test output to capture it
                import sys
                from io import StringIO
                
                old_stdout = sys.stdout
                sys.stdout = captured_output = StringIO()
                
                try:
                    test_with_existing_file()
                    test_result = captured_output.getvalue()
                finally:
                    sys.stdout = old_stdout
                
                st.code(test_result, language="text")
        
        st.markdown("### 🗄️ Database Diagnostics")
        
        if st.button("Check Database"):
            sessions = db.get_sessions(limit=5)
            st.markdown("**Recent Sessions:**")
            for session in sessions:
                with st.expander(f"Session {session['id']}: {session['patient_name']} - {session['doctor_name']}"):
                    st.json({
                        'id': session['id'],
                        'status': session['status'],
                        'has_transcription_text': bool(session.get('transcription_text')),
                        'transcription_preview': session.get('transcription_text', '')[:200] if session.get('transcription_text') else 'None'
                    })
                    
                    # Check transcription table
                    transcription_data = db.get_transcription_with_speakers(session['id'])
                    if transcription_data:
                        st.json({
                            'has_speakers': len(transcription_data.get('speakers', [])),
                            'transcription_id': transcription_data['transcription']['id'] if transcription_data.get('transcription') else 'None'
                        })
                    else:
                        st.warning("No transcription data found in transcriptions table")
        
        st.markdown("### 🔧 Configuration")
        
        col1, col2 = st.columns(2)
        with col1:
            continuity_threshold = st.slider("Continuity Time Threshold (seconds)", 1.0, 5.0, 3.0, 0.5)
            
        with col2:
            confidence_threshold = st.slider("Confidence Threshold", 0.5, 1.0, 0.8, 0.1)
        
        st.info(f"Current settings: {continuity_threshold}s continuity, {confidence_threshold} confidence")

if __name__ == "__main__":
    main() 