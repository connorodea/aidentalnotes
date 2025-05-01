"""
deepgram_utils.py - Audio Transcription for AI Dental Note Generator

This module handles the transcription of audio files to text using Deepgram's API.
"""
import os
import logging
import tempfile
from pathlib import Path
import asyncio
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Deepgram API key
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=60))
async def transcribe_audio(audio_content: bytes, filename: str) -> str:
    """
    Transcribe audio to text using Deepgram's API.
    
    Args:
        audio_content: Binary audio content
        filename: Original filename of the audio
        
    Returns:
        str: Transcribed text
        
    Raises:
        Exception: If transcription fails after retries
    """
    try:
        logger.info(f"Transcribing audio file: {filename}")
        
        # Create a temporary file to store the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as temp_file:
            temp_file.write(audio_content)
            temp_file_path = temp_file.name
        
        try:
            # Initialize the Deepgram client
            deepgram = DeepgramClient(DEEPGRAM_API_KEY)
            
            # Create configuration options for the transcription
            options = PrerecordedOptions(
                model="nova-2",  # Using Nova-2 for high accuracy
                smart_format=True,  # Enable smart formatting for better readability
                diarize=True,  # Speaker identification (useful for dental contexts)
                punctuate=True,  # Add punctuation
                language="en",  # English language
                detect_topics=True,  # Detect topics in the conversation
                summarize="v2",  # Generate a summary
                tier="enhanced"  # Use enhanced tier for dental accuracy
            )
            
            # Use a file source for transcription
            with open(temp_file_path, "rb") as audio_file:
                source = FileSource(audio_file)
                
                # Perform the transcription
                response = await deepgram.listen.prerecorded.v("1").transcribe_file(source, options)
                
                # Extract the transcribed text
                results = response.results
                transcription = results.channels[0].alternatives[0].transcript
                
                logger.info(f"Successfully transcribed audio to text of length: {len(transcription)}")
                return transcription
        
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
    
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        raise Exception(f"Failed to transcribe audio: {str(e)}")

def is_audio_file_valid(filename: str) -> bool:
    """
    Check if an audio file has a valid extension.
    
    Args:
        filename: The name of the audio file
        
    Returns:
        bool: True if the file extension is valid, False otherwise
    """
    valid_extensions = ['.wav', '.mp3', '.m4a', '.mp4', '.mpeg', '.mpga', '.webm', '.ogg', '.flac']
    return Path(filename).suffix.lower() in valid_extensions

def get_audio_duration(audio_content: bytes) -> float:
    """
    Get the duration of an audio file in seconds.
    
    Args:
        audio_content: Binary audio content
        
    Returns:
        float: Duration in seconds
    """
    try:
        from pydub import AudioSegment
        import io
        
        # Load audio file into memory
        audio = AudioSegment.from_file(io.BytesIO(audio_content))
        
        # Get duration in seconds
        duration_seconds = len(audio) / 1000.0
        return duration_seconds
    except Exception as e:
        logger.warning(f"Could not determine audio duration: {str(e)}")
        # Return an estimated duration based on file size (rough approximation)
        # Assuming ~10KB per second for MP3 files at typical bitrates
        return len(audio_content) / 10000
