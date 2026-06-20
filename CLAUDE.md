# VNPY Alpha - Claude Code 操作指南

> **文档版本**: 1.0.0  
> **最后更新**: 2026-06-21  
> **适用对象**: Claude Code AI 助手

---

## 🎯 快速参考

### 项目定位
A 股量化交易系统，核心是**行业轮动策略**和**多因子选股**。

### 关键文件
| 文件 | 用途 | 修改频率 |
|------|------|----------|
| `alpha/strategy/industry_rotation.py` | 行业轮动策略核心 | 高 |
| `alpha/strategy/stock_screener_strategy.py` | 选股策略基类 | 中 |
| `core/data_source_router.py` | 数据源路由 | 低 |
| `tests/integration/test_industry_rotation.py` | 集成测试 | 高 |

### 常用命令
```bash
# 运行测试
python3 -m pytest tests/integration/test_industry_rotation.py -v

# 运行单个测试类
python3 -m pytest tests/integration/test_industry_rotation.py::TestIndustryRotationValuation -v

# 检查代码质量
python3 -m flake8 alpha/strategy/industry_rotation.py

# 查看日志
tail -f logs/strategy.log
```

---

## 📋 代码修改工作流

### 1. 修改前检查清单
- [ ] 理解当前实现逻辑
- [ ] 确认修改范围（单文件 vs 多文件）
- [ ] 检查是否有相关测试
- [ ] 评估边界条件影响

### 2. 修改步骤
```bash
# 1. 阅读目标文件
read alpha/strategy/industry_rotation.py

# 2. 理解上下文
read alpha/strategy/stock_screener_strategy.py

# 3. 进行修改
edit alpha/strategy/industry_rotation.py

# 4. 运行测试验证
exec python3 -m pytest tests/integration/test_industry_rotation.py -v

# 5. 检查边界条件
# - NaN/Inf 处理
# - 除零保护
# - 空值处理
# - 代码标准化（北交所等）
```

### 3. 修改后验证
```bash
# 运行完整测试套件
exec python3 -m pytest tests/integration/ -v

# 检查覆盖率
exec python3 -m pytest --cov=alpha.strategy --cov-report=term-missing

# 验证日志输出
exec python3 -c "
import logging
logging.basicConfig(level=logging.WARNING)
from alpha.strategy.industry_rotation import IndustryRotationStrategy
# 测试代码...
"
```

---

## 🔍 代码审查要点

### 边界条件检查
1. **数值处理**
   ```python
   # ✅ 正确：防护 NaN/Inf
   def safe_float(value, default=None):
       if value is None or value == '':
           return default
       try:
           result = float(value)
           if math.isinf(result):
               return default
           return result
       except (ValueError, TypeError):
           return default
   ```

2. **除零保护**
   ```python
   # ✅ 正确：检查除数
   def _calculate_industry_turnover(self, stocks, bars):
       total_volume = sum(bars[s].volume for s in stocks if s in bars)
       if total_volume == 0:
           return 0.0  # 避免除零
       return total_volume / 1_000_000
   ```

3. **代码标准化**
   ```python
   # ✅ 正确：覆盖所有交易所
   def _normalize_symbol(code: str, target_market: str = None) -> str:
       if len(code) == 6:
           first_two = code[:2]
           first_three = code[:3]
           if first_three in ('600', '601', '603', '605', '688'):
               return f"{code}.SSE"
           elif first_two in ('83', '87', '88', '43'):
               return f"{code}.BSE"  # 北交所
           else:
               return f"{code}.SZSE"
   ```

### 日志规范
```python
# ✅ 正确：使用 logging 模块
import logging
logger = logging.getLogger(__name__)

# 记录 fallback 使用
logger.warning(
    "Valuation cache penetration for %s: using hardcoded fallback values",
    symbol
)

# ❌ 避免：print 语句
print(f"Error: {e}")  # 不要这样做
```

### 错误处理
```python
# ✅ 正确：明确的 fallback + 日志
try:
    result = fetch_data()
except Exception as e:
    logger.warning(f"Data fetch failed: {e}, using fallback")
    result = DEFAULT_VALUE

# ❌ 避免：静默吞掉异常
try:
    result = fetch_data()
except:
    pass  # 不要这样做
```

---

## 🧪 测试编写指南

### 测试结构
```python
class TestIndustryRotationValuation:
    """估值数据获取测试"""
    
    def test_safe_float_conversion(self):
        """测试安全数值转换"""
        assert safe_float('12.5') == 12.5
        assert safe_float('nan') is None
        assert safe_float(float('inf')) is None
        assert safe_float(None) is None
    
    def test_get_stock_valuation_fallback(self):
        """测试估值 fallback 机制"""
        fetcher = ValuationFetcher()
        # Mock 数据源失败
        with patch.object(fetcher, '_fetch_from_tushare', side_effect=Exception("API error")):
            with patch.object(fetcher, '_fetch_from_akshare', side_effect=Exception("API error")):
                result = fetcher._fetch_symbol_valuation('000001.SZSE')
                assert result == (15.0, 2.0, 1.5, 'fallback')
```

### 测试覆盖范围
- ✅ 正常路径（happy path）
- ✅ 边界条件（NaN, Inf, 0, None）
- ✅ 错误处理（API 失败、数据缺失）
- ✅ 代码标准化（各交易所代码）

### 运行测试
```bash
# 运行所有测试
python3 -m pytest tests/integration/test_industry_rotation.py -v

# 运行特定测试类
python3 -m pytest tests/integration/test_industry_rotation.py::TestIndustryRotationValuation -v

# 运行单个测试
python3 -m pytest tests/integration/test_industry_rotation.py::TestIndustryRotationValuation::test_safe_float_conversion -v
```

---

## 📊 数据流理解

### 行业轮动策略数据流
```
1. 初始化
   IndustryRotationStrategy.__init__()
   ↓
2. 加载行业配置
   INDUSTRY_STOCKS = {...}
   ↓
3. 计算行业评分
   _calculate_industry_scores()
   ├── 动量评分 (40%)
   ├── 估值评分 (30%)
   ├── 资金流评分 (20%)
   └── 波动率评分 (10%)
   ↓
4. 选股
   _select_stocks_in_industries()
   ↓
5. 组合构建
   create_portfolio()
```

### 估值数据获取流程
```
_get_industry_valuation(industry)
↓
检查内存缓存
↓ (miss)
检查本地 Parquet 缓存
↓ (miss)
调用 ValuationFetcher._fetch_symbol_valuation()
├── 尝试 Tushare API
├── 失败 → 尝试 AKShare API
├── 失败 → 使用硬编码 fallback (PE=15, PB=2)
└── 记录 warning 日志
↓
计算行业平均估值
↓
返回 (PE, PB, dividend_yield, source)
```

---

## 🔧 常见问题解决

### 1. 测试失败：ImportError
**症状**: `ModuleNotFoundError: No module named 'vnpy'`
**解决**:
```bash
# 确保在项目根目录
cd /Users/rowang/projects/vnpy

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -e .
```

### 2. 估值数据获取失败
**症状**: 日志中出现 "Valuation cache penetration"
**原因**: Tushare/AKShare API 不可用
**解决**:
- 检查网络连接
- 验证 API token: `echo $TUSHARE_TOKEN`
- 系统会自动使用 fallback 值

### 3. 北交所代码识别错误
**症状**: 83/87/88/43 开头的代码被错误映射
**解决**: 已修复，确认 `_normalize_symbol()` 包含北交所逻辑

### 4. 除零错误
**症状**: `ZeroDivisionError` in `_calculate_industry_turnover`
**解决**: 已修复，检查 `total_volume == 0` 的情况

---

## 📝 代码提交规范

### Commit Message 格式
```
<type>: <subject>

<body>

<footer>
```

### Type 类型
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式（不影响逻辑）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具

### 示例
```bash
git commit -m "fix: 修复 industry_rotation.py 的 4 个 P0 边界条件问题

1. safe_float(): 添加 math.isinf() 防护
2. _normalize_symbol(): 北交所代码标准化（83/87/88/43 → .BSE）
3. _calculate_industry_turnover(): 除零保护
4. 估值缓存穿透: 添加 warning 日志

修复由 coding-agents CLI (Claude Code) 完成，22 个测试全部通过。"
```

---

## 🚀 性能优化建议

### 1. 缓存策略
```python
# ✅ 使用内存缓存减少 API 调用
_cache = {}

def get_valuation(symbol):
    if symbol in _cache:
        return _cache[symbol]
    result = fetch_from_api(symbol)
    _cache[symbol] = result
    return result
```

### 2. 批量处理
```python
# ✅ 批量获取数据，减少 API 调用次数
def fetch_multiple_valuations(symbols):
    # 一次 API 调用获取多个 symbol
    return api.fetch_batch(symbols)
```

### 3. 异步处理
```python
# ✅ 使用 asyncio 并行获取数据
import asyncio

async def fetch_all(symbols):
    tasks = [fetch_symbol(s) for s in symbols]
    return await asyncio.gather(*tasks)
```

---

## 🔒 安全注意事项

### API Token 管理
```python
# ✅ 从环境变量读取
import os
TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN')

# ❌ 不要硬编码
TUSHARE_TOKEN = 'your_token_here'  # 危险！
```

### 数据验证
```python
# ✅ 验证输入数据
def process_data(data):
    if not isinstance(data, dict):
        raise ValueError("Expected dict")
    if 'price' not in data:
        raise KeyError("Missing 'price' field")
    # 处理数据...
```

---

## 📚 相关资源

### 内部文档
- `AGENTS.md` - 通用 AI agent 指南
- `docs/ARCHITECTURE.md` - 系统架构
- `docs/DATA_FLOW.md` - 数据流详解

### 外部资源
- [VNPY 官方文档](https://www.vnpy.com/docs/)
- [Tushare API](https://tushare.pro/document/2)
- [AKShare 文档](https://akshare.akfamily.xyz/)

---

## 🆘 获取帮助

### 调试步骤
1. 检查日志: `tail -f logs/strategy.log`
2. 运行测试: `python3 -m pytest tests/ -v`
3. 查看代码注释
4. 搜索历史 issue

### 联系支持
- 内部: 联系 Atlas (Chief Architect)
- 外部: 查看相关文档或提交 issue

---

**最后更新**: 2026-06-21 by Atlas
