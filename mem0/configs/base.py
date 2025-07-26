import os
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from mem0.embeddings.configs import EmbedderConfig
from mem0.graphs.configs import GraphStoreConfig
from mem0.llms.configs import LlmConfig
from mem0.vector_stores.configs import VectorStoreConfig

# Set up the directory path with environment variable support
home_dir = os.path.expanduser("~")
mem0_dir = os.environ.get("MEM0_DIR") or os.path.join(home_dir, ".mem0")

# Data path configuration with environment variable support
def get_data_path():
    """Get the base data path from environment variable or default"""
    return os.environ.get("MEM0_DATA_PATH", "./data")

def resolve_path(path, base_path=None):
    """Resolve path relative to base_path if it's not absolute"""
    if os.path.isabs(path):
        return path
    base = base_path or get_data_path()
    return os.path.join(base, path)


class MemoryItem(BaseModel):
    id: str = Field(..., description="The unique identifier for the text data")
    memory: str = Field(
        ..., description="The memory deduced from the text data"
    )  # TODO After prompt changes from platform, update this
    hash: Optional[str] = Field(None, description="The hash of the memory")
    # The metadata value can be anything and not just string. Fix it
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the text data")
    score: Optional[float] = Field(None, description="The score associated with the text data")
    created_at: Optional[str] = Field(None, description="The timestamp when the memory was created")
    updated_at: Optional[str] = Field(None, description="The timestamp when the memory was updated")


class MemoryConfig(BaseModel):
    vector_store: VectorStoreConfig = Field(
        description="Configuration for the vector store",
        default_factory=VectorStoreConfig,
    )
    llm: LlmConfig = Field(
        description="Configuration for the language model",
        default_factory=LlmConfig,
    )
    embedder: EmbedderConfig = Field(
        description="Configuration for the embedding model",
        default_factory=EmbedderConfig,
    )
    # Data path configuration with environment variable support
    data_path: str = Field(
        default_factory=get_data_path,
        description="Base data directory path"
    )
    history_db_path: str = Field(
        default_factory=lambda: os.environ.get("MEM0_HISTORY_DB_PATH") or resolve_path("history.db"),
        description="Path to the history database"
    )
    vector_storage_path: str = Field(
        default_factory=lambda: os.environ.get("MEM0_VECTOR_STORAGE_PATH") or resolve_path("vector_store"),
        description="Path to the vector storage directory"
    )
    graph_store: GraphStoreConfig = Field(
        description="Configuration for the graph",
        default_factory=GraphStoreConfig,
    )
    version: str = Field(
        description="The version of the API",
        default="v1.1",
    )
    custom_fact_extraction_prompt: Optional[str] = Field(
        description="Custom prompt for the fact extraction",
        default=None,
    )
    custom_update_memory_prompt: Optional[str] = Field(
        description="Custom prompt for the update memory",
        default=None,
    )

    def model_post_init(self, __context):
        """Post-initialization to ensure directories exist"""
        self.ensure_directories_exist()

    def ensure_directories_exist(self):
        """Ensure all configured directories exist"""
        directories = [
            self.data_path,
            os.path.dirname(self.history_db_path),
            self.vector_storage_path,
        ]

        for directory in directories:
            if directory and not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                except PermissionError:
                    raise PermissionError(f"Cannot create directory: {directory}. Check permissions.")
                except Exception as e:
                    raise RuntimeError(f"Failed to create directory {directory}: {e}")

    def validate_paths(self):
        """Validate that all paths are accessible"""
        paths_to_check = [
            ("data_path", self.data_path),
            ("history_db_path", os.path.dirname(self.history_db_path)),
            ("vector_storage_path", self.vector_storage_path),
        ]

        for name, path in paths_to_check:
            if not os.path.exists(path):
                raise ValueError(f"Path for {name} does not exist: {path}")
            if not os.access(path, os.R_OK | os.W_OK):
                raise PermissionError(f"No read/write access to {name}: {path}")


class AzureConfig(BaseModel):
    """
    Configuration settings for Azure.

    Args:
        api_key (str): The API key used for authenticating with the Azure service.
        azure_deployment (str): The name of the Azure deployment.
        azure_endpoint (str): The endpoint URL for the Azure service.
        api_version (str): The version of the Azure API being used.
        default_headers (Dict[str, str]): Headers to include in requests to the Azure API.
    """

    api_key: str = Field(
        description="The API key used for authenticating with the Azure service.",
        default=None,
    )
    azure_deployment: str = Field(description="The name of the Azure deployment.", default=None)
    azure_endpoint: str = Field(description="The endpoint URL for the Azure service.", default=None)
    api_version: str = Field(description="The version of the Azure API being used.", default=None)
    default_headers: Optional[Dict[str, str]] = Field(
        description="Headers to include in requests to the Azure API.", default=None
    )
