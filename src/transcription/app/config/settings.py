"""
Application Configuration Settings
"""
import os
from pathlib import Path
from typing import Dict, Any
import logging

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
LOGS_DIR = BASE_DIR / "logs"
DB_DIR = BASE_DIR

# Ensure directories exist
for directory in [DATA_DIR, AUDIO_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True)

class Config:
    """Base configuration class"""
    
    # Application settings
    APP_NAME = "MedTranscribe"
    APP_VERSION = "1.0.0"
    DEBUG = False
    
    # Database settings
    DATABASE_URL = str(DB_DIR / "transcriptions.db")
    DATABASE_ECHO = False
    
    # Audio processing settings
    SUPPORTED_AUDIO_FORMATS = ['.mp3', '.wav', '.m4a', '.mp4']
    MAX_AUDIO_SIZE_MB = 100
    DEFAULT_MODEL_SIZE = "tiny"
    AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large"]
    
    # Transcription settings
    CONTINUITY_THRESHOLD_SECONDS = 3.0
    CONFIDENCE_THRESHOLD = 0.8
    MAX_SEGMENTS_PER_SESSION = 1000
    
    # UI settings
    PAGE_TITLE = "MedTranscribe - AI Medical Transcription"
    PAGE_ICON = "🏥"
    LAYOUT = "wide"
    INITIAL_SIDEBAR_STATE = "expanded"
    
    # Security settings
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Logging settings
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = str(LOGS_DIR / "app.log")
    
    # API settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    LLM_MODEL = "gpt-3.5-turbo"
    LLM_TEMPERATURE = 0.3
    LLM_MAX_TOKENS = 500
    
    # Performance settings
    MAX_WORKERS = 4
    TIMEOUT_SECONDS = 300
    RETRY_ATTEMPTS = 3
    
    # File paths
    TEMP_DIR = DATA_DIR / "temp"
    UPLOADS_DIR = DATA_DIR / "uploads"
    EXPORTS_DIR = DATA_DIR / "exports"
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith('_') and not callable(getattr(cls, key))
        }

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    DATABASE_ECHO = True
    LOG_LEVEL = "DEBUG"

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    LOG_LEVEL = "WARNING"
    DATABASE_ECHO = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    DATABASE_URL = ":memory:"
    LOG_LEVEL = "DEBUG"

# Configuration mapping
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name: str = None) -> Config:
    """Get configuration class based on environment"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    
    return config_map.get(config_name, DevelopmentConfig)

# Current configuration instance
current_config = get_config() 