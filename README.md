# AI Dental Note Generator

![AI Dental Notes Logo](https://via.placeholder.com/150x150?text=AIDentalNotes)

A web-based Micro SaaS that converts voice or text into structured SOAP-format dental notes using Whisper and GPT-4.

## Overview

AI Dental Note Generator is designed to help dentists, dental hygienists, and dental service organizations (DSOs) reduce administrative overhead and boost clinical efficiency by automating the creation of professional SOAP notes from either voice recordings or text input.

### Key Features

- **Voice-to-Note Conversion**: Upload audio recordings or record directly in the app
- **Advanced Speech Recognition**: Powered by Deepgram's AI-based speech recognition for high accuracy with dental terminology
- **Text-to-Note Conversion**: Paste or type clinical observations for processing
- **Structured SOAP Format**: All notes follow the standard Subjective, Objective, Assessment, Plan format
- **Dental Terminology**: Optimized for dental-specific terminology and notation
- **Easy Export**: Copy, download, or export notes to your practice management system

## Getting Started

### Prerequisites

- Python 3.11 or higher
- PostgreSQL (for production) or SQLite (for development)
- Node.js (for React frontend in post-MVP phase)
- OpenAI API key
- Stripe account (for subscription management)

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/aidentalnotes.git
   cd aidentalnotes
   ```

2. Run the setup script:
   ```bash
   chmod +x scripts/install_dependencies.sh
   ./scripts/install_dependencies.sh
   ```

3. Create and configure your environment variables:
   ```bash
   cp backend/.env.example backend/.env
   # Edit the .env file with your API keys and settings
   ```

4. Start the backend (development mode):
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

5. Start the frontend (in a new terminal):
   ```bash
   cd frontend
   streamlit run streamlit_app.py
   ```

6. Open your browser and navigate to:
   - Frontend: http://localhost:8501
   - API Documentation: http://localhost:8000/docs

### Deployment

For production deployment on a Ubuntu 22.04 VPS (like Hetzner):

```bash
chmod +x scripts/deploy.sh
sudo ./scripts/deploy.sh
```

The script will:
1. Set up the server environment
2. Install all dependencies
3. Configure NGINX with SSL
4. Set up systemd services for automatic startup
5. Configure PostgreSQL database

## Architecture

### Tech Stack

- **Backend**: FastAPI (Python 3.11)
- **Frontend**: 
  - MVP: Streamlit
  - Post-MVP: React + Tailwind CSS
- **Database**: PostgreSQL (production) / SQLite (development)
- **Authentication**: JWT tokens
- **AI Services**:
  - Speech-to-Text: OpenAI Whisper
  - SOAP Generation: OpenAI GPT-4
- **Deployment**: Hetzner VPS, NGINX, Certbot, systemd

### Project Structure

```
aidentalnotes/
├── backend/
│   ├── main.py                # FastAPI application
│   ├── soap_generator.py      # GPT prompt formatter + LLM caller
│   ├── whisper_utils.py       # Transcribes audio to text
│   ├── auth.py                # JWT validator + license checker
│   ├── stripe_webhook.py      # Webhook receiver and license DB updater
│   ├── requirements.txt       # Python dependencies
│   └── .env                   # Environment variables
├── frontend/
│   ├── streamlit_app.py       # Streamlit MVP
│   ├── static/                # Static assets
│   └── templates/             # HTML templates
├── nginx/
│   └── aidentalnotes.conf     # NGINX configuration
├── systemd/
│   ├── aidentalnotes.service          # Backend service
│   └── aidentalnotes-streamlit.service # Frontend service
└── scripts/
    ├── deploy.sh              # Production deployment script
    └── install_dependencies.sh # Development setup script
```

## Business Model

AI Dental Note Generator follows a SaaS (Software as a Service) model with monthly recurring revenue through the following subscription tiers:

- **Starter**: $49/mo (solo practitioner, 100 notes/mo)
- **Pro**: $99/mo (multi-user, 500 notes/mo)
- **Enterprise**: Custom pricing (white-label, team usage)

## License

This project is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.

## Contact

For support or inquiries, contact us at:
- Email: support@aidentalnotes.com
- Website: https://aidentalnotes.com
