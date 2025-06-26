import whisper
import os
import subprocess
import sys
import torch
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings("ignore")

class VoiceTranscriber:
    """
    Voice transcription system with speaker diarization for medical consultations.
    Identifies doctor vs patient speech and formats as chat-based transcriptions.
    """
    
    def __init__(self, model_size: str = "tiny", audio_file: str = "call_data.mp3"):
        self.model_size = model_size
        self.audio_file = self._resolve_audio_path(audio_file)
        self.whisper_model = None
        self.speakers = {
            'SPEAKER_00': 'Person 1',
            'SPEAKER_01': 'Person 2'
        }
        self._ensure_dependencies()
        self._load_models()
    
    def _resolve_audio_path(self, audio_file: str) -> str:
        """Resolve audio file path relative to script location"""
        if os.path.isabs(audio_file):
            return audio_file
        return os.path.join(os.path.dirname(__file__), audio_file)
    
    def _ensure_dependencies(self) -> None:
        """Check and ensure all required dependencies are available"""
        if not self._check_ffmpeg():
            self._handle_missing_ffmpeg()
        
        if not os.path.exists(self.audio_file):
            raise FileNotFoundError(f"Audio file not found: {self.audio_file}")
    
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available"""
        # Check for local ffmpeg.exe
        local_ffmpeg = os.path.join(os.path.dirname(__file__), "ffmpeg.exe")
        if os.path.exists(local_ffmpeg):
            return True
        
        # Check conda's ffmpeg installation
        conda_ffmpeg = os.path.join(os.path.expanduser("~"), "anaconda3", "Library", "bin", "ffmpeg.exe")
        if os.path.exists(conda_ffmpeg):
            conda_bin = os.path.dirname(conda_ffmpeg)
            if conda_bin not in os.environ.get("PATH", ""):
                os.environ["PATH"] = conda_bin + os.pathsep + os.environ.get("PATH", "")
            return True
        
        # Check system PATH
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _handle_missing_ffmpeg(self) -> None:
        """Handle missing ffmpeg dependency"""
        print("FFmpeg is required but not found. Please install it:")
        print("1. Download from: https://ffmpeg.org/download.html")
        print("2. Or use chocolatey: choco install ffmpeg")
        print("3. Or use conda: conda install ffmpeg")
        print("4. Make sure ffmpeg is in your PATH")
        sys.exit(1)
    
    def _load_models(self) -> None:
        """Load Whisper model for transcription"""
        try:
            print(f"Loading Whisper model: {self.model_size}")
            self.whisper_model = whisper.load_model(self.model_size)
            print("✅ Models loaded successfully")
        except Exception as e:
            print(f"❌ Error loading models: {e}")
            sys.exit(1)
    
    def _transcribe_audio(self) -> Dict:
        """Transcribe audio using Whisper with word-level timestamps"""
        try:
            print("🎵 Transcribing audio...")
            result = self.whisper_model.transcribe(
                self.audio_file,
                word_timestamps=True,
                verbose=False
            )
            print("✅ Transcription completed")
            return result
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            raise
    
    def _perform_speaker_diarization(self, transcription_result: Dict) -> List[Dict]:
        """
        Perform simple speaker diarization based on audio characteristics
        In a real implementation, you'd use pyannote.audio or similar
        """
        segments = []
        
        # Extract segments with word-level timestamps
        if 'segments' in transcription_result:
            for i, segment in enumerate(transcription_result['segments']):
                # Simple speaker assignment based on segment patterns
                # In reality, you'd use voice embeddings and clustering
                speaker_id = f"SPEAKER_{i % 2:02d}"  # Alternating speakers for demo
                
                segments.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'].strip(),
                    'speaker': self.speakers.get(speaker_id, f'Speaker {i % 2 + 1}'),
                    'confidence': segment.get('avg_logprob', 0.0)
                })
        
        return segments
    
    def _detect_speaker_continuity(self, segments: List[Dict]) -> List[Dict]:
        """Detect when segments belong to the same speaker vs actual speaker changes"""
        
        if not segments:
            return segments
            
        # First, group segments that are likely from the same speaker
        grouped_segments = []
        current_group = [segments[0]]
        
        for i in range(1, len(segments)):
            prev_segment = segments[i-1]
            curr_segment = segments[i]
            
            # Check if this segment continues the previous one
            time_gap = curr_segment['start'] - prev_segment['end']
            prev_text = prev_segment['text'].strip()
            curr_text = curr_segment['text'].strip()
            
            # Indicators that it's the same speaker continuing:
            # 1. Short time gap (< 3 seconds)
            # 2. Previous text ends mid-sentence (no period, question mark, etc.)
            # 3. Current text starts with lowercase or connecting word
            
            is_continuation = (
                time_gap < 3.0 and (
                    not prev_text.endswith(('.', '!', '?')) or
                    curr_text.lower().startswith(('and', 'but', 'so', 'because', 'or', 'that', 'which', 'who'))
                )
            )
            
            if is_continuation:
                current_group.append(curr_segment)
            else:
                grouped_segments.append(current_group)
                current_group = [curr_segment]
        
        # Add the last group
        grouped_segments.append(current_group)
        
        # Now merge segments within each group and assign speakers
        merged_segments = []
        current_speaker_id = 0
        
        for group in grouped_segments:
            # Merge all segments in the group
            merged_text = " ".join(seg['text'].strip() for seg in group)
            merged_segment = {
                'start': group[0]['start'],
                'end': group[-1]['end'],
                'text': merged_text,
                'speaker': f'Speaker_{current_speaker_id}',
                'confidence': sum(seg.get('confidence', 0) for seg in group) / len(group)
            }
            merged_segments.append(merged_segment)
            current_speaker_id = 1 - current_speaker_id  # Alternate between 0 and 1
        
        return merged_segments

    def _analyze_speaker_context(self, segments: List[Dict]) -> Dict[str, str]:
        """Use LLM to analyze conversation and identify doctor vs patient"""
        
        # Create conversation text for analysis
        conversation_text = ""
        for i, segment in enumerate(segments):
            speaker_id = f"Speaker_{i % 2}"
            text = segment['text']
            conversation_text += f"{speaker_id}: {text}\n"
        
        # LLM prompt to analyze the conversation
        analysis_prompt = f"""
        Analyze this medical conversation transcript. The speakers have been automatically grouped by voice continuity.
        
        Identify which speaker is the DOCTOR and which is the PATIENT based on content:

        Transcript:
        {conversation_text}

        Look for these indicators:
        - PATIENT: Describes symptoms, says "Dr." or "Doctor", asks for help, mentions personal feelings/issues
        - DOCTOR: Asks diagnostic questions, provides medical advice, suggests treatments, uses clinical language

        Respond with ONLY this format:
        PATIENT: Speaker_0
        DOCTOR: Speaker_1

        Or:
        PATIENT: Speaker_1  
        DOCTOR: Speaker_0
        """
        
        try:
            # Try to import and use LLM service
            from llm_services import generate_response
            response = generate_response(analysis_prompt)
            print(f"🤖 LLM Analysis: {response.strip()}")
            
            # Parse the response
            mapping = {}
            for line in response.strip().split('\n'):
                if 'PATIENT:' in line:
                    patient_speaker = line.split('PATIENT:')[1].strip()
                    mapping['patient'] = patient_speaker
                elif 'DOCTOR:' in line:
                    doctor_speaker = line.split('DOCTOR:')[1].strip()
                    mapping['doctor'] = doctor_speaker
            
            return mapping
            
        except Exception as e:
            print(f"❌ LLM analysis failed: {e}")
            # Fallback to simple keyword analysis
            return self._fallback_speaker_analysis(segments)
    
    def _fallback_speaker_analysis(self, segments: List[Dict]) -> Dict[str, str]:
        """Fallback method using keyword analysis"""
        speaker_scores = {'Person 1': 0, 'Person 2': 0}
        
        patient_keywords = ['dr.', 'doctor', 'feeling', 'anxious', 'trouble', 'sleeping', 'symptoms', 'help', 'nervous']
        doctor_keywords = ['thank you for sharing', 'sounds like', 'experienced', 'therapy', 'medication', 'refer', 'monitor']
        
        for segment in segments:
            text = segment['text'].lower()
            speaker = segment['speaker']
            
            patient_score = sum(1 for keyword in patient_keywords if keyword in text)
            doctor_score = sum(1 for keyword in doctor_keywords if keyword in text)
            
            if patient_score > doctor_score:
                speaker_scores[speaker] += patient_score
            elif doctor_score > patient_score:
                speaker_scores[speaker] -= doctor_score
        
        # Determine roles based on scores
        sorted_speakers = sorted(speaker_scores.items(), key=lambda x: x[1], reverse=True)
        patient_speaker = sorted_speakers[0][0]  # Higher score = more patient-like
        doctor_speaker = sorted_speakers[1][0]
        
        return {'patient': patient_speaker, 'doctor': doctor_speaker}
    
    def _remap_speakers(self, segments: List[Dict], speaker_mapping: Dict[str, str]) -> List[Dict]:
        """Remap speaker labels based on context analysis"""
        for segment in segments:
            current_speaker = segment['speaker']
            if current_speaker == speaker_mapping.get('patient'):
                segment['speaker'] = 'Patient'
                segment['role'] = 'patient'
            elif current_speaker == speaker_mapping.get('doctor'):
                segment['speaker'] = 'Doctor'
                segment['role'] = 'doctor'
        
        return segments
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format timestamp from seconds to MM:SS format"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _generate_chat_format(self, segments: List[Dict]) -> str:
        """Generate chat-based transcription format"""
        chat_output = []
        chat_output.append("=" * 60)
        chat_output.append("🏥 MEDICAL CONSULTATION TRANSCRIPTION")
        chat_output.append("=" * 60)
        chat_output.append(f"📁 File: {os.path.basename(self.audio_file)}")
        chat_output.append(f"⏰ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        chat_output.append("=" * 60)
        
        current_speaker = None
        for segment in segments:
            timestamp = self._format_timestamp(segment['start'])
            speaker = segment['speaker']
            text = segment['text']
            
            # Add speaker change indicator
            if speaker != current_speaker:
                chat_output.append("")
                icon = "👨‍💼" if speaker == "Person 1" else "🧑‍🤝‍🧑"
                chat_output.append(f"{icon} {speaker.upper()} [{timestamp}]:")
                current_speaker = speaker
            
            # Add the text with proper indentation
            chat_output.append(f"   {text}")
        
        chat_output.append("")
        chat_output.append("=" * 60)
        chat_output.append("📊 TRANSCRIPTION COMPLETE")
        chat_output.append("=" * 60)
        
        return "\n".join(chat_output)
    
    def _generate_contextual_chat_format(self, segments: List[Dict]) -> str:
        """Generate chat format with correct speaker identification"""
        chat_output = []
        chat_output.append("=" * 60)
        chat_output.append("🏥 MEDICAL CONSULTATION TRANSCRIPTION")
        chat_output.append("=" * 60)
        chat_output.append(f"📁 File: {os.path.basename(self.audio_file)}")
        chat_output.append(f"⏰ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        chat_output.append("🤖 Speaker identification: AI-Enhanced")
        chat_output.append("=" * 60)
        
        current_speaker = None
        for segment in segments:
            timestamp = self._format_timestamp(segment['start'])
            speaker = segment['speaker']
            text = segment['text']
            
            # Add speaker change indicator
            if speaker != current_speaker:
                chat_output.append("")
                icon = "👨‍⚕️" if speaker == "Doctor" else "🧑‍🤝‍🧑"
                chat_output.append(f"{icon} {speaker.upper()} [{timestamp}]:")
                current_speaker = speaker
            
            # Add the text with proper indentation
            chat_output.append(f"   {text}")
        
        chat_output.append("")
        chat_output.append("=" * 60)
        chat_output.append("📊 TRANSCRIPTION COMPLETE")
        chat_output.append("=" * 60)
        
        return "\n".join(chat_output)
    
    def _save_transcription(self, chat_content: str) -> str:
        """Save transcription to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcription_{timestamp}.txt"
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(chat_content)
            print(f"💾 Transcription saved: {filename}")
            return filepath
        except Exception as e:
            print(f"❌ Error saving file: {e}")
            return ""
    
    def transcribe_conversation(self, save_to_file: bool = True) -> Tuple[str, Optional[str]]:
        """
        Main method to transcribe conversation with speaker diarization
        
        Returns:
            Tuple of (chat_formatted_text, file_path_if_saved)
        """
        try:
            # Step 1: Transcribe audio
            transcription_result = self._transcribe_audio()
            
            # Step 2: Perform speaker diarization
            print("🎭 Identifying speakers...")
            segments = self._perform_speaker_diarization(transcription_result)
            
            # Step 3: Format as chat
            print("💬 Formatting chat transcription...")
            chat_content = self._generate_chat_format(segments)
            
            # Step 4: Save to file if requested
            filepath = None
            if save_to_file:
                filepath = self._save_transcription(chat_content)
            
            return chat_content, filepath
            
        except Exception as e:
            error_msg = f"❌ Transcription failed: {e}"
            print(error_msg)
            return error_msg, None
    
    def transcribe_with_context(self, session_id: int = None, save_to_file: bool = False) -> Tuple[str, List[Dict]]:
        """Main method with contextual speaker identification"""
        try:
            start_time = datetime.now()
            
            # Step 1: Basic transcription
            transcription_result = self._transcribe_audio()
            
            # Step 2: Initial speaker diarization  
            print("🎭 Initial speaker segmentation...")
            segments = self._perform_speaker_diarization(transcription_result)
            
            # Step 3: Detect speaker continuity (merge segments from same speaker)
            print("🔗 Detecting speaker continuity...")
            segments = self._detect_speaker_continuity(segments)
            
            # Step 4: Context analysis using LLM
            print("🤖 Analyzing conversation context...")
            speaker_mapping = self._analyze_speaker_context(segments)
            
            # Step 5: Remap speakers based on context
            print("🔄 Remapping speakers based on context...")
            segments = self._remap_speakers(segments, speaker_mapping)
            
            # Step 6: Generate formatted output
            print("💬 Generating contextual transcription...")
            chat_content = self._generate_contextual_chat_format(segments)
            
            # Step 7: Save to database if session_id provided
            if session_id:
                try:
                    from database import db
                    processing_time = (datetime.now() - start_time).total_seconds()
                    confidence_score = sum(seg.get('confidence', 0) for seg in segments) / len(segments) if segments else 0
                    
                    print("💾 Saving to database...")
                    db.save_transcription(
                        session_id=session_id,
                        transcription_text=chat_content,
                        segments=segments,
                        speaker_mapping=speaker_mapping,
                        confidence_score=confidence_score,
                        processing_time=processing_time
                    )
                    db.update_session_status(session_id, 'completed')
                except ImportError:
                    print("⚠️ Database module not available, skipping database save")
                except Exception as e:
                    print(f"⚠️ Database save failed: {e}")
            
            # Legacy file save if requested
            if save_to_file:
                self._save_transcription(chat_content)
            
            return chat_content, segments
            
        except Exception as e:
            error_msg = f"❌ Contextual transcription failed: {e}"
            print(error_msg)
            if session_id:
                try:
                    from database import db
                    db.update_session_status(session_id, 'error')
                except:
                    pass
            return error_msg, []
    
    def get_conversation_summary(self, segments: List[Dict]) -> Dict:
        """Generate conversation summary statistics"""
        total_duration = max([seg['end'] for seg in segments]) if segments else 0
        speaker_stats = {}
        
        for segment in segments:
            speaker = segment['speaker']
            duration = segment['end'] - segment['start']
            
            if speaker not in speaker_stats:
                speaker_stats[speaker] = {
                    'total_time': 0,
                    'word_count': 0,
                    'segments': 0
                }
            
            speaker_stats[speaker]['total_time'] += duration
            speaker_stats[speaker]['word_count'] += len(segment['text'].split())
            speaker_stats[speaker]['segments'] += 1
        
        return {
            'total_duration': total_duration,
            'speaker_stats': speaker_stats,
            'total_segments': len(segments)
        }


class ContextualTranscriber(VoiceTranscriber):
    """
    Enhanced transcriber that uses LLM to correctly identify speakers based on context
    This is an alias for the enhanced VoiceTranscriber class
    """
    
    def __init__(self, model_size: str = "tiny", audio_file: str = "call_data.mp3"):
        super().__init__(model_size, audio_file)


class LiveTranscriber(VoiceTranscriber):
    """
    Extended class for live/real-time transcription capabilities
    """
    
    def __init__(self, model_size: str = "tiny"):
        # Initialize without audio file for live transcription
        self.model_size = model_size
        self.whisper_model = None
        self.speakers = {
            'SPEAKER_00': 'Person 1',
            'SPEAKER_01': 'Person 2'
        }
        self.conversation_buffer = []
        self.current_speakers = {}
        self._ensure_dependencies_live()
        self._load_models()
    
    def _ensure_dependencies_live(self) -> None:
        """Check dependencies for live transcription"""
        if not self._check_ffmpeg():
            self._handle_missing_ffmpeg()
    
    def transcribe_audio_chunk(self, audio_chunk_path: str) -> str:
        """Transcribe a single audio chunk for live processing"""
        try:
            result = self.whisper_model.transcribe(audio_chunk_path, verbose=False)
            return result['text'].strip()
        except Exception as e:
            return f"Error: {e}"
    
    def process_live_audio(self, audio_chunks: List[str]) -> str:
        """Process multiple audio chunks for live transcription"""
        live_output = []
        live_output.append("🔴 LIVE TRANSCRIPTION")
        live_output.append("-" * 40)
        
        for i, chunk_path in enumerate(audio_chunks):
            if os.path.exists(chunk_path):
                text = self.transcribe_audio_chunk(chunk_path)
                speaker = "Person 1" if i % 2 == 0 else "Person 2"
                icon = "👨‍💼" if speaker == "Person 1" else "🧑‍🤝‍🧑"
                
                live_output.append(f"\n{icon} {speaker}: {text}")
        
        return "\n".join(live_output)
    
    def process_audio_chunk(self, audio_chunk_path: str) -> Dict:
        """Process a single audio chunk in real-time"""
        try:
            # Transcribe the chunk
            result = self.whisper_model.transcribe(audio_chunk_path, word_timestamps=True, verbose=False)
            
            if 'segments' in result:
                for segment in result['segments']:
                    # Add to conversation buffer
                    self.conversation_buffer.append({
                        'start': segment['start'],
                        'end': segment['end'], 
                        'text': segment['text'].strip(),
                        'timestamp': datetime.now()
                    })
                
                # Analyze buffer for speaker continuity and context
                if len(self.conversation_buffer) >= 2:
                    return self._analyze_realtime_speakers()
            
            return {"status": "processing", "segments": self.conversation_buffer}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _analyze_realtime_speakers(self) -> Dict:
        """Analyze speakers in real-time based on accumulated segments"""
        
        # Group recent segments by continuity
        recent_segments = self.conversation_buffer[-10:]  # Last 10 segments
        grouped = self._detect_speaker_continuity(recent_segments)
        
        # Quick LLM analysis for speaker identification
        if len(grouped) >= 2:
            speaker_mapping = self._analyze_speaker_context(grouped)
            grouped = self._remap_speakers(grouped, speaker_mapping)
        
        return {
            "status": "active",
            "current_segments": grouped,
            "total_segments": len(self.conversation_buffer)
        }


class RealTimeTranscriber(ContextualTranscriber):
    """Real-time transcriber with dynamic speaker detection"""
    
    def __init__(self, model_size: str = "tiny"):
        self.model_size = model_size
        self.whisper_model = None
        self.conversation_buffer = []
        self.current_speakers = {}
        self._load_models()
    
    def process_audio_chunk(self, audio_chunk_path: str) -> Dict:
        """Process a single audio chunk in real-time"""
        try:
            # Transcribe the chunk
            result = self.whisper_model.transcribe(audio_chunk_path, word_timestamps=True, verbose=False)
            
            if 'segments' in result:
                for segment in result['segments']:
                    # Add to conversation buffer
                    self.conversation_buffer.append({
                        'start': segment['start'],
                        'end': segment['end'], 
                        'text': segment['text'].strip(),
                        'timestamp': datetime.now()
                    })
                
                # Analyze buffer for speaker continuity and context
                if len(self.conversation_buffer) >= 2:
                    return self._analyze_realtime_speakers()
            
            return {"status": "processing", "segments": self.conversation_buffer}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _analyze_realtime_speakers(self) -> Dict:
        """Analyze speakers in real-time based on accumulated segments"""
        
        # Group recent segments by continuity
        recent_segments = self.conversation_buffer[-10:]  # Last 10 segments
        grouped = self._detect_speaker_continuity(recent_segments)
        
        # Quick LLM analysis for speaker identification
        if len(grouped) >= 2:
            speaker_mapping = self._analyze_speaker_context(grouped)
            grouped = self._remap_speakers(grouped, speaker_mapping)
        
        return {
            "status": "active",
            "current_segments": grouped,
            "total_segments": len(self.conversation_buffer)
        }


def test_with_existing_file():
    """Test with existing transcription file to validate approach"""
    print("🧪 Testing speaker continuity detection...")
    
    # Sample from your file (the problematic case)
    test_segments = [
        {
            'start': 0.0,
            'end': 5.5,
            'text': "Hi, Dr. I've been feeling really anxious lately. I have trouble sleeping. My thoughts are racing at night,",
            'speaker': 'Person 1'
        },
        {
            'start': 6.0,
            'end': 9.0,
            'text': "and I often feel overwhelmed even with small tasks.",
            'speaker': 'Person 2'  # This is wrong - should be same speaker
        },
        {
            'start': 9.5,
            'end': 14.0,
            'text': "Thank you for sharing that. It sounds like you're dealing with significant anxiety symptoms.",
            'speaker': 'Person 1'  # This should be doctor
        }
    ]
    
    transcriber = ContextualTranscriber()
    
    # Test continuity detection
    print("Before continuity detection:")
    for seg in test_segments:
        print(f"  {seg['speaker']}: {seg['text']}")
    
    corrected = transcriber._detect_speaker_continuity(test_segments)
    
    print("\nAfter continuity detection:")
    for seg in corrected:
        print(f"  {seg['speaker']}: {seg['text']}")
    
    # Test context analysis
    mapping = transcriber._analyze_speaker_context(corrected)
    print(f"\nLLM Speaker Mapping: {mapping}")
    
    final = transcriber._remap_speakers(corrected, mapping)
    
    print("\nFinal result:")
    for seg in final:
        print(f"  {seg['speaker']}: {seg['text']}")


def main():
    """Main function demonstrating usage"""
    try:
        # Create transcriber instance
        transcriber = ContextualTranscriber(model_size="tiny")
        
        # Perform transcription with speaker diarization
        chat_content, saved_file = transcriber.transcribe_conversation(save_to_file=True)
        
        # Display results
        print("\n" + chat_content)
        
        if saved_file:
            print(f"\n📄 Full transcription saved to: {saved_file}")
        
    except Exception as e:
        print(f"❌ Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
