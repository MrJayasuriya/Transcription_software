#!/usr/bin/env python3
"""
Startup script for MedTranscribe Streamlit App
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_environment():
    """Setup environment and dependencies"""
    print("🏥 MedTranscribe - Setting up environment...")
    
    # Check if required files exist
    current_dir = Path(__file__).parent
    required_files = ['main.py', 'transcribe.py', 'llm_services.py', 'streamlit_app.py']
    
    for file in required_files:
        if not (current_dir / file).exists():
            print(f"❌ Required file missing: {file}")
            return False
    
    # Check environment variables
    if not os.getenv('OPENROUTER_API_KEY'):
        print("⚠️  Warning: OPENROUTER_API_KEY not found in environment")
        print("   Please set it in your .env file or environment variables")
    
    print("✅ Environment check completed")
    return True

def run_streamlit():
    """Run the Streamlit application"""
    if not setup_environment():
        sys.exit(1)
    
    print("🚀 Starting MedTranscribe...")
    print("📱 Opening in your browser at http://localhost:8501")
    print("🛑 Press Ctrl+C to stop")
    
    # Run streamlit with optimized settings
    cmd = [
        sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
        "--server.port=8501",
        "--server.address=localhost", 
        "--browser.gatherUsageStats=false",
        "--theme.primaryColor=#0ea5e9",
        "--theme.backgroundColor=#ffffff",
        "--theme.secondaryBackgroundColor=#f0f9ff",
        "--theme.textColor=#1f2937"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 MedTranscribe stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Streamlit: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_streamlit() 