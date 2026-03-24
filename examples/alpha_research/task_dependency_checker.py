#!/usr/bin/env python3
"""
任务依赖检查器

功能:
- 检查上游任务是否成功完成
- 检查数据新鲜度
- 依赖失败时跳过任务并告警
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

class DependencyChecker:
    def __init__(self, state_file: str = "./.task_state.json"):
        self.state_file = Path(state_file)
        self.state = self._load_state()
    
    def check_dependencies(self, task_name: str, dependencies: list) -> tuple[bool, str]:
        """
        检查依赖是否满足
        
        Args:
            task_name: 当前任务名称
            dependencies: 依赖配置列表
            
        Returns:
            (is_ready, message)
        """
        if not dependencies:
            return True, "✅ 无依赖要求"
        
        for dep in dependencies:
            upstream_task = dep["task"]
            condition = dep.get("condition", "success")
            max_age = dep.get("max_age_minutes", 120)
            required = dep.get("required", True)
            
            # 检查上游任务状态
            if upstream_task not in self.state:
                msg = f"❌ 依赖任务 {upstream_task} 从未执行"
                if required:
                    return False, msg
                else:
                    print(f"⚠️  警告：{msg} (非必需，继续执行)")
                    continue
            
            last_run = self.state[upstream_task]
            
            # 检查执行状态
            if condition == "success" and last_run.get("status") != "success":
                msg = f"❌ 依赖任务 {upstream_task} 执行失败 (状态：{last_run.get('status')})"
                if required:
                    return False, msg
                else:
                    print(f"⚠️  警告：{msg} (非必需，继续执行)")
                    continue
            
            # 检查数据新鲜度
            last_run_time = datetime.fromisoformat(last_run["timestamp"])
            age_minutes = (datetime.now() - last_run_time).total_seconds() / 60
            
            if age_minutes > max_age:
                msg = f"❌ 依赖任务 {upstream_task} 数据过期 ({age_minutes:.0f} 分钟 > {max_age} 分钟)"
                if required:
                    return False, msg
                else:
                    print(f"⚠️  警告：{msg} (非必需，继续执行)")
                    continue
        
        return True, "✅ 所有依赖满足"
    
    def update_state(self, task_name: str, status: str, duration_seconds: float = 0):
        """更新任务状态"""
        self.state[task_name] = {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "duration_seconds": duration_seconds
        }
        self._save_state()
    
    def _load_state(self) -> dict:
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {}
    
    def _save_state(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)


def load_dependencies(config_file: str = "./config/task_dependencies.json") -> dict:
    """加载依赖配置"""
    config_path = Path(config_file)
    if not config_path.exists():
        return {}
    
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def main():
    """主函数 - 用于测试"""
    if len(sys.argv) < 2:
        print("用法：python3 task_dependency_checker.py <任务名称>")
        print("示例：python3 task_dependency_checker.py 每日选股")
        sys.exit(1)
    
    task_name = sys.argv[1]
    
    # 加载依赖配置
    dependencies_config = load_dependencies()
    dependencies = dependencies_config.get(task_name, {}).get("depends_on", [])
    
    # 检查依赖
    checker = DependencyChecker()
    is_ready, message = checker.check_dependencies(task_name, dependencies)
    
    print(f"\n任务：{task_name}")
    print(f"依赖检查：{message}")
    
    if not is_ready:
        print("\n⚠️  跳过任务执行")
        sys.exit(1)
    else:
        print("\n✅ 开始执行任务...")
        sys.exit(0)


if __name__ == "__main__":
    main()
