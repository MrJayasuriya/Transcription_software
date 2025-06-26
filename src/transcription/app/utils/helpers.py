"""
Helper utility functions for MedTranscribe application
"""
import base64
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def format_duration(seconds: float) -> str:
    """Format duration in MM:SS format"""
    if not seconds or seconds < 0:
        return "00:00"
    
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def format_timestamp(dt: datetime) -> str:
    """Format datetime for display"""
    if not dt:
        return ""
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt
    
    now = datetime.now()
    diff = now - dt
    
    if diff.days == 0:
        return f"Today at {dt.strftime('%H:%M')}"
    elif diff.days == 1:
        return f"Yesterday at {dt.strftime('%H:%M')}"
    elif diff.days < 7:
        return f"{diff.days} days ago"
    else:
        return dt.strftime('%Y-%m-%d %H:%M')


def generate_file_hash(file_data: bytes) -> str:
    """Generate SHA-256 hash for file data"""
    return hashlib.sha256(file_data).hexdigest()


def encode_audio_for_html(audio_data: bytes, filename: str) -> str:
    """Encode audio data for HTML5 audio player"""
    b64_audio = base64.b64encode(audio_data).decode()
    file_extension = Path(filename).suffix.lower()
    
    # Determine MIME type
    mime_type = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.m4a': 'audio/mp4',
        '.mp4': 'audio/mp4'
    }.get(file_extension, 'audio/mpeg')
    
    return f"data:{mime_type};base64,{b64_audio}"


def create_download_filename(patient_name: str, session_date: str, 
                           file_type: str = "txt") -> str:
    """Create standardized download filename"""
    # Clean patient name for filename
    clean_name = "".join(c for c in patient_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    clean_name = clean_name.replace(' ', '_')
    
    # Format date
    try:
        if isinstance(session_date, str):
            date_obj = datetime.fromisoformat(session_date)
        else:
            date_obj = session_date
        date_str = date_obj.strftime('%Y-%m-%d')
    except:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    return f"transcription_{clean_name}_{date_str}.{file_type}"


def validate_session_data(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate session data before processing"""
    errors = []
    
    # Required fields
    required_fields = ['patient_name', 'doctor_name', 'session_date']
    for field in required_fields:
        if not session_data.get(field):
            errors.append(f"Missing required field: {field}")
    
    # Validate names (basic check)
    if session_data.get('patient_name') and len(session_data['patient_name'].strip()) < 2:
        errors.append("Patient name must be at least 2 characters")
    
    if session_data.get('doctor_name') and len(session_data['doctor_name'].strip()) < 2:
        errors.append("Doctor name must be at least 2 characters")
    
    # Validate date
    if session_data.get('session_date'):
        try:
            if isinstance(session_data['session_date'], str):
                datetime.fromisoformat(session_data['session_date'])
        except ValueError:
            errors.append("Invalid session date format")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }


def parse_transcription_text(transcription_text: str) -> List[Dict[str, Any]]:
    """Parse transcription text into messages"""
    if not transcription_text:
        return []
    
    lines = transcription_text.split('\n')
    messages = []
    current_speaker = None
    current_message = ""
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('=') or line.startswith('📁') or line.startswith('⏰') or line.startswith('🤖'):
            continue
        
        # Detect speaker changes
        speaker_indicators = ['👨‍⚕️ DOCTOR', '🧑‍🤝‍🧑 PATIENT', 'DOCTOR', 'PATIENT', 'Person 1', 'Person 2']
        is_speaker_line = any(indicator in line.upper() for indicator in [s.upper() for s in speaker_indicators])
        
        if is_speaker_line or '[' in line and ']:' in line:
            # Save previous message
            if current_speaker and current_message:
                is_doctor = any(d in current_speaker.upper() for d in ['DOCTOR', 'DR.'])
                messages.append({
                    'speaker': current_speaker,
                    'text': current_message.strip(),
                    'is_doctor': is_doctor,
                    'timestamp': datetime.now().strftime('%H:%M')
                })
            
            # Start new message
            current_speaker = line
            current_message = ""
        elif line.strip() and not line.startswith('📊'):
            # Message content
            if line.startswith('   ') or current_speaker:
                current_message += line.strip() + " "
    
    # Add final message
    if current_speaker and current_message:
        is_doctor = any(d in current_speaker.upper() for d in ['DOCTOR', 'DR.'])
        messages.append({
            'speaker': current_speaker,
            'text': current_message.strip(),
            'is_doctor': is_doctor,
            'timestamp': datetime.now().strftime('%H:%M')
        })
    
    return messages


def create_text_export(session_data: Dict[str, Any], messages: List[Dict[str, Any]]) -> str:
    """Create text export of conversation"""
    output = f"""Medical Consultation Transcript
=====================================
Patient: {session_data.get('patient_name', 'Unknown')}
Doctor: {session_data.get('doctor_name', 'Unknown')}
Date: {session_data.get('session_date', 'Unknown')}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Conversation:
=============

"""
    
    for message in messages:
        # Extract clean speaker name
        speaker_name = message['speaker']
        if 'DOCTOR' in speaker_name.upper():
            speaker_name = session_data.get('doctor_name', 'Doctor')
        else:
            speaker_name = session_data.get('patient_name', 'Patient')
        
        # Add timestamp and message
        timestamp = message.get('timestamp', '')
        text = message.get('text', '').strip()
        
        if timestamp:
            output += f"[{timestamp}] {speaker_name}: {text}\n\n"
        else:
            output += f"{speaker_name}: {text}\n\n"
    
    output += f"""
=====================================
End of Transcript
Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}
"""
    
    return output


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input"""
    if not text:
        return ""
    
    # Remove or escape potentially dangerous characters
    text = text.strip()
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text


def get_date_range_filter(filter_type: str) -> Optional[datetime]:
    """Get date filter based on type"""
    if filter_type == "today":
        return datetime.now().date()
    elif filter_type == "yesterday":
        return (datetime.now() - timedelta(days=1)).date()
    elif filter_type == "last_7_days":
        return datetime.now() - timedelta(days=7)
    elif filter_type == "last_30_days":
        return datetime.now() - timedelta(days=30)
    
    return None 