"""Service for prompt caching with exact match and semantic similarity."""
import os
import json
import hashlib
import time
from typing import Optional, Dict, Any, Tuple, List
from dotenv import load_dotenv

load_dotenv()

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

# Import embedding service
from commander.services.embedding_service import (
    get_embedding,
    cosine_similarity,
    get_embedding_hash
)

# Configuration
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SEMANTIC_CACHE_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.85"))
CACHE_TTL_EXAMPLES = int(os.getenv("CACHE_TTL_EXAMPLES", "604800"))  # 7 days in seconds
CACHE_TTL_EVALUATION = int(os.getenv("CACHE_TTL_EVALUATION", "86400"))  # 24 hours in seconds
CACHE_TTL_DEFAULT = int(os.getenv("CACHE_TTL_DEFAULT", "86400"))  # 24 hours

# Initialize Redis client
redis_client = None
if REDIS_AVAILABLE and CACHE_ENABLED:
    try:
        # Handle TLS connections (rediss://) for Upstash and other providers
        if REDIS_URL.startswith("rediss://"):
            # For TLS connections, use ssl_cert_reqs=None to allow self-signed certs
            # The rediss:// URL already indicates TLS, so we don't need ssl=True
            redis_client = redis.from_url(
                REDIS_URL,
                decode_responses=True,
                ssl_cert_reqs=None
            )
        else:
            redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        
        # Test connection
        redis_client.ping()
        print("DEBUG: Redis connection established for caching")
    except Exception as e:
        print(f"WARNING: Redis not available, using in-memory cache: {e}")
        import traceback
        traceback.print_exc()
        redis_client = None

# In-memory fallback cache
_memory_cache: Dict[str, Tuple[Any, float]] = {}
_memory_semantic_cache: Dict[str, List[Tuple[str, List[float], Any]]] = {}  # task_type -> [(prompt_hash, embedding, result), ...]


def _get_cache_ttl(task_type: str) -> int:
    """Get TTL for a task type."""
    if "example" in task_type.lower() or "generation" in task_type.lower():
        return CACHE_TTL_EXAMPLES
    elif "evaluation" in task_type.lower() or "validation" in task_type.lower():
        return CACHE_TTL_EVALUATION
    else:
        return CACHE_TTL_DEFAULT


def _get_exact_cache_key(prompt: str, task_type: str, temperature: float) -> str:
    """Generate exact cache key."""
    cache_key = f"{prompt}|{task_type}|{temperature}"
    prompt_hash = hashlib.md5(cache_key.encode()).hexdigest()
    return f"exact:{task_type}:{prompt_hash}"


def _get_semantic_cache_key(task_type: str, embedding_hash: str) -> str:
    """Generate semantic cache key."""
    return f"semantic:{task_type}:{embedding_hash}"


def get_cached_result(
    prompt: str,
    task_type: str = "default",
    temperature: float = 0.7
) -> Optional[Any]:
    """
    Get cached result for a prompt (exact match first, then semantic).
    
    Args:
        prompt: The prompt to look up
        task_type: Type of task (for cache key organization)
        temperature: Temperature used (affects cache key)
        
    Returns:
        Cached result if found, None otherwise
    """
    if not CACHE_ENABLED:
        return None
    
    # Step 1: Check exact cache
    exact_key = _get_exact_cache_key(prompt, task_type, temperature)
    
    if redis_client:
        try:
            cached = redis_client.get(exact_key)
            if cached:
                print(f"DEBUG: Cache HIT (exact) for task: {task_type}")
                return json.loads(cached)
        except Exception as e:
            print(f"WARNING: Redis exact cache lookup failed: {e}")
    else:
        # In-memory exact cache
        if exact_key in _memory_cache:
            result, expiry = _memory_cache[exact_key]
            if time.time() < expiry:
                print(f"DEBUG: Cache HIT (exact, memory) for task: {task_type}")
                return result
            else:
                del _memory_cache[exact_key]
    
    # Step 2: Check semantic cache
    prompt_embedding = get_embedding(prompt)
    if not prompt_embedding:
        return None  # Can't do semantic search without embedding
    
    embedding_hash = get_embedding_hash(prompt_embedding)
    semantic_key = _get_semantic_cache_key(task_type, embedding_hash)
    
    if redis_client:
        try:
            # Get all semantic cache entries for this task type
            # Limit to first 50 keys to avoid performance issues
            pattern = f"semantic:{task_type}:*"
            keys = redis_client.keys(pattern)[:50]  # Limit to 50 entries for performance
            
            best_match = None
            best_similarity = 0.0
            
            for key in keys:
                try:
                    cached_data = redis_client.get(key)
                    if cached_data:
                        data = json.loads(cached_data)
                        cached_embedding = data.get("embedding")
                        cached_result = data.get("result")
                        
                        if cached_embedding:
                            similarity = cosine_similarity(prompt_embedding, cached_embedding)
                            if similarity > best_similarity and similarity >= SEMANTIC_CACHE_THRESHOLD:
                                best_similarity = similarity
                                best_match = cached_result
                                
                                # Early exit if we find a very high similarity match
                                if best_similarity >= 0.95:
                                    break
                except Exception as e:
                    continue
            
            if best_match:
                print(f"DEBUG: Cache HIT (semantic, similarity={best_similarity:.3f}) for task: {task_type}")
                return best_match
                
        except Exception as e:
            print(f"WARNING: Redis semantic cache lookup failed: {e}")
    else:
        # In-memory semantic cache
        if task_type in _memory_semantic_cache:
            best_match = None
            best_similarity = 0.0
            
            for prompt_hash, cached_embedding, cached_result in _memory_semantic_cache[task_type]:
                similarity = cosine_similarity(prompt_embedding, cached_embedding)
                if similarity > best_similarity and similarity >= SEMANTIC_CACHE_THRESHOLD:
                    best_similarity = similarity
                    best_match = cached_result
            
            if best_match:
                print(f"DEBUG: Cache HIT (semantic, memory, similarity={best_similarity:.3f}) for task: {task_type}")
                return best_match
    
    print(f"DEBUG: Cache MISS for task: {task_type}")
    return None


def set_cached_result(
    prompt: str,
    result: Any,
    task_type: str = "default",
    temperature: float = 0.7
) -> None:
    """
    Store result in cache (both exact and semantic).
    
    Args:
        prompt: The prompt that generated the result
        result: The result to cache
        task_type: Type of task
        temperature: Temperature used
    """
    if not CACHE_ENABLED:
        return
    
    ttl = _get_cache_ttl(task_type)
    
    # Store in exact cache
    exact_key = _get_exact_cache_key(prompt, task_type, temperature)
    
    if redis_client:
        try:
            redis_client.setex(exact_key, ttl, json.dumps(result))
        except Exception as e:
            print(f"WARNING: Failed to store in Redis exact cache: {e}")
    else:
        # In-memory exact cache
        expiry = time.time() + ttl
        _memory_cache[exact_key] = (result, expiry)
    
    # Store in semantic cache
    prompt_embedding = get_embedding(prompt)
    if prompt_embedding:
        embedding_hash = get_embedding_hash(prompt_embedding)
        semantic_key = _get_semantic_cache_key(task_type, embedding_hash)
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        
        semantic_data = {
            "embedding": prompt_embedding,
            "result": result,
            "prompt_hash": prompt_hash,
            "timestamp": time.time()
        }
        
        if redis_client:
            try:
                redis_client.setex(semantic_key, ttl, json.dumps(semantic_data))
            except Exception as e:
                print(f"WARNING: Failed to store in Redis semantic cache: {e}")
        else:
            # In-memory semantic cache
            if task_type not in _memory_semantic_cache:
                _memory_semantic_cache[task_type] = []
            
            # Add to list (limit to 100 entries per task type to prevent memory bloat)
            _memory_semantic_cache[task_type].append((prompt_hash, prompt_embedding, result))
            if len(_memory_semantic_cache[task_type]) > 100:
                _memory_semantic_cache[task_type].pop(0)  # Remove oldest
    
    print(f"DEBUG: Cached result for task: {task_type}")


def clear_cache(task_type: Optional[str] = None) -> None:
    """
    Clear cache entries.
    
    Args:
        task_type: If provided, clear only this task type. Otherwise clear all.
    """
    if redis_client:
        try:
            if task_type:
                pattern = f"*:{task_type}:*"
            else:
                pattern = "*"
            
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
                print(f"DEBUG: Cleared {len(keys)} cache entries")
        except Exception as e:
            print(f"WARNING: Failed to clear Redis cache: {e}")
    else:
        # Clear in-memory cache
        if task_type:
            keys_to_delete = [k for k in _memory_cache.keys() if f":{task_type}:" in k]
            for key in keys_to_delete:
                del _memory_cache[key]
            if task_type in _memory_semantic_cache:
                del _memory_semantic_cache[task_type]
        else:
            _memory_cache.clear()
            _memory_semantic_cache.clear()
        print(f"DEBUG: Cleared in-memory cache")

