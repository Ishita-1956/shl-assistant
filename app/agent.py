"""
LLM-powered conversational agent for SHL assessment recommendations.
Uses Groq API (free) with Llama model for multi-turn conversation.
"""
import os
import json
import re
import logging
import traceback
from dotenv import load_dotenv
from openai import OpenAI
try:
    from app.retriever import search_assessments
    from app.prompts import SYSTEM_PROMPT, QUERY_EXTRACTION_PROMPT
except ImportError:
    from retriever import search_assessments
    from prompts import SYSTEM_PROMPT, QUERY_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# Use Groq API (free tier) — OpenAI-compatible
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MODEL = "llama-3.3-70b-versatile"

if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY not set in .env! Get a free key at https://console.groq.com")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url=GROQ_BASE_URL,
)


def _build_conversation_text(messages) -> str:
    """Build a plaintext version of the conversation for query extraction."""
    lines = []
    for msg in messages:
        role = msg.role if hasattr(msg, 'role') else msg.get('role', '')
        content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
        lines.append(f"{role.upper()}: {content}")
    return "\n".join(lines)


def _extract_search_query(messages) -> str:
    """Use LLM to extract a focused search query from the conversation."""
    conversation_text = _build_conversation_text(messages)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": QUERY_EXTRACTION_PROMPT.format(conversation=conversation_text)}
            ],
            temperature=0.0,
            max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Query extraction failed: {e}")
        # Fallback: use the last user message as the search query
        for msg in reversed(messages):
            role = msg.role if hasattr(msg, 'role') else msg.get('role', '')
            content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
            if role == "user":
                return content
        return ""


def _format_catalog_context(items: list) -> str:
    """Format retrieved catalog items for injection into the system prompt."""
    if not items:
        return "No matching items found in the catalog."

    lines = []
    for i, item in enumerate(items, 1):
        lines.append(f"""--- Product {i} ---
Name: {item['name']}
URL: {item['url']}
Test Type: {item['test_type']}
Keys: {item['keys']}
Duration: {item.get('duration') or 'Not specified'}
Languages: {item.get('languages') or 'Not specified'}
Job Levels: {item.get('job_levels', '')}
Description: {item.get('description', '')}
Remote: {item.get('remote', '')}
Adaptive: {item.get('adaptive', '')}""")

    return "\n\n".join(lines)


def _parse_llm_response(raw_text: str) -> dict:
    """Parse the LLM's JSON response, handling markdown code fences."""
    text = raw_text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from the text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError:
                parsed = {
                    "reply": raw_text,
                    "recommendations": None,
                    "end_of_conversation": False
                }
        else:
            parsed = {
                "reply": raw_text,
                "recommendations": None,
                "end_of_conversation": False
            }

    # Normalize recommendations
    recs = parsed.get("recommendations")
    if recs is not None and not isinstance(recs, list):
        parsed["recommendations"] = None
    if isinstance(recs, list) and len(recs) == 0:
        parsed["recommendations"] = None

    return parsed


def generate_reply(messages) -> dict:
    """
    Generate a reply given the conversation history.
    """
    try:
        # Step 1: Extract search query
        search_query = _extract_search_query(messages)
        logger.info(f"Search query: {search_query}")

        # Step 2: Retrieve catalog items
        catalog_items = search_assessments(search_query, top_k=15)
        logger.info(f"Retrieved {len(catalog_items)} catalog items")

        # Step 3: Build system prompt with catalog context
        catalog_context = _format_catalog_context(catalog_items)
        system_prompt = SYSTEM_PROMPT.format(catalog_context=catalog_context)

        # Step 4: Build messages for LLM
        llm_messages = [{"role": "system", "content": system_prompt}]

        for msg in messages:
            role = msg.role if hasattr(msg, 'role') else msg.get('role', '')
            content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
            llm_messages.append({"role": role, "content": content})

        # Step 5: Call LLM (Groq with Llama)
        response = client.chat.completions.create(
            model=MODEL,
            messages=llm_messages,
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )

        raw_text = response.choices[0].message.content
        logger.info(f"LLM raw response length: {len(raw_text)}")

        # Step 6: Parse response
        parsed = _parse_llm_response(raw_text)

        result = {
            "reply": parsed.get("reply", "I'm having trouble processing your request."),
            "recommendations": parsed.get("recommendations"),
            "end_of_conversation": parsed.get("end_of_conversation", False)
        }

        # Clean up recommendations to match schema
        if result["recommendations"] is not None:
            cleaned_recs = []
            for rec in result["recommendations"]:
                cleaned_recs.append({
                    "name": rec.get("name", ""),
                    "url": rec.get("url", ""),
                    "test_type": rec.get("test_type", "K"),
                    "keys": rec.get("keys", ""),
                    "duration": rec.get("duration", ""),
                    "languages": rec.get("languages", ""),
                })
            result["recommendations"] = cleaned_recs

        return result

    except Exception as e:
        logger.error(f"generate_reply error: {traceback.format_exc()}")
        raise