from typing import List
from .models import SkillCategory, SkillTest
import re

def match_skills_to_tests(extracted_skills: List[str]) -> List[SkillTest]:
    """
    Given a list of extracted skills, try to match them against existing tests.
    Option A: Only suggest tests we have pre-seeded categories for.
    Option B (Commented): Dynamically generate tests using AI.
    """
    matched_tests = []
    seen_test_ids = set()
    
    categories = list(SkillCategory.objects.all())
    
    for skill in extracted_skills:
        skill_lower = skill.lower()
        matched = False
        
        # Option A: Fuzzy Match against existing categories
        for category in categories:
            # simple substring matching
            if skill_lower in category.name.lower() or category.name.lower() in skill_lower:
                matched = True
                tests = category.tests.filter(is_active=True)
                for test in tests:
                    if test.id not in seen_test_ids:
                        matched_tests.append(test)
                        seen_test_ids.add(test.id)
                break
                
        # Option B (Enhancement): Dynamically generate new SkillTest via AI
        if not matched:
            try:
                from groq import Groq
                from django.conf import settings
                from django.utils.text import slugify
                import json
                
                if settings.GROQ_API_KEY:
                    client = Groq(api_key=settings.GROQ_API_KEY, timeout=15.0)
                    prompt = f'''Generate a short coding problem or conceptual interview question for the skill: "{skill}".
                    Return a JSON object with: 
                    - "title": (string)
                    - "test_type": (string "coding" or "communication")
                    - "problem_statement": (string)
                    - "duration_minutes": (int)
                    - "instructions": (string)
                    Only return the raw JSON object, no other text.
                    '''
                    
                    completion = client.chat.completions.create(
                        model="llama3-70b-8192",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=400,
                        response_format={"type": "json_object"}
                    )
                    
                    resp_json = json.loads(completion.choices[0].message.content)
                    
                    # Create category if doesn't exist
                    new_cat, _ = SkillCategory.objects.get_or_create(
                        name=skill, 
                        defaults={'description': f'Verified tests for {skill}', 'icon': 'Brain'}
                    )
                    
                    # Create test
                    new_test = SkillTest.objects.create(
                        category=new_cat,
                        title=resp_json.get('title', f"{skill} Assessment"),
                        difficulty='medium',
                        duration_minutes=resp_json.get('duration_minutes', 30),
                        instructions=resp_json.get('instructions', ''),
                        test_type=resp_json.get('test_type', 'communication'),
                        problem_statement=resp_json.get('problem_statement', ''),
                        is_active=True
                    )
                    
                    matched_tests.append(new_test)
                    seen_test_ids.add(new_test.id)
            except Exception as e:
                print(f"Failed to generate test for {skill}: {e}")

    # Always include baseline communication tests for every user
    comm_tests = SkillTest.objects.filter(test_type='communication', is_active=True)
    for ct in comm_tests:
        if ct.id not in seen_test_ids:
            matched_tests.append(ct)
            seen_test_ids.add(ct.id)

    return matched_tests
