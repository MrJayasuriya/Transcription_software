"""
Dashboard page for MedTranscribe application
"""
import streamlit as st
from datetime import datetime
from typing import Dict, Any

from ..services.database_service import db_service
from ..components import render_stats_cards, render_session_card
from ..utils import get_logger

logger = get_logger(__name__)


def render_dashboard():
    """Render the main dashboard page"""
    st.title("🏥 MedTranscribe Dashboard")
    
    try:
        # Get statistics
        stats = db_service.get_stats()
        
        # Render stats cards
        render_stats_cards(stats)
        
        st.divider()
        
        # Recent sessions section
        col1, col2 = st.columns([2.5, 1.5])
        
        with col1:
            st.subheader("📋 Recent Sessions")
            
            # Get recent sessions (last 10)
            from ..models import SessionFilter
            recent_filter = SessionFilter(limit=10, offset=0)
            recent_sessions = db_service.get_sessions(recent_filter)
            
            if recent_sessions:
                for session in recent_sessions:
                    session_dict = session.to_dict()
                    if render_session_card(session_dict, show_audio=False):
                        # Handle session selection
                        st.switch_page("pages/transcription.py")
            else:
                st.info("No sessions found. Upload your first audio file to get started!")
        
        with col2:
            st.subheader("📊 Quick Analytics")
            
            # Additional analytics
            render_quick_analytics()
    
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}")
        st.error("Failed to load dashboard data. Please try refreshing the page.")


def render_quick_analytics():
    """Render quick analytics section"""
    try:
        # Get additional statistics
        from ..models import SessionFilter, SessionStatus
        
        # This week's sessions
        this_week_filter = SessionFilter(date_filter="last_7_days", limit=100)
        this_week_sessions = db_service.get_sessions(this_week_filter)
        
        # Completed vs pending
        completed_filter = SessionFilter(status=SessionStatus.COMPLETED, limit=100)
        completed_sessions = db_service.get_sessions(completed_filter)
        
        pending_filter = SessionFilter(status=SessionStatus.PENDING, limit=100)
        pending_sessions = db_service.get_sessions(pending_filter)
        
        # Display metrics
        st.metric("📅 This Week", len(this_week_sessions))
        st.metric("✅ Completed", len(completed_sessions))
        st.metric("⏳ Pending", len(pending_sessions))
        
        # Processing status pie chart
        if len(completed_sessions) > 0 or len(pending_sessions) > 0:
            st.markdown("**Processing Status**")
            completed_pct = len(completed_sessions) / (len(completed_sessions) + len(pending_sessions)) * 100
            st.progress(completed_pct / 100)
            st.caption(f"{completed_pct:.1f}% Completed")
    
    except Exception as e:
        logger.error(f"Error rendering analytics: {str(e)}")
        st.error("Failed to load analytics data")


def render_activity_feed():
    """Render recent activity feed"""
    st.subheader("🔔 Recent Activity")
    
    try:
        # Get recent sessions with different statuses
        from ..models import SessionFilter
        
        activity_filter = SessionFilter(limit=5)
        recent_activity = db_service.get_sessions(activity_filter)
        
        if recent_activity:
            for session in recent_activity:
                activity_time = session.updated_at or session.created_at
                time_str = activity_time.strftime("%H:%M") if activity_time else "Unknown"
                
                if session.status.value == "completed":
                    st.success(f"✅ {time_str} - Completed transcription for {session.patient_name}")
                elif session.status.value == "processing":
                    st.info(f"🔄 {time_str} - Processing audio for {session.patient_name}")
                elif session.status.value == "pending":
                    st.warning(f"⏳ {time_str} - New session created for {session.patient_name}")
                elif session.status.value == "error":
                    st.error(f"❌ {time_str} - Error processing {session.patient_name}")
        else:
            st.info("No recent activity")
    
    except Exception as e:
        logger.error(f"Error rendering activity feed: {str(e)}")
        st.error("Failed to load activity data")


if __name__ == "__main__":
    render_dashboard() 