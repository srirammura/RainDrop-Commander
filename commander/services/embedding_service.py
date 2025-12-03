"""Service to generate embeddings for semantic caching."""
import os
import hashlib
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

# Try to import OpenAI for embeddings
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"

# Initialize OpenAI client if available
openai_client = None
if OPENAI_AVAILABLE and OPENAI_API_KEY and CACHE_ENABLED:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"WARNING: Failed to initialize OpenAI client for embeddings: {e}")
        openai_client = None


def get_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding for text using OpenAI embeddings API.
    
    Args:
        text: Text to generate embedding for
        
    Returns:
        Embedding vector as list of floats, or None if unavailable
    """
    if not CACHE_ENABLED:
        return None
        
    if not openai_client:
        return None
    
    if not text or len(text.strip()) == 0:
        return None
    
    try:
        # Truncate very long text (embeddings have token limits)
        max_chars = 8000  # Safe limit for embedding models
        text_to_embed = text[:max_chars] if len(text) > max_chars else text
        
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text_to_embed
        )
        
        if response and response.data and len(response.data) > 0:
            return response.data[0].embedding
        else:
            return None
            
    except Exception as e:
        print(f"WARNING: Failed to generate embedding: {e}")
        return None


def cosine_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    Calculate cosine similarity between two embeddings.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        Cosine similarity score (0.0 to 1.0)
    """
    if not embedding1 or not embedding2:
        return 0.0
    
    if len(embedding1) != len(embedding2):
        return 0.0
    
    try:
        import numpy as np
        
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return float(similarity)
        
    except ImportError:
        # Fallback calculation without numpy
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = sum(a * a for a in embedding1) ** 0.5
        norm2 = sum(b * b for b in embedding2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    except Exception as e:
        print(f"WARNING: Failed to calculate cosine similarity: {e}")
        return 0.0


def get_embedding_hash(embedding: List[float]) -> str:
    """
    Generate a hash for an embedding vector (for Redis key).
    
    Args:
        embedding: Embedding vector
        
    Returns:
        Hash string
    """
    if not embedding:
        return ""
    
    # Convert embedding to string representation and hash it
    embedding_str = ",".join([f"{v:.6f}" for v in embedding[:10]])  # Use first 10 dimensions for hash
    return hashlib.md5(embedding_str.encode()).hexdigest()

