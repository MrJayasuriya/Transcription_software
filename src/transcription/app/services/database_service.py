"""
Database service for transcription management
"""
import sqlite3
import json
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from ..models import (
    Session, TranscriptionResult, AudioSegment, 
    SessionFilter, SessionStatus, SpeakerType
)
from ..config import current_config

logger = logging.getLogger(__name__)


class DatabaseService:
    """Database service for managing transcription sessions"""
    
    def __init__(self, db_path: str = None):
        """Initialize database service"""
        self.db_path = db_path or current_config.DATABASE_URL
        self.init_database()
        logger.info(f"Database service initialized with path: {self.db_path}")
    
    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_name TEXT NOT NULL,
                    doctor_name TEXT NOT NULL,
                    session_date TEXT NOT NULL,
                    audio_filename TEXT NOT NULL,
                    audio_data BLOB,
                    file_size INTEGER,
                    duration REAL,
                    session_notes TEXT DEFAULT '',
                    model_used TEXT DEFAULT 'tiny',
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Transcriptions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    transcription_text TEXT,
                    segments_json TEXT,
                    speaker_mapping TEXT,
                    confidence_score REAL DEFAULT 0.0,
                    processing_time REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                )
            """)
            
            # Speakers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS speakers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transcription_id INTEGER NOT NULL,
                    speaker_type TEXT NOT NULL,
                    start_time REAL NOT NULL,
                    end_time REAL NOT NULL,
                    text TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    segment_order INTEGER DEFAULT 0,
                    FOREIGN KEY (transcription_id) REFERENCES transcriptions (id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(session_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_doctor ON sessions(doctor_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_patient ON sessions(patient_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcriptions_session ON transcriptions(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_speakers_transcription ON speakers(transcription_id)")
            
            conn.commit()
            logger.info("Database tables initialized successfully")
    
    def save_session(self, session: Session) -> int:
        """Save a new session to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO sessions (
                        patient_name, doctor_name, session_date, audio_filename,
                        audio_data, file_size, duration, session_notes, model_used, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session.patient_name, session.doctor_name, session.session_date,
                    session.audio_filename, session.audio_data, session.file_size,
                    session.duration, session.session_notes, session.model_used,
                    session.status.value
                ))
                
                session_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Session saved successfully with ID: {session_id}")
                return session_id
                
        except Exception as e:
            logger.error(f"Error saving session: {str(e)}")
            raise
    
    def save_transcription(self, transcription: TranscriptionResult) -> int:
        """Save transcription results to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Save main transcription
                cursor.execute("""
                    INSERT INTO transcriptions (
                        session_id, transcription_text, segments_json,
                        speaker_mapping, confidence_score, processing_time
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    transcription.session_id, transcription.transcription_text,
                    transcription.segments_json, transcription.speaker_mapping,
                    transcription.confidence_score, transcription.processing_time
                ))
                
                transcription_id = cursor.lastrowid
                
                # Save individual speaker segments
                for segment in transcription.segments:
                    cursor.execute("""
                        INSERT INTO speakers (
                            transcription_id, speaker_type, start_time, end_time,
                            text, confidence, segment_order
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        transcription_id, segment.speaker_type.value,
                        segment.start_time, segment.end_time, segment.text,
                        segment.confidence, segment.segment_order
                    ))
                
                # Update session status to completed
                cursor.execute(
                    "UPDATE sessions SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (transcription.session_id,)
                )
                
                conn.commit()
                logger.info(f"Transcription saved successfully with ID: {transcription_id}")
                return transcription_id
                
        except Exception as e:
            logger.error(f"Error saving transcription: {str(e)}")
            raise
    
    def get_sessions(self, filter_params: SessionFilter = None) -> List[Session]:
        """Retrieve sessions with optional filtering"""
        try:
            filter_params = filter_params or SessionFilter()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = """
                    SELECT s.*, t.transcription_text, t.confidence_score,
                           COUNT(sp.id) as segment_count
                    FROM sessions s
                    LEFT JOIN transcriptions t ON s.id = t.session_id
                    LEFT JOIN speakers sp ON t.id = sp.transcription_id
                    WHERE 1=1
                """
                params = []
                
                if filter_params.doctor_name:
                    query += " AND s.doctor_name LIKE ?"
                    params.append(f"%{filter_params.doctor_name}%")
                
                if filter_params.patient_name:
                    query += " AND s.patient_name LIKE ?"
                    params.append(f"%{filter_params.patient_name}%")
                
                if filter_params.status:
                    query += " AND s.status = ?"
                    params.append(filter_params.status.value)
                
                # Date filtering
                if filter_params.date_filter:
                    if isinstance(filter_params.date_filter, str):
                        if filter_params.date_filter == "last_7_days":
                            query += " AND DATE(s.session_date) >= DATE('now', '-7 days')"
                        elif filter_params.date_filter == "last_30_days":
                            query += " AND DATE(s.session_date) >= DATE('now', '-30 days')"
                    else:
                        query += " AND DATE(s.session_date) = ?"
                        params.append(str(filter_params.date_filter))
                
                query += """
                    GROUP BY s.id, t.id
                    ORDER BY s.created_at DESC
                    LIMIT ? OFFSET ?
                """
                params.extend([filter_params.limit, filter_params.offset])
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                sessions = []
                for row in rows:
                    session = Session(
                        id=row['id'],
                        patient_name=row['patient_name'],
                        doctor_name=row['doctor_name'],
                        session_date=row['session_date'],
                        audio_filename=row['audio_filename'],
                        file_size=row['file_size'],
                        duration=row['duration'],
                        session_notes=row['session_notes'],
                        model_used=row['model_used'],
                        status=SessionStatus(row['status']),
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
                    sessions.append(session)
                
                logger.info(f"Retrieved {len(sessions)} sessions")
                return sessions
                
        except Exception as e:
            logger.error(f"Error retrieving sessions: {str(e)}")
            raise
    
    def get_session_by_id(self, session_id: int) -> Optional[Session]:
        """Get complete session data by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT s.*, t.transcription_text, t.segments_json, t.speaker_mapping,
                           t.confidence_score, t.processing_time
                    FROM sessions s
                    LEFT JOIN transcriptions t ON s.id = t.session_id
                    WHERE s.id = ?
                """, (session_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                session = Session(
                    id=row['id'],
                    patient_name=row['patient_name'],
                    doctor_name=row['doctor_name'],
                    session_date=row['session_date'],
                    audio_filename=row['audio_filename'],
                    file_size=row['file_size'],
                    duration=row['duration'],
                    session_notes=row['session_notes'],
                    model_used=row['model_used'],
                    status=SessionStatus(row['status']),
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                
                # Add transcription if available
                if row['transcription_text']:
                    transcription = TranscriptionResult(
                        session_id=session_id,
                        transcription_text=row['transcription_text'],
                        segments_json=row['segments_json'],
                        speaker_mapping=row['speaker_mapping'],
                        confidence_score=row['confidence_score'],
                        processing_time=row['processing_time']
                    )
                    session.transcription = transcription
                
                logger.info(f"Retrieved session {session_id}")
                return session
                
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {str(e)}")
            raise
    
    def get_audio_data(self, session_id: int) -> Optional[bytes]:
        """Get audio file data for playback"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT audio_data FROM sessions WHERE id = ?", (session_id,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Error retrieving audio data for session {session_id}: {str(e)}")
            return None
    
    def get_transcription_by_session_id(self, session_id: int) -> Optional['TranscriptionResult']:
        """Get transcription result by session ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM transcriptions WHERE session_id = ?
                """, (session_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Import here to avoid circular imports
                from ..models.session import TranscriptionResult, AudioSegment, SpeakerType
                
                # Get segments
                cursor.execute("""
                    SELECT * FROM speakers WHERE transcription_id = ? ORDER BY segment_order
                """, (row['id'],))
                
                segment_rows = cursor.fetchall()
                segments = []
                
                for seg_row in segment_rows:
                    segment = AudioSegment(
                        speaker_type=SpeakerType(seg_row['speaker_type']),
                        start_time=seg_row['start_time'],
                        end_time=seg_row['end_time'],
                        text=seg_row['text'],
                        confidence=seg_row['confidence'],
                        segment_order=seg_row['segment_order']
                    )
                    segments.append(segment)
                
                transcription = TranscriptionResult(
                    session_id=session_id,
                    transcription_text=row['transcription_text'],
                    segments=segments,
                    segments_json=row['segments_json'],
                    speaker_mapping=row['speaker_mapping'],
                    confidence_score=row['confidence_score'],
                    processing_time=row['processing_time']
                )
                
                logger.info(f"Retrieved transcription for session {session_id}")
                return transcription
                
        except Exception as e:
            logger.error(f"Error retrieving transcription for session {session_id}: {str(e)}")
            return None
    
    def update_session_status(self, session_id: int, status: SessionStatus):
        """Update session processing status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sessions SET status = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """, (status.value, session_id))
                conn.commit()
                logger.info(f"Updated session {session_id} status to {status.value}")
        except Exception as e:
            logger.error(f"Error updating session {session_id} status: {str(e)}")
            raise
    
    def delete_session(self, session_id: int):
        """Delete session and all related data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
                conn.commit()
                logger.info(f"Deleted session {session_id}")
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {str(e)}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total sessions
                cursor.execute("SELECT COUNT(*) FROM sessions")
                total_sessions = cursor.fetchone()[0]
                
                # This month sessions
                cursor.execute("""
                    SELECT COUNT(*) FROM sessions 
                    WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
                """)
                this_month = cursor.fetchone()[0]
                
                # Average confidence
                cursor.execute("SELECT AVG(confidence_score) FROM transcriptions")
                avg_confidence = cursor.fetchone()[0] or 0.0
                
                # Total duration
                cursor.execute("SELECT SUM(duration) FROM sessions WHERE duration IS NOT NULL")
                total_duration = cursor.fetchone()[0] or 0.0
                
                stats = {
                    'total_sessions': total_sessions,
                    'this_month': this_month,
                    'avg_confidence': round(avg_confidence * 100, 1) if avg_confidence else 0,
                    'total_duration_hours': round(total_duration / 3600, 1)
                }
                
                logger.info("Retrieved database statistics")
                return stats
                
        except Exception as e:
            logger.error(f"Error retrieving stats: {str(e)}")
            raise
    
    def search_sessions(self, search_query: str, date_filter=None) -> List[Session]:
        """Search sessions by patient name, doctor name, or notes"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = """
                    SELECT s.*, t.transcription_text
                    FROM sessions s
                    LEFT JOIN transcriptions t ON s.id = t.session_id
                    WHERE (s.patient_name LIKE ? OR s.doctor_name LIKE ? OR s.session_notes LIKE ?)
                """
                params = [f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"]
                
                # Add date filtering
                if date_filter:
                    if isinstance(date_filter, str):
                        if date_filter == "last_7_days":
                            query += " AND DATE(s.session_date) >= DATE('now', '-7 days')"
                        elif date_filter == "last_30_days":
                            query += " AND DATE(s.session_date) >= DATE('now', '-30 days')"
                    else:
                        query += " AND DATE(s.session_date) = ?"
                        params.append(str(date_filter))
                
                query += " ORDER BY s.created_at DESC LIMIT 20"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                sessions = []
                for row in rows:
                    session = Session(
                        id=row['id'],
                        patient_name=row['patient_name'],
                        doctor_name=row['doctor_name'],
                        session_date=row['session_date'],
                        audio_filename=row['audio_filename'],
                        file_size=row['file_size'],
                        duration=row['duration'],
                        session_notes=row['session_notes'],
                        model_used=row['model_used'],
                        status=SessionStatus(row['status']),
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
                    sessions.append(session)
                
                logger.info(f"Search found {len(sessions)} sessions for query: {search_query}")
                return sessions
                
        except Exception as e:
            logger.error(f"Error searching sessions: {str(e)}")
            raise
    
    def get_doctors(self) -> List[str]:
        """Get list of unique doctor names"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT doctor_name FROM sessions ORDER BY doctor_name")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error retrieving doctors: {str(e)}")
            return []
    
    def get_patients(self) -> List[str]:
        """Get list of unique patient names"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT patient_name FROM sessions ORDER BY patient_name")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error retrieving patients: {str(e)}")
            return []


# Global database service instance
db_service = DatabaseService() 