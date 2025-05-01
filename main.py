k"""
main.py - FastAPI Application for AI Dental Note Generator

This module sets up the FastAPI application with all routes and middleware.
"""
import os
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form, Header, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pydantic import BaseModel
from dotenv import load_dotenv

# Import our modules
from auth import verify_token, create_token, RateLimiter
from soap_generator import generate_soap_note
from deepgram_utils import transcribe_audio, transcribe_audio_with_diarization
from stripe_webhook import handle_webhook_event

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Define our request and response models
class TextNoteRequest(BaseModel):
    text: str

class NoteResponse(BaseModel):
    soap_note: str

# Setup lifespan events for application startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting AI Dental Notes API...")
    # Initialize any resources here
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Dental Notes API...")
    # Clean up any resources here

# Create the FastAPI application
app = FastAPI(
    title="AI Dental Note Generator API",
    description="Converts voice or text to SOAP-formatted dental notes",
    version="1.0.0",
    lifespan=lifespan
)

# Rate limiter middleware
rate_limiter = RateLimiter(limit=10, window=60)  # 10 requests per minute by default

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*" if os.getenv("ENVIRONMENT") == "development" else "https://aidentalnotes.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify API is running correctly.
    """
    return {"status": "ok"}

@app.post("/generate_note", response_model=NoteResponse)
async def generate_note_from_text(
    request: TextNoteRequest,
    authorization: str = Header(None),
    client_ip: Optional[str] = Header(None, alias="X-Forwarded-For")
):
    """
    Generate a SOAP note from text input.
    """
    # Verify the token
    token_data = verify_token(authorization)
    
    # Apply rate limiting
    if not rate_limiter.allow_request(token_data["sub"] or client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, 
            detail="Rate limit exceeded. Please try again later."
        )
    
    # Generate the note
    try:
        soap_note = await generate_soap_note(request.text)
        return {"soap_note": soap_note}
    except Exception as e:
        logger.error(f"Error generating note: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate note. Please try again later."
        )

@app.post("/generate_note_from_audio", response_model=NoteResponse)
async def generate_note_from_audio(
    audio_file: UploadFile = File(...),
    use_diarization: bool = Form(False),
    authorization: str = Header(None),
    client_ip: Optional[str] = Header(None, alias="X-Forwarded-For")
):
    """
    Generate a SOAP note from an audio file.
    
    Args:
        audio_file: The audio file to transcribe
        use_diarization: Whether to use speaker diarization for multi-speaker scenarios
        authorization: The JWT token for authentication
        client_ip: The client IP address for rate limiting
    """
    # Verify the token
    token_data = verify_token(authorization)
    
    # Apply rate limiting
    if not rate_limiter.allow_request(token_data["sub"] or client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, 
            detail="Rate limit exceeded. Please try again later."
        )
    
    # Check file type and support more audio formats
    supported_content_types = [
        "audio/wav", "audio/x-wav",
        "audio/mp3", "audio/mpeg",
        "audio/ogg", "application/ogg",
        "audio/flac",
        "audio/x-m4a", "audio/mp4"
    ]
    
    if audio_file.content_type not in supported_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Please upload a supported audio file (WAV, MP3, OGG, FLAC, M4A)."
        )
    
    try:
        # Read the audio file content
        audio_content = await audio_file.read()
        
        # Get file extension from content type
        extension_map = {
            "audio/wav": ".wav", "audio/x-wav": ".wav",
            "audio/mp3": ".mp3", "audio/mpeg": ".mp3",
            "audio/ogg": ".ogg", "application/ogg": ".ogg",
            "audio/flac": ".flac",
            "audio/x-m4a": ".m4a", "audio/mp4": ".m4a"
        }
        file_ext = extension_map.get(audio_file.content_type, ".wav")
        
        # Update the filename with the correct extension if it doesn't have one
        if not Path(audio_file.filename).suffix:
            audio_file.filename = f"{audio_file.filename}{file_ext}"
        
        # Transcribe the audio with or without diarization
        if use_diarization:
            transcription_result = await transcribe_audio_with_diarization(audio_content, audio_file.filename)
            
            # Format the transcription with speaker labels for better context
            speaker_texts = []
            for speaker, text in transcription_result["by_speaker"].items():
                speaker_texts.append(f"{speaker}: {text}")
            
            transcription = "\n\n".join(speaker_texts)
        else:
            transcription = await transcribe_audio(audio_content, audio_file.filename)
        
        # Generate the note
        soap_note = await generate_soap_note(transcription)
        
        # Record the successful transcription in the database
        db = SessionLocal()
        try:
            # Increment the license usage count
            license = db.query(License).filter(License.user_id == token_data["sub"]).first()
            if license:
                license.notes_used += 1
                db.commit()
        finally:
            db.close()
        
        return {"soap_note": soap_note}
    except Exception as e:
        logger.error(f"Error processing audio and generating note: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process audio and generate note: {str(e)}"
        )

@app.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Webhook endpoint for Stripe events.
    """
    # Get the signature header from the request
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature"
        )
    
    # Get the request body
    body = await request.body()
    
    # Handle the webhook event
    try:
        event_data = handle_webhook_event(body, signature)
        return {"status": "success", "event": event_data.get("type")}
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# Main entry point
if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run("main:app", host=host, port=port, reload=True if os.getenv("ENVIRONMENT") == "development" else False)
