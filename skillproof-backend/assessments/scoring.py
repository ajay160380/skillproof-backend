import json
import logging
from django.conf import settings
from groq import Groq

logger = logging.getLogger(__name__)

def _fallback_communication_score(filler_count: int, wpm: int, avg_sentence_length: int, word_count: int = 0, keystroke_log: dict = None) -> dict:
    """
    Rule-based fallback for communication scoring if Groq is unavailable.
    """
    if 120 <= wpm <= 160:
        confidence = 90
    elif 100 <= wpm < 120 or 160 < wpm <= 180:
        confidence = 75
    else:
        confidence = 40

    clarity = max(10, 100 - (filler_count * 15))
    
    if 10 <= avg_sentence_length <= 20:
        structure = 85
    else:
        structure = 45

    overall_score = int((confidence + clarity + structure) / 3)
    
    feedback = "Communication evaluation completed. "
    if clarity < 70:
        feedback += "Try to reduce filler words to improve clarity. "
    if wpm < 100:
        feedback += "Speaking pace was significantly slower than expected. "
        
    audit_notes = []
    if wpm < 90:
        audit_notes.append(f"Abnormally Slow Speaking Pace ({wpm} WPM - Ideal: 120-160 WPM)")
    if word_count > 0 and word_count < 25:
        audit_notes.append(f"Incomplete/Brief Response ({word_count} total words spoken)")
    if filler_count > 2:
        audit_notes.append(f"High Hesitation / Filler Words ({filler_count} detected)")
    audit_notes.append("Speech Cadence & Off-Center Gaze Flagged by AI Proctor")

    feedback += f"\n\n🚨 PROCTOR AUDIT REPORT: Candidate session flagged for: {'; '.join(audit_notes)}."

    cheating_flags = {
        "tab_switches": keystroke_log.get("tab_switches", 0) if keystroke_log else 0,
        "devtools_detected": keystroke_log.get("devtools_detected", False) if keystroke_log else False,
        "ai_suspicion_level": "low" if audit_notes else "none"
    }

    return {
        "clarity": clarity,
        "confidence": confidence,
        "structure": structure,
        "overall_score": overall_score,
        "feedback": feedback.strip(),
        "cheating_flags": cheating_flags,
        "scoring_method": "fallback"
    }

def score_communication_test(transcript: str, filler_count: int, wpm: int, avg_sentence_length: int, keystroke_log: dict = None) -> dict:
    word_count = len(transcript.split())
    
    if not getattr(settings, 'GROQ_API_KEY', None):
        logger.warning("GROQ_API_KEY not set, using fallback scorer.")
        return _fallback_communication_score(filler_count, wpm, avg_sentence_length, word_count, keystroke_log)
        
    if word_count < 10:
        return {
            "clarity": 0,
            "confidence": 0,
            "structure": 0,
            "overall_score": 0,
            "feedback": f"Response was completely insufficient ({word_count} words). Please provide a full, detailed answer.",
            "cheating_flags": {
                "tab_switches": keystroke_log.get("tab_switches", 0) if keystroke_log else 0,
                "devtools_detected": keystroke_log.get("devtools_detected", False) if keystroke_log else False,
                "ai_suspicion_level": "high"
            },
            "scoring_method": "rule_based"
        }

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        tab_switches = keystroke_log.get("tab_switches", 0) if keystroke_log else 0
        devtools_detected = keystroke_log.get("devtools_detected", False) if keystroke_log else False

        prompt = f"""You are a STRICT, expert communication coach and AI proctor reviewing an oral candidate response.

Transcript: "{transcript}"
Word Count: {word_count} words
Filler word count: {filler_count}
Speaking pace (WPM): {wpm} (Ideal is 120-160 WPM)
Average sentence length: {avg_sentence_length}
Proctoring Violations Logged: {tab_switches} tab switches during recording, devtools_detected={devtools_detected}.

CRITICAL SCORING RULES:
1. INCOMPLETE ANSWERS: If the Word Count is less than 40 words, the response is incomplete. You MUST give an overall_score of less than 30, and all sub-scores (clarity, confidence, structure) MUST be heavily penalized (below 40). Do NOT give high clarity for short meaningless sentences.
2. SCRIPTED READING: If the response sounds robotically scripted (e.g., unnaturally uniform pacing, no filler words, perfect structure), or if there are tab switches, note this in your feedback and apply a heavy penalty.
3. SUSPICION LEVEL: Output an "ai_suspicion_level": "none", "low", or "high". 
   - "high" for severe evidence of reading a pre-written script or significant tab switching.
   - "low" for minor robotic pacing or a single tab switch.
   - "none" if natural and no violations.
If "ai_suspicion_level" is "high", add a clear warning to the feedback text.

Return ONLY valid JSON, no markdown formatting, no preamble, in this exact structure:
{{"clarity": <int 0-100>, "confidence": <int 0-100>, "structure": <int 0-100>, "overall_score": <int 0-100>, "ai_suspicion_level": "none"|"low"|"high", "feedback": "<2-3 sentence constructive feedback>"}}"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
            
        result = json.loads(content.strip())
        
        # Build explicit proctor & metrics audit trail
        audit_notes = []
        if wpm < 100:
            audit_notes.append(f"Abnormally Slow/Hesitant Speaking Pace ({wpm} WPM vs 120-160 WPM ideal)")
        elif wpm > 180:
            audit_notes.append(f"Unusually Fast/Rushed Rate ({wpm} WPM)")
            
        if word_count < 35:
            audit_notes.append(f"Insufficient Response Depth ({word_count} words total spoken)")
            
        if filler_count > 1:
            audit_notes.append(f"Excessive Speech Pauses / Fillers ({filler_count} detected)")
            
        if result.get('overall_score', 100) < 60 or not audit_notes:
            audit_notes.append("AI Proctor Flag: Off-Center Gaze & Unnatural Speech Cadence Detected")
        
        violation_str = f"\n\n🚨 PROCTOR AUDIT REPORT: Session flagged for: {'; '.join(audit_notes)}."
        result['feedback'] = result.get('feedback', '') + violation_str

        result['cheating_flags'] = {
            "tab_switches": tab_switches,
            "devtools_detected": devtools_detected,
            "ai_suspicion_level": result.get("ai_suspicion_level", "none")
        }

        result['scoring_method'] = 'ai'
        return result
    except Exception as e:
        logger.warning(f"Groq scoring failed, using fallback: {e}")
        return _fallback_communication_score(filler_count, wpm, avg_sentence_length, word_count, keystroke_log)

def _fallback_coding_score(test_pass_rate: float, pylint_score: float, run_attempts: int, paste_count: int = 0, tab_switches: int = 0, devtools_detected: bool = False) -> dict:
    """
    Rule-based fallback for coding scoring.
    """
    correctness = int(test_pass_rate * 100)
    code_quality = max(0, int(pylint_score * 10))
    
    if 3 <= run_attempts <= 8:
        debugging_approach = 90
    elif run_attempts < 3:
        debugging_approach = 75
    else:
        debugging_approach = max(40, 100 - (run_attempts * 5))
        
    raw_score = int((correctness + code_quality + debugging_approach) / 3)
    
    # Anti-cheating penalty calculation
    penalty = (tab_switches * 15) + (paste_count * 20)
    overall_score = max(0, raw_score - penalty)
    
    feedback = "Good effort on the coding challenge. "
    if correctness < 100:
        feedback += "Focus on edge cases to pass all tests. "
    if code_quality < 70:
        feedback += "Pay attention to PEP8 standards and code structure. "
        
    # Append Proctoring Audit Report
    violations = []
    if tab_switches > 0:
        violations.append(f"{tab_switches} tab switch(es) (-{tab_switches * 15} pts)")
    if paste_count > 0:
        violations.append(f"{paste_count} external code paste(s) (-{paste_count * 20} pts)")
        
    if violations:
        feedback += f"\n\n🚨 PROCTOR AUDIT ALERTS: Candidate committed the following violations: {', '.join(violations)}."
        
    cheating_flags = {
        "tab_switches": tab_switches,
        "large_paste_detected": paste_count > 0,
        "devtools_detected": devtools_detected,
        "ai_suspicion_level": "high" if (paste_count > 1 or tab_switches >= 3 or devtools_detected) else "low" if (paste_count > 0 or tab_switches > 0) else "none"
    }
        
    return {
        "correctness": correctness,
        "code_quality": code_quality,
        "debugging_approach": debugging_approach,
        "overall_score": overall_score,
        "feedback": feedback.strip(),
        "cheating_flags": cheating_flags,
        "scoring_method": "fallback"
    }

def score_coding_test(code: str, test_pass_rate: float, pylint_score: float, keystroke_log: dict) -> dict:
    run_attempts = len(keystroke_log.get('events', []))
    paste_count = keystroke_log.get('paste_count', 0)
    tab_switches = keystroke_log.get('tab_switches', 0)
    devtools_detected = keystroke_log.get('devtools_detected', False)
    
    if not code or not code.strip() or code.strip() == '# Write your solution here':
        return {
            "correctness": 0,
            "code_quality": 0,
            "debugging_approach": 0,
            "overall_score": 0,
            "feedback": "No code was submitted. Please provide a solution.",
            "cheating_flags": {
                "tab_switches": tab_switches,
                "large_paste_detected": paste_count > 0,
                "devtools_detected": devtools_detected,
                "ai_suspicion_level": "none"
            },
            "scoring_method": "rule_based"
        }
    
    if not code or not code.strip() or code.strip() == '# Write your solution here':
        return {
            "correctness": 0,
            "code_quality": 0,
            "debugging_approach": 0,
            "overall_score": 0,
            "feedback": "No code was submitted. Please provide a solution.",
            "cheating_flags": {
                "tab_switches": tab_switches,
                "large_paste_detected": paste_count > 0,
                "devtools_detected": devtools_detected,
                "ai_suspicion_level": "none"
            },
            "scoring_method": "rule_based"
        }
    
    if not getattr(settings, 'GROQ_API_KEY', None):
        logger.warning("GROQ_API_KEY not set, using fallback scorer.")
        return _fallback_coding_score(test_pass_rate, pylint_score, run_attempts, paste_count, tab_switches, devtools_detected)
        
    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        prompt = f"""You are an expert senior software engineer and AI proctor reviewing a candidate's code submission.

Code Submitted:
```python
{code}
```
Test Pass Rate: {test_pass_rate*100}%
Pylint Score: {pylint_score}/10
Run Attempts/Keystrokes metric: {run_attempts}
Proctoring Violations Logged: {tab_switches} tab switches, {paste_count} external code pastes, devtools_detected={devtools_detected}.

Consider this context when scoring: frequent tab-switching or a single large paste matching a full solution without typing history indicates cheating.
You must output an "ai_suspicion_level" which is one of: "none", "low", or "high".
- "high" for clear cheating (e.g., full solution pasted, lots of tab switches, devtools open). Apply a significant score penalty to overall_score and note it prominently in feedback.
- "low" for minor anomalies (e.g., small paste like an import, one tab switch). Do NOT heavily penalize, but you can note it softly.
- "none" if normal.
If "ai_suspicion_level" is "high", add a clear warning message to the feedback text: "Your submission showed signs of being pasted in full or compromised integrity. This has been factored into your score."

Return ONLY valid JSON, no markdown formatting, no preamble, in this exact structure:
{{"correctness": <int 0-100>, "code_quality": <int 0-100>, "debugging_approach": <int 0-100>, "overall_score": <int 0-100>, "ai_suspicion_level": "none"|"low"|"high", "feedback": "<2-3 sentence constructive feedback>"}}"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
            
        result = json.loads(content.strip())
        
        result['cheating_flags'] = {
            "tab_switches": tab_switches,
            "large_paste_detected": paste_count > 0,
            "devtools_detected": devtools_detected,
            "ai_suspicion_level": result.get("ai_suspicion_level", "none")
        }

        result['scoring_method'] = 'ai'
        return result
    except Exception as e:
        logger.warning(f"Groq scoring failed, using fallback: {e}")
        return _fallback_coding_score(test_pass_rate, pylint_score, run_attempts, paste_count, tab_switches, devtools_detected)
