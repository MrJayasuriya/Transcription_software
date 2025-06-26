# 🏥 MedTranscribe - AI Medical Transcription System

A production-ready medical transcription application with intelligent speaker detection, WhatsApp-style conversation interface, and comprehensive session management.

## ✨ Features

- 🎙️ **AI-Powered Transcription**: Uses OpenAI Whisper for accurate speech-to-text
- 🤖 **Intelligent Speaker Detection**: Automatically identifies doctor vs patient speakers
- 💬 **WhatsApp-Style Interface**: Modern chat bubbles with proper conversation flow
- 💾 **Database Integration**: SQLite database with audio storage and playback
- 📊 **Analytics Dashboard**: Real-time statistics and session management
- 🔍 **Advanced Filtering**: Date-wise filtering with calendar interface
- 📥 **Export Functionality**: Download transcriptions as formatted text files
- 🎵 **Audio Playback**: HTML5 audio player for session review
- 🔒 **Production Ready**: Proper logging, error handling, and security

## 🏗️ Architecture

The application follows a modular, production-ready architecture:

```
src/transcription/
├── app/                    # Main application package
│   ├── config/            # Configuration management
│   ├── models/            # Data models and schemas
│   ├── services/          # Business logic services
│   ├── utils/             # Utility functions
│   ├── components/        # Reusable UI components
│   ├── pages/             # Streamlit pages
│   └── main.py           # Application entry point
├── data/                  # Data storage
│   ├── audio/            # Audio file storage
│   └── exports/          # Export files
├── logs/                  # Application logs
├── tests/                 # Test suite
├── requirements.txt       # Production dependencies
├── run_production.py     # Production runner
├── Dockerfile            # Docker configuration
└── docker-compose.yml   # Docker Compose setup
```

## 🚀 Quick Start

### Method 1: Direct Python

1. **Install Dependencies**
   ```bash
   cd src/transcription
   pip install -r requirements.txt
   ```

2. **Set Environment Variables** (Optional)
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"  # For LLM features
   export SECRET_KEY="your-secret-key"          # For production security
   ```

3. **Run the Application**
   ```bash
   python run_production.py
   ```

4. **Access the Application**
   Open your browser to `http://localhost:8501`

### Method 2: Docker

1. **Build and Run**
   ```bash
   cd src/transcription
   docker-compose up --build
   ```

2. **Access the Application**
   Open your browser to `http://localhost:8501`

### Method 3: Production Docker

1. **Production with Nginx**
   ```bash
   docker-compose --profile production up --build
   ```

2. **Access via Nginx**
   Open your browser to `http://localhost`

## 📖 Usage Guide

### 1. Dashboard
- View system statistics and recent sessions
- Monitor processing status and analytics
- Quick navigation to transcription management

### 2. Transcription Management
- **Upload Audio**: Support for MP3, WAV, M4A, MP4 formats
- **Session Details**: Patient name, doctor name, session date, notes
- **Model Selection**: Choose Whisper model size (tiny to large)
- **Real-time Processing**: Live progress updates during transcription

### 3. Session Viewing
- **Audio Playback**: Built-in HTML5 audio player
- **Chat Interface**: WhatsApp-style conversation bubbles
- **Speaker Identification**: Automatic doctor/patient detection
- **Download Options**: Export as formatted text file

### 4. Advanced Features
- **Date Filtering**: Click calendar with 7-day quick access
- **Search Functionality**: Search across patient names, doctors, notes
- **Session Management**: Complete CRUD operations
- **Error Handling**: Comprehensive error reporting and recovery

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment (development/production) | `development` |
| `OPENAI_API_KEY` | OpenAI API key for LLM features | None |
| `SECRET_KEY` | Security key for production | Auto-generated |
| `STREAMLIT_SERVER_HEADLESS` | Run without browser | `false` |

### Configuration Files

- `app/config/settings.py`: Main configuration with environment-specific settings
- `.streamlit/config.toml`: Streamlit UI theme configuration
- `docker-compose.yml`: Docker environment configuration

## 🛠️ Development

### Project Structure

- **Models** (`app/models/`): Data classes with validation and serialization
- **Services** (`app/services/`): Business logic for database and transcription
- **Components** (`app/components/`): Reusable UI components
- **Pages** (`app/pages/`): Streamlit page implementations
- **Utils** (`app/utils/`): Helper functions and utilities

### Key Components

1. **DatabaseService**: SQLite database management with session CRUD
2. **TranscriptionService**: Audio processing and Whisper integration
3. **UI Components**: Reusable Streamlit widgets and layouts
4. **Configuration Management**: Environment-specific settings

### Adding New Features

1. **New Models**: Add to `app/models/` with proper validation
2. **New Services**: Implement in `app/services/` with error handling
3. **New UI Components**: Add to `app/components/` for reusability
4. **New Pages**: Create in `app/pages/` and register in main navigation

## 🔒 Security Features

- **Input Validation**: Comprehensive data validation and sanitization
- **File Upload Limits**: Size and format restrictions for audio files
- **SQL Injection Protection**: Parameterized queries and ORM usage
- **Error Handling**: Secure error messages without sensitive data exposure
- **Container Security**: Non-root user in Docker containers
- **Resource Limits**: Memory and CPU limits in production

## 📊 Performance

### Optimizations

- **Parallel Processing**: Async operations where possible
- **Database Indexing**: Optimized queries with proper indexes
- **Caching**: Session state management and data caching
- **Resource Management**: Proper cleanup and memory management

### Monitoring

- **Logging**: Structured logging with rotation
- **Health Checks**: Docker health monitoring
- **Metrics**: Built-in statistics and analytics
- **Error Tracking**: Comprehensive error logging and reporting

## 🚀 Deployment

### Production Checklist

- [ ] Set production environment variables
- [ ] Configure proper SECRET_KEY
- [ ] Set up SSL certificates (if using Nginx)
- [ ] Configure resource limits
- [ ] Set up log rotation
- [ ] Configure backup strategy for database
- [ ] Test all functionality in production environment

### Scaling Options

1. **Horizontal Scaling**: Run multiple containers behind load balancer
2. **Database Scaling**: Move to PostgreSQL for larger deployments
3. **Storage Scaling**: Use external storage for audio files
4. **Processing Scaling**: Implement async task queue for transcription

## 🤝 Contributing

1. Follow the existing code structure and patterns
2. Add comprehensive error handling and logging
3. Include unit tests for new functionality
4. Update documentation for new features
5. Ensure security best practices

## 📝 License

This project is proprietary software. All rights reserved.

## 🆘 Support

For support and questions:
- Check the logs in `logs/app.log`
- Review the configuration in `app/config/`
- Verify system requirements and dependencies
- Check Docker container health status

---

**MedTranscribe v1.0.0** - Production-Ready AI Medical Transcription System 