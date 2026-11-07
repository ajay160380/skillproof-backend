"""
AI Skill Gap Analyzer & Personalized Learning Roadmap Generator.

Uses Groq LLM to analyze a user's assessment history, resume skills, and
job market data to produce actionable skill insights with a fallback to
rule-based analysis when the API is unavailable.
"""
import json
import logging
from django.conf import settings
from django.db.models import Avg, Max
from .models import TestAttempt, SkillScore, SkillInsight
from skills.models import SkillCategory, SkillTest
from badges.models import Badge
from jobs.models import JobListing

logger = logging.getLogger(__name__)


def _compute_market_averages():
    """
    Compute the platform-wide average score per skill category
    to serve as a benchmark (market average).
    """
    averages = (
        SkillScore.objects
        .filter(attempt__status='completed')
        .values('attempt__test__category__name', 'attempt__test__category_id')
        .annotate(avg_score=Avg('overall_score'))
    )
    return {
        item['attempt__test__category__name']: {
            'avg': round(item['avg_score'] or 0),
            'category_id': item['attempt__test__category_id'],
        }
        for item in averages
    }


def _get_user_skill_data(user):
    """
    Aggregate the user's best score per skill category,
    their sub_scores, and related metadata.
    """
    # Get best score per category
    completed_attempts = TestAttempt.objects.filter(
        user=user, status='completed'
    ).select_related('test__category', 'score')

    skill_data = {}
    for attempt in completed_attempts:
        cat_name = attempt.test.category.name
        cat_id = attempt.test.category.id
        score = getattr(attempt, 'score', None)
        if not score:
            continue

        if cat_name not in skill_data or score.overall_score > skill_data[cat_name]['score']:
            skill_data[cat_name] = {
                'score': score.overall_score,
                'category_id': cat_id,
                'sub_scores': score.sub_scores or {},
                'feedback': score.ai_feedback_text[:200] if score.ai_feedback_text else '',
                'test_type': attempt.test.test_type,
                'test_title': attempt.test.title,
            }

    return skill_data


def _get_in_demand_skills():
    """
    Determine which skills are most in-demand based on active job listings.
    """
    demand = (
        JobListing.objects
        .filter(is_active=True)
        .values('required_tests__category__name')
        .annotate(job_count=Max('id'))  # Use count-like proxy
    )
    return {
        item['required_tests__category__name']: True
        for item in demand
        if item['required_tests__category__name']
    }


def _get_untested_skills(user, user_skill_data):
    """
    Find skill categories the user hasn't tested yet.
    """
    all_categories = SkillCategory.objects.all()
    tested_names = set(user_skill_data.keys())
    untested = []
    for cat in all_categories:
        if cat.name not in tested_names:
            tests = SkillTest.objects.filter(category=cat, is_active=True)
            if tests.exists():
                untested.append({
                    'name': cat.name,
                    'category_id': cat.id,
                    'test_id': tests.first().id,
                    'test_title': tests.first().title,
                    'test_type': tests.first().test_type,
                    'duration': tests.first().duration_minutes,
                })
    return untested


def _fallback_insights(user, user_skill_data, market_avgs, in_demand, untested_skills):
    """
    Rule-based fallback when Groq API is unavailable.
    Generates deterministic insights from raw score data.
    """
    if not user_skill_data:
        return None

    # Build radar data
    radar_data = []
    for skill_name, data in user_skill_data.items():
        market_avg = market_avgs.get(skill_name, {}).get('avg', 65)
        radar_data.append({
            'skill': skill_name,
            'score': data['score'],
            'market_avg': market_avg,
        })

    # Sort to find strongest/weakest
    sorted_skills = sorted(user_skill_data.items(), key=lambda x: x[1]['score'])
    weakest = sorted_skills[0] if sorted_skills else None
    strongest = sorted_skills[-1] if sorted_skills else None

    # Readiness score = weighted average of all scores
    scores = [d['score'] for d in user_skill_data.values()]
    readiness_score = round(sum(scores) / len(scores)) if scores else 0

    # Gap analysis
    gap_analysis = []
    for skill_name, data in user_skill_data.items():
        market_avg = market_avgs.get(skill_name, {}).get('avg', 65)
        delta = data['score'] - market_avg
        if delta >= 10:
            status = 'above'
        elif delta >= -5:
            status = 'at'
        else:
            status = 'below'

        tips = []
        if data['score'] < 60:
            tips.append(f"Focus on fundamentals — your {skill_name} score suggests gaps in core concepts.")
            tips.append("Practice with easier problems first, then progress to medium difficulty.")
        elif data['score'] < 80:
            tips.append(f"Good foundation in {skill_name}. Target advanced concepts to push past 80.")
            tips.append("Review the AI feedback from your last attempt for specific improvement areas.")
        else:
            tips.append(f"Excellent {skill_name} proficiency. Consider mentoring others or tackling expert challenges.")
            tips.append("Keep your skills sharp by retaking assessments periodically.")

        gap_analysis.append({
            'skill': skill_name,
            'score': data['score'],
            'market_avg': market_avg,
            'status': status,
            'delta': delta,
            'is_in_demand': skill_name in in_demand,
            'tips': tips,
        })

    # Roadmap: prioritize weakest skills and untested in-demand skills
    roadmap = []
    order = 1

    # First: address weak skills below market
    for ga in sorted(gap_analysis, key=lambda x: x['score']):
        if ga['status'] == 'below' and order <= 5:
            # Find a test for this skill
            cat_id = market_avgs.get(ga['skill'], {}).get('category_id')
            test = SkillTest.objects.filter(category_id=cat_id, is_active=True).first() if cat_id else None
            roadmap.append({
                'order': order,
                'title': f"Improve {ga['skill']}",
                'description': f"Your {ga['skill']} score ({ga['score']}) is {abs(ga['delta'])} points below the platform average ({ga['market_avg']}). Retaking the assessment after practice can boost your profile.",
                'action_type': 'retake_test' if test else 'practice',
                'test_id': test.id if test else None,
                'test_title': test.title if test else None,
                'priority': 'high',
                'estimated_minutes': test.duration_minutes if test else 30,
            })
            order += 1

    # Second: take untested in-demand skills
    for us in untested_skills:
        if us['name'] in in_demand and order <= 5:
            roadmap.append({
                'order': order,
                'title': f"Get Verified in {us['name']}",
                'description': f"{us['name']} is in-demand on the platform but you haven't been assessed yet. Taking the {us['test_title']} assessment will strengthen your profile.",
                'action_type': 'take_test',
                'test_id': us['test_id'],
                'test_title': us['test_title'],
                'priority': 'high' if us['name'] in in_demand else 'medium',
                'estimated_minutes': us['duration'],
            })
            order += 1

    # Third: fill remaining with untested skills
    for us in untested_skills:
        if us['name'] not in in_demand and order <= 5:
            roadmap.append({
                'order': order,
                'title': f"Explore {us['name']}",
                'description': f"You haven't taken the {us['test_title']} assessment yet. Expanding your verified skill set makes your portfolio more attractive.",
                'action_type': 'take_test',
                'test_id': us['test_id'],
                'test_title': us['test_title'],
                'priority': 'medium',
                'estimated_minutes': us['duration'],
            })
            order += 1

    # If still less than 3 items, add improvement suggestions for 'at' market skills
    for ga in gap_analysis:
        if ga['status'] == 'at' and order <= 5:
            cat_id = market_avgs.get(ga['skill'], {}).get('category_id')
            test = SkillTest.objects.filter(category_id=cat_id, is_active=True).first() if cat_id else None
            roadmap.append({
                'order': order,
                'title': f"Level Up {ga['skill']}",
                'description': f"You're near the platform average for {ga['skill']} ({ga['score']} vs {ga['market_avg']}). A few more points could unlock better opportunities.",
                'action_type': 'retake_test' if test else 'practice',
                'test_id': test.id if test else None,
                'test_title': test.title if test else None,
                'priority': 'low',
                'estimated_minutes': test.duration_minutes if test else 30,
            })
            order += 1

    return {
        'readiness_score': readiness_score,
        'strongest_skill': {'name': strongest[0], 'score': strongest[1]['score']} if strongest else None,
        'weakest_skill': {'name': weakest[0], 'score': weakest[1]['score']} if weakest else None,
        'radar_data': radar_data,
        'gap_analysis': gap_analysis,
        'roadmap': roadmap[:5],
        'scoring_method': 'fallback',
    }


def _ai_insights(user, user_skill_data, market_avgs, in_demand, untested_skills):
    """
    Use Groq LLM to generate rich, personalized skill gap analysis
    with a structured JSON response.
    """
    try:
        from groq import Groq
    except ImportError:
        logger.warning("Groq not installed, using fallback insights.")
        return None

    if not getattr(settings, 'GROQ_API_KEY', None):
        logger.warning("GROQ_API_KEY not set, using fallback insights.")
        return None

    # Build the data context for the LLM
    skills_context = []
    for skill_name, data in user_skill_data.items():
        market_avg = market_avgs.get(skill_name, {}).get('avg', 65)
        skills_context.append({
            'skill': skill_name,
            'user_score': data['score'],
            'market_avg': market_avg,
            'sub_scores': data['sub_scores'],
            'is_in_demand': skill_name in in_demand,
        })

    untested_context = [{'skill': u['name'], 'test_title': u['test_title'], 'is_in_demand': u['name'] in in_demand} for u in untested_skills[:5]]

    prompt = f"""You are an expert career coach and technical skills analyst. Analyze this candidate's verified skill assessment data and generate a personalized skill gap analysis with an actionable learning roadmap.

CANDIDATE DATA:
{json.dumps(skills_context, indent=2)}

UNTESTED SKILLS AVAILABLE ON PLATFORM:
{json.dumps(untested_context, indent=2)}

Return ONLY valid JSON (no markdown, no preamble) in this EXACT structure:
{{
  "readiness_score": <int 0-100, overall career readiness based on all scores and coverage>,
  "gap_analysis": [
    {{
      "skill": "<skill name>",
      "score": <their score>,
      "market_avg": <market avg>,
      "status": "above" | "at" | "below",
      "delta": <score minus market_avg>,
      "tips": ["<specific actionable tip 1>", "<specific actionable tip 2>"]
    }}
  ],
  "roadmap": [
    {{
      "order": <1-5>,
      "title": "<concise action title>",
      "description": "<1-2 sentence explanation of why and what to do>",
      "priority": "high" | "medium" | "low",
      "estimated_minutes": <int>
    }}
  ]
}}

Rules:
1. Be specific and actionable in tips — reference actual sub_score areas.
2. Prioritize in-demand skills in the roadmap.
3. Include untested in-demand skills in the roadmap.
4. Order roadmap items by impact (highest impact first).
5. Maximum 5 roadmap items, maximum analysis entries for all tested skills.
6. Do not invent skills or scores not in the data."""

    try:
        from config.ai_service import call_groq_json
        result = call_groq_json([{"role": "user", "content": prompt}], temperature=0.2, max_tokens=1500)
        if not result or not isinstance(result, dict):
            raise ValueError("Invalid Groq JSON response structure")

        # Validate and enrich with data the LLM shouldn't generate
        readiness_score = result.get('readiness_score', 0)
        if not isinstance(readiness_score, int) or readiness_score < 0 or readiness_score > 100:
            scores = [d['score'] for d in user_skill_data.values()]
            readiness_score = round(sum(scores) / len(scores)) if scores else 0

        # Ensure radar_data uses real scores (not LLM-generated)
        radar_data = []
        for skill_name, data in user_skill_data.items():
            market_avg = market_avgs.get(skill_name, {}).get('avg', 65)
            radar_data.append({
                'skill': skill_name,
                'score': data['score'],
                'market_avg': market_avg,
            })

        # Enrich roadmap items with test IDs from our database
        roadmap = result.get('roadmap', [])
        for item in roadmap:
            # Try to match roadmap items to actual tests
            if 'test_id' not in item or not item.get('test_id'):
                title_lower = item.get('title', '').lower()
                # Search across skill names
                for skill_name, data in user_skill_data.items():
                    if skill_name.lower() in title_lower:
                        cat_id = market_avgs.get(skill_name, {}).get('category_id')
                        test = SkillTest.objects.filter(category_id=cat_id, is_active=True).first() if cat_id else None
                        if test:
                            item['test_id'] = test.id
                            item['test_title'] = test.title
                            item['action_type'] = 'retake_test'
                        break
                else:
                    # Check untested skills
                    for us in untested_skills:
                        if us['name'].lower() in title_lower:
                            item['test_id'] = us['test_id']
                            item['test_title'] = us['test_title']
                            item['action_type'] = 'take_test'
                            break

            # Ensure action_type exists
            if 'action_type' not in item:
                item['action_type'] = 'practice'

        # Find strongest/weakest from real data
        sorted_skills = sorted(user_skill_data.items(), key=lambda x: x[1]['score'])
        weakest = sorted_skills[0] if sorted_skills else None
        strongest = sorted_skills[-1] if sorted_skills else None

        # Validate gap_analysis entries against real data
        gap_analysis = result.get('gap_analysis', [])
        for ga in gap_analysis:
            skill_name = ga.get('skill', '')
            if skill_name in user_skill_data:
                # Enforce real scores
                ga['score'] = user_skill_data[skill_name]['score']
                ga['market_avg'] = market_avgs.get(skill_name, {}).get('avg', 65)
                ga['delta'] = ga['score'] - ga['market_avg']
                ga['is_in_demand'] = skill_name in in_demand

        return {
            'readiness_score': readiness_score,
            'strongest_skill': {'name': strongest[0], 'score': strongest[1]['score']} if strongest else None,
            'weakest_skill': {'name': weakest[0], 'score': weakest[1]['score']} if weakest else None,
            'radar_data': radar_data,
            'gap_analysis': gap_analysis,
            'roadmap': roadmap[:5],
            'scoring_method': 'ai',
        }

    except Exception as e:
        logger.warning(f"Groq insight generation failed: {e}")
        return None


def generate_skill_insights(user):
    """
    Main entry point. Generates (or returns cached) skill insights for a user.
    Uses AI when available, falls back to rule-based analysis.
    """
    # Check if we have a cached insight that's still valid
    current_attempt_count = TestAttempt.objects.filter(
        user=user, status='completed'
    ).count()

    if current_attempt_count == 0:
        return None  # No data to analyze

    cached = SkillInsight.objects.filter(user=user).first()
    if cached and cached.last_attempt_count == current_attempt_count:
        # Return cached result
        return {
            'readiness_score': cached.readiness_score,
            'strongest_skill': cached.strongest_skill,
            'weakest_skill': cached.weakest_skill,
            'radar_data': cached.radar_data,
            'gap_analysis': cached.gap_analysis,
            'roadmap': cached.roadmap,
            'scoring_method': cached.scoring_method,
            'generated_at': cached.generated_at.isoformat(),
            'cached': True,
        }

    # Generate fresh insights
    user_skill_data = _get_user_skill_data(user)
    if not user_skill_data:
        return None

    market_avgs = _compute_market_averages()
    in_demand = _get_in_demand_skills()
    untested_skills = _get_untested_skills(user, user_skill_data)

    # Try AI first, fall back to rules
    result = _ai_insights(user, user_skill_data, market_avgs, in_demand, untested_skills)
    if not result:
        result = _fallback_insights(user, user_skill_data, market_avgs, in_demand, untested_skills)

    if not result:
        return None

    # Cache the result
    SkillInsight.objects.filter(user=user).delete()  # Remove old cache
    SkillInsight.objects.create(
        user=user,
        readiness_score=result['readiness_score'],
        radar_data=result['radar_data'],
        gap_analysis=result['gap_analysis'],
        roadmap=result['roadmap'],
        strongest_skill=result.get('strongest_skill'),
        weakest_skill=result.get('weakest_skill'),
        scoring_method=result['scoring_method'],
        last_attempt_count=current_attempt_count,
    )

    result['cached'] = False
    return result
