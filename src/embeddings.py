"""
Ollama embeddings integration for semantic search.

Handles local embedding generation using Ollama API.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
import json
from dataclasses import dataclass

import httpx
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""
    base_url: str = "http://localhost:11434"
    model: str = "nomic-embed-text"  # 768 dimensions
    timeout: float = 60.0
    batch_size: int = 32
    max_text_length: int = 8192  # Typical model context limit


class OllamaEmbeddings:
    """Ollama embeddings client for local embedding generation."""
    
    def __init__(self, config: EmbeddingConfig = None):
        self.config = config or EmbeddingConfig()
        self.logger = logging.getLogger(__name__)
        self.client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=httpx.Timeout(self.config.timeout)
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
    
    async def is_model_available(self) -> bool:
        """Check if the embedding model is available in Ollama."""
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            
            models = response.json().get("models", [])
            available_models = [model["name"] for model in models]
            
            is_available = any(
                self.config.model in model_name 
                for model_name in available_models
            )
            
            if not is_available:
                self.logger.warning(
                    f"Model {self.config.model} not found. Available models: {available_models}"
                )
            
            return is_available
            
        except Exception as e:
            self.logger.error(f"Error checking model availability: {e}")
            return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model."""
        try:
            response = await self.client.post("/api/show", json={"name": self.config.model})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error getting model info: {e}")
            return {}
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for embedding generation.
        
        Handles long texts by truncating or chunking as needed.
        """
        if not text or not text.strip():
            return ""
        
        # Clean whitespace
        text = " ".join(text.split())
        
        # Truncate if too long (simple strategy)
        if len(text) > self.config.max_text_length:
            self.logger.debug(f"Truncating text from {len(text)} to {self.config.max_text_length} chars")
            text = text[:self.config.max_text_length]
        
        return text
    
    async def embed_single(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Normalized embedding vector as numpy array
        """
        processed_text = self._preprocess_text(text)
        if not processed_text:
            self.logger.warning("Empty text provided for embedding")
            # Return zero vector with correct dimensions
            return np.zeros(768, dtype=np.float32)
        
        try:
            response = await self.client.post(
                "/api/embeddings",
                json={
                    "model": self.config.model,
                    "prompt": processed_text
                }
            )
            response.raise_for_status()
            
            result = response.json()
            embedding = np.array(result["embedding"], dtype=np.float32)
            
            # Normalize for cosine similarity
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            return embedding
            
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error generating embedding: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            self.logger.error(f"Error generating embedding: {e}")
            raise
    
    async def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of normalized embedding vectors
        """
        if not texts:
            return []
        
        embeddings = []
        
        # Process in batches to manage memory and API limits
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            batch_embeddings = []
            
            self.logger.debug(f"Processing batch {i//self.config.batch_size + 1}: {len(batch)} texts")
            
            # Process batch items concurrently
            tasks = [self.embed_single(text) for text in batch]
            
            try:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Error embedding text {i+j}: {result}")
                        # Add zero vector for failed embeddings
                        batch_embeddings.append(np.zeros(768, dtype=np.float32))
                    else:
                        batch_embeddings.append(result)
                
                embeddings.extend(batch_embeddings)
                
            except Exception as e:
                self.logger.error(f"Batch embedding failed: {e}")
                # Add zero vectors for entire failed batch
                embeddings.extend([np.zeros(768, dtype=np.float32)] * len(batch))
        
        self.logger.info(f"Generated embeddings for {len(texts)} texts")
        return embeddings
    
    async def embed_conversations(self, message_contents: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings specifically for conversation messages.
        
        Handles conversation-specific preprocessing and chunking.
        """
        if not message_contents:
            return []
        
        self.logger.info(f"Generating embeddings for {len(message_contents)} messages")
        
        # Filter and preprocess conversation messages
        processed_texts = []
        for content in message_contents:
            if content and len(content.strip()) > 10:  # Skip very short messages
                processed_texts.append(self._preprocess_conversation_message(content))
            else:
                processed_texts.append("")  # Empty for short messages
        
        return await self.embed_batch(processed_texts)
    
    def _preprocess_conversation_message(self, content: str) -> str:
        """Specialized preprocessing for conversation messages."""
        if not content:
            return ""
        
        # Clean common artifacts from Claude conversations
        content = content.strip()
        
        # Remove excessive whitespace
        content = " ".join(content.split())
        
        # Handle very long messages by taking the first part (often most relevant)
        if len(content) > self.config.max_text_length:
            # Try to break at sentence boundaries
            sentences = content.split('. ')
            truncated = ""
            for sentence in sentences:
                if len(truncated + sentence) < self.config.max_text_length:
                    truncated += sentence + ". "
                else:
                    break
            
            if truncated:
                content = truncated.strip()
            else:
                content = content[:self.config.max_text_length]
        
        return content


async def test_ollama_embeddings(config: EmbeddingConfig = None):
    """Test Ollama embeddings functionality."""
    config = config or EmbeddingConfig()
    
    async with OllamaEmbeddings(config) as embedder:
        # Check model availability
        if not await embedder.is_model_available():
            raise RuntimeError(f"Model {config.model} not available in Ollama")
        
        # Get model info
        model_info = await embedder.get_model_info()
        logger.info(f"Model info: {model_info.get('details', {})}")
        
        # Test single embedding
        test_text = "This is a test message for embedding generation."
        embedding = await embedder.embed_single(test_text)
        
        logger.info(f"Generated embedding with shape: {embedding.shape}")
        logger.info(f"Embedding norm: {np.linalg.norm(embedding):.4f}")
        
        # Test batch embeddings
        test_texts = [
            "First test message about database optimization",
            "Second message discussing API implementation",
            "Third message about frontend development"
        ]
        
        embeddings = await embedder.embed_batch(test_texts)
        logger.info(f"Generated {len(embeddings)} batch embeddings")
        
        # Test similarity
        if len(embeddings) >= 2:
            similarity = np.dot(embeddings[0], embeddings[1])
            logger.info(f"Similarity between first two embeddings: {similarity:.4f}")
        
        return embeddings


if __name__ == "__main__":
    # Quick test
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        try:
            config = EmbeddingConfig(model="nomic-embed-text")
            embeddings = await test_ollama_embeddings(config)
            print(f"✓ Generated {len(embeddings)} test embeddings")
            print(f"✓ Embedding dimension: {embeddings[0].shape[0]}")
        except Exception as e:
            print(f"✗ Embedding test failed: {e}")
            return 1
        return 0
    
    sys.exit(asyncio.run(main()))