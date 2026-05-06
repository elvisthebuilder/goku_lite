import logging
import uuid
import time
import litellm
from qdrant_client import QdrantClient
from qdrant_client.http import models
from .config import config

logger = logging.getLogger(__name__)

class CloudMemory:
    def __init__(self):
        if not config.QDRANT_URL or not config.QDRANT_API_KEY:
            self.client = None
            logger.warning("QDRANT_URL or API_KEY missing. Memory disabled.")
            return

        try:
            self.client = QdrantClient(
                url=config.QDRANT_URL,
                api_key=config.QDRANT_API_KEY,
            )
            self.collection_name = "goku_lite_mem"
            self._ensure_collection()
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant Client: {e}")
            self.client = None

    def _ensure_collection(self):
        if not self.client: return
        try:
            collections = self.client.get_collections().collections
            if not any(c.name == self.collection_name for c in collections):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE), # text-embedding-3-small
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant Cloud: {e}")
            self.client = None

    async def _get_embedding(self, text: str):
        """Fetch embedding from cloud provider."""
        try:
            # Determine provider and model
            model = "text-embedding-3-small" # Default
            api_key = config.OPENAI_API_KEY
            
            if config.GEMINI_API_KEY and not api_key:
                model = "gemini/text-embedding-004"
                api_key = config.GEMINI_API_KEY
            elif "ollama" in config.GOKU_MODEL.lower():
                # If using Ollama, try to use a common embedding model
                model = "ollama/mxbai-embed-large"
                api_key = config.OLLAMA_API_KEY or "ollama"

            if not api_key and not config.OPENAI_API_KEY:
                logger.warning("No API Key found for embeddings. Memory will be disabled for this turn.")
                return None

            resp = await litellm.aembedding(
                model=model,
                input=[text],
                api_key=api_key,
                api_base=config.OLLAMA_API_BASE if "ollama" in model else None
            )
            return resp.data[0]['embedding']
        except Exception as e:
            if "401" in str(e) or "Unauthorized" in str(e):
                logger.warning(f"Memory Note: Embedding provider ({model}) unauthorized. Check keys. Continuing without memory.")
            else:
                logger.error(f"Embedding failed: {e}")
            return None

    async def add_memory(self, text: str, metadata: dict = None):
        if not self.client: return
        vector = await self._get_embedding(text)
        if not vector: return

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload={
                            "text": text, 
                            "timestamp": time.time(), 
                            "metadata": metadata or {}
                        }
                    )
                ]
            )
            logger.info("Memory saved to Qdrant Cloud.")
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    async def search_memory(self, query: str, limit: int = 3):
        if not self.client: return []
        vector = await self._get_embedding(query)
        if not vector: return []

        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=limit
            )
            return [hit.payload for hit in results]
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []

memory = CloudMemory()
