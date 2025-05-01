"""
soap_generator.py - GPT Integration for AI Dental Note Generator

This module handles the conversion of raw text into structured SOAP notes
using the OpenAI GPT-4 API.
"""
import os
import logging
import openai
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GPT model to use
GPT_MODEL = "gpt-4"

# System prompt for GPT-4
SYSTEM_PROMPT = """
You are a specialized dental assistant AI that converts clinical notes into standardized SOAP format.
Your task is to organize and structure dental examination notes into the following sections:

1. Subjective: Patient complaints, history, and symptoms from the patient's perspective.
2. Objective: Clinical findings during examination, including visual observations, probing depths, radiographic findings, etc.
3. Assessment: Diagnosis and interpretation of the findings.
4. Plan: Treatment recommendations, procedures performed, medications prescribed, and follow-up.

Follow these guidelines:
- Use clear, professional dental terminology consistent with standard practice
- Include all relevant clinical information from the provided notes
- Organize information logically within each section
- Be concise but comprehensive
- Format with clear section headers and bullet points for readability
- Do not invent or fabricate information not present in the original notes
- Use standardized dental notation (Universal/ADA Numbering System) for teeth
- Include proper dental procedure codes (CDT codes) where appropriate

The output should be clear enough to be directly entered into a dental practice management system.
"""

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=60))
async def generate_soap_note(input_text: str) -> str:
    """
    Generate a structured SOAP note from dental clinician input.
    
    Args:
        input_text: Raw text from the clinician (transcribed or directly input)
        
    Returns:
        str: Formatted SOAP note in professional dental format
        
    Raises:
        Exception: If OpenAI API call fails after retries
    """
    try:
        logger.info(f"Generating SOAP note from input text of length: {len(input_text)}")
        
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": input_text}
            ],
            temperature=0.2,  # Lower temperature for more consistent, professional outputs
            max_tokens=1500,  # Adjust as needed based on expected note length
            top_p=0.9,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        
        # Extract the generated text
        soap_note = response.choices[0].message.content.strip()
        
        logger.info(f"Successfully generated SOAP note of length: {len(soap_note)}")
        return soap_note
    
    except Exception as e:
        logger.error(f"Error generating SOAP note: {str(e)}")
        raise Exception(f"Failed to generate SOAP note: {str(e)}")

def extract_keywords(soap_note: str) -> list:
    """
    Extract important keywords and codes from a SOAP note for indexing or reference.
    
    Args:
        soap_note: The formatted SOAP note
        
    Returns:
        list: List of extracted keywords and codes
    """
    keywords = []
    
    # Extract CDT codes (dental procedure codes)
    import re
    cdt_pattern = r'D\d{4}'
    cdt_codes = re.findall(cdt_pattern, soap_note)
    keywords.extend(cdt_codes)
    
    # Extract dental terms
    dental_terms = [
        "caries", "decay", "cavity", "restoration", "crown", "bridge", "implant",
        "extraction", "root canal", "periodontal", "gingivitis", "periodontitis",
        "prophylaxis", "scaling", "root planing", "fluoride", "sealant",
        "occlusion", "malocclusion", "TMJ", "bruxism", "abscess", "pulpitis"
    ]
    
    for term in dental_terms:
        if re.search(r'\b' + re.escape(term) + r'\b', soap_note, re.IGNORECASE):
            keywords.append(term.lower())
    
    # Extract teeth numbers
    teeth_pattern = r'\b(?:tooth|teeth)\s+#?(\d{1,2}(?:-\d{1,2})?)\b'
    teeth_mentions = re.findall(teeth_pattern, soap_note, re.IGNORECASE)
    for tooth in teeth_mentions:
        keywords.append(f"tooth_{tooth}")
    
    # Extract diagnoses
    diagnosis_section = re.search(r'Assessment:(.+?)Plan:', soap_note, re.DOTALL | re.IGNORECASE)
    if diagnosis_section:
        diagnosis_text = diagnosis_section.group(1).strip()
        # Look for formal diagnoses often preceded by numbers or bullets
        diagnoses = re.findall(r'(?:\d+\.|\*|\-)\s*([A-Z][^.]*\.)', diagnosis_text)
        keywords.extend([d.strip().lower() for d in diagnoses])
    
    # Extract medications and treatments
    medications = [
        "amoxicillin", "clindamycin", "penicillin", "ibuprofen", "acetaminophen",
        "lidocaine", "benzocaine", "epinephrine", "articaine", "chlorhexidine"
    ]
    
    for med in medications:
        if re.search(r'\b' + re.escape(med) + r'\b', soap_note, re.IGNORECASE):
            keywords.append(f"med_{med.lower()}")
    
    # Remove duplicates and return
    return list(set(keywords))
