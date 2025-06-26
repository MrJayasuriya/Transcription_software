"""
Services module for MedTranscribe application
"""

from .database_service import DatabaseService, db_service

# Note: TranscriptionService imports are avoided here to prevent circular dependencies
# Import transcription_service directly where needed

__all__ = [
    'DatabaseService',
    'db_service'
] 