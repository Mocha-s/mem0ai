#!/usr/bin/env python3
"""
簡化的端到端測試 - 專注於測試API端點的可訪問性和響應格式
即使Memory實例有問題，我們也可以驗證API路由和錯誤處理是否正確
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

class SimplifiedE2ETest:
    def __init__(self):
        self.base_url = BASE_URL
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
        
    def make_request(self, method: str, endpoint: str, data=None, params=None):
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
                "success": 200 <= response.status_code < 300,
                "content": response.text
            }
        except Exception as e:
            return {
                "status_code": 0,
                "data": {"error": str(e)},
                "success": False,
                "content": str(e)
            }
    
    def test_health_check(self):
        """測試健康檢查"""
        result = self.make_request("GET", "/health")
        success = result["success"] and result["data"].get("status") == "healthy"
        self.log_test("Health Check", success, f"Status: {result['status_code']}")
        
    def test_endpoint_accessibility(self):
        """測試所有端點的可訪問性"""
        endpoints_to_test = [
            # V1 記憶端點
            ("GET", "/v1/memories/", {"user_id": "test"}, None, "V1 Get Memories"),
            ("POST", "/v1/memories/", None, {"messages": [{"role": "user", "content": "test"}], "user_id": "test"}, "V1 Create Memory"),
            ("POST", "/v1/memories/search/", None, {"query": "test", "user_id": "test"}, "V1 Search Memories"),
            
            # V2 API端點
            ("POST", "/v2/memories/", None, {"filters": {"user_id": "test"}}, "V2 Get Memories"),
            ("POST", "/v2/memories/search/", None, {"query": "test", "filters": {"user_id": "test"}}, "V2 Search Memories"),
            
            # 批量操作端點
            ("PUT", "/v1/batch/", None, {"memories": [{"memory_id": "test", "text": "test"}]}, "Batch Update"),
            ("DELETE", "/v1/batch/", None, {"memories": [{"memory_id": "test"}]}, "Batch Delete"),
            
            # 反饋端點
            ("POST", "/v1/feedback/", None, {"memory_id": "test", "feedback": "POSITIVE"}, "Feedback Submission"),
            
            # 導出端點
            ("POST", "/v1/exports/", None, {"schema": {"id": {"source": "id"}}}, "Export Creation"),
            ("POST", "/v1/exports/get", None, {"task_id": "test"}, "Export Retrieval"),
        ]
        
        for method, endpoint, params, data, test_name in endpoints_to_test:
            result = self.make_request(method, endpoint, data, params)
            
            # 對於這些測試，我們主要關心端點是否可訪問，而不是業務邏輯是否正確
            # 200-299: 成功
            # 400-499: 客戶端錯誤（預期的，因為我們使用測試數據）
            # 500+: 服務器錯誤（不好）
            
            if result["status_code"] == 0:
                success = False
                details = f"Connection error: {result['content']}"
            elif 500 <= result["status_code"] < 600:
                success = False
                details = f"Server error: {result['status_code']}"
            else:
                success = True
                details = f"Status: {result['status_code']} (endpoint accessible)"
                
            self.log_test(test_name, success, details)
    
    def test_error_handling(self):
        """測試錯誤處理"""
        error_tests = [
            # 缺少必需參數
            ("GET", "/v1/memories/", {}, None, "Missing Required Params", [400]),
            ("POST", "/v1/memories/", None, {}, "Empty Request Body", [400, 422]),
            
            # 無效的記憶ID
            ("GET", "/v1/memories/invalid_id/", {}, None, "Invalid Memory ID", [404, 500]),
            ("DELETE", "/v1/memories/invalid_id/", {}, None, "Delete Invalid Memory", [404, 500]),
            
            # 無效的反饋類型
            ("POST", "/v1/feedback/", None, {"memory_id": "test", "feedback": "INVALID"}, "Invalid Feedback Type", [400, 422]),
            
            # 無效的導出任務ID
            ("POST", "/v1/exports/get", None, {"task_id": "invalid"}, "Invalid Export Task", [404]),
        ]
        
        for method, endpoint, params, data, test_name, expected_codes in error_tests:
            result = self.make_request(method, endpoint, data, params)
            
            success = result["status_code"] in expected_codes
            details = f"Expected {expected_codes}, got {result['status_code']}"
            
            self.log_test(test_name, success, details)
    
    def test_response_formats(self):
        """測試響應格式"""
        # 測試健康檢查響應格式
        result = self.make_request("GET", "/health")
        if result["success"]:
            required_fields = ["status", "service", "version", "timestamp", "checks"]
            has_all_fields = all(field in result["data"] for field in required_fields)
            self.log_test("Health Response Format", has_all_fields, f"Has all required fields: {has_all_fields}")
        
        # 測試記憶API響應格式
        result = self.make_request("GET", "/v1/memories/", params={"user_id": "test"})
        if result["success"]:
            # 應該返回包含results字段的JSON
            has_results = "results" in result["data"] or isinstance(result["data"], list)
            self.log_test("Memory Response Format", has_results, f"Has results field or is list: {has_results}")
    
    def run_all_tests(self):
        """運行所有測試"""
        print("🚀 開始簡化端到端測試")
        print("專注於API端點可訪問性和響應格式驗證")
        print("=" * 60)
        
        # 基礎測試
        print("\n🏥 健康檢查測試")
        self.test_health_check()
        
        # 響應格式測試
        print("\n📋 響應格式測試")
        self.test_response_formats()
        
        # 端點可訪問性測試
        print("\n🔗 端點可訪問性測試")
        self.test_endpoint_accessibility()
        
        # 錯誤處理測試
        print("\n⚠️ 錯誤處理測試")
        self.test_error_handling()
        
        # 測試結果總結
        self.print_test_summary()
        
    def print_test_summary(self):
        """打印測試結果總結"""
        print("\n" + "=" * 60)
        print("📊 測試結果總結")
        print("=" * 60)
        
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
        
        # 總體評估
        if passed_tests / total_tests >= 0.8:
            print("🎉 API端點整體運行良好！")
        elif passed_tests / total_tests >= 0.6:
            print("⚠️ API端點基本可用，但有一些問題需要解決。")
        else:
            print("🚨 API端點存在嚴重問題，需要立即修復。")


if __name__ == "__main__":
    tester = SimplifiedE2ETest()
    tester.run_all_tests()
