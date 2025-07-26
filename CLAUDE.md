# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mem0 is an intelligent memory layer for AI assistants and agents that enables personalized AI interactions. The project consists of multiple components:

- `mem0/` - Core Python library providing the memory layer functionality
- `embedchain/` - Legacy RAG framework (maintained for compatibility)
- `server/` - FastAPI REST API server for standalone deployment
- `openmemory/` - Full-stack web UI and API for memory management
- `vercel-ai-sdk/` - TypeScript provider for Vercel AI SDK integration
- `mem0-ts/` - TypeScript client library
- `examples/` - Example applications and integrations
- `evaluation/` - Evaluation framework and benchmarks

## Development Commands

### Python (Core Library)
```bash
# Install development dependencies
hatch env create

# Install all optional dependencies
make install_all

# Format code
make format

# Lint code  
make lint

# Run tests
make test

# Build package
make build

# Publish package
make publish
```

### TypeScript Components
```bash
# Vercel AI SDK Provider
cd vercel-ai-sdk
pnpm install
pnpm build
pnpm test

# TypeScript Client
cd mem0-ts
pnpm install
pnpm build
```

### Server Components
```bash
# FastAPI Server
cd server
pip install -r requirements.txt
python main.py

# OpenMemory UI
cd openmemory/ui
pnpm install
pnpm dev

# OpenMemory API
cd openmemory/api
pip install -r requirements.txt
python main.py
```

## Core Architecture

### Memory System
- **Memory Class** (`mem0/memory/main.py`): Main entry point providing add(), search(), update(), delete() operations
- **Storage Layer** (`mem0/memory/storage.py`): SQLite-based metadata storage with vector store integration
- **Vector Stores** (`mem0/vector_stores/`): Pluggable vector database backends (Qdrant, Chroma, Pinecone, etc.)
- **Embeddings** (`mem0/embeddings/`): Text embedding providers (OpenAI, HuggingFace, etc.)
- **LLMs** (`mem0/llms/`): Language model providers for fact extraction and memory processing

### Graph Memory
- **Graph Memory** (`mem0/memory/graph_memory.py`): Advanced memory with relationship modeling
- **Graph Stores** (`mem0/graphs/`): Support for Neo4j, Memgraph, and Neptune graph databases

### Configuration System
- **Base Config** (`mem0/configs/base.py`): Core configuration classes
- **Component Configs**: Separate config files for embeddings, LLMs, and vector stores
- **Factory Pattern** (`mem0/utils/factory.py`): Dynamic component instantiation

### Client Architecture
- **Memory Client** (`mem0/client/main.py`): REST API client for hosted platform
- **Async Support**: Full async/await support across all components

## Key Integration Patterns

### Multi-Level Memory
The system supports three memory levels:
- **User Memory**: Long-term user preferences and history
- **Session Memory**: Conversation-specific context
- **Agent Memory**: Agent-specific knowledge and behavior

### Metadata and Filtering
All memory operations support rich metadata and filtering:
```python
# Add with metadata
memory.add(messages, user_id="user123", metadata={"source": "chat", "topic": "cooking"})

# Search with filters
results = memory.search(query="preferences", user_id="user123", filters={"topic": "cooking"})
```

### Memory Types
- **Episodic**: Event-based memories with temporal context
- **Semantic**: Fact-based knowledge without temporal context
- **Procedural**: Process and workflow memories

## Testing Strategy

### Unit Tests
- Component-specific tests in `tests/` directory
- Mocked external dependencies (LLMs, vector stores)
- Coverage for core memory operations

### Integration Tests
- End-to-end memory workflows
- Real LLM and vector store integrations
- Multi-component interaction testing

### Evaluation Framework
- Benchmark suite in `evaluation/` directory
- Metrics for memory accuracy, retrieval quality, and performance
- Comparison with baseline systems

## Development Guidelines

### Code Organization
- Each component (LLMs, embeddings, vector stores) follows a common base class pattern
- Configuration-driven component selection via factory classes
- Consistent async/sync API design across all components

### Error Handling
- Graceful degradation when optional dependencies are missing
- Comprehensive validation of user inputs and configurations
- Structured logging for debugging and monitoring

### Performance Considerations
- Lazy loading of heavy dependencies
- Connection pooling for database operations
- Batched operations for bulk memory management
- Efficient similarity search with configurable limits

## Multi-Platform Support

### Python Library
- Core functionality in `mem0/` package
- Support for Python 3.9+ with optional dependencies for different backends

### TypeScript/JavaScript
- Client library in `mem0-ts/` for Node.js applications  
- Vercel AI SDK provider in `vercel-ai-sdk/` for AI applications
- React components and hooks in example applications

### REST API
- FastAPI server providing HTTP endpoints
- OpenAPI specification for API documentation
- Docker containerization support

### Platform Integration
- Hosted platform client in `mem0/client/`
- Self-hosted deployment options
- MCP (Model Context Protocol) server support in `openmemory/`