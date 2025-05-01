#!/bin/bash

# deploy.sh - Deployment script for AI Dental Note Generator
# This script automates the deployment process on a fresh Ubuntu 22.04 server

set -e  # Exit on any error

# Check if script is run as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Please use sudo."
    exit 1
fi

# Configuration variables
APP_USER="aidentalnotes"
APP_DIR="/home/$APP_USER/aidentalnotes"
DOMAIN="aidentalnotes.com"
EMAIL="admin@aidentalnotes.com"  # For Certbot notifications

# Display banner
echo "============================================="
echo "  AI Dental Note Generator Deployment Tool"
echo "============================================="
echo ""

# Create user if not exists
if ! id -u $APP_USER > /dev/null 2>&1; then
    echo "Creating user $APP_USER..."
    useradd -m -s /bin/bash $APP_USER
    echo "$APP_USER ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$APP_USER
    chmod 0440 /etc/sudoers.d/$APP_USER
fi

# Update system
echo "Updating system packages..."
apt update && apt upgrade -y

# Install dependencies
echo "Installing dependencies..."
apt install -y python3.11 python3.11-venv python3.11-dev python3-pip \
    nginx certbot python3-certbot-nginx postgresql postgresql-contrib \
    ffmpeg git supervisor ufw build-essential libpq-dev

# Configure firewall
echo "Configuring firewall..."
ufw allow ssh
ufw allow http
ufw allow https
ufw allow 8000  # API backend
ufw allow 8501  # Streamlit frontend
ufw --force enable

# Setup PostgreSQL
echo "Setting up PostgreSQL..."
sudo -u postgres psql -c "CREATE USER $APP_USER WITH PASSWORD '$APP_USER';"
sudo -u postgres psql -c "CREATE DATABASE aidentalnotes OWNER $APP_USER;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE aidentalnotes TO $APP_USER;"

# Clone repository or create directories
if [ ! -d "$APP_DIR" ]; then
    echo "Creating application directories..."
    mkdir -p $APP_DIR
    mkdir -p $APP_DIR/backend
    mkdir -p $APP_DIR/frontend
    mkdir -p $APP_DIR/nginx
    mkdir -p $APP_DIR/systemd
    mkdir -p $APP_DIR/scripts
    chown -R $APP_USER:$APP_USER $APP_DIR
fi

# Create Python virtual environment
echo "Setting up Python virtual environment..."
sudo -u $APP_USER bash -c "python3.11 -m venv $APP_DIR/venv"
sudo -u $APP_USER bash -c "source $APP_DIR/venv/bin/activate && pip install --upgrade pip"

# Install Python requirements
echo "Installing Python requirements..."
sudo -u $APP_USER bash -c "source $APP_DIR/venv/bin/activate && pip install fastapi uvicorn pydantic python-multipart python-jose[cryptography] passlib[bcrypt] httpx openai python-dotenv pyjwt sqlalchemy psycopg2-binary stripe deepgram-sdk pydub streamlit loguru tenacity"

# Copy application files (in a real setup, you'd clone from Git or copy from deployment package)
echo "Copying application files..."
# For demonstration, we'll assume files are in current directory
if [ -d "./aidentalnotes" ]; then
    cp -r ./aidentalnotes/* $APP_DIR/
    chown -R $APP_USER:$APP_USER $APP_DIR
fi

# Configure environment variables
echo "Setting up environment variables..."
if [ ! -f "$APP_DIR/backend/.env" ]; then
    cat > $APP_DIR/backend/.env << EOF
# Environment variables for AI Dental Note Generator
JWT_SECRET=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration
DATABASE_URL=postgresql://$APP_USER:$APP_USER@localhost/aidentalnotes

# Stripe for subscriptions
STRIPE_SECRET_KEY=your_stripe_secret_key_here
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret_here

# Service Configuration
LOG_LEVEL=INFO
ENVIRONMENT=production
HOST=0.0.0.0
PORT=8000
EOF
    chown $APP_USER:$APP_USER $APP_DIR/backend/.env
    chmod 600 $APP_DIR/backend/.env
fi

# Configure NGINX
echo "Configuring NGINX..."
if [ -f "$APP_DIR/nginx/aidentalnotes.conf" ]; then
    cp $APP_DIR/nginx/aidentalnotes.conf /etc/nginx/sites-available/
    ln -sf /etc/nginx/sites-available/aidentalnotes.conf /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
else
    echo "NGINX configuration file not found. Skipping..."
fi

# Configure systemd services
echo "Setting up systemd services..."
if [ -f "$APP_DIR/systemd/aidentalnotes.service" ]; then
    cp $APP_DIR/systemd/aidentalnotes.service /etc/systemd/system/
fi
if [ -f "$APP_DIR/systemd/aidentalnotes-streamlit.service" ]; then
    cp $APP_DIR/systemd/aidentalnotes-streamlit.service /etc/systemd/system/
fi

# SSL certificates with Certbot
echo "Setting up SSL certificates..."
certbot --nginx -d $DOMAIN -d www.$DOMAIN --email $EMAIL --agree-tos --non-interactive

# Enable and start services
echo "Starting services..."
systemctl daemon-reload
systemctl enable nginx
systemctl start nginx
systemctl enable aidentalnotes
systemctl start aidentalnotes
systemctl enable aidentalnotes-streamlit
systemctl start aidentalnotes-streamlit

# Final status check
echo "Checking service status..."
systemctl status nginx | grep Active
systemctl status aidentalnotes | grep Active
systemctl status aidentalnotes-streamlit | grep Active

echo ""
echo "============================================="
echo "  Deployment Complete!"
echo "============================================="
echo ""
echo "Your AI Dental Note Generator should now be running at:"
echo "  https://$DOMAIN"
echo ""
echo "Please complete the following manual steps:"
echo "1. Update the .env file with your actual API keys"
echo "2. Restart the services after updating environment variables:"
echo "   sudo systemctl restart aidentalnotes aidentalnotes-streamlit"
echo ""
echo "Thank you for using AI Dental Note Generator!"
