"""
Transcription service for audio processing
"""
import logging
import tempfile
import os
from typing import Dict, Any, Tuple, List, Optional
from pathlib import Path

from ..models import Session, TranscriptionResult, AudioSegment, SessionStatus, SpeakerType
from ..config import current_config
from .database_service import db_service

# Import the existing transcription logic
# Import from the root directory
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

# We'll use lazy import to avoid circular imports
def get_contextual_transcriber():
    """Lazy import of ContextualTranscriber to avoid circular imports"""
    try:
        # Try importing from main module first (where ContextualTranscriber actually exists)
        import importlib.util
        main_path = Path(__file__).parent.parent.parent / "main.py"
        spec = importlib.util.spec_from_file_location("main_module", main_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.ContextualTranscriber
        else:
            raise ImportError("Could not load main module")
    except Exception as e:
        # Fallback - try transcribe module with VoiceTranscriber
        try:
            import importlib.util
            transcribe_path = Path(__file__).parent.parent.parent / "transcribe.py"
            spec = importlib.util.spec_from_file_location("transcribe_module", transcribe_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module.VoiceTranscriber  # Use VoiceTranscriber as fallback
            else:
                raise ImportError("Could not find any transcriber class")
        except Exception as e2:
            raise ImportError(f"Could not find ContextualTranscriber: {e}, fallback failed: {e2}")

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Service for handling audio transcription and processing"""
    
    def __init__(self):
        """Initialize transcription service"""
        self.db_service = db_service
        logger.info("Transcription service initialized")
    
    def process_audio_file(self, audio_data: bytes, audio_filename: str, 
                          session_details: Dict[str, Any], 
                          model_size: str = "tiny") -> Dict[str, Any]:
        """
        Process uploaded audio file and return transcription results
        
        Args:
            audio_data: Raw audio file data
            audio_filename: Original filename
            session_details: Session metadata
            model_size: Whisper model size to use
            
        Returns:
            Dictionary with session data and processing results
        """
        session_id = None
        temp_path = None
        
        try:
            # Create session object
            session = Session(
                patient_name=session_details['patient_name'],
                doctor_name=session_details['doctor_name'],
                session_date=session_details['session_date'],
                audio_filename=audio_filename,
                audio_data=audio_data,
                file_size=len(audio_data),
                session_notes=session_details.get('session_notes', ''),
                model_used=model_size,
                status=SessionStatus.PENDING
            )
            
            # Save session to database
            session_id = self.db_service.save_session(session)
            session.id = session_id
            
            logger.info(f"Created session {session_id} for patient {session.patient_name}")
            
            # Update status to processing
            self.db_service.update_session_status(session_id, SessionStatus.PROCESSING)
            
            # Save audio to temporary file for processing
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_file.write(audio_data)
                temp_path = tmp_file.name
            
            logger.info(f"Processing audio file for session {session_id}")
            
            # Initialize transcriber and process
            ContextualTranscriber = get_contextual_transcriber()
            transcriber = ContextualTranscriber(model_size=model_size, audio_file=temp_path)
            chat_content, segments = transcriber.transcribe_with_context(session_id=session_id)
            
            # Create transcription result object
            transcription = TranscriptionResult(
                session_id=session_id,
                transcription_text=chat_content,
                segments_json="",  # Will be populated by segments
                speaker_mapping="",  # Will be populated by mapping
                confidence_score=self._calculate_average_confidence(segments),
                processing_time=0.0,  # Could be measured
                segments=self._convert_segments(segments)
            )
            
            # Save transcription to database
            transcription_id = self.db_service.save_transcription(transcription)
            
            # Get complete session data
            complete_session = self.db_service.get_session_by_id(session_id)
            
            logger.info(f"Successfully processed session {session_id}")
            
            return {
                'success': True,
                'session': complete_session.to_dict() if complete_session else None,
                'transcription_id': transcription_id,
                'message': 'Transcription completed successfully'
            }
            
        except Exception as e:
            logger.error(f"Error processing session {session_id}: {str(e)}")
            
            # Update session status to error if session was created
            if session_id:
                self.db_service.update_session_status(session_id, SessionStatus.ERROR)
            
            return {
                'success': False,
                'session_id': session_id,
                'error': str(e),
                'message': 'Transcription failed'
            }
            
        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                    logger.info(f"Cleaned up temporary file: {temp_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {temp_path}: {str(e)}")
    
    def _calculate_average_confidence(self, segments: List[Dict]) -> float:
        """Calculate average confidence from segments"""
        if not segments:
            return 0.0
        
        total_confidence = sum(segment.get('confidence', 0.0) for segment in segments)
        return total_confidence / len(segments)
    
    def _convert_segments(self, segments: List[Dict]) -> List[AudioSegment]:
        """Convert raw segments to AudioSegment objects"""
        audio_segments = []
        
        for i, segment in enumerate(segments):
            # Determine speaker type from segment data
            speaker_type = SpeakerType.OTHER
            if 'speaker' in segment:
                speaker_str = segment['speaker'].lower()
                if 'doctor' in speaker_str or 'dr' in speaker_str:
                    speaker_type = SpeakerType.DOCTOR
                elif 'patient' in speaker_str:
                    speaker_type = SpeakerType.PATIENT
            
            audio_segment = AudioSegment(
                speaker_type=speaker_type,
                start_time=segment.get('start', 0.0),
                end_time=segment.get('end', 0.0),
                text=segment.get('text', ''),
                confidence=segment.get('confidence', 0.0),
                segment_order=i
            )
            
            audio_segments.append(audio_segment)
        
        return audio_segments
    
    def get_session_with_transcription(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get complete session data with transcription"""
        try:
            session = self.db_service.get_session_by_id(session_id)
            if not session:
                return None
            
            return session.to_dict()
            
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {str(e)}")
            return None
    
    def validate_audio_file(self, audio_filename: str, audio_size: int) -> Dict[str, Any]:
        """Validate uploaded audio file"""
        file_path = Path(audio_filename)
        file_extension = file_path.suffix.lower()
        
        # Check file format
        if file_extension not in current_config.SUPPORTED_AUDIO_FORMATS:
            return {
                'valid': False,
                'error': f"Unsupported file format. Supported formats: {', '.join(current_config.SUPPORTED_AUDIO_FORMATS)}"
            }
        
        # Check file size
        max_size_bytes = current_config.MAX_AUDIO_SIZE_MB * 1024 * 1024
        if audio_size > max_size_bytes:
            return {
                'valid': False,
                'error': f"File size too large. Maximum size: {current_config.MAX_AUDIO_SIZE_MB}MB"
            }
        
        return {'valid': True}
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported transcription models"""
        return current_config.AVAILABLE_MODELS
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        try:
            stats = self.db_service.get_stats()
            
            # Add additional processing metrics
            stats.update({
                'supported_formats': current_config.SUPPORTED_AUDIO_FORMATS,
                'available_models': current_config.AVAILABLE_MODELS,
                'max_file_size_mb': current_config.MAX_AUDIO_SIZE_MB
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error retrieving processing stats: {str(e)}")
            return {}


# Global transcription service instance
transcription_service = TranscriptionService() 