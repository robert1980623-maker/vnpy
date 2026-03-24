#!/usr/bin/env python3
"""
数据新鲜度监控器 (重构版)

功能:
- 检查数据新鲜度
- 生成监控报告
- 触发告警
- 自动修复决策
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict
import yaml


@dataclass
class StockStatus:
    """单只股票状态"""
    symbol: str
    data_date: str
    age_hours: float
    status: str  # fresh/warning/critical
    file_path: str


@dataclass
class MonitorReport:
    """监控报告"""
    check_time: str
    expected_date: str
    status: str  # fresh/partial_stale/stale
    fresh_count: int
    stale_count: int
    warning_count: int
    critical_count: int
    fresh_ratio: float
    quality_score: float
    stale_stocks: List[Dict]
    actions_recommended: List[str]
    alerts: List[Dict]


class DataFreshnessMonitor:
    """数据新鲜度监控器"""
    
    def __init__(self, config_path: str = "./config/data_freshness_config.yaml"):
        self.config = self._load_config(config_path)
        self.data_dir = Path("./data/akshare/bars")
        self.cache_dir = Path("./cache/freshness_monitor")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 从配置加载阈值
        self.max_age_hours = self.config["freshness"]["max_age_hours"]
        self.warning_threshold = self.config["freshness"]["warning_threshold"]
        self.critical_threshold = self.config["freshness"]["critical_threshold"]
        self.target_fresh_ratio = self.config["freshness"]["target_fresh_ratio"]
        
        self.check_time = datetime.now()
        self.today = self.check_time.strftime("%Y-%m-%d")
        
        self.report = None
    
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        
        # 默认配置
        return {
            "freshness": {
                "max_age_hours": 24,
                "warning_threshold": 48,
                "critical_threshold": 72,
                "target_fresh_ratio": 0.95
            }
        }
    
    def check_data_freshness(self) -> MonitorReport:
        """检查数据新鲜度"""
        print("=" * 70)
        print(f"数据新鲜度检查 - {self.check_time.strftime('%Y-%m-%d %H:%M')}")
        print("=" * 70)
        print(f"期望日期：{self.today}")
        print(f"允许滞后：{self.max_age_hours} 小时\n")
        
        if not self.data_dir.exists():
            print(f"❌ 数据目录不存在：{self.data_dir}")
            return self._create_error_report("数据目录不存在")
        
        csv_files = list(self.data_dir.glob("*.csv"))
        if not csv_files:
            print(f"❌ 数据目录为空")
            return self._create_error_report("数据目录为空")
        
        print(f"检查 {len(csv_files)} 个文件...\n")
        
        fresh_count = 0
        warning_count = 0
        critical_count = 0
        stale_stocks = []
        
        for csv_file in csv_files:
            symbol = csv_file.stem.replace("_", ".").upper()
            
            try:
                # 读取最后一行
                result = subprocess.run(
                    ["tail", "-1", str(csv_file)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode != 0 or not result.stdout.strip():
                    continue
                
                last_line = result.stdout.strip().split(",")
                if len(last_line) < 2:
                    continue
                
                data_date = last_line[1]
                data_datetime = datetime.strptime(data_date, "%Y-%m-%d")
                age_hours = (self.check_time - data_datetime).total_seconds() / 3600
                
                # 判断状态
                if age_hours <= self.max_age_hours:
                    status = "fresh"
                    fresh_count += 1
                elif age_hours <= self.warning_threshold:
                    status = "warning"
                    warning_count += 1
                elif age_hours <= self.critical_threshold:
                    status = "critical"
                    critical_count += 1
                else:
                    status = "critical"
                    critical_count += 1
                
                stale_stocks.append({
                    "symbol": symbol,
                    "data_date": data_date,
                    "age_hours": round(age_hours, 1),
                    "status": status,
                    "file_path": str(csv_file)
                })
                
            except Exception as e:
                critical_count += 1
                stale_stocks.append({
                    "symbol": symbol,
                    "data_date": "unknown",
                    "age_hours": -1,
                    "status": "error",
                    "file_path": str(csv_file),
                    "error": str(e)
                })
        
        # 计算统计
        stale_count = warning_count + critical_count
        total = fresh_count + stale_count
        fresh_ratio = fresh_count / total if total > 0 else 0
        
        # 判断整体状态
        if fresh_ratio >= self.target_fresh_ratio:
            overall_status = "fresh"
        elif fresh_ratio >= 0.80:
            overall_status = "partial_stale"
        else:
            overall_status = "stale"
        
        # 生成建议动作
        actions = self._generate_actions(fresh_ratio, stale_stocks)
        
        # 生成告警
        alerts = self._generate_alerts(fresh_ratio, stale_stocks)
        
        # 创建报告
        self.report = MonitorReport(
            check_time=self.check_time.isoformat(),
            expected_date=self.today,
            status=overall_status,
            fresh_count=fresh_count,
            stale_count=stale_count,
            warning_count=warning_count,
            critical_count=critical_count,
            fresh_ratio=round(fresh_ratio, 4),
            quality_score=round(fresh_ratio * 100, 2),
            stale_stocks=sorted(stale_stocks, key=lambda x: x["age_hours"], reverse=True)[:20],
            actions_recommended=actions,
            alerts=alerts
        )
        
        # 打印结果
        self._print_report()
        
        return self.report
    
    def _generate_actions(self, fresh_ratio: float, stale_stocks: List[Dict]) -> List[str]:
        """生成建议动作"""
        actions = []
        
        if fresh_ratio < self.target_fresh_ratio:
            actions.append("触发增量下载任务")
        
        if fresh_ratio < 0.80:
            actions.append("触发紧急补采任务")
            actions.append("发送严重告警通知")
        
        critical_stocks = [s for s in stale_stocks if s["status"] == "critical"]
        if critical_stocks:
            actions.append(f"优先更新 {len(critical_stocks)} 只严重滞后股票")
        
        return actions
    
    def _generate_alerts(self, fresh_ratio: float, stale_stocks: List[Dict]) -> List[Dict]:
        """生成告警"""
        alerts = []
        
        if fresh_ratio < 0.80:
            alerts.append({
                "level": "critical",
                "message": f"数据新鲜率低于 80% (当前：{fresh_ratio*100:.1f}%)",
                "timestamp": self.check_time.isoformat()
            })
        elif fresh_ratio < self.target_fresh_ratio:
            alerts.append({
                "level": "warning",
                "message": f"数据新鲜率低于目标 (当前：{fresh_ratio*100:.1f}%, 目标：{self.target_fresh_ratio*100:.1f}%)",
                "timestamp": self.check_time.isoformat()
            })
        
        critical_stocks = [s for s in stale_stocks if s["status"] == "critical" and s["age_hours"] > 0]
        for stock in critical_stocks[:5]:
            alerts.append({
                "level": "critical",
                "message": f"股票 {stock['symbol']} 数据滞后 {stock['age_hours']:.1f} 小时",
                "timestamp": self.check_time.isoformat()
            })
        
        return alerts
    
    def _create_error_report(self, error_message: str) -> MonitorReport:
        """创建错误报告"""
        return MonitorReport(
            check_time=self.check_time.isoformat(),
            expected_date=self.today,
            status="error",
            fresh_count=0,
            stale_count=0,
            warning_count=0,
            critical_count=0,
            fresh_ratio=0.0,
            quality_score=0.0,
            stale_stocks=[],
            actions_recommended=["检查数据目录配置", "验证数据下载任务"],
            alerts=[{
                "level": "critical",
                "message": error_message,
                "timestamp": self.check_time.isoformat()
            }]
        )
    
    def _print_report(self):
        """打印报告"""
        if not self.report:
            return
        
        print(f"\n📊 统计:")
        print(f"  新鲜数据：{self.report.fresh_count} 只")
        print(f"  警告数据：{self.report.warning_count} 只")
        print(f"  严重滞后：{self.report.critical_count} 只")
        
        print(f"\n📈 质量评分:")
        print(f"  新鲜率：{self.report.fresh_ratio*100:.1f}%")
        print(f"  质量分：{self.report.quality_score:.1f}/100")
        
        if self.report.status == "fresh":
            print(f"\n✅ 数据新鲜：{self.report.fresh_count}/{self.report.fresh_count + self.report.stale_count}")
        elif self.report.status == "partial_stale":
            print(f"\n⚠️ 部分滞后：{self.report.stale_count} 只股票需要更新")
        else:
            print(f"\n❌ 数据滞后：{self.report.stale_count} 只股票需要立即更新")
        
        if self.report.stale_stocks:
            print(f"\n📉 滞后股票 Top 5:")
            for stock in self.report.stale_stocks[:5]:
                if stock["age_hours"] > 0:
                    print(f"  - {stock['symbol']}: {stock['data_date']} ({stock['age_hours']:.1f} 小时前) [{stock['status']}]")
        
        if self.report.actions_recommended:
            print(f"\n💡 建议动作:")
            for action in self.report.actions_recommended:
                print(f"  • {action}")
    
    def save_report(self, output_path: str = "./reports/data_freshness_report.json"):
        """保存报告"""
        if not self.report:
            print("⚠️ 没有报告可保存")
            return
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(asdict(self.report), f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 报告已保存：{output_file}")
    
    def should_trigger_auto_fix(self) -> bool:
        """判断是否应该触发自动修复"""
        if not self.report:
            return False
        
        return (
            self.report.fresh_ratio < self.target_fresh_ratio or
            self.report.critical_count > 0
        )
    
    def get_stale_stocks_for_update(self, limit: int = 50) -> List[str]:
        """获取需要更新的股票列表"""
        if not self.report:
            return []
        
        stale = [s for s in self.report.stale_stocks if s["age_hours"] > 0]
        return [s["symbol"] for s in stale[:limit]]


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description="数据新鲜度监控")
    parser.add_argument("--once", action="store_true", help="只执行一次")
    parser.add_argument("--no-auto-fix", action="store_true", help="禁用自动修复")
    parser.add_argument("--no-notify", action="store_true", help="禁用通知")
    parser.add_argument("--config", default="./config/data_freshness_config.yaml", help="配置文件路径")
    args = parser.parse_args()
    
    monitor = DataFreshnessMonitor(config_path=args.config)
    monitor.check_data_freshness()
    monitor.save_report()
    
    if not args.no_auto_fix and monitor.should_trigger_auto_fix():
        print("\n🔄 触发自动修复...")
        # 这里可以调用自动修复逻辑
        stale_stocks = monitor.get_stale_stocks_for_update()
        print(f"   需要更新的股票：{len(stale_stocks)} 只")


if __name__ == "__main__":
    main()
