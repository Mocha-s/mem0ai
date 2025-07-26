import os
import warnings
from typing import Literal, Optional

from openai import OpenAI

from mem0.configs.embeddings.base import BaseEmbedderConfig
from mem0.embeddings.base import EmbeddingBase


class OpenAIEmbedding(EmbeddingBase):
    def __init__(self, config: Optional[BaseEmbedderConfig] = None):
        super().__init__(config)

        # Use configuration values which already handle environment variables
        # Set default embedding dimensions based on model
        if self.config.embedding_dims is None:
            if "text-embedding-3-small" in self.config.model:
                self.config.embedding_dims = 1536
            elif "text-embedding-3-large" in self.config.model:
                self.config.embedding_dims = 3072
            else:
                self.config.embedding_dims = 1536  # Default fallback

        # Use configuration values (which already handle environment variables)
        api_key = self.config.api_key
        base_url = self.config.openai_base_url
        # Deprecation warning for old environment variable (handled in config now)
        if os.environ.get("OPENAI_API_BASE") and not os.environ.get("OPENAI_BASE_URL"):
            warnings.warn(
                "The environment variable 'OPENAI_API_BASE' is deprecated and will be removed in the 0.1.80. "
                "Please use 'OPENAI_BASE_URL' instead.",
                DeprecationWarning,
            )

        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def embed(self, text, memory_action: Optional[Literal["add", "search", "update"]] = None):
        """
        Get the embedding for the given text using OpenAI.

        Args:
            text (str): The text to embed.
            memory_action (optional): The type of embedding to use. Must be one of "add", "search", or "update". Defaults to None.
        Returns:
            list: The embedding vector.
        """
        text = text.replace("\n", " ")
        return (
            self.client.embeddings.create(input=[text], model=self.config.model, dimensions=self.config.embedding_dims)
            .data[0]
            .embedding
        )
