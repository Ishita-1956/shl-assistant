"""
FastAPI application for the SHL Assessment Recommendation Assistant.
"""
import os
import logging
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
try:
    from app.schemas import ChatRequest, ChatResponse
    from app.agent import generate_reply
except ImportError:
    from schemas import ChatRequest, ChatResponse
    from agent import generate_reply

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SHL Assessment Recommendation Assistant",
    description="AI-powered assistant for recommending SHL assessment products",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend files
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_frontend():
    """Serve the chat UI."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "SHL Assessment Recommendation API. Use POST /chat to interact."}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        logger.info(f"Chat request with {len(request.messages)} messages")
        response = generate_reply(request.messages)
        logger.info(f"Chat response: recommendations={len(response.get('recommendations') or [])}, end={response.get('end_of_conversation')}")
        return response
    except Exception as e:
        logger.error(f"Chat error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))