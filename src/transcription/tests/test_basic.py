"""
Basic tests for MedTranscribe application
"""
import unittest
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import Config, current_config
from app.models import Session, SessionStatus, SpeakerType
from app.utils import format_file_size, format_duration


class TestBasicFunctionality(unittest.TestCase):
    """Test basic application functionality"""
    
    def test_config_loading(self):
        """Test configuration loading"""
        self.assertIsNotNone(current_config)
        self.assertEqual(current_config.APP_NAME, "MedTranscribe")
        self.assertEqual(current_config.APP_VERSION, "1.0.0")
    
    def test_session_model(self):
        """Test Session model functionality"""
        session = Session(
            patient_name="Test Patient",
            doctor_name="Dr. Test",
            session_date="2024-01-01",
            audio_filename="test.mp3"
        )
        
        self.assertEqual(session.patient_name, "Test Patient")
        self.assertEqual(session.doctor_name, "Dr. Test")
        self.assertEqual(session.status, SessionStatus.PENDING)
        self.assertTrue(session.is_processing is False)
        self.assertTrue(session.is_completed is False)
    
    def test_utility_functions(self):
        """Test utility functions"""
        # Test file size formatting
        self.assertEqual(format_file_size(1024), "1.0 KB")
        self.assertEqual(format_file_size(1048576), "1.0 MB")
        
        # Test duration formatting
        self.assertEqual(format_duration(60), "01:00")
        self.assertEqual(format_duration(125), "02:05")
    
    def test_speaker_types(self):
        """Test speaker type enum"""
        self.assertEqual(SpeakerType.DOCTOR.value, "doctor")
        self.assertEqual(SpeakerType.PATIENT.value, "patient")


class TestModelValidation(unittest.TestCase):
    """Test model validation and serialization"""
    
    def test_session_to_dict(self):
        """Test session serialization"""
        session = Session(
            patient_name="Test Patient",
            doctor_name="Dr. Test",
            session_date="2024-01-01",
            audio_filename="test.mp3",
            file_size=1024000
        )
        
        session_dict = session.to_dict()
        
        self.assertIsInstance(session_dict, dict)
        self.assertEqual(session_dict['patient_name'], "Test Patient")
        self.assertEqual(session_dict['file_size_mb'], 0.98)  # ~1MB
        self.assertIn('status', session_dict)


if __name__ == '__main__':
    unittest.main() 