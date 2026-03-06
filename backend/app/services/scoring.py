import json
import asyncio
import logging
from openai import AsyncOpenAI
from app.config import get_settings

logger = logging.getLogger(__name__)

SCORING_PROMPT = """You are an expert HR interviewer evaluator. Analyze the following phone interview transcript and score the candidate on 6 dimensions.

**Job Description:**
{job_description}

**Interview Transcript:**
{transcript}

Score each dimension from 1.0 to 10.0 (one decimal). Be rigorous but fair.

**Dimensions:**
1. **Communication** — Clarity, articulation, listening skills, professional tone
2. **Experience** — Relevance and depth of past experience to the role
3. **Motivation** — Genuine interest in the role and company, enthusiasm
4. **Availability** — Readiness to start, reasonable notice period/timeline
5. **Cultural Fit** — Values alignment, teamwork orientation, adaptability
6. **Role Fit** — Overall suitability for the specific position requirements

Return your response as a JSON object with EXACTLY this structure (no markdown, no code fences):
{{
    "communication": 7.5,
    "experience": 8.0,
    "motivation": 6.5,
    "availability": 9.0,
    "cultural_fit": 7.0,
    "role_fit": 7.5,
    "overall": 7.6,
    "summary": "2-3 sentence summary of the candidate's strengths and areas of concern."
}}

The "overall" score should be a weighted average: Experience (25%), Role Fit (25%), Communication (15%), Motivation (15%), Cultural Fit (10%), Availability (10%).
"""


class ScoringEngine:
    """LLM-powered interview transcript scoring engine (via OpenRouter)."""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.LLM_BASE_URL,
            default_headers={
                "HTTP-Referer": "https://voicescreen.app",
                "X-Title": "VoiceScreen HR Screening",
            },
            max_retries=0,  # We handle retries ourselves
        )
        self.model = settings.LLM_MODEL

    async def score_transcript(
        self, transcript: str, job_description: str = "General role"
    ) -> dict:
        """Score an interview transcript on 6 dimensions.
        
        Retries up to 3 times with exponential backoff for rate limits.
        """
        prompt = SCORING_PROMPT.format(
            job_description=job_description,
            transcript=transcript,
        )

        # Retry with backoff for rate limits
        for attempt in range(4):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert HR evaluation assistant. Always respond with valid JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=500,
                )
                break
            except Exception as e:
                if "429" in str(e) and attempt < 3:
                    wait = (attempt + 1) * 10  # 10s, 20s, 30s
                    logger.warning(f"Rate limited, retrying in {wait}s (attempt {attempt + 1}/3)")
                    await asyncio.sleep(wait)
                else:
                    raise

        content = response.choices[0].message.content
        if not content:
            logger.warning(f"LLM returned empty content for model {self.model}")
            return {
                "communication": 5.0, "experience": 5.0, "motivation": 5.0,
                "availability": 5.0, "cultural_fit": 5.0, "role_fit": 5.0,
                "overall": 5.0,
                "summary": "Scoring returned empty response — using default scores.",
            }
        content = content.strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        try:
            result = json.loads(content)
            # Ensure all scores are floats
            for key in ["communication", "experience", "motivation", "availability", "cultural_fit", "role_fit", "overall"]:
                if key in result:
                    result[key] = float(result[key])
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse scoring response: {str(e)}\nContent: {content[:200]}")
            result = {
                "communication": 5.0,
                "experience": 5.0,
                "motivation": 5.0,
                "availability": 5.0,
                "cultural_fit": 5.0,
                "role_fit": 5.0,
                "overall": 5.0,
                "summary": f"Failed to parse scoring response. Using default scores.",
            }

        return result
