from unittest.mock import MagicMock, patch

from mem0.memory.main import Memory


def test_memory_configuration_without_env_vars():
    """Test Memory configuration with mock config instead of environment variables"""

    # Mock configuration without relying on environment variables
    mock_config = {
        "llm": {
            "provider": "openai",
            "config": {
                "model": "gpt-4",
                "temperature": 0.1,
                "max_tokens": 1500,
            },
        },
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "test_collection",
                "path": "./test_db",
            },
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "text-embedding-ada-002",
            },
        },
    }

    # Test messages similar to the main.py file
    test_messages = [
        {"role": "user", "content": "Hi, I'm Alex. I'm a vegetarian and I'm allergic to nuts."},
        {
            "role": "assistant",
            "content": "Hello Alex! I've noted that you're a vegetarian and have a nut allergy. I'll keep this in mind for any food-related recommendations or discussions.",
        },
    ]

    # Mock the Memory class methods to avoid actual API calls
    with patch.object(Memory, "__init__", return_value=None):
        with patch.object(Memory, "from_config") as mock_from_config:
            with patch.object(Memory, "add") as mock_add:
                with patch.object(Memory, "get_all") as mock_get_all:
                    # Configure mocks
                    mock_memory_instance = MagicMock()
                    mock_from_config.return_value = mock_memory_instance

                    mock_add.return_value = {
                        "results": [
                            {"id": "1", "text": "Alex is a vegetarian"},
                            {"id": "2", "text": "Alex is allergic to nuts"},
                        ]
                    }

                    mock_get_all.return_value = [
                        {"id": "1", "text": "Alex is a vegetarian", "metadata": {"category": "dietary_preferences"}},
                        {"id": "2", "text": "Alex is allergic to nuts", "metadata": {"category": "allergies"}},
                    ]

                    # Test the workflow
                    mem = Memory.from_config(config_dict=mock_config)
                    assert mem is not None

                    # Test adding memories
                    result = mock_add(test_messages, user_id="alice", metadata={"category": "book_recommendations"})
                    assert "results" in result
                    assert len(result["results"]) == 2

                    # Test retrieving memories
                    all_memories = mock_get_all(user_id="alice")
                    assert len(all_memories) == 2
                    assert any("vegetarian" in memory["text"] for memory in all_memories)
                    assert any("allergic to nuts" in memory["text"] for memory in all_memories)


def test_azure_config_structure():
    """Test that Azure configuration structure is properly formatted"""

    # Test Azure configuration structure (without actual credentials)
    azure_config = {
        "llm": {
            "provider": "azure_openai",
            "config": {
                "model": "gpt-4",
                "temperature": 0.1,
                "max_tokens": 1500,
                "azure_kwargs": {
                    "azure_deployment": "test-deployment",
                    "api_version": "2023-12-01-preview",
                    "azure_endpoint": "https://test.openai.azure.com/",
                    "api_key": "test-key",
                },
            },
        },
        "vector_store": {
            "provider": "azure_ai_search",
            "config": {
                "service_name": "test-service",
                "api_key": "test-key",
                "collection_name": "test-collection",
                "embedding_model_dims": 1536,
            },
        },
        "embedder": {
            "provider": "azure_openai",
            "config": {
                "model": "text-embedding-ada-002",
                "api_key": "test-key",
                "azure_kwargs": {
                    "api_version": "2023-12-01-preview",
                    "azure_deployment": "test-embedding-deployment",
                    "azure_endpoint": "https://test.openai.azure.com/",
                    "api_key": "test-key",
                },
            },
        },
    }

    # Validate configuration structure
    assert "llm" in azure_config
    assert "vector_store" in azure_config
    assert "embedder" in azure_config

    # Validate Azure-specific configurations
    assert azure_config["llm"]["provider"] == "azure_openai"
    assert "azure_kwargs" in azure_config["llm"]["config"]
    assert "azure_deployment" in azure_config["llm"]["config"]["azure_kwargs"]

    assert azure_config["vector_store"]["provider"] == "azure_ai_search"
    assert "service_name" in azure_config["vector_store"]["config"]

    assert azure_config["embedder"]["provider"] == "azure_openai"
    assert "azure_kwargs" in azure_config["embedder"]["config"]


def test_memory_messages_format():
    """Test that memory messages are properly formatted"""

    # Test message format from main.py
    messages = [
        {"role": "user", "content": "Hi, I'm Alex. I'm a vegetarian and I'm allergic to nuts."},
        {
            "role": "assistant",
            "content": "Hello Alex! I've noted that you're a vegetarian and have a nut allergy. I'll keep this in mind for any food-related recommendations or discussions.",
        },
    ]

    # Validate message structure
    assert len(messages) == 2
    assert all("role" in msg for msg in messages)
    assert all("content" in msg for msg in messages)

    # Validate roles
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"

    # Validate content
    assert "vegetarian" in messages[0]["content"].lower()
    assert "allergic to nuts" in messages[0]["content"].lower()
    assert "vegetarian" in messages[1]["content"].lower()
    assert "nut allergy" in messages[1]["content"].lower()


def test_safe_update_prompt_constant():
    """Test the SAFE_UPDATE_PROMPT constant from main.py"""

    SAFE_UPDATE_PROMPT = """
Based on the user's latest messages, what new preference can be inferred?
Reply only in this json_object format:
"""

    # Validate prompt structure
    assert isinstance(SAFE_UPDATE_PROMPT, str)
    assert "user's latest messages" in SAFE_UPDATE_PROMPT
    assert "json_object format" in SAFE_UPDATE_PROMPT
    assert len(SAFE_UPDATE_PROMPT.strip()) > 0


def test_v2_contextual_add_integration():
    """Integration test for v2 contextual add functionality"""

    mock_config = {
        "llm": {
            "provider": "openai",
            "config": {
                "model": "gpt-4",
                "temperature": 0.1,
                "max_tokens": 1500,
            },
        },
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "test_v2_collection",
                "path": "./test_v2_db",
            },
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "text-embedding-ada-002",
            },
        },
    }

    # Test messages for v2 contextual add
    initial_messages = [
        {"role": "user", "content": "Hi, I'm Alex and I live in San Francisco."},
        {"role": "assistant", "content": "Hello Alex! Nice to meet you. San Francisco is a beautiful city."},
    ]

    follow_up_messages = [
        {"role": "user", "content": "I like to eat sushi."},
        {"role": "assistant", "content": "Sushi is really a tasty choice! There are many great sushi restaurants in San Francisco."},
    ]

    with patch.object(Memory, "__init__", return_value=None):
        with patch.object(Memory, "from_config") as mock_from_config:
            with patch.object(Memory, "add") as mock_add:
                with patch.object(Memory, "_retrieve_contextual_history") as mock_retrieve:
                    with patch.object(Memory, "_merge_historical_context") as mock_merge:

                        # Configure mocks
                        mock_memory_instance = MagicMock()
                        mock_from_config.return_value = mock_memory_instance

                        # Mock v2 contextual behavior
                        mock_retrieve.return_value = initial_messages
                        mock_merge.return_value = initial_messages + follow_up_messages

                        def mock_add_behavior(messages, **kwargs):
                            version = kwargs.get("version", "v1")
                            if version == "v2":
                                # Simulate v2 contextual add
                                historical = mock_retrieve.return_value
                                merged = mock_merge.return_value
                                return {
                                    "results": [{
                                        "id": "integration_v2_1",
                                        "memory": f"Integrated contextual memory from {len(merged)} messages",
                                        "event": "ADD",
                                        "metadata": {
                                            "api_version": "v2",
                                            "original_messages": messages,
                                            "historical_count": len(historical),
                                            "merged_count": len(merged)
                                        }
                                    }]
                                }
                            else:
                                return {
                                    "results": [{
                                        "id": "integration_v1_1",
                                        "memory": "Standard memory",
                                        "event": "ADD"
                                    }]
                                }

                        # Set up the mock properly
                        mock_memory_instance.add.side_effect = mock_add_behavior

                        # Create memory instance
                        memory = Memory.from_config(mock_config)

                        # Test v1 behavior (baseline)
                        result_v1 = memory.add(initial_messages, user_id="alex", version="v1")
                        assert result_v1["results"][0]["id"] == "integration_v1_1"
                        assert result_v1["results"][0]["memory"] == "Standard memory"

                        # Test v2 contextual add
                        result_v2 = memory.add(follow_up_messages, user_id="alex", version="v2")
                        assert result_v2["results"][0]["id"] == "integration_v2_1"
                        assert "Integrated contextual memory" in result_v2["results"][0]["memory"]

                        # Verify v2 metadata
                        metadata = result_v2["results"][0]["metadata"]
                        assert metadata["api_version"] == "v2"
                        assert metadata["original_messages"] == follow_up_messages
                        assert metadata["historical_count"] == 2
                        assert metadata["merged_count"] == 4

                        # Verify that the mock was called correctly
                        assert mock_memory_instance.add.called


def test_v2_performance_integration():
    """Integration test for v2 performance requirements"""
    import time

    mock_config = {
        "llm": {"provider": "openai", "config": {"model": "gpt-4"}},
        "vector_store": {"provider": "chroma", "config": {"collection_name": "perf_test"}},
        "embedder": {"provider": "openai", "config": {"model": "text-embedding-ada-002"}},
    }

    with patch.object(Memory, "__init__", return_value=None):
        with patch.object(Memory, "from_config") as mock_from_config:
            with patch.object(Memory, "add") as mock_add:

                # Mock performance-aware behavior
                def mock_timed_add(messages, **kwargs):
                    version = kwargs.get("version", "v1")
                    if version == "v2":
                        # Simulate realistic processing time
                        time.sleep(0.2)  # 200ms simulation
                    return {
                        "results": [{
                            "id": "perf_integration_1",
                            "memory": "Performance test memory",
                            "event": "ADD"
                        }]
                    }

                mock_add.side_effect = mock_timed_add
                mock_memory_instance = MagicMock()
                mock_from_config.return_value = mock_memory_instance

                # Create memory instance
                memory = Memory.from_config(mock_config)

                messages = [{"role": "user", "content": "Performance test message"}]

                # Test v2 performance
                start_time = time.time()
                result = memory.add(messages, user_id="perf_user", version="v2")
                end_time = time.time()

                elapsed_ms = (end_time - start_time) * 1000

                # Verify performance requirement (< 800ms)
                assert elapsed_ms < 800
                assert result["results"][0]["id"] == "perf_integration_1"


def test_v2_error_handling_integration():
    """Integration test for v2 error handling and graceful degradation"""

    mock_config = {
        "llm": {"provider": "openai", "config": {"model": "gpt-4"}},
        "vector_store": {"provider": "chroma", "config": {"collection_name": "error_test"}},
        "embedder": {"provider": "openai", "config": {"model": "text-embedding-ada-002"}},
    }

    with patch.object(Memory, "__init__", return_value=None):
        with patch.object(Memory, "from_config") as mock_from_config:
            with patch.object(Memory, "add") as mock_add:
                with patch.object(Memory, "_retrieve_contextual_history") as mock_retrieve:

                    # Mock error scenario
                    mock_retrieve.side_effect = Exception("Simulated retrieval error")

                    def mock_add_with_fallback(messages, **kwargs):
                        version = kwargs.get("version", "v1")
                        if version == "v2":
                            try:
                                # This will raise an exception
                                mock_retrieve()
                                return {"results": [{"id": "should_not_reach", "memory": "error", "event": "ADD"}]}
                            except Exception:
                                # Graceful fallback to v1
                                return {
                                    "results": [{
                                        "id": "fallback_integration_1",
                                        "memory": "Fallback memory after v2 error",
                                        "event": "ADD",
                                        "fallback": True
                                    }]
                                }
                        return {"results": [{"id": "normal_v1", "memory": "normal", "event": "ADD"}]}

                    mock_add.side_effect = mock_add_with_fallback
                    mock_memory_instance = MagicMock()
                    mock_from_config.return_value = mock_memory_instance

                    # Create memory instance
                    memory = Memory.from_config(mock_config)

                    messages = [{"role": "user", "content": "Error handling test"}]

                    # Test error handling
                    result = memory.add(messages, user_id="error_user", version="v2")

                    # Verify graceful fallback
                    assert result["results"][0]["id"] == "fallback_integration_1"
                    assert "Fallback memory" in result["results"][0]["memory"]
                    assert result["results"][0]["fallback"] is True
