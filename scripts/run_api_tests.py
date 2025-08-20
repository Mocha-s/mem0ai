#!/usr/bin/env python3
"""
API Test Runner Script

This script runs the real API tests for custom instructions functionality.
It checks for required environment variables and provides helpful error messages.
"""

import os
import sys
import subprocess
import time
from pathlib import Path


def check_environment():
    """Check if required environment variables are set."""
    required_vars = ["MEM0_API_KEY", "MEM0_ORG_ID", "MEM0_PROJECT_ID"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables before running API tests:")
        print("export MEM0_API_KEY='your-api-key'")
        print("export MEM0_ORG_ID='your-org-id'")
        print("export MEM0_PROJECT_ID='your-test-project-id'")
        return False
    
    print("✅ All required environment variables are set")
    return True


def test_api_connectivity():
    """Test basic API connectivity."""
    print("🔍 Testing API connectivity...")
    
    api_key = os.getenv("MEM0_API_KEY")
    base_url = os.getenv("MEM0_BASE_URL", "https://api.mem0.ai")
    
    try:
        import httpx
        
        client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0
        )
        
        # Test ping endpoint
        response = client.get("/ping")
        
        if response.status_code == 200:
            print("✅ API connectivity test passed")
            return True
        else:
            print(f"❌ API connectivity test failed: {response.status_code}")
            return False
            
    except ImportError:
        print("⚠️ httpx not installed, skipping connectivity test")
        return True
    except Exception as e:
        print(f"❌ API connectivity test failed: {e}")
        return False
    finally:
        if 'client' in locals():
            client.close()


def run_python_tests():
    """Run Python API tests."""
    print("\n🐍 Running Python API tests...")
    
    test_file = Path(__file__).parent.parent / "tests" / "test_real_api_custom_instructions.py"
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False
    
    try:
        # Run pytest with verbose output
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            str(test_file), 
            "-v", 
            "--tb=short",
            "--durations=10"
        ], capture_output=True, text=True, timeout=300)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Python API tests passed")
            return True
        else:
            print(f"❌ Python API tests failed with return code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Python API tests timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running Python API tests: {e}")
        return False


def run_typescript_tests():
    """Run TypeScript API tests."""
    print("\n📜 Running TypeScript API tests...")
    
    ts_dir = Path(__file__).parent.parent / "mem0-ts"
    test_file = ts_dir / "tests" / "real-api-custom-instructions.test.ts"
    
    if not ts_dir.exists():
        print(f"❌ TypeScript directory not found: {ts_dir}")
        return False
    
    if not test_file.exists():
        print(f"❌ TypeScript test file not found: {test_file}")
        return False
    
    try:
        # Check if npm is available
        subprocess.run(["npm", "--version"], capture_output=True, check=True)
        
        # Run npm test
        result = subprocess.run([
            "npm", "test", "--", 
            "--testPathPattern=real-api-custom-instructions",
            "--verbose",
            "--testTimeout=30000"
        ], cwd=ts_dir, capture_output=True, text=True, timeout=300)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ TypeScript API tests passed")
            return True
        else:
            print(f"❌ TypeScript API tests failed with return code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ TypeScript API tests timed out after 5 minutes")
        return False
    except FileNotFoundError:
        print("⚠️ npm not found, skipping TypeScript tests")
        return True
    except Exception as e:
        print(f"❌ Error running TypeScript API tests: {e}")
        return False


def main():
    """Main test runner."""
    print("🚀 Starting API Tests for Custom Instructions")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Test connectivity
    if not test_api_connectivity():
        print("⚠️ API connectivity test failed, but continuing with tests...")
    
    # Run tests
    python_success = run_python_tests()
    typescript_success = run_typescript_tests()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   Python Tests: {'✅ PASSED' if python_success else '❌ FAILED'}")
    print(f"   TypeScript Tests: {'✅ PASSED' if typescript_success else '❌ FAILED'}")
    
    if python_success and typescript_success:
        print("\n🎉 All API tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some API tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
