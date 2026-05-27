import json
from pydantic import TypeAdapter, BaseModel
from google import genai
from google.genai.types import GenerateContentConfig

from dubbing.config import settings

class TranslationResponse(BaseModel):
    translation: str
    notes: str

def translate_with_peak_alignment(english_text, marked_text, original_duration, anchor_info):
    client = genai.Client(api_key=settings.gemini_api_key)

    anchor_hints = "\n".join([
        f"- Segment {a['segment']}: '{a['word']}' must have EXCITEMENT at {a['fraction']:.0%} into the segment (time: {a['peak_time']:.2f}s)"
        for a in anchor_info
    ])

    lang_name = settings.target_language_name

    prompt = f"""Translate this sports commentary from English to {lang_name}.

ORIGINAL TEXT WITH ANCHOR POINTS:
"{marked_text}"

CRITICAL: Peak timing constraints
These points MUST have emotional excitement/intensity peaks AT THESE EXACT TIMES:
{anchor_hints}

TRANSLATION CONSTRAINTS:
1. Translate as a complete, coherent narrative
2. {lang_name} is denser than English (20-30% fewer syllables) - be concise
3. Total duration should be ~{original_duration:.1f} seconds at natural pace
4. Natural speech patterns - this is live sports commentary
5. DO NOT add excessive punctuation

OUTPUT:
Return ONLY valid JSON:
{{
  "translation": "Complete {lang_name} translation",
  "notes": "Peak alignment strategy and timing"
}}
"""

    print(f"Translating to {lang_name.upper()} with peak alignment...")

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents={'text': prompt},
            config=GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=TypeAdapter(
                    TranslationResponse
                ).json_schema()
            )
        )

        result = json.loads(response.text)
        return result['translation'], result.get('notes', '')

    except Exception as e:
        print(f"ERROR: {e}")
        return None, ""
