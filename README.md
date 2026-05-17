# SHL Assessment Recommender

A conversational recommendation engine built to streamline the process of finding relevant SHL assessment products for talent acquisition, development, and management.

## Tech Stack

- **Backend / API:** FastAPI, Python 3
- **Conversational Engine:** Groq API (Llama-3.3-70b-versatile)
- **Vector Database / Search:** ChromaDB
- **Embeddings:** sentence-transformers (`all-MiniLM-L6-v2`)
- **Frontend:** HTML5, CSS3, Vanilla JavaScript

## Functionality

The application solves the problem of navigating a complex catalog of over 400 SHL assessment products by providing a conversational interface. 
- **Semantic Search:** Embeds the product catalog (names, descriptions, target job levels, assessment types) and retrieves the most relevant candidates based on the user's natural language queries.
- **Conversational Refinement:** The LLM acts as an expert consultant, asking clarifying questions when queries are too broad and filtering recommendations based on specific constraints (e.g., role, seniority, cognitive vs. personality assessments).
- **Structured Data Extraction:** The LLM reliably formats recommendations into a structured JSON payload, which the frontend renders as an actionable comparison table, highlighting test types, durations, and languages.

## Setup & Installation

### Prerequisites
- Python 3.9+
- A free Groq API key (`GROQ_API_KEY`)

### Steps

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   Create a `.env` file in the project root:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

3. **Build the Vector Database**
   Run the setup script to fetch the SHL catalog, generate embeddings, and build the ChromaDB index.
   ```bash
   python setup.py
   ```

4. **Start the Development Server**
   ```bash
   cd app
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access the Application**
   Open your browser and navigate to `http://localhost:8000`.
