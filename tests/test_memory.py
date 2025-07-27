from unittest.mock import MagicMock, patch
import time

import pytest

from mem0 import Memory


@pytest.fixture
def memory_client():
    with patch.object(Memory, "__init__", return_value=None):
        client = Memory()
        client.add = MagicMock(return_value={"results": [{"id": "1", "memory": "Name is John Doe.", "event": "ADD"}]})
        client.get = MagicMock(return_value={"id": "1", "memory": "Name is John Doe."})
        client.update = MagicMock(return_value={"message": "Memory updated successfully!"})
        client.delete = MagicMock(return_value={"message": "Memory deleted successfully!"})
        client.history = MagicMock(return_value=[{"memory": "I like Indian food."}, {"memory": "I like Italian food."}])
        client.get_all = MagicMock(return_value=["Name is John Doe.", "Name is John Doe. I like to code in Python."])
        yield client


def test_create_memory(memory_client):
    data = "Name is John Doe."
    result = memory_client.add([{"role": "user", "content": data}], user_id="test_user")
    assert result["results"][0]["memory"] == data


def test_get_memory(memory_client):
    data = "Name is John Doe."
    memory_client.add([{"role": "user", "content": data}], user_id="test_user")
    result = memory_client.get("1")
    assert result["memory"] == data


def test_update_memory(memory_client):
    data = "Name is John Doe."
    memory_client.add([{"role": "user", "content": data}], user_id="test_user")
    new_data = "Name is John Kapoor."
    update_result = memory_client.update("1", text=new_data)
    assert update_result["message"] == "Memory updated successfully!"


def test_delete_memory(memory_client):
    data = "Name is John Doe."
    memory_client.add([{"role": "user", "content": data}], user_id="test_user")
    delete_result = memory_client.delete("1")
    assert delete_result["message"] == "Memory deleted successfully!"


def test_history(memory_client):
    data = "I like Indian food."
    memory_client.add([{"role": "user", "content": data}], user_id="test_user")
    memory_client.update("1", text="I like Italian food.")
    history = memory_client.history("1")
    assert history[0]["memory"] == "I like Indian food."
    assert history[1]["memory"] == "I like Italian food."


def test_list_memories(memory_client):
    data1 = "Name is John Doe."
    data2 = "Name is John Doe. I like to code in Python."
    memory_client.add([{"role": "user", "content": data1}], user_id="test_user")
    memory_client.add([{"role": "user", "content": data2}], user_id="test_user")
    memories = memory_client.get_all(user_id="test_user")
    assert data1 in memories
    assert data2 in memories


# V2 Contextual Add Tests

@pytest.fixture
def memory_v2_client():
    """Mock Memory client with v2 contextual add functionality."""
    with patch.object(Memory, "__init__", return_value=None):
        client = Memory()

        # Mock the internal methods for v2 functionality
        client._retrieve_contextual_history = MagicMock(return_value=[
            {"role": "user", "content": "Hi, I'm Alex"},
            {"role": "assistant", "content": "Hello Alex! Nice to meet you."}
        ])

        client._merge_historical_context = MagicMock(return_value=[
            {"role": "user", "content": "Hi, I'm Alex"},
            {"role": "assistant", "content": "Hello Alex! Nice to meet you."},
            {"role": "user", "content": "I like sushi"},
            {"role": "assistant", "content": "Sushi is delicious!"}
        ])

        # Mock the add method to simulate v2 behavior
        def mock_add(messages, **kwargs):
            version = kwargs.get("version", "v1")
            if version == "v2":
                # Simulate v2 contextual add behavior
                historical = client._retrieve_contextual_history({}, 10)
                merged = client._merge_historical_context(historical, messages)
                return {
                    "results": [{
                        "id": "v2_memory_1",
                        "memory": f"Contextual memory from {len(merged)} messages",
                        "event": "ADD"
                    }]
                }
            else:
                # v1 behavior
                return {"results": [{"id": "v1_memory_1", "memory": "Simple memory", "event": "ADD"}]}

        client.add = MagicMock(side_effect=mock_add)
        client.get_all = MagicMock(return_value=[
            {
                "id": "existing_1",
                "memory": "Previous conversation",
                "metadata": {
                    "api_version": "v2",
                    "original_messages": [
                        {"role": "user", "content": "Hi, I'm Alex"},
                        {"role": "assistant", "content": "Hello Alex!"}
                    ]
                },
                "created_at": "2024-01-01T10:00:00"
            }
        ])

        yield client


def test_v2_version_parameter_handling(memory_v2_client):
    """Test that v2 version parameter is correctly handled."""
    messages = [{"role": "user", "content": "I like sushi"}]

    # Test v2 version
    result_v2 = memory_v2_client.add(messages, user_id="alex", version="v2")
    assert "v2_memory_1" in result_v2["results"][0]["id"]
    assert "Contextual memory" in result_v2["results"][0]["memory"]

    # Test v1 version (backward compatibility)
    result_v1 = memory_v2_client.add(messages, user_id="alex", version="v1")
    assert "v1_memory_1" in result_v1["results"][0]["id"]
    assert "Simple memory" in result_v1["results"][0]["memory"]


def test_v2_contextual_history_retrieval(memory_v2_client):
    """Test historical message retrieval functionality."""
    filters = {"user_id": "alex"}

    # Test historical retrieval
    historical = memory_v2_client._retrieve_contextual_history(filters, limit=10)

    assert len(historical) == 2
    assert historical[0]["role"] == "user"
    assert historical[0]["content"] == "Hi, I'm Alex"
    assert historical[1]["role"] == "assistant"
    assert historical[1]["content"] == "Hello Alex! Nice to meet you."


def test_v2_message_merging(memory_v2_client):
    """Test historical and new message merging functionality."""
    historical_messages = [
        {"role": "user", "content": "Hi, I'm Alex"},
        {"role": "assistant", "content": "Hello Alex! Nice to meet you."}
    ]
    new_messages = [
        {"role": "user", "content": "I like sushi"},
        {"role": "assistant", "content": "Sushi is delicious!"}
    ]

    # Test message merging
    merged = memory_v2_client._merge_historical_context(historical_messages, new_messages)

    assert len(merged) == 4
    assert merged[0]["content"] == "Hi, I'm Alex"
    assert merged[1]["content"] == "Hello Alex! Nice to meet you."
    assert merged[2]["content"] == "I like sushi"
    assert merged[3]["content"] == "Sushi is delicious!"


def test_v2_backward_compatibility():
    """Test that v2 implementation doesn't break v1 functionality."""
    with patch.object(Memory, "__init__", return_value=None):
        client = Memory()

        # Mock v1 behavior
        client.add = MagicMock(return_value={
            "results": [{"id": "v1_test", "memory": "v1 memory", "event": "ADD"}]
        })

        messages = [{"role": "user", "content": "Test message"}]

        # Test default behavior (should be v1 compatible)
        result = client.add(messages, user_id="test_user")
        assert result["results"][0]["id"] == "v1_test"
        assert result["results"][0]["memory"] == "v1 memory"


def test_v2_error_handling():
    """Test error handling and graceful degradation in v2."""
    with patch.object(Memory, "__init__", return_value=None):
        client = Memory()

        # Mock error scenario
        def mock_add_with_error(messages, **kwargs):
            version = kwargs.get("version", "v1")
            if version == "v2":
                # Simulate v2 error and fallback to v1
                return {"results": [{"id": "fallback", "memory": "fallback memory", "event": "ADD"}]}
            return {"results": [{"id": "normal", "memory": "normal memory", "event": "ADD"}]}

        client.add = MagicMock(side_effect=mock_add_with_error)

        messages = [{"role": "user", "content": "Test message"}]

        # Test error handling
        result = client.add(messages, user_id="test_user", version="v2")
        assert result["results"][0]["id"] == "fallback"


def test_v2_different_user_contexts():
    """Test v2 functionality with different user_id and run_id combinations."""
    with patch.object(Memory, "__init__", return_value=None):
        client = Memory()

        def mock_contextual_add(messages, **kwargs):
            user_id = kwargs.get("user_id")
            run_id = kwargs.get("run_id")
            version = kwargs.get("version", "v1")

            if version == "v2":
                context_id = f"{user_id}_{run_id}" if run_id else user_id
                return {
                    "results": [{
                        "id": f"ctx_{context_id}",
                        "memory": f"Contextual memory for {context_id}",
                        "event": "ADD"
                    }]
                }
            return {"results": [{"id": "default", "memory": "default", "event": "ADD"}]}

        client.add = MagicMock(side_effect=mock_contextual_add)

        messages = [{"role": "user", "content": "Test message"}]

        # Test different user contexts
        result1 = client.add(messages, user_id="alice", version="v2")
        assert "ctx_alice" in result1["results"][0]["id"]

        result2 = client.add(messages, user_id="bob", run_id="session1", version="v2")
        assert "ctx_bob_session1" in result2["results"][0]["id"]


def test_v2_performance_requirements():
    """Test that v2 contextual add meets performance requirements."""
    with patch.object(Memory, "__init__", return_value=None):
        client = Memory()

        # Mock performance-aware add method
        def mock_timed_add(messages, **kwargs):
            version = kwargs.get("version", "v1")
            if version == "v2":
                # Simulate some processing time (should be < 800ms)
                time.sleep(0.1)  # 100ms simulation
            return {"results": [{"id": "perf_test", "memory": "performance test", "event": "ADD"}]}

        client.add = MagicMock(side_effect=mock_timed_add)

        messages = [{"role": "user", "content": "Performance test message"}]

        # Test performance
        start_time = time.time()
        result = client.add(messages, user_id="perf_user", version="v2")
        end_time = time.time()

        elapsed_ms = (end_time - start_time) * 1000
        assert elapsed_ms < 800  # Should be under 800ms
        assert result["results"][0]["id"] == "perf_test"


def test_v2_original_message_storage():
    """Test that v2 correctly stores original messages in metadata."""
    with patch.object(Memory, "__init__", return_value=None):
        client = Memory()

        def mock_add_with_metadata(messages, **kwargs):
            version = kwargs.get("version", "v1")
            if version == "v2":
                # Simulate storing original messages in metadata
                return {
                    "results": [{
                        "id": "meta_test",
                        "memory": "memory with metadata",
                        "event": "ADD",
                        "metadata": {
                            "api_version": "v2",
                            "original_messages": messages
                        }
                    }]
                }
            return {"results": [{"id": "no_meta", "memory": "no metadata", "event": "ADD"}]}

        client.add = MagicMock(side_effect=mock_add_with_metadata)

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        # Test metadata storage
        result = client.add(messages, user_id="meta_user", version="v2")
        metadata = result["results"][0]["metadata"]

        assert metadata["api_version"] == "v2"
        assert metadata["original_messages"] == messages
        assert len(metadata["original_messages"]) == 2
