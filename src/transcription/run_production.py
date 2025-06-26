#!/usr/bin/env python3
"""
Production runner for MedTranscribe application
"""
import os
import sys
from pathlib import Path
import subprocess
import signal
import logging
from typing import Optional

# Add app directory to Python path
APP_DIR = Path(__file__).parent
sys.path.insert(0, str(APP_DIR))

from app.config import current_config, get_config
from app.utils import setup_logging


def setup_environment():
    """Setup production environment"""
    # Set environment variables for production
    os.environ['FLASK_ENV'] = 'production'
    os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
    os.environ['STREAMLIT_SERVER_ENABLE_CORS'] = 'false'
    os.environ['STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION'] = 'true'
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting MedTranscribe in production mode")
    
    return logger


def check_dependencies():
    """Check if all required dependencies are installed"""
    logger = logging.getLogger(__name__)
    
    try:
        import streamlit
        import whisper
        import openai
        import torch
        import librosa
        logger.info("All core dependencies are available")
        return True
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        print(f"❌ Missing dependency: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        return False


def check_system_requirements():
    """Check system requirements"""
    logger = logging.getLogger(__name__)
    
    # Check Python version
    if sys.version_info < (3, 8):
        logger.error("Python 3.8+ required")
        print("❌ Python 3.8+ is required")
        return False
    
    # Check available disk space (at least 1GB)
    try:
        import shutil
        free_space = shutil.disk_usage(APP_DIR).free
        if free_space < 1024 * 1024 * 1024:  # 1GB
            logger.warning("Low disk space detected")
            print("⚠️ Warning: Less than 1GB free disk space")
    except Exception as e:
        logger.warning(f"Could not check disk space: {e}")
    
    logger.info("System requirements check passed")
    return True


def run_streamlit_app(port: int = 8501, host: str = "0.0.0.0"):
    """Run the Streamlit application"""
    logger = logging.getLogger(__name__)
    
    # Streamlit command
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(APP_DIR / "streamlit_main.py"),
        "--server.port", str(port),
        "--server.address", host,
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--theme.base", "light",
        "--theme.primaryColor", "#007bff",
        "--theme.backgroundColor", "#ffffff",
        "--theme.secondaryBackgroundColor", "#f8f9fa"
    ]
    
    logger.info(f"Starting Streamlit server on {host}:{port}")
    print(f"🚀 Starting MedTranscribe on http://{host}:{port}")
    
    try:
        # Start the process
        process = subprocess.Popen(cmd, cwd=APP_DIR)
        
        # Handle graceful shutdown
        def signal_handler(sig, frame):
            logger.info("Received shutdown signal")
            print("\n🛑 Shutting down MedTranscribe...")
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Wait for process to complete
        return_code = process.wait()
        
        if return_code != 0:
            logger.error(f"Streamlit process exited with code {return_code}")
            print(f"❌ Application exited with error code {return_code}")
        
        return return_code
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        print(f"❌ Failed to start application: {e}")
        return 1


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MedTranscribe Production Runner")
    parser.add_argument("--port", type=int, default=8501, help="Port to run on (default: 8501)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--check-only", action="store_true", help="Only check system requirements")
    
    args = parser.parse_args()
    
    # Setup environment
    logger = setup_environment()
    
    print("🏥 MedTranscribe - AI Medical Transcription System")
    print("=" * 50)
    
    # Check system requirements
    print("🔍 Checking system requirements...")
    if not check_system_requirements():
        return 1
    
    print("📦 Checking dependencies...")
    if not check_dependencies():
        return 1
    
    print("✅ All checks passed!")
    
    if args.check_only:
        print("👍 System is ready to run MedTranscribe")
        return 0
    
    # Initialize database
    try:
        from app.services import db_service
        print("💾 Initializing database...")
        # Database initialization happens automatically in service
        print("✅ Database ready")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        print(f"❌ Database initialization failed: {e}")
        return 1
    
    # Start the application
    return run_streamlit_app(port=args.port, host=args.host)


if __name__ == "__main__":
    sys.exit(main()) 