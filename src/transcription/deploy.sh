#!/bin/bash

# MedTranscribe Deployment Script
set -e

echo "🏥 MedTranscribe Deployment Script"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is installed
check_docker() {
    if command -v docker &> /dev/null; then
        log_success "Docker is installed"
        return 0
    else
        log_error "Docker is not installed. Please install Docker first."
        return 1
    fi
}

# Check if Docker Compose is installed
check_docker_compose() {
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        log_success "Docker Compose is available"
        return 0
    else
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        return 1
    fi
}

# Check Python installation
check_python() {
    if command -v python3 &> /dev/null; then
        python_version=$(python3 --version | cut -d' ' -f2)
        log_success "Python $python_version is installed"
        return 0
    else
        log_error "Python 3 is not installed. Please install Python 3.8+ first."
        return 1
    fi
}

# Create directories
create_directories() {
    log_info "Creating necessary directories..."
    mkdir -p data/audio data/exports logs
    log_success "Directories created"
}

# Setup environment
setup_environment() {
    log_info "Setting up environment..."
    
    if [ ! -f ".env" ]; then
        log_warning "Creating .env file from template..."
        cat > .env << EOF
# MedTranscribe Environment Configuration
FLASK_ENV=production
SECRET_KEY=medtranscribe-$(openssl rand -hex 16 2>/dev/null || echo "change-this-secret-key")
OPENAI_API_KEY=
EOF
        log_warning "Please edit .env file and set your OPENAI_API_KEY if needed"
    else
        log_success "Environment file already exists"
    fi
}

# Install Python dependencies
install_python_deps() {
    log_info "Installing Python dependencies..."
    
    if command -v pip3 &> /dev/null; then
        pip3 install -r requirements.txt
        log_success "Python dependencies installed"
    else
        log_error "pip3 not found. Please install pip first."
        return 1
    fi
}

# Run tests
run_tests() {
    log_info "Running basic tests..."
    
    if python3 -m pytest tests/ -v 2>/dev/null || python3 tests/test_basic.py; then
        log_success "Tests passed"
    else
        log_warning "Tests failed or pytest not available"
    fi
}

# Deploy with Docker
deploy_docker() {
    log_info "Deploying with Docker..."
    
    # Build and start services
    docker-compose down 2>/dev/null || true
    docker-compose build
    docker-compose up -d
    
    # Wait for service to be ready
    log_info "Waiting for service to start..."
    sleep 10
    
    # Check if service is running
    if curl -f http://localhost:8501/_stcore/health &>/dev/null; then
        log_success "MedTranscribe is running at http://localhost:8501"
    else
        log_warning "Service might still be starting. Check with: docker-compose logs"
    fi
}

# Deploy with Python directly
deploy_python() {
    log_info "Deploying with Python..."
    
    # Install dependencies
    install_python_deps
    
    # Run the application
    log_info "Starting MedTranscribe..."
    python3 run_production.py --check-only
    
    log_success "System check completed. Run 'python3 run_production.py' to start the application"
}

# Main deployment function
main() {
    echo ""
    log_info "Starting deployment process..."
    
    # Check system requirements
    log_info "Checking system requirements..."
    
    # Create directories
    create_directories
    
    # Setup environment
    setup_environment
    
    # Choose deployment method
    echo ""
    echo "Choose deployment method:"
    echo "1) Docker (Recommended for production)"
    echo "2) Python direct (Development/testing)"
    echo "3) System check only"
    echo ""
    read -p "Enter your choice (1-3): " choice
    
    case $choice in
        1)
            if check_docker && check_docker_compose; then
                deploy_docker
            else
                log_error "Docker requirements not met"
                exit 1
            fi
            ;;
        2)
            if check_python; then
                deploy_python
            else
                log_error "Python requirements not met"
                exit 1
            fi
            ;;
        3)
            check_python
            check_docker
            check_docker_compose
            log_success "System check completed"
            ;;
        *)
            log_error "Invalid choice"
            exit 1
            ;;
    esac
    
    echo ""
    log_success "Deployment completed!"
    echo ""
    echo "📚 Next steps:"
    echo "  - Access the application at http://localhost:8501"
    echo "  - Check logs: docker-compose logs (Docker) or logs/app.log (Python)"
    echo "  - Review configuration in app/config/settings.py"
    echo "  - Set OPENAI_API_KEY in .env for LLM features"
    echo ""
}

# Run main function
main "$@" 