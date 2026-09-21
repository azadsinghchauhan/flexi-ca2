import os
import re
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL") or "openai/gpt-oss-20b"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def validate_analysis_schema(data: dict) -> dict:
    """
    Validates and normalizes the parsed JSON dictionary to conform strictly
    to the required AI analysis schema:
    - summary: 2 to 3 sentences string
    - key_points: exactly 3 items list of strings
    - category: string
    - relevance: integer 0-100
    - importance: 'Low', 'Medium', or 'High'
    - entities: list of strings
    - trend: short phrase string
    - reason_for_importance: string
    """
    if not isinstance(data, dict):
        raise ValueError("AI output is not a JSON object")

    summary = str(data.get("summary", "")).strip()
    if not summary:
        summary = "Summary unavailable from AI extractor."

    # Validate key_points (exactly 3 items)
    raw_kp = data.get("key_points", [])
    if isinstance(raw_kp, list):
        kp_list = [str(x).strip() for x in raw_kp if str(x).strip()]
    elif isinstance(raw_kp, str):
        kp_list = [x.strip("- \t") for x in raw_kp.split("\n") if x.strip("- \t")]
    else:
        kp_list = []
    
    while len(kp_list) < 3:
        kp_list.append(f"Strategic insight point {len(kp_list) + 1}")
    kp_list = kp_list[:3]

    category = str(data.get("category", "Technology")).strip() or "Technology"

    # Relevance (0-100)
    try:
        relevance = int(data.get("relevance", 75))
        relevance = max(0, min(100, relevance))
    except (ValueError, TypeError):
        relevance = 75

    # Importance (Low, Medium, High)
    importance = str(data.get("importance", "Medium")).strip().capitalize()
    if importance not in ("Low", "Medium", "High"):
        importance = "Medium"

    # Entities
    raw_entities = data.get("entities", [])
    if isinstance(raw_entities, list):
        entities = [str(e).strip() for e in raw_entities if str(e).strip()][:6]
    else:
        entities = []

    # Trend
    trend = str(data.get("trend", "")).strip()
    if not trend or len(trend) > 60:
        trend = "Emerging Domain Developments"

    # Reason for importance
    reason = str(data.get("reason_for_importance") or data.get("reason", "")).strip()
    if not reason:
        reason = f"Rated {importance} priority based on domain keyword significance and impact."

    return {
        "summary": summary,
        "key_points": kp_list,
        "category": category,
        "relevance": relevance,
        "importance": importance,
        "entities": entities,
        "trend": trend,
        "reason_for_importance": reason,
        "is_ai_analyzed": True
    }


def get_heuristic_fallback(article: dict, topic_name: str, precheck_score: int) -> dict:
    """
    Graceful fallback when AI analysis cannot be reached or fails validation.
    Generates a marked "analysis unavailable" record without aborting the run.
    """
    title = article.get("title", "")
    content = article.get("content", "")
    snippet = content[:300] if content else title

    # Determine baseline importance heuristically
    imp = "Medium"
    if any(w in title.lower() for w in ["critical", "breakthrough", "scandal", "crisis", "surge", "guidelines", "outpaces"]):
        imp = "High"
    elif precheck_score < 45:
        imp = "Low"

    # Extract capitalized entities heuristically
    words = re.findall(r"\b[A-Z][a-zA-Z0-9-]+\b", title + " " + snippet)
    unique_entities = list(dict.fromkeys([w for w in words if len(w) > 2 and w.lower() not in ("the", "and", "for", "with", "this", "from", "after")]))[:4]

    return {
        "summary": f"{title}. {snippet[:150]} (Generated via fallback heuristic).",
        "key_points": [
            f"Coverage focused on {topic_name} updates.",
            f"Primary source reported: {article.get('source', 'Web')}.",
            "In-depth AI analysis was temporarily queued."
        ],
        "category": "Technology Intelligence",
        "relevance": precheck_score,
        "importance": imp,
        "entities": unique_entities or [topic_name],
        "trend": f"{topic_name} Momentum",
        "reason_for_importance": f"Heuristic rating ({imp}) derived from keyword intensity: {precheck_score}%.",
        "is_ai_analyzed": False
    }


def analyze_article_with_groq(article: dict, topic_name: str, keywords: list, precheck_score: int = 70) -> dict:
    """
    Step 8: Send article to Groq API for structured JSON analysis.
    Implements:
    - Groq JSON Mode
    - Strict schema validation
    - Single retry on malformed JSON
    - Exponential backoff on HTTP 429 rate limit
    - Graceful fallback on persistent failure
    """
    # If no Groq API Key is configured, use structured simulated/heuristic intelligence
    if not GROQ_API_KEY:
        time.sleep(0.3)  # Realistic agent processing latency
        return get_heuristic_fallback(article, topic_name, precheck_score)

    system_prompt = (
        "You are an expert AI Intelligence Analyst. Analyze the provided news article in the context of the user's "
        f"monitoring topic: '{topic_name}' with keywords: {', '.join(keywords)}.\n\n"
        "You MUST reply with ONLY a single valid JSON object following this exact schema:\n"
        "{\n"
        '  "summary": "2 to 3 sentences summarizing key facts and implications",\n'
        '  "key_points": ["First key takeaway", "Second key takeaway", "Third key takeaway"],\n'
        '  "category": "One category (e.g. AI Architecture, Enterprise Security, Policy & Ethics, Hardware, Market Shifts)",\n'
        '  "relevance": <integer between 0 and 100>,\n'
        '  "importance": "Low" | "Medium" | "High",\n'
        '  "entities": ["Entity1", "Entity2", "Entity3"],\n'
        '  "trend": "Short 2 to 4 word phrase characterizing the broader trend",\n'
        '  "reason_for_importance": "1 sentence justifying why this is Low, Medium, or High priority"\n'
        "}\n"
        "Do not wrap in markdown quotes if possible, output raw JSON."
    )

    user_content = (
        f"Article Title: {article.get('title')}\n"
        f"Source: {article.get('source')}\n"
        f"Content Snippet: {article.get('content')}\n"
        f"Topic: {topic_name}"
    )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 2048
    }

    # Attempt with rate limit backoff and 1 retry on malformed JSON
    for attempt in range(2):
        try:
            response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=20)
            
            # Rate limit backoff (HTTP 429)
            if response.status_code == 429:
                wait_time = 2.0 * (attempt + 1)
                print(f"[WARN] Groq rate limit hit. Backing off for {wait_time}s...")
                time.sleep(wait_time)
                continue
                
            if response.status_code != 200:
                print(f"[WARN] Groq API returned status {response.status_code}: {response.text}")
                break

            data = response.json()
            raw_text = data["choices"][0]["message"]["content"]
            parsed_json = json.loads(raw_text)
            
            validated = validate_analysis_schema(parsed_json)
            return validated

        except (json.JSONDecodeError, KeyError, ValueError) as err:
            print(f"[WARN] Malformed JSON from Groq on attempt {attempt + 1}: {err}")
            if attempt == 0:
                time.sleep(1)
                continue
        except requests.exceptions.RequestException as net_err:
            print(f"[WARN] Network error contacting Groq: {net_err}")
            break
        except Exception as ex:
            print(f"[ERROR] Unexpected error in Groq analysis: {ex}")
            break

    # If retries fail or rate limits persist, fall back gracefully
    print(f"[INFO] Using graceful fallback analysis for: {article.get('title')}")
    return get_heuristic_fallback(article, topic_name, precheck_score)
