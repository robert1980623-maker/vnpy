# 涨停龙头策略 🐉

## 快速开始

### 1. 运行策略
```bash
cd /Users/rowang/projects/vnpy/examples/alpha_research

# 手动运行选股
python3 limit_up_strategy_runner.py --auto --notify

# 查看结果
cat reports/limit_up_strategy/report_$(date +%Y%m%d).json
```

### 2. 查看 Cron 任务
```bash
openclaw cron list | grep "涨停龙头"
```

### 3. 运行测试
```bash
pytest tests/test_limit_up_strategy.py -v
python3 test_limit_up_demo.py
```

## 策略逻辑

1. **获取涨停股票** - 每日收盘后获取所有涨停股票
2. **筛选龙头** - 连续涨停≥2 天，量比≥1.5，市值 50-500 亿
3. **评分排名** - 连板数 (40%) + 板块效应 (25%) + 量比 (20%) + 市值 (15%)
4. **生成信号** - TOP5 龙头候选，自动止损止盈
5. **发送通知** - Slack 推送选股结果

## 核心参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 最小连板 | 2 天 | 至少 2 个涨停板 |
| 量比阈值 | 1.5 | 成交量放大倍数 |
| 市值范围 | 50-500 亿 | 偏好中小盘 |
| 最大持仓 | 5 只 | 同时持仓上限 |
| 止损 | -8% | 亏损止损线 |
| 止盈 | +20% | 盈利止盈线 |

## 文件结构

```
strategies/
├── __init__.py              # 包初始化
├── limit_up_leader.py       # 核心策略
└── README.md                # 本文件

../
├── limit_up_strategy_runner.py  # 运行器
├── test_limit_up_demo.py        # 演示脚本
├── config/limit_up_strategy.json # 配置
└── docs/LIMIT_UP_STRATEGY.md    # 详细文档
```

## 调度时间

- **Cron 表达式**: `0 17 * * 1-5`
- **运行时间**: 交易日 17:00（收盘后）
- **执行模型**: qwen3.5-plus

## 风险提示

⚠️ 涨停股波动大，请谨慎使用！
- 先用模拟盘测试
- 严格执行止损
- 控制仓位（≤ 总资金 10%）

## 更多文档

- [完整策略文档](../docs/LIMIT_UP_STRATEGY.md)
- [总结报告](../LIMIT_UP_STRATEGY_SUMMARY.md)
