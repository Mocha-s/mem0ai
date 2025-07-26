#!/usr/bin/env python3
"""
端到端記憶操作測試腳本
測試所有API端點的完整功能，包括記憶的創建、查詢、更新、刪除、搜索、批量操作、導出和反饋功能
"""

import json
import time
import requests
import sys
from typing import Dict, List, Any

# API基礎URL
BASE_URL = "http://localhost:8000"

class MemoryE2ETest:
    def __init__(self):
        self.base_url = BASE_URL
        self.test_user_id = "test_user_e2e"
        self.test_agent_id = "test_agent_e2e"
        self.created_memory_ids = []
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """記錄測試結果"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
    def make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """發送HTTP請求"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, params=params)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, params=params)
            elif method.upper() == "DELETE":
                response = requests.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return {
                "status_code": response.status_code,
                "data": response.json() if response.content else {},
                "success": 200 <= response.status_code < 300
            }
        except Exception as e:
            return {
                "status_code": 0,
                "data": {"error": str(e)},
                "success": False
            }
    
    def test_health_check(self):
        """測試健康檢查端點"""
        result = self.make_request("GET", "/health")
        success = result["success"] and result["data"].get("status") == "healthy"
        self.log_test("Health Check", success, f"Status: {result['status_code']}")
        
    def test_create_memory_v1(self):
        """測試V1記憶創建"""
        data = {
            "messages": [
                {"role": "user", "content": "這是第一個測試記憶"},
                {"role": "assistant", "content": "我理解了這個測試記憶"}
            ],
            "user_id": self.test_user_id,
            "metadata": {"test_type": "e2e", "priority": "high"}
        }
        
        result = self.make_request("POST", "/v1/memories/", data)
        success = result["success"]
        
        if success and "results" in result["data"]:
            # 提取記憶ID
            memories = result["data"]["results"]
            if memories:
                memory_id = memories[0].get("id")
                if memory_id:
                    self.created_memory_ids.append(memory_id)
                    
        self.log_test("Create Memory V1", success, f"Status: {result['status_code']}")
        return success
        
    def test_create_multiple_memories(self):
        """創建多個測試記憶"""
        test_memories = [
            {
                "messages": [{"role": "user", "content": f"測試記憶 {i}"}],
                "user_id": self.test_user_id,
                "metadata": {"test_index": i, "category": "batch_test"}
            }
            for i in range(2, 6)  # 創建記憶2-5
        ]
        
        success_count = 0
        for i, memory_data in enumerate(test_memories):
            result = self.make_request("POST", "/v1/memories/", memory_data)
            if result["success"] and "results" in result["data"]:
                memories = result["data"]["results"]
                if memories:
                    memory_id = memories[0].get("id")
                    if memory_id:
                        self.created_memory_ids.append(memory_id)
                        success_count += 1
                        
        success = success_count == len(test_memories)
        self.log_test("Create Multiple Memories", success, f"Created {success_count}/{len(test_memories)} memories")
        return success
        
    def test_get_memories_v1(self):
        """測試V1記憶獲取"""
        result = self.make_request("GET", "/v1/memories/", params={"user_id": self.test_user_id})
        success = result["success"] and isinstance(result["data"], list)
        
        memory_count = len(result["data"]) if isinstance(result["data"], list) else 0
        self.log_test("Get Memories V1", success, f"Retrieved {memory_count} memories")
        return success
        
    def test_get_memory_by_id(self):
        """測試根據ID獲取記憶"""
        if not self.created_memory_ids:
            self.log_test("Get Memory by ID", False, "No memory IDs available")
            return False
            
        memory_id = self.created_memory_ids[0]
        result = self.make_request("GET", f"/v1/memories/{memory_id}/")
        success = result["success"] and "id" in result["data"]
        
        self.log_test("Get Memory by ID", success, f"Memory ID: {memory_id}")
        return success
        
    def test_search_memories_v1(self):
        """測試V1記憶搜索"""
        data = {
            "query": "測試記憶",
            "user_id": self.test_user_id
        }
        
        result = self.make_request("POST", "/v1/memories/search/", data)
        success = result["success"] and isinstance(result["data"], list)
        
        search_count = len(result["data"]) if isinstance(result["data"], list) else 0
        self.log_test("Search Memories V1", success, f"Found {search_count} memories")
        return success
        
    def test_update_memory(self):
        """測試記憶更新"""
        if not self.created_memory_ids:
            self.log_test("Update Memory", False, "No memory IDs available")
            return False
            
        memory_id = self.created_memory_ids[0]
        update_data = {
            "text": "這是更新後的測試記憶內容"
        }
        
        result = self.make_request("PUT", f"/v1/memories/{memory_id}/", update_data)
        success = result["success"]
        
        self.log_test("Update Memory", success, f"Updated memory {memory_id}")
        return success
        
    def test_memory_history(self):
        """測試記憶歷史"""
        if not self.created_memory_ids:
            self.log_test("Memory History", False, "No memory IDs available")
            return False
            
        memory_id = self.created_memory_ids[0]
        result = self.make_request("GET", f"/v1/memories/{memory_id}/history/")
        success = result["success"]
        
        self.log_test("Memory History", success, f"History for memory {memory_id}")
        return success

    def test_v2_get_memories(self):
        """測試V2記憶獲取（複雜過濾器）"""
        data = {
            "filters": {
                "user_id": self.test_user_id,
                "metadata": {
                    "test_type": "e2e"
                }
            },
            "limit": 10
        }

        result = self.make_request("POST", "/v2/memories/", data)
        success = result["success"] and "memories" in result["data"]

        memory_count = len(result["data"].get("memories", [])) if success else 0
        self.log_test("V2 Get Memories", success, f"Retrieved {memory_count} memories with filters")
        return success

    def test_v2_search_memories(self):
        """測試V2記憶搜索（複雜過濾器）"""
        data = {
            "query": "測試",
            "filters": {
                "user_id": self.test_user_id
            },
            "limit": 5
        }

        result = self.make_request("POST", "/v2/memories/search/", data)
        success = result["success"] and "results" in result["data"]

        search_count = len(result["data"].get("results", [])) if success else 0
        self.log_test("V2 Search Memories", success, f"Found {search_count} memories")
        return success

    def test_feedback_submission(self):
        """測試反饋提交"""
        if not self.created_memory_ids:
            self.log_test("Feedback Submission", False, "No memory IDs available")
            return False

        memory_id = self.created_memory_ids[0]
        feedback_data = {
            "memory_id": memory_id,
            "feedback": "POSITIVE",
            "feedback_reason": "這個記憶很有用"
        }

        result = self.make_request("POST", "/v1/feedback/", feedback_data)
        success = result["success"]

        self.log_test("Feedback Submission", success, f"Feedback for memory {memory_id}")
        return success

    def test_batch_update(self):
        """測試批量更新"""
        if len(self.created_memory_ids) < 2:
            self.log_test("Batch Update", False, "Need at least 2 memory IDs")
            return False

        batch_data = {
            "memories": [
                {
                    "memory_id": self.created_memory_ids[0],
                    "text": "批量更新的記憶1"
                },
                {
                    "memory_id": self.created_memory_ids[1],
                    "text": "批量更新的記憶2"
                }
            ]
        }

        result = self.make_request("PUT", "/v1/batch/", batch_data)
        success = result["success"] and result["data"].get("successful_count", 0) > 0

        successful_count = result["data"].get("successful_count", 0) if success else 0
        self.log_test("Batch Update", success, f"Updated {successful_count} memories")
        return success

    def test_export_creation(self):
        """測試導出創建"""
        export_data = {
            "schema": {
                "id": {"source": "id"},
                "content": {"source": "text"},
                "user": {"source": "user_id"},
                "created_at": {"source": "created_at"}
            },
            "filters": {
                "user_id": self.test_user_id
            },
            "processing_instruction": "導出所有測試記憶"
        }

        result = self.make_request("POST", "/v1/exports/", export_data)
        success = result["success"] and "id" in result["data"]

        export_id = result["data"].get("id", "") if success else ""
        self.log_test("Export Creation", success, f"Export ID: {export_id}")

        # 如果創建成功，測試獲取導出結果
        if success and export_id:
            time.sleep(2)  # 等待導出處理
            self.test_export_retrieval(export_id)

        return success

    def test_export_retrieval(self, export_id: str):
        """測試導出結果獲取"""
        get_data = {
            "task_id": export_id
        }

        result = self.make_request("POST", "/v1/exports/get", get_data)
        success = result["success"] and "status" in result["data"]

        status = result["data"].get("status", "") if success else ""
        self.log_test("Export Retrieval", success, f"Export status: {status}")
        return success

    def test_batch_delete(self):
        """測試批量刪除"""
        if len(self.created_memory_ids) < 2:
            self.log_test("Batch Delete", False, "Need at least 2 memory IDs")
            return False

        # 保留前兩個記憶，刪除其餘的
        memories_to_delete = self.created_memory_ids[2:]
        if not memories_to_delete:
            self.log_test("Batch Delete", False, "No memories to delete")
            return False

        batch_data = {
            "memories": [
                {"memory_id": memory_id}
                for memory_id in memories_to_delete
            ]
        }

        result = self.make_request("DELETE", "/v1/batch/", batch_data)
        success = result["success"] and result["data"].get("successful_count", 0) > 0

        successful_count = result["data"].get("successful_count", 0) if success else 0
        self.log_test("Batch Delete", success, f"Deleted {successful_count} memories")

        # 更新記憶ID列表
        if success:
            self.created_memory_ids = self.created_memory_ids[:2]

        return success

    def test_delete_memory_by_id(self):
        """測試根據ID刪除記憶"""
        if not self.created_memory_ids:
            self.log_test("Delete Memory by ID", False, "No memory IDs available")
            return False

        memory_id = self.created_memory_ids[-1]  # 刪除最後一個
        result = self.make_request("DELETE", f"/v1/memories/{memory_id}/")
        success = result["success"]

        self.log_test("Delete Memory by ID", success, f"Deleted memory {memory_id}")

        if success:
            self.created_memory_ids.remove(memory_id)

        return success

    def test_delete_all_memories(self):
        """測試刪除所有記憶"""
        result = self.make_request("DELETE", "/v1/memories/", params={"user_id": self.test_user_id})
        success = result["success"]

        self.log_test("Delete All Memories", success, f"Deleted all memories for user {self.test_user_id}")

        if success:
            self.created_memory_ids.clear()

        return success

    def run_all_tests(self):
        """運行所有測試"""
        print("🚀 開始端到端記憶操作測試")
        print("=" * 50)

        # 基礎測試
        self.test_health_check()

        # 記憶創建測試
        print("\n📝 記憶創建測試")
        self.test_create_memory_v1()
        self.test_create_multiple_memories()

        # 記憶查詢測試
        print("\n🔍 記憶查詢測試")
        self.test_get_memories_v1()
        self.test_get_memory_by_id()
        self.test_search_memories_v1()

        # V2 API測試
        print("\n🔄 V2 API測試")
        self.test_v2_get_memories()
        self.test_v2_search_memories()

        # 記憶更新測試
        print("\n✏️ 記憶更新測試")
        self.test_update_memory()
        self.test_memory_history()

        # 反饋測試
        print("\n💬 反饋功能測試")
        self.test_feedback_submission()

        # 批量操作測試
        print("\n📦 批量操作測試")
        self.test_batch_update()

        # 導出功能測試
        print("\n📤 導出功能測試")
        self.test_export_creation()

        # 刪除操作測試
        print("\n🗑️ 刪除操作測試")
        self.test_batch_delete()
        self.test_delete_memory_by_id()
        self.test_delete_all_memories()

        # 測試結果總結
        self.print_test_summary()

    def print_test_summary(self):
        """打印測試結果總結"""
        print("\n" + "=" * 50)
        print("📊 測試結果總結")
        print("=" * 50)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests

        print(f"總測試數: {total_tests}")
        print(f"通過測試: {passed_tests} ✅")
        print(f"失敗測試: {failed_tests} ❌")
        print(f"成功率: {(passed_tests/total_tests*100):.1f}%")

        if failed_tests > 0:
            print("\n❌ 失敗的測試:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")

        print("\n🎯 測試完成!")


if __name__ == "__main__":
    tester = MemoryE2ETest()
    tester.run_all_tests()
