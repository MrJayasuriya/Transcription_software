import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import base64

class TranscriptionDatabase:
    """Database manager for medical transcription sessions"""
    
    def __init__(self, db_path: str = "transcriptions.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_name TEXT NOT NULL,
                    doctor_name TEXT NOT NULL,
                    session_date DATE NOT NULL,
                    session_notes TEXT,
                    audio_filename TEXT NOT NULL,
                    audio_data BLOB,
                    duration REAL,
                    file_size INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    model_used TEXT DEFAULT 'tiny'
                )
            """)
            
            # Transcriptions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    transcription_text TEXT NOT NULL,
                    segments_json TEXT,
                    speaker_mapping JSON,
                    confidence_score REAL,
                    processing_time REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                )
            """)
            
            # Speakers table for segment-level data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS speakers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transcription_id INTEGER NOT NULL,
                    speaker_type TEXT NOT NULL,
                    start_time REAL NOT NULL,
                    end_time REAL NOT NULL,
                    text TEXT NOT NULL,
                    confidence REAL,
                    segment_order INTEGER,
                    FOREIGN KEY (transcription_id) REFERENCES transcriptions (id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_doctor ON sessions(doctor_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_patient ON sessions(patient_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(session_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcriptions_session ON transcriptions(session_id)")
            
            conn.commit()
    
    def save_session(self, patient_name: str, doctor_name: str, session_date: str, 
                    audio_file_data: bytes, audio_filename: str, session_notes: str = "",
                    model_used: str = "tiny") -> int:
        """Save a new session to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO sessions (patient_name, doctor_name, session_date, session_notes,
                                    audio_filename, audio_data, file_size, model_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (patient_name, doctor_name, session_date, session_notes,
                  audio_filename, audio_file_data, len(audio_file_data), model_used))
            
            session_id = cursor.lastrowid
            conn.commit()
            return session_id
    
    def save_transcription(self, session_id: int, transcription_text: str, 
                          segments: List[Dict], speaker_mapping: Dict,
                          confidence_score: float = 0.0, processing_time: float = 0.0) -> int:
        """Save transcription results to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Save main transcription
            cursor.execute("""
                INSERT INTO transcriptions (session_id, transcription_text, segments_json,
                                          speaker_mapping, confidence_score, processing_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, transcription_text, json.dumps(segments),
                  json.dumps(speaker_mapping), confidence_score, processing_time))
            
            transcription_id = cursor.lastrowid
            
            # Save individual speaker segments
            for i, segment in enumerate(segments):
                cursor.execute("""
                    INSERT INTO speakers (transcription_id, speaker_type, start_time, end_time,
                                        text, confidence, segment_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (transcription_id, segment.get('speaker', 'Unknown'),
                      segment.get('start', 0), segment.get('end', 0),
                      segment.get('text', ''), segment.get('confidence', 0.0), i))
            
            # Update session status
            cursor.execute("UPDATE sessions SET status = 'completed' WHERE id = ?", (session_id,))
            
            conn.commit()
            return transcription_id
    
    def get_sessions(self, doctor_name: str = None, patient_name: str = None, 
                    date_filter = None, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Retrieve sessions with optional filtering"""
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
            
            if doctor_name:
                query += " AND s.doctor_name LIKE ?"
                params.append(f"%{doctor_name}%")
            
            if patient_name:
                query += " AND s.patient_name LIKE ?"
                params.append(f"%{patient_name}%")
            
            # Date filtering
            if date_filter:
                if isinstance(date_filter, str):
                    if date_filter == "last_7_days":
                        query += " AND DATE(s.session_date) >= DATE('now', '-7 days')"
                    elif date_filter == "last_30_days":
                        query += " AND DATE(s.session_date) >= DATE('now', '-30 days')"
                else:
                    # Specific date
                    query += " AND DATE(s.session_date) = ?"
                    params.append(str(date_filter))
            
            query += """
                GROUP BY s.id, t.id
                ORDER BY s.created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_session_by_id(self, session_id: int) -> Optional[Dict]:
        """Get complete session data by ID"""
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
            
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def get_transcription_with_speakers(self, session_id: int) -> Optional[Dict]:
        """Get transcription with speaker segments"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get transcription
            cursor.execute("""
                SELECT * FROM transcriptions WHERE session_id = ?
            """, (session_id,))
            transcription = cursor.fetchone()
            
            if not transcription:
                return None
            
            # Get speakers
            cursor.execute("""
                SELECT * FROM speakers WHERE transcription_id = ?
                ORDER BY segment_order
            """, (transcription['id'],))
            speakers = cursor.fetchall()
            
            return {
                'transcription': dict(transcription),
                'speakers': [dict(speaker) for speaker in speakers]
            }
    
    def get_audio_data(self, session_id: int) -> Optional[bytes]:
        """Get audio file data for playback"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT audio_data FROM sessions WHERE id = ?", (session_id,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def update_session_status(self, session_id: int, status: str):
        """Update session processing status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (status, session_id))
            conn.commit()
    
    def delete_session(self, session_id: int):
        """Delete session and all related data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
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
            
            return {
                'total_sessions': total_sessions,
                'this_month': this_month,
                'avg_confidence': round(avg_confidence * 100, 1) if avg_confidence else 0,
                'total_duration_hours': round(total_duration / 3600, 1)
            }
    
    def search_sessions(self, search_query: str, date_filter = None) -> List[Dict]:
        """Search sessions by patient name, doctor name, or notes"""
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
            
            # Add date filtering to search
            if date_filter:
                if isinstance(date_filter, str):
                    if date_filter == "last_7_days":
                        query += " AND DATE(s.session_date) >= DATE('now', '-7 days')"
                    elif date_filter == "last_30_days":
                        query += " AND DATE(s.session_date) >= DATE('now', '-30 days')"
                else:
                    # Specific date
                    query += " AND DATE(s.session_date) = ?"
                    params.append(str(date_filter))
            
            query += " ORDER BY s.created_at DESC LIMIT 20"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_doctors(self) -> List[str]:
        """Get list of unique doctor names"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT doctor_name FROM sessions ORDER BY doctor_name")
            return [row[0] for row in cursor.fetchall()]
    
    def get_patients(self) -> List[str]:
        """Get list of unique patient names"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT patient_name FROM sessions ORDER BY patient_name")
            return [row[0] for row in cursor.fetchall()]

# Global database instance
db = TranscriptionDatabase() 