"""
Data models for transcription sessions
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class SessionStatus(Enum):
    """Session processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class SpeakerType(Enum):
    """Speaker types in medical conversations"""
    DOCTOR = "doctor"
    PATIENT = "patient"
    NURSE = "nurse"
    OTHER = "other"


@dataclass
class AudioSegment:
    """Individual audio segment with speaker information"""
    id: Optional[int] = None
    transcription_id: Optional[int] = None
    speaker_type: SpeakerType = SpeakerType.OTHER
    start_time: float = 0.0
    end_time: float = 0.0
    text: str = ""
    confidence: float = 0.0
    segment_order: int = 0
    
    def __post_init__(self):
        """Convert string speaker_type to enum if needed"""
        if isinstance(self.speaker_type, str):
            self.speaker_type = SpeakerType(self.speaker_type.lower())
    
    @property
    def duration(self) -> float:
        """Calculate segment duration"""
        return self.end_time - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'transcription_id': self.transcription_id,
            'speaker_type': self.speaker_type.value,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'text': self.text,
            'confidence': self.confidence,
            'segment_order': self.segment_order,
            'duration': self.duration
        }


@dataclass
class TranscriptionResult:
    """Transcription processing result"""
    id: Optional[int] = None
    session_id: Optional[int] = None
    transcription_text: str = ""
    segments_json: str = ""
    speaker_mapping: str = ""
    confidence_score: float = 0.0
    processing_time: float = 0.0
    created_at: Optional[datetime] = None
    segments: List[AudioSegment] = field(default_factory=list)
    
    def __post_init__(self):
        """Set created_at if not provided and convert string timestamps to datetime"""
        # Convert string timestamp to datetime object if needed
        if isinstance(self.created_at, str):
            try:
                self.created_at = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                self.created_at = datetime.now()
        elif self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def average_confidence(self) -> float:
        """Calculate average confidence from segments"""
        if not self.segments:
            return self.confidence_score
        
        total_confidence = sum(segment.confidence for segment in self.segments)
        return total_confidence / len(self.segments)
    
    @property
    def total_duration(self) -> float:
        """Calculate total duration from segments"""
        if not self.segments:
            return 0.0
        
        return sum(segment.duration for segment in self.segments)
    
    def get_segments_by_speaker(self, speaker_type: SpeakerType) -> List[AudioSegment]:
        """Get segments filtered by speaker type"""
        return [segment for segment in self.segments if segment.speaker_type == speaker_type]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'transcription_text': self.transcription_text,
            'segments_json': self.segments_json,
            'speaker_mapping': self.speaker_mapping,
            'confidence_score': self.confidence_score,
            'processing_time': self.processing_time,
            'created_at': self.created_at.isoformat() if self.created_at and hasattr(self.created_at, 'isoformat') else str(self.created_at) if self.created_at else None,
            'segments': [segment.to_dict() for segment in self.segments],
            'average_confidence': self.average_confidence,
            'total_duration': self.total_duration
        }


@dataclass
class Session:
    """Medical transcription session"""
    id: Optional[int] = None
    patient_name: str = ""
    doctor_name: str = ""
    session_date: str = ""
    audio_filename: str = ""
    audio_data: Optional[bytes] = None
    file_size: Optional[int] = None
    duration: Optional[float] = None
    session_notes: str = ""
    model_used: str = "tiny"
    status: SessionStatus = SessionStatus.PENDING
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    transcription: Optional[TranscriptionResult] = None
    
    def __post_init__(self):
        """Set timestamps if not provided and convert string timestamps to datetime"""
        now = datetime.now()
        
        # Convert string timestamps to datetime objects if needed
        if isinstance(self.created_at, str):
            try:
                self.created_at = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                self.created_at = now
        elif self.created_at is None:
            self.created_at = now
            
        if isinstance(self.updated_at, str):
            try:
                self.updated_at = datetime.fromisoformat(self.updated_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                self.updated_at = now
        elif self.updated_at is None:
            self.updated_at = now
        
        # Convert string status to enum if needed
        if isinstance(self.status, str):
            self.status = SessionStatus(self.status.lower())
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0.0
    
    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string"""
        if not self.duration:
            return "00:00"
        
        minutes = int(self.duration // 60)
        seconds = int(self.duration % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    @property
    def is_completed(self) -> bool:
        """Check if session is completed"""
        return self.status == SessionStatus.COMPLETED
    
    @property
    def is_processing(self) -> bool:
        """Check if session is processing"""
        return self.status == SessionStatus.PROCESSING
    
    @property
    def has_error(self) -> bool:
        """Check if session has error"""
        return self.status == SessionStatus.ERROR
    
    def update_status(self, status: SessionStatus):
        """Update session status with timestamp"""
        self.status = status
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'patient_name': self.patient_name,
            'doctor_name': self.doctor_name,
            'session_date': self.session_date,
            'audio_filename': self.audio_filename,
            'file_size': self.file_size,
            'file_size_mb': self.file_size_mb,
            'duration': self.duration,
            'duration_formatted': self.duration_formatted,
            'session_notes': self.session_notes,
            'model_used': self.model_used,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at and hasattr(self.created_at, 'isoformat') else str(self.created_at) if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at and hasattr(self.updated_at, 'isoformat') else str(self.updated_at) if self.updated_at else None,
            'transcription': self.transcription.to_dict() if self.transcription else None,
            'is_completed': self.is_completed,
            'is_processing': self.is_processing,
            'has_error': self.has_error
        }


@dataclass
class SessionFilter:
    """Filter parameters for session queries"""
    doctor_name: Optional[str] = None
    patient_name: Optional[str] = None
    status: Optional[SessionStatus] = None
    date_filter: Optional[str] = None
    search_query: Optional[str] = None
    limit: int = 50
    offset: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'doctor_name': self.doctor_name,
            'patient_name': self.patient_name,
            'status': self.status.value if self.status else None,
            'date_filter': self.date_filter,
            'search_query': self.search_query,
            'limit': self.limit,
            'offset': self.offset
        } 