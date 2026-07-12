# 项目校招级改造计划

> 创建日期: 2026-07-12
> 目标: Demo → 面试可讲 30min+ 的产品级项目

---

## 基线评估

| 维度 | 当前 | 目标 |
|------|------|------|
| 分析逻辑 | ✅ 通用 RFM/漏斗/CLV | 保持 |
| 代码架构 | ✅ 模块化 + 单次加载 | 保持 |
| 测试覆盖 | ✅ 29 用例 | → mypy 严格模式通过 |
| 数据接入 | ❌ 列名全程硬编码 | → 列名映射配置 |
| 入口方式 | ❌ 文件名写死在 config.py | → CLI argparse |
| 业务参数 | ⚠️ 部分硬编码 | → 全部外置到 TOML |
| CI/CD | ❌ 无 | → GitHub Actions |
| 架构文档 | ❌ 无 | → ARCHITECTURE.md |

---

## Phase 1 ─ 数据接入层解耦 (核心改造)

### 1.1 列名映射配置 `column_mapping.toml`

```toml
[required]
customer_id = "CustomerID"
invoice_no   = "InvoiceNo"
invoice_date = "InvoiceDate"
quantity     = "Quantity"
unit_price   = "UnitPrice"

[optional]
stock_code   = "StockCode"
description  = "Description"
country      = "Country"
```

**影响文件**: `data_preprocessing.py` / `rfm_analysis.py` / `funnel_attribution.py` / `clv_estimation.py`

### 1.2 Schema 校验 `src/schema.py` (新增)

- 用 dataclass 定义列名映射，类型安全
- `validate_columns(df, mapping)` — 启动时检查必填列是否存在，缺列→友好报错
- 取消订单检测逻辑可配置 (现在是写死的 `"C"` 前缀)

### 1.3 业务参数外置 `business_params.toml`

```toml
[funnel]
repeat_buyer_threshold = 2
regular_buyer_threshold = 5
high_value_quantile = 0.80
vip_quantile = 0.95

[clv]
min_lifespan_days = 30
freq_cap = 10
projection_months = 12
```

**影响文件**: `funnel_attribution.py` / `clv_estimation.py`

---

## Phase 2 ─ CLI 入口与运行方式

### 2.1 argparse CLI

```bash
# 基础用法
python -m src.main --data ./data/my_orders.xlsx

# 指定输出目录
python -m src.main --data ./data/my_orders.xlsx --output ./results

# 使用自定义列名映射
python -m src.main --data ./data/my_orders.xlsx --mapping ./column_mapping.toml

# 跳过图表（无 GUI 环境）
python -m src.main --data ./data/my_orders.xlsx --no-plot

# 仅运行某个模块
python -m src.main --data ./data/my_orders.xlsx --only rfm
```

### 2.2 程序化 API (保持兼容)

```python
from src.config import load_config
from src.data_preprocessing import load_and_clean
from src.rfm_analysis import run_rfm

cfg = load_config("column_mapping.toml")
df = load_and_clean("data/my_orders.xlsx", column_mapping=cfg)
rfm, summary = run_rfm(df, "output/")
```

**影响文件**: `src/main.py` / `src/config.py`

---

## Phase 3 ─ 类型安全与静态检查

### 3.1 mypy 严格模式

```toml
[tool.mypy]
strict = true
```

修复所有类型错误（预估 15-30 个），主要是:
- `dict` → `dict[str, int]`
- pandas Series/DataFrame 泛型标注
- matplotlib Figure/Axes 类型

### 3.2 ruff lint

```toml
[tool.ruff]
target-version = "py312"
```

统一代码风格，自动修复。

---

## Phase 4 ─ CI/CD (GitHub Actions)

### 4.1 `.github/workflows/ci.yml`

```yaml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -e ".[dev]"
      - run: pytest -v
      - run: mypy src/
      - run: ruff check src/ tests/
```

每次 push 自动跑测试 + 类型检查 + lint。仓库 badge 显示 passing/failing。

---

## Phase 5 ─ 架构文档

### 5.1 `docs/ARCHITECTURE.md`
- 数据流图 (文本)
- 设计决策记录 (为什么不用 BG/NBD、为什么 np.select)
- 扩展指南

### 5.2 `docs/MODULES.md`
- 每个模块的职责边界
- 函数索引 (签名 + 一句话说明)
- 依赖关系

---

## Phase 6 ─ README 升级

- Badge: CI passing / coverage / Python version
- "换一份数据怎么跑" 快速指南
- "面试怎么说" 精简版
- 技术选型理由

---

## 依赖顺序

```
Phase 1 (数据解耦) → Phase 2 (CLI)
     ↓
Phase 3 (mypy) 可以和第 5 步并行
     ↓
Phase 4 (CI) 依赖 Phase 3 通过
     ↓
Phase 5-6 (文档) 可以与 Phase 4 并行
```

---

## 验收标准 (不可跳过)

| 门 | 命令 | 预期 |
|----|------|------|
| 测试 | `pytest -v` | 29+ 用例全绿 |
| 类型 | `mypy src/ --strict` | 0 errors |
| Lint | `ruff check src/ tests/` | 0 warnings |
| 管线 | `python -m src.main --data <file>` | 三模块正常输出 |
| 文档 | 面试官能看懂 | — |

---

## 任务清单

- [ ] Phase 1.1: 创建 `column_mapping.toml`
- [ ] Phase 1.2: 创建 `src/schema.py` (列名校验)
- [ ] Phase 1.3: 重构 `data_preprocessing.py` 接受列名映射
- [ ] Phase 1.4: 重构 `rfm_analysis.py` 接受列名映射
- [ ] Phase 1.5: 重构 `funnel_attribution.py` 接受列名映射
- [ ] Phase 1.6: 重构 `clv_estimation.py` 接受列名映射
- [ ] Phase 1.7: 创建 `business_params.toml`
- [ ] Phase 2.1: `main.py` 改为 argparse CLI
- [ ] Phase 2.2: `config.py` 改为动态加载配置
- [ ] Phase 3.1: 更新 `pyproject.toml` (mypy + ruff)
- [ ] Phase 3.2: 修复所有 mypy 错误
- [ ] Phase 4.1: 创建 `.github/workflows/ci.yml`
- [ ] Phase 5.1: 创建 `docs/ARCHITECTURE.md`
- [ ] Phase 5.2: 创建 `docs/MODULES.md`
- [ ] Phase 6.1: 更新 README (badge + 使用指南)
- [ ] Phase 6.2: 更新测试适配新接口
- [ ] 最终验证: `pytest && mypy && python -m src.main --data ...`
