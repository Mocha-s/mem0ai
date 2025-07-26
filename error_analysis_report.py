#!/usr/bin/env python3
"""
錯誤分析報告 - 詳細分析API測試中的錯誤
"""

import requests
import json
import os

BASE_URL = "http://localhost:8000"

def check_service_dependencies():
    """檢查服務依賴"""
    print("🔍 檢查服務依賴")
    print("=" * 40)
    
    # 檢查Qdrant連接
    try:
        response = requests.get("http://localhost:6333/collections", timeout=5)
        if response.status_code == 200:
            collections = response.json().get("result", {}).get("collections", [])
            print(f"✅ Qdrant服務: 正常運行")
            print(f"   可用集合: {[c['name'] for c in collections]}")
        else:
            print(f"❌ Qdrant服務: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Qdrant服務: 連接失敗 - {e}")
    
    # 檢查環境變量
    print(f"\n🔧 環境變量檢查:")
    env_vars = ["OPENAI_API_KEY", "HISTORY_DB_PATH", "NEO4J_URI", "QDRANT_HOST"]
    for var in env_vars:
        value = os.environ.get(var, "未設置")
        if var == "OPENAI_API_KEY" and value != "未設置":
            value = f"{value[:8]}..." if len(value) > 8 else value
        print(f"   {var}: {value}")

def test_api_with_detailed_errors():
    """詳細測試API並捕獲錯誤"""
    print("\n🧪 詳細API測試")
    print("=" * 40)
    
    # 測試健康檢查
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ 健康檢查: {response.status_code}")
        health_data = response.json()
        for check, status in health_data.get("checks", {}).items():
            print(f"   {check}: {status}")
    except Exception as e:
        print(f"❌ 健康檢查失敗: {e}")
    
    # 測試記憶創建（詳細錯誤）
    print(f"\n📝 記憶創建測試:")
    try:
        memory_data = {
            "messages": [
                {"role": "user", "content": "測試記憶內容"}
            ],
            "user_id": "error_test_user"
        }
        
        response = requests.post(f"{BASE_URL}/v1/memories/", json=memory_data)
        print(f"   狀態碼: {response.status_code}")
        print(f"   響應頭: {dict(response.headers)}")
        print(f"   響應內容: {response.text}")
        
        if response.status_code >= 400:
            print(f"❌ 記憶創建失敗")
            try:
                error_data = response.json()
                print(f"   錯誤詳情: {error_data}")
            except:
                print(f"   原始錯誤: {response.text}")
        else:
            result_data = response.json()
            print(f"✅ 記憶創建響應: {result_data}")
            
    except Exception as e:
        print(f"❌ 記憶創建請求失敗: {e}")

def analyze_configuration_issues():
    """分析配置問題"""
    print(f"\n⚙️ 配置問題分析")
    print("=" * 40)
    
    issues_found = []
    
    # 檢查OPENAI_API_KEY
    if not os.environ.get("OPENAI_API_KEY"):
        issues_found.append({
            "問題": "OPENAI_API_KEY未設置",
            "影響": "無法使用OpenAI的LLM和嵌入模型",
            "解決方案": "設置有效的OpenAI API密鑰"
        })
    
    # 檢查Qdrant連接
    try:
        response = requests.get("http://localhost:6333/collections", timeout=5)
        if response.status_code != 200:
            issues_found.append({
                "問題": "Qdrant服務不可用",
                "影響": "無法存儲和檢索向量數據",
                "解決方案": "確保Qdrant服務正在運行"
            })
    except:
        issues_found.append({
            "問題": "無法連接到Qdrant",
            "影響": "向量存儲功能不可用",
            "解決方案": "檢查Qdrant服務狀態和網絡連接"
        })
    
    # 檢查配置端點
    try:
        test_config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "host": "localhost",
                    "port": 6333
                }
            }
        }
        response = requests.post(f"{BASE_URL}/configure", json=test_config)
        if response.status_code >= 400:
            issues_found.append({
                "問題": "配置端點返回錯誤",
                "影響": "無法動態重新配置Memory實例",
                "解決方案": "檢查配置參數和依賴服務"
            })
    except Exception as e:
        issues_found.append({
            "問題": f"配置端點請求失敗: {e}",
            "影響": "無法測試配置功能",
            "解決方案": "檢查API服務狀態"
        })
    
    if issues_found:
        print("❌ 發現以下問題:")
        for i, issue in enumerate(issues_found, 1):
            print(f"\n{i}. {issue['問題']}")
            print(f"   影響: {issue['影響']}")
            print(f"   解決方案: {issue['解決方案']}")
    else:
        print("✅ 未發現明顯的配置問題")

def provide_recommendations():
    """提供修復建議"""
    print(f"\n💡 修復建議")
    print("=" * 40)
    
    recommendations = [
        {
            "優先級": "高",
            "建議": "設置OPENAI_API_KEY環境變量",
            "命令": "export OPENAI_API_KEY='your-api-key-here'"
        },
        {
            "優先級": "高", 
            "建議": "確保Qdrant服務運行",
            "命令": "docker run -p 6333:6333 qdrant/qdrant"
        },
        {
            "優先級": "中",
            "建議": "重新啟動API服務以加載新配置",
            "命令": "重啟容器或重新加載配置"
        },
        {
            "優先級": "低",
            "建議": "使用本地向量存儲作為備選",
            "命令": "配置使用ChromaDB或其他本地向量存儲"
        }
    ]
    
    for rec in recommendations:
        print(f"🔧 [{rec['優先級']}] {rec['建議']}")
        print(f"   命令: {rec['命令']}\n")

def main():
    print("🚨 API測試錯誤分析報告")
    print("=" * 50)
    
    check_service_dependencies()
    test_api_with_detailed_errors()
    analyze_configuration_issues()
    provide_recommendations()
    
    print("\n📋 總結")
    print("=" * 40)
    print("主要問題: Memory實例配置不完整")
    print("根本原因: OPENAI_API_KEY未設置，導致LLM和嵌入模型無法初始化")
    print("影響範圍: 記憶創建、搜索等核心功能無法正常工作")
    print("修復優先級: 立即設置API密鑰並重新配置服務")

if __name__ == "__main__":
    main()
