# services/embedding_service.py
import os
import logging
from typing import Optional, List
from google import genai

logger = logging.getLogger("embedding_service")

def get_embedding(text: str) -> Optional[List[float]]:
    """Generates vector embedding for text using Google Gemini text-embedding-004 model."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("Gemini API key is not configured. Cannot generate embedding.")
        return None
    try:
        client = genai.Client(api_key=api_key)
        res = client.models.embed_content(
            model="text-embedding-004",
            contents=text
        )
        if res.embeddings and len(res.embeddings) > 0:
            return res.embeddings[0].values
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
    return None
