"""
Evaluation script for the SHL Assessment Recommender API.
Measures retrieval quality, recommendation relevance, and groundedness.
"""
import os
import json
import logging
from app.retriever import search_assessments
from app.agent import client, MODEL, SYSTEM_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample test cases
TEST_CASES = [
    {
        "query": "senior software engineer with Java and cloud",
        "expected_keywords": ["Java", "Cloud", "Software"],
        "expected_test_type": "K" # Knowledge & Skills
    },
    {
        "query": "graduate financial analyst with no experience",
        "expected_keywords": ["Graduate", "Financial", "Analytical", "Numerical", "Scenarios"],
        "expected_test_type": "A" # Ability or Biodata
    },
    {
        "query": "entry level contact center customer service",
        "expected_keywords": ["Customer Service", "Contact Center", "Simulation", "Entry-Level"],
        "expected_test_type": "S" # Simulation or Personality
    }
]

def evaluate_retrieval():
    """Evaluates the ChromaDB retrieval accuracy based on keywords."""
    logger.info("--- Evaluating Retrieval Quality ---")
    total_score = 0
    max_score = len(TEST_CASES) * 3

    for case in TEST_CASES:
        results = search_assessments(case["query"], top_k=5)
        
        # Check if expected keywords appear in retrieved item names or descriptions
        keyword_hits = 0
        for res in results:
            text = (res['name'] + " " + res['description']).lower()
            for kw in case["expected_keywords"]:
                if kw.lower() in text:
                    keyword_hits += 1
                    break # count at most one hit per result to avoid skew
                    
        # Score 0-3 based on hits
        score = min(3, keyword_hits)
        total_score += score
        logger.info(f"Query: '{case['query']}' -> Score: {score}/3")
        
    accuracy = (total_score / max_score) * 100
    logger.info(f"Retrieval Quality Score: {accuracy:.1f}%\n")
    return accuracy

def evaluate_groundedness():
    """Evaluates if the LLM relies only on the provided catalog (no hallucinations)."""
    logger.info("--- Evaluating Groundedness ---")
    
    query = "We need an assessment for Rust programming and Elixir."
    # We know Rust/Elixir might not be in the catalog natively. Let's see if the LLM hallucinates it.
    
    # 1. Retrieve
    catalog_items = search_assessments(query, top_k=5)
    
    # 2. Format catalog
    context = ""
    for i, item in enumerate(catalog_items, 1):
        context += f"Name: {item['name']}\n"
    
    system_prompt = SYSTEM_PROMPT.format(catalog_context=context)
    
    # 3. Call LLM
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        reply = json.loads(response.choices[0].message.content)
        recs = reply.get("recommendations")
        
        # Groundedness Check: If recs exist, do they exactly match the retrieved catalog?
        if recs:
            retrieved_names = [item['name'] for item in catalog_items]
            hallucinated = []
            for rec in recs:
                if rec['name'] not in retrieved_names:
                    hallucinated.append(rec['name'])
            
            if hallucinated:
                logger.error(f"Groundedness Failed: Hallucinated {hallucinated}")
                return False
            else:
                logger.info("Groundedness Passed: All recommendations exist in the catalog context.")
                return True
        else:
            logger.info("Groundedness Passed: LLM correctly refused to recommend non-existent products.")
            return True
            
    except Exception as e:
        logger.error(f"Groundedness evaluation error: {e}")
        return False

if __name__ == "__main__":
    evaluate_retrieval()
    evaluate_groundedness()
