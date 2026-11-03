import re
import logging


logger = logging.getLogger(__name__)

def transcribe_audio(file_path: str) -> str:
    """
    Transcribes audio file using Groq Whisper API to avoid local OOM crashes.
    """
    from django.conf import settings
    try:
        from groq import Groq
        if not getattr(settings, 'GROQ_API_KEY', None):
            return "Transcript unavailable (No API Key)"
            
        client = Groq(api_key=settings.GROQ_API_KEY, timeout=30.0)
        logger.info(f"Transcribing {file_path} with Groq Whisper...")
        
        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(file_path, audio_file.read()),
                model="whisper-large-v3",
                response_format="json"
            )
            
        return transcription.text.strip()
    except Exception as e:
        logger.error(f"Error transcribing audio with Groq: {e}")
        return "Audio transcription failed due to an error."

def calculate_speech_metrics(transcript: str, audio_duration_seconds: float) -> dict:
    """
    Calculates basic speech metrics: WPM, filler word count, avg sentence length.
    """
    filler_words = ["um", "uh", "like", "basically", "you know"]
    
    # Count filler words (case-insensitive)
    filler_count = 0
    transcript_lower = transcript.lower()
    for fw in filler_words:
        # use regex for exact word boundary matches for single words
        # but "you know" is two words, so basic count is fine or regex \b
        count = len(re.findall(r'\b' + re.escape(fw) + r'\b', transcript_lower))
        filler_count += count
        
    words = [w for w in transcript.split() if w.strip()]
    word_count = len(words)
    
    duration_minutes = max(audio_duration_seconds / 60.0, 0.01) # prevent div by zero
    wpm = int(word_count / duration_minutes)
    
    # Sentence length
    sentences = [s.strip() for s in re.split(r'[.!?]+', transcript) if s.strip()]
    if sentences:
        avg_sentence_length = int(word_count / len(sentences))
    else:
        avg_sentence_length = word_count
        
    return {
        "filler_word_count": filler_count,
        "words_per_minute": wpm,
        "avg_sentence_length": avg_sentence_length,
    }
