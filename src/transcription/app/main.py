"""
Main Streamlit application for MedTranscribe
"""
import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.config import current_config
from app.utils import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)


def configure_streamlit():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title=current_config.PAGE_TITLE,
        page_icon=current_config.PAGE_ICON,
        layout=current_config.LAYOUT,
        initial_sidebar_state=current_config.INITIAL_SIDEBAR_STATE
    )
    
    # Custom CSS for medical theme
    st.markdown("""
    <style>
    .main > div {
        padding-top: 2rem;
    }
    
    .stAlert {
        margin-top: 1rem;
    }
    
    .metric-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #007bff;
    }
    
    .chat-container {
        background-color: #f0f0f0;
        padding: 20px;
        border-radius: 10px;
        height: 60vh;
        overflow-y: auto;
        background-image: 
            radial-gradient(circle at 20px 80px, #e8e8e8 1px, transparent 1px),
            radial-gradient(circle at 80px 20px, #e8e8e8 1px, transparent 1px);
        background-size: 100px 100px;
    }
    
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    
    /* Hide Streamlit style */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    </style>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Render application sidebar with navigation"""
    with st.sidebar:
        st.title("🏥 MedTranscribe")
        st.markdown(f"*Version {current_config.APP_VERSION}*")
        
        st.divider()
        
        # Navigation
        page = st.selectbox(
            "📍 Navigate",
            options=["Dashboard", "Transcription"],
            index=0,
            key="navigation"
        )
        
        st.divider()
        
        # App info
        st.markdown("### ℹ️ About")
        st.markdown("""
        **MedTranscribe** is an AI-powered medical transcription system that:
        
        • 🎙️ Transcribes medical conversations
        • 🤖 Identifies speakers automatically  
        • 💾 Stores sessions securely
        • 📊 Provides conversation analytics
        """)
        
        st.divider()
        
        # System status
        st.markdown("### 📊 System Status")
        try:
            from app.services.database_service import db_service
            stats = db_service.get_stats()
            st.metric("Total Sessions", stats.get('total_sessions', 0))
            st.metric("This Month", stats.get('this_month', 0))
            st.success("🟢 System Online")
        except Exception as e:
            st.error("🔴 Database Error")
            logger.error(f"Sidebar stats error: {str(e)}")
        
        return page


def main():
    """Main application function"""
    try:
        # Configure Streamlit
        configure_streamlit()
        
        # Render sidebar and get selected page
        selected_page = render_sidebar()
        
        # Route to appropriate page
        if selected_page == "Dashboard":
            from app.pages.dashboard import render_dashboard
            render_dashboard()
        elif selected_page == "Transcription":
            from app.pages.transcription import render_transcription_page
            render_transcription_page()
        else:
            # Default to dashboard
            from app.pages.dashboard import render_dashboard
            render_dashboard()
    
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error("An unexpected error occurred. Please refresh the page.")
        
        if current_config.DEBUG:
            st.exception(e)


if __name__ == "__main__":
    main() 