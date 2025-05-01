#!/bin/bash

# install_dependencies.sh - Setup script for AI Dental Note Generator
# This script installs required dependencies on a development machine

set -e  # Exit on any error

# Display banner
echo "============================================="
echo "  AI Dental Note Generator Setup Tool"
echo "============================================="
echo ""

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    CYGWIN*)    MACHINE=Windows;;
    MINGW*)     MACHINE=Windows;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

echo "Detected OS: $MACHINE"
echo ""

# Function to install Linux dependencies
install_linux_deps() {
    echo "Installing Linux dependencies..."
    sudo apt update
    sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip \
        postgresql postgresql-contrib libpq-dev ffmpeg build-essential
}

# Function to install Mac dependencies
install_mac_deps() {
    echo "Installing Mac dependencies..."
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    # Install dependencies
    brew update
    brew install python@3.11 postgresql ffmpeg
    brew services start postgresql
}

# Function to install Windows dependencies
install_windows_deps() {
    echo "Installing Windows dependencies..."
    echo "Please install the following manually:"
    echo "1. Python 3.11 from https://www.python.org/downloads/"
    echo "2. PostgreSQL from https://www.postgresql.org/download/windows/"
    echo "3. FFmpeg from https://www.gyan.dev/ffmpeg/builds/"
    echo ""
    echo "After installation, add them to your PATH and run this script again."
    
    # Check if Python is installed
    if command -v python3.11 &> /dev/null; then
        echo "Python 3.11 is installed."
    else
        echo "Python 3.11 is NOT installed."
    fi
    
    # Check if PostgreSQL is installed
    if command -v psql &> /dev/null; then
        echo "PostgreSQL is installed."
    else
        echo "PostgreSQL is NOT installed."
    fi
    
    # Check if FFmpeg is installed
    if command -v ffmpeg &> /dev/null; then
        echo "FFmpeg is installed."
    else
        echo "FFmpeg is NOT installed."
    fi
}

# Install OS-specific dependencies
case "${MACHINE}" in
    Linux)      install_linux_deps;;
    Mac)        install_mac_deps;;
    Windows)    install_windows_deps;;
    *)          echo "Unsupported OS. Please install dependencies manually.";;
esac

# Create project directory
echo "Creating project directory..."
mkdir -p aidentalnotes
cd aidentalnotes

# Create virtual environment
echo "Setting up Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate || venv/Scripts/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "Installing Python dependencies..."
pip install fastapi uvicorn pydantic python-multipart python-jose passlib httpx \
    openai python-dotenv pyjwt sqlalchemy psycopg2-binary stripe streamlit \
    deepgram-sdk pydub pytest loguru tenacity

# Create project structure
echo "Creating project structure..."
mkdir -p backend
mkdir -p frontend
mkdir -p nginx
mkdir -p systemd
mkdir -p scripts

# Create placeholder files
touch backend/main.py
touch backend/soap_generator.py
touch backend/whisper_utils.py
touch backend/auth.py
touch backend/stripe_webhook.py
touch backend/.env.example
touch frontend/streamlit_app.py

# Create .env.example file
cat > backend/.env.example << 'EOF'
# Environment variables for AI Dental Note Generator
# Copy this file to .env and fill in the values

# API Security
JWT_SECRET=your_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# OpenAI API for GPT-4
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration
# Uncomment and set values for PostgreSQL
# DATABASE_URL=postgresql://username:password@localhost/aidentalnotes

# Uncomment for SQLite (simpler setup for development)
DATABASE_URL=sqlite:///./aidentalnotes.db

# Stripe for subscriptions
STRIPE_SECRET_KEY=your_stripe_secret_key_here
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret_here

# Service Configuration
LOG_LEVEL=INFO
ENVIRONMENT=development  # development or production
HOST=0.0.0.0
PORT=8000
EOF

echo ""
echo "============================================="
echo "  Setup Complete!"
echo "============================================="
echo ""
echo "Your AI Dental Note Generator development environment is ready!"
echo ""
echo "Next steps:"
echo "1. Create a .env file from the template:"
echo "   cp backend/.env.example backend/.env"
echo "2. Edit backend/.env with your API keys and database settings"
echo "3. Start the backend API (from project root):"
echo "   source venv/bin/activate"  # or venv/Scripts/activate on Windows
echo "   cd backend"
echo "   uvicorn main:app --reload"
echo "4. Start the frontend (in another terminal):"
echo "   source venv/bin/activate"  # or venv/Scripts/activate on Windows
echo "   cd frontend"
echo "   streamlit run streamlit_app.py"
echo ""
echo "Happy coding!"
