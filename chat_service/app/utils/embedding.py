import logging
import openai
from typing import List, Optional
import numpy as np
from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_text_embedding(text: str) -> Optional[List[float]]:
    """
    Get text embedding using OpenAI's embedding model.

    Args:
        text (str): Text to embed

    Returns:
        Optional[List[float]]: Vector embedding or None if error
    """
    try:
        # Use OpenAI's embedding model
        response = await openai.Embedding.acreate(
            input=text, model=settings.EMBEDDING_MODEL
        )

        # Extract embedding from response
        embedding = response["data"][0]["embedding"]
        return embedding
    except Exception as e:
        logger.error(f"Error getting text embedding: {e}")
        return None


async def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1 (List[float]): First vector
        vec2 (List[float]): Second vector

    Returns:
        float: Cosine similarity (0-1)
    """
    if not vec1 or not vec2:
        return 0.0

    # Convert to numpy arrays
    v1 = np.array(vec1)
    v2 = np.array(vec2)

    # Calculate cosine similarity
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)

    # Avoid division by zero
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0

    return dot_product / (norm_v1 * norm_v2)
