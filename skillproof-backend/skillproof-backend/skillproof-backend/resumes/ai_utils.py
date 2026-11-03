import json
import re
from groq import Groq
from django.conf import settings

def extract_text_from_file(file_path: str) -> str:
    ext = file_path.lower().split('.')[-1]
    if ext == 'pdf':
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""
    elif ext == 'docx':
        try:
            from docx import Document
            doc = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except Exception as e:
            print(f"Error reading DOCX: {e}")
            return ""
    return ""

def extract_skills_via_keywords(text: str) -> list:
    # Fallback keyword list
    common_skills = [
        "Python", "Java", "C++", "C#", "JavaScript", "TypeScript", "React", "Angular", "Vue",
        "Node.js", "Django", "Flask", "Spring", "SQL", "MySQL", "PostgreSQL", "MongoDB", "AWS",
        "Azure", "GCP", "Docker", "Kubernetes", "Machine Learning", "Data Science", "UI/UX Design",
        "Communication", "Team Leadership", "Project Management", "Agile", "Scrum", "Git",
        "Linux", "Cybersecurity", "Blockchain", "DevOps", "HTML", "CSS", "Tailwind"
    ]
    extracted = []
    text_lower = text.lower()
    for skill in common_skills:
        # Use regex to match whole words where possible or just simple substring
        if re.search(r'\b' + re.escape(skill.lower()) + r'\b', text_lower):
            extracted.append(skill)
    return extracted[:12]

def extract_skills_via_ai(text: str) -> list:
    if not text or not text.strip():
        return []
    if not settings.GROQ_API_KEY:
        return extract_skills_via_keywords(text)
        
    models_to_try = ["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"]
    
    try:
        client = Groq(api_key=settings.GROQ_API_KEY, timeout=15.0)
    except Exception as e:
        print(f"Failed to initialize Groq client: {e}")
        return extract_skills_via_keywords(text)
        
    prompt = f"""
    Extract a clean list of the top 3 to 5 most important HARD technical skills (e.g., programming languages, frameworks, core technical tools) mentioned in this resume text.
    Do NOT include generic soft skills like "Adaptability", "Time Management", "Communication", or "Problem-solving".
    Do NOT include trivial or tiny skills.
    Return ONLY a JSON array of skill strings, no markdown, no explanation, maximum of 5 skills, ordered by how prominently they're featured:

    Resume text: {text[:5000]}

    Example output format: ["Python", "React", "AWS", "SQL", "Docker"]
    """
    
    for model_name in models_to_try:
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=200,
            )
            
            response_text = completion.choices[0].message.content.strip()
            if not response_text:
                continue
                
            # Clean up markdown code blocks if any
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Find JSON array using regex if other text is included
            match = re.search(r'\[.*?\]', response_text, re.DOTALL)
            if match:
                response_text = match.group(0)
                
            skills_list = json.loads(response_text)
            if isinstance(skills_list, list) and len(skills_list) > 0:
                return [str(s).strip() for s in skills_list[:12] if str(s).strip()]
        except Exception as e:
            print(f"Groq extraction with model {model_name} failed: {e}")
            continue

    return extract_skills_via_keywords(text)
