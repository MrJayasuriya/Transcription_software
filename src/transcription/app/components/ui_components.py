"""
Reusable UI components for Streamlit interface
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import time
import base64

from ..utils.helpers import format_file_size, format_timestamp, encode_audio_for_html, parse_transcription_text, create_text_export


def render_whatsapp_chat(messages: List[Dict[str, Any]], session_data: Dict[str, Any] = None) -> None:
    """
    Render WhatsApp-style chat interface for conversation transcription
    
    Args:
        messages: List of message dictionaries with speaker, text, is_doctor
        session_data: Session information for context
    """
    st.markdown("""
    <style>
    .chat-container {
        max-height: 500px;
        overflow-y: auto;
        border: 1px solid #e1e5e9;
        border-radius: 10px;
        padding: 15px;
        background-color: #f8f9fa;
        margin-bottom: 20px;
    }
    
    .message {
        margin-bottom: 15px;
        display: flex;
        align-items: flex-start;
        animation: fadeIn 0.3s ease-in;
    }
    
    .message.doctor {
        justify-content: flex-end;
    }
    
    .message.patient {
        justify-content: flex-start;
    }
    
    .message-bubble {
        max-width: 70%;
        padding: 12px 16px;
        border-radius: 18px;
        font-size: 14px;
        line-height: 1.4;
        position: relative;
        word-wrap: break-word;
    }
    
    .message.doctor .message-bubble {
        background: linear-gradient(135deg, #007bff, #0056b3);
        color: white;
        border-bottom-right-radius: 4px;
        margin-left: 10px;
    }
    
    .message.patient .message-bubble {
        background: #ffffff;
        color: #333;
        border: 1px solid #e1e5e9;
        border-bottom-left-radius: 4px;
        margin-right: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .speaker-avatar {
        width: 35px;
        height: 35px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        font-weight: bold;
        margin: 0 8px;
        flex-shrink: 0;
    }
    
    .doctor-avatar {
        background: linear-gradient(135deg, #007bff, #0056b3);
        color: white;
    }
    
    .patient-avatar {
        background: linear-gradient(135deg, #28a745, #1e7e34);
        color: white;
    }
    
    .message-time {
        font-size: 11px;
        opacity: 0.7;
        margin-top: 4px;
    }
    
    .chat-header {
        background: linear-gradient(135deg, #6c757d, #495057);
        color: white;
        padding: 15px;
        border-radius: 10px 10px 0 0;
        margin-bottom: 0;
        text-align: center;
    }
    
    .chat-stats {
        display: flex;
        justify-content: space-around;
        background: #e9ecef;
        padding: 10px;
        border-radius: 0 0 10px 10px;
        margin-bottom: 15px;
        font-size: 12px;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    </style>
    """, unsafe_allow_html=True)
    
    if not messages:
        st.info("📭 No conversation messages available")
        return
    
    # Chat Header
    if session_data:
        st.markdown(f"""
        <div class="chat-header">
            <h4 style="margin: 0;">💬 Medical Consultation</h4>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">
                {session_data.get('patient_name', 'Patient')} • Dr. {session_data.get('doctor_name', 'Doctor')}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Chat Stats
        doctor_count = sum(1 for msg in messages if msg.get('is_doctor', False))
        patient_count = len(messages) - doctor_count
        
        st.markdown(f"""
        <div class="chat-stats">
            <span>👨‍⚕️ Doctor: {doctor_count} messages</span>
            <span>🧑‍🤝‍🧑 Patient: {patient_count} messages</span>
            <span>💬 Total: {len(messages)} messages</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Chat Messages
    chat_html = '<div class="chat-container">'
    
    for i, message in enumerate(messages):
        is_doctor = message.get('is_doctor', False)
        speaker_class = 'doctor' if is_doctor else 'patient'
        avatar_emoji = '👨‍⚕️' if is_doctor else '🧑‍🤝‍🧑'
        avatar_class = 'doctor-avatar' if is_doctor else 'patient-avatar'
        
        # Clean and format message text
        text = message.get('text', '').strip()
        if not text:
            continue
            
        # Escape HTML
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        
        timestamp = message.get('timestamp', datetime.now().strftime('%H:%M'))
        
        if is_doctor:
            chat_html += f"""
            <div class="message {speaker_class}">
                <div class="message-bubble">
                    {text}
                    <div class="message-time">{timestamp}</div>
                </div>
                <div class="speaker-avatar {avatar_class}">{avatar_emoji}</div>
            </div>
            """
        else:
            chat_html += f"""
            <div class="message {speaker_class}">
                <div class="speaker-avatar {avatar_class}">{avatar_emoji}</div>
                <div class="message-bubble">
                    {text}
                    <div class="message-time">{timestamp}</div>
                </div>
            </div>
            """
    
    chat_html += '</div>'
    
    st.markdown(chat_html, unsafe_allow_html=True)


def render_enhanced_session_details(session: Any, unique_id: str = None) -> None:
    """
    Render enhanced session details with audio player and chat interface
    
    Args:
        session: Session object with transcription data
        unique_id: Unique identifier for UI elements
    """
    if not unique_id:
        unique_id = f"{session.id}_{int(time.time() * 1000)}"
    
    # Check if session is selected
    session_key = f"selected_session_{unique_id}"
    if session_key not in st.session_state:
        st.session_state[session_key] = False
    
    # Toggle button
    if st.button(f"👁️ View Details", key=f"view_btn_{unique_id}"):
        st.session_state[session_key] = not st.session_state[session_key]
        st.rerun()
    
    # Show details if selected
    if st.session_state[session_key]:
        with st.container():
            st.markdown("---")
            
            # Session Header
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                ### 📋 Session Details
                **Patient:** {session.patient_name}  
                **Doctor:** Dr. {session.doctor_name}  
                **Date:** {session.session_date}  
                **Status:** {session.status.value.title() if hasattr(session.status, 'value') else str(session.status).title()}
                """)
                
                if hasattr(session, 'session_notes') and session.session_notes:
                    st.markdown(f"**Notes:** {session.session_notes}")
            
            with col2:
                # Session Stats
                st.markdown("### 📊 Stats")
                if hasattr(session, 'duration') and session.duration:
                    duration_str = f"{int(session.duration // 60):02d}:{int(session.duration % 60):02d}"
                    st.metric("Duration", duration_str)
                
                if hasattr(session, 'file_size') and session.file_size:
                    st.metric("File Size", format_file_size(session.file_size))
            
            # Audio Player
            st.markdown("### 🎵 Audio Playback")
            try:
                from ..services.database_service import db_service
                audio_data = db_service.get_audio_data(session.id)
                
                if audio_data:
                    audio_base64 = encode_audio_for_html(audio_data, session.audio_filename or "audio.mp3")
                    st.markdown(f"""
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin: 10px 0;">
                        <audio controls style="width: 100%;">
                            <source src="{audio_base64}" type="audio/mpeg">
                            Your browser does not support the audio element.
                        </audio>
                        <p style="margin: 5px 0 0 0; font-size: 12px; color: #6c757d;">
                            🎧 {session.audio_filename or 'Audio file'}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("🔇 Audio file not available")
            except Exception as e:
                st.error(f"❌ Error loading audio: {str(e)}")
            
            # Transcription
            st.markdown("### 💬 Conversation Transcript")
            
            try:
                transcription = db_service.get_transcription_by_session_id(session.id)
                
                if transcription and transcription.transcription_text:
                    # Parse messages for chat interface
                    messages = parse_transcription_text(transcription.transcription_text)
                    
                    # Session data for chat
                    session_data = {
                        'patient_name': session.patient_name,
                        'doctor_name': session.doctor_name,
                        'session_date': session.session_date
                    }
                    
                    if messages:
                        # Render WhatsApp-style chat
                        render_whatsapp_chat(messages, session_data)
                        
                        # Download Options
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            # Download as Text
                            text_export = create_text_export(session_data, messages)
                            st.download_button(
                                label="📄 Download as Text",
                                data=text_export,
                                file_name=f"transcript_{session.patient_name}_{session.session_date}.txt",
                                mime="text/plain",
                                key=f"download_txt_{unique_id}"
                            )
                        
                        with col2:
                            # Download Raw Transcript
                            st.download_button(
                                label="📋 Download Raw",
                                data=transcription.transcription_text,
                                file_name=f"raw_transcript_{session.patient_name}_{session.session_date}.txt",
                                mime="text/plain",
                                key=f"download_raw_{unique_id}"
                            )
                        
                        with col3:
                            # Export as JSON
                            import json
                            json_data = {
                                'session': session_data,
                                'messages': messages,
                                'metadata': {
                                    'confidence_score': getattr(transcription, 'confidence_score', None),
                                    'processing_time': getattr(transcription, 'processing_time', None),
                                    'generated_at': datetime.now().isoformat()
                                }
                            }
                            
                            st.download_button(
                                label="📊 Export JSON",
                                data=json.dumps(json_data, indent=2),
                                file_name=f"conversation_{session.patient_name}_{session.session_date}.json",
                                mime="application/json",
                                key=f"download_json_{unique_id}"
                            )
                    
                    else:
                        # Fallback to raw text
                        st.text_area(
                            "Raw Transcription",
                            transcription.transcription_text,
                            height=300,
                            key=f"raw_text_{unique_id}"
                        )
                        
                        st.download_button(
                            label="📥 Download Transcript",
                            data=transcription.transcription_text,
                            file_name=f"transcript_{session.patient_name}_{session.session_date}.txt",
                            mime="text/plain",
                            key=f"simple_download_{unique_id}"
                        )
                    
                    # Transcription Stats
                    if hasattr(transcription, 'confidence_score') and transcription.confidence_score:
                        st.info(f"🎯 Confidence Score: {transcription.confidence_score:.1%}")
                    
                    if hasattr(transcription, 'processing_time') and transcription.processing_time:
                        st.info(f"⏱️ Processing Time: {transcription.processing_time:.1f} seconds")
                
                else:
                    st.info("📭 No transcription available yet")
                    
            except Exception as e:
                st.error(f"❌ Error loading transcription: {str(e)}")
            
            # Close button
            st.markdown("---")
            if st.button(f"🔙 Close Details", key=f"close_btn_{unique_id}"):
                st.session_state[session_key] = False
                st.rerun()


def render_session_card(session: Any, show_audio: bool = True) -> bool:
    """
    Render a session card in the UI with enhanced details
    
    Args:
        session: Session object
        show_audio: Whether to show enhanced details (now always shows in details)
        
    Returns:
        True if session was selected (deprecated, handled internally now)
    """
    with st.container():
        # Session header
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
        
        # Enhanced details section
        unique_id = f"card_{session.id}_{int(time.time() * 1000)}"
        render_enhanced_session_details(session, unique_id)
        
        st.divider()
        return False  # Not needed anymore since we handle it internally


def render_audio_player(session_id: int, filename: str):
    """Render audio player for a session"""
    try:
        from ..services import db_service
        
        audio_data = db_service.get_audio_data(session_id)
        if audio_data:
            audio_base64 = encode_audio_for_html(audio_data, filename)
            st.markdown(f"""
                <audio controls style="width: 100%; margin: 5px 0;">
                    <source src="{audio_base64}" type="audio/mpeg">
                    Your browser does not support the audio element.
                </audio>
            """, unsafe_allow_html=True)
        else:
            st.info("Audio not available")
    except Exception as e:
        st.error(f"Error loading audio: {str(e)}")


def render_upload_form() -> Optional[Dict[str, Any]]:
    """
    Render the audio upload form
    
    Returns:
        Dictionary with upload data if form is submitted, None otherwise
    """
    with st.form("upload_form", clear_on_submit=True):
        st.subheader("🎙️ New Transcription")
        
        # Session details
        col1, col2 = st.columns(2)
        
        with col1:
            patient_name = st.text_input("Patient Name*", placeholder="Enter patient name")
            session_date = st.date_input("Session Date*", value=datetime.now().date())
        
        with col2:
            doctor_name = st.text_input("Doctor Name*", placeholder="Enter doctor name")
            model_size = st.selectbox("Model Size", 
                                    options=["tiny", "base", "small", "medium", "large"],
                                    index=0,
                                    help="Larger models are more accurate but slower")
        
        # Audio upload
        uploaded_file = st.file_uploader(
            "Upload Audio File*",
            type=['mp3', 'wav', 'm4a', 'mp4'],
            help="Maximum file size: 100MB"
        )
        
        # Session notes
        session_notes = st.text_area("Session Notes", placeholder="Optional notes about this session")
        
        # Submit button
        submit_button = st.form_submit_button("🚀 Start Transcription", type="primary")
        
        if submit_button:
            # Validation
            if not all([patient_name, doctor_name, session_date, uploaded_file]):
                st.error("Please fill in all required fields and upload an audio file.")
                return None
            
            # Convert date to string properly  
            session_date_str = session_date.isoformat() if hasattr(session_date, 'isoformat') else str(session_date)
            
            return {
                'patient_name': patient_name.strip(),
                'doctor_name': doctor_name.strip(),
                'session_date': session_date_str,
                'session_notes': session_notes.strip(),
                'model_size': model_size,
                'uploaded_file': uploaded_file
            }
    
    return None


def render_stats_cards(stats: Dict[str, Any]):
    """Render statistics cards"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📊 Total Sessions",
            value=stats.get('total_sessions', 0)
        )
    
    with col2:
        st.metric(
            label="📅 This Month", 
            value=stats.get('this_month', 0)
        )
    
    with col3:
        st.metric(
            label="🎯 Avg Confidence",
            value=f"{stats.get('avg_confidence', 0)}%"
        )
    
    with col4:
        st.metric(
            label="⏱️ Total Hours",
            value=f"{stats.get('total_duration_hours', 0)}h"
        )


def render_filters() -> Dict[str, Any]:
    """
    Render filter controls for sessions
    
    Returns:
        Dictionary with filter parameters
    """
    with st.expander("🔍 Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            doctor_filter = st.text_input("Doctor Name", placeholder="Filter by doctor")
        
        with col2:
            patient_filter = st.text_input("Patient Name", placeholder="Filter by patient")
        
        with col3:
            status_filter = st.selectbox("Status", 
                                       options=["All", "Completed", "Processing", "Pending", "Error"],
                                       index=0)
        
        # Date filtering
        st.subheader("📅 Date Filter")
        date_filter_type = st.selectbox(
            "Date Range",
            options=["All", "Today", "Yesterday", "Last 7 days", "Last 30 days", "Custom Date"],
            index=0
        )
        
        custom_date = None
        if date_filter_type == "Custom Date":
            custom_date = st.date_input("Select Date")
        
        # Search
        search_query = st.text_input("🔍 Search", placeholder="Search in patient names, doctor names, or notes")
        
        return {
            'doctor_name': doctor_filter.strip() if doctor_filter else None,
            'patient_name': patient_filter.strip() if patient_filter else None,
            'status': status_filter.lower() if status_filter != "All" else None,
            'date_filter': date_filter_type.lower().replace(' ', '_') if date_filter_type != "All" else None,
            'custom_date': custom_date,
            'search_query': search_query.strip() if search_query else None
        }


def render_chat_message(message: Dict[str, Any], message_id: str):
    """Render individual chat message with WhatsApp-style UI"""
    is_doctor = message.get('is_doctor', False)
    text = message.get('text', '')
    timestamp = message.get('timestamp', '')
    
    # Create alignment classes
    alignment = "margin-left: 20%; text-align: right;" if is_doctor else "margin-right: 20%; text-align: left;"
    bubble_color = "#DCF8C6" if is_doctor else "#FFFFFF"
    tail_style = "right: -8px; border-left: 8px solid #DCF8C6;" if is_doctor else "left: -8px; border-right: 8px solid #FFFFFF;"
    
    chat_html = f"""
    <div style="margin: 10px 0; {alignment}">
        <div style="
            background-color: {bubble_color};
            padding: 10px 15px;
            border-radius: 18px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            position: relative;
            display: inline-block;
            max-width: 70%;
            word-wrap: break-word;
            font-size: 14px;
            line-height: 1.4;
        ">
            <div style="
                position: absolute;
                bottom: 4px;
                {tail_style}
                width: 0;
                height: 0;
                border-top: 4px solid transparent;
                border-bottom: 4px solid transparent;
            "></div>
            <div style="margin-bottom: 15px; color: #333;">{text}</div>
            <div style="
                font-size: 11px; 
                color: #666; 
                text-align: right;
                margin-top: 5px;
            ">{timestamp}</div>
        </div>
    </div>
    """
    
    st.markdown(chat_html, unsafe_allow_html=True) 