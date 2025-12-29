"""Embedding generation service with caching."""

import hashlib
import json
import logging
import time
from typing import Any

from openai import AsyncOpenAI

from ds_common.metrics.service import get_metrics_service


class EmbeddingService:
    """Service for generating and caching text embeddings."""

    def __init__(
        self,
        openai_client: AsyncOpenAI,
        redis_client: Any | None = None,
        model: str | None = None,
        dimensions: int | None = None,
    ):
        """
        Initialize the embedding service.

        Args:
            openai_client: OpenAI async client (or compatible client for Ollama, etc.)
            redis_client: Optional Redis client for caching
            model: Embedding model name (default: "text-embedding-3-small")
            dimensions: Embedding dimensions (default: 1536)
        """
        self.logger = logging.getLogger(__name__)
        self.openai_client = openai_client
        self.redis_client = redis_client
        self.model = model or "text-embedding-3-small"
        self.dimensions = dimensions or 1536
        self.cache_ttl = 86400 * 30  # 30 days
        self.metrics = get_metrics_service()

    def _get_cache_key(self, text: str) -> str:
        """
        Generate cache key for text.

        Args:
            text: Text to generate key for

        Returns:
            Cache key
        """
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"embedding:{self.model}:{text_hash}"

    async def generate(self, text: str) -> list[float]:
        """
        Generate embedding for text, using cache if available.

        Args:
            text: Text to generate embedding for

        Returns:
            Embedding vector (1536 dimensions)
        """
        cache_key = self._get_cache_key(text)

        # Try to get from cache
        cache_hit = False
        if self.redis_client:
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    self.logger.debug(f"Cache hit for embedding: {cache_key[:20]}...")
                    cache_hit = True
                    return json.loads(cached)
            except Exception as e:
                self.logger.warning(f"Failed to get from cache: {e}")

        # Generate embedding
        start_time = time.time()
        status = "success"
        self.logger.debug(f"Generating embedding for text: {text[:50]}...")
        try:
            response = await self.openai_client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimensions,
            )

            embedding = response.data[0].embedding
        except Exception:
            status = "error"
            raise
        finally:
            duration = time.time() - start_time
            self.metrics.record_embedding_generation(self.model, duration, status)

        # Cache the result
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(embedding),
                )
                self.logger.debug(f"Cached embedding: {cache_key[:20]}...")
            except Exception as e:
                self.logger.warning(f"Failed to cache embedding: {e}")

        return embedding

    async def generate_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to generate embeddings for

        Returns:
            List of embedding vectors
        """
        # Check cache for each text
        results: list[list[float] | None] = [None] * len(texts)
        texts_to_generate: list[tuple[int, str]] = []

        if self.redis_client:
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                try:
                    cached = await self.redis_client.get(cache_key)
                    if cached:
                        results[i] = json.loads(cached)
                    else:
                        texts_to_generate.append((i, text))
                except Exception as e:
                    self.logger.warning(f"Failed to check cache: {e}")
                    texts_to_generate.append((i, text))
        else:
            texts_to_generate = [(i, text) for i, text in enumerate(texts)]

        # Generate embeddings for uncached texts
        if texts_to_generate:
            texts_list = [text for _, text in texts_to_generate]
            self.logger.debug(f"Generating {len(texts_list)} embeddings in batch")
            response = await self.openai_client.embeddings.create(
                model=self.model,
                input=texts_list,
                dimensions=self.dimensions,
            )

            # Store results and cache
            for (i, text), embedding_data in zip(texts_to_generate, response.data):
                embedding = embedding_data.embedding
                results[i] = embedding

                # Cache the result
                if self.redis_client:
                    cache_key = self._get_cache_key(text)
                    try:
                        await self.redis_client.setex(
                            cache_key,
                            self.cache_ttl,
                            json.dumps(embedding),
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to cache embedding: {e}")

        return [emb for emb in results if emb is not None]
