#!/usr/bin/env python3
"""
Mem0 环境变量配置验证脚本

验证数据库路径配置的一致性，避免数据分散问题。
"""

import os
import sys
from pathlib import Path

def load_env_file(env_path):
    """加载 .env 文件"""
    env_vars = {}
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except Exception as e:
        print(f"❌ 无法读取 .env 文件: {e}")
        return None
    return env_vars

def validate_paths(env_vars):
    """验证路径配置的一致性"""
    print("🔍 验证路径配置...")
    
    issues = []
    warnings = []
    
    # 检查关键路径变量
    key_paths = {
        'MEM0_DATA_PATH': '基础数据目录',
        'MEM0_HISTORY_DB_PATH': '历史数据库路径',
        'MEM0_VECTOR_STORAGE_PATH': '向量存储路径',
        'MEM0_DIR': 'Mem0配置目录'
    }
    
    print("\n📋 当前路径配置:")
    for var, desc in key_paths.items():
        value = env_vars.get(var, '未设置')
        print(f"   {var}: {value}")
        
        if var == 'MEM0_HISTORY_DB_PATH':
            # 关键检查：数据库路径必须是绝对路径
            if value == '未设置' or not value.startswith('/'):
                issues.append(f"{var} 应该使用绝对路径（如 /app/data/history.db）")
        
        elif var == 'MEM0_DATA_PATH':
            # 数据目录可以是相对路径（开发环境）
            if value == '未设置':
                warnings.append(f"{var} 未设置，将使用默认值")
    
    # 检查路径一致性
    data_path = env_vars.get('MEM0_DATA_PATH', './data')
    history_path = env_vars.get('MEM0_HISTORY_DB_PATH', '')
    
    if history_path and not history_path.startswith('/app/data/'):
        issues.append("MEM0_HISTORY_DB_PATH 应该以 /app/data/ 开头以确保容器内外一致性")
    
    return issues, warnings

def check_docker_setup():
    """检查 Docker 配置"""
    print("\n🐳 检查 Docker 配置...")
    
    # 检查 docker-compose.yaml 是否存在
    compose_file = Path("docker-compose.yaml")
    if not compose_file.exists():
        print("⚠️  未找到 docker-compose.yaml 文件")
        return False
    
    # 检查数据目录是否存在
    data_dir = Path("./data")
    if not data_dir.exists():
        print("⚠️  数据目录 ./data 不存在，首次运行时会自动创建")
    else:
        print(f"✅ 数据目录存在: {data_dir.absolute()}")
        
        # 检查数据库文件
        db_file = data_dir / "history.db"
        if db_file.exists():
            size = db_file.stat().st_size
            print(f"✅ 数据库文件存在: {db_file} ({size} bytes)")
        else:
            print("⚠️  数据库文件不存在，首次运行时会自动创建")
    
    return True

def main():
    print("🧪 Mem0 环境变量配置验证")
    print("=" * 50)
    
    # 检查 .env 文件
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ 未找到 .env 文件")
        print("请确保在正确的目录运行此脚本（包含 .env 文件的目录）")
        sys.exit(1)
    
    print(f"✅ 找到配置文件: {env_file.absolute()}")
    
    # 加载环境变量
    env_vars = load_env_file(env_file)
    if env_vars is None:
        sys.exit(1)
    
    # 验证路径配置
    issues, warnings = validate_paths(env_vars)
    
    # 检查 Docker 设置
    docker_ok = check_docker_setup()
    
    # 显示结果
    print("\n" + "=" * 50)
    print("📊 验证结果:")
    
    if issues:
        print(f"\n❌ 发现 {len(issues)} 个配置问题:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    
    if warnings:
        print(f"\n⚠️  {len(warnings)} 个警告:")
        for i, warning in enumerate(warnings, 1):
            print(f"   {i}. {warning}")
    
    if not issues and docker_ok:
        print("\n🎉 配置验证通过！")
        print("数据库路径配置正确，可以避免数据分散问题。")
    elif not issues:
        print("\n✅ 环境变量配置正确")
        print("建议检查 Docker 环境设置")
    else:
        print(f"\n❌ 发现配置问题，请修复后重试")
        sys.exit(1)

if __name__ == "__main__":
    main()