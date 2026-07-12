# 架构设计文档

> 最后更新: 2026-07-12

---

## 设计目标

一个**可配置、可复用、面试可讲**的电商用户分析工具。核心原则:

1. **数据与代码解耦** ─ 换数据只改 TOML 配置文件，不改源码
2. **单次加载、多次消费** ─ 23MB Excel 只读一次，通过 DataFrame 参数传递
3. **向量化优先** ─ 有 pandas 向量化方案用向量化，没有才用循环
4. **类型安全** ─ mypy strict 模式零错误

---

## 数据流

```
┌─────────────────────┐
│  column_mapping.toml │ ← 用户定义: 我的 Excel 列叫什么名
│  business_params.toml│ ← 用户定义: 漏斗阈值、CLV 参数
└──────┬──────────────┘
       │
       ▼
┌──────────────┐    ┌─────────────────────────┐
│  schema.py   │───→│ 列名验证 + 类型转换      │
│  (新增)      │    │ 缺列 → 友好报错并退出     │
└──────────────┘    └───────────┬─────────────┘
                                │
       ┌────────────────────────┘
       ▼
┌──────────────────┐
│ data_preprocessing│  加载 Excel → 清洗 (去空/去退款/去异常) → 标准化列名
│   .py            │  输出: clean_df (统一内部列名)
└──────┬───────────┘
       │  clean_df (只传一次)
       ├──────────────────────────────┬──────────────────────────────┐
       ▼                              ▼                              ▼
┌──────────────┐            ┌──────────────────┐           ┌──────────────────┐
│ rfm_analysis │            │ funnel_attribution│           │ clv_estimation   │
│              │            │                  │           │                  │
│ compute_rfm  │            │ build_funnel     │           │ estimate_clv     │
│  ↓           │            │  ↓               │           │  ↓               │
│ score_rfm    │            │ analyze_dropoff  │           │ summarize_clv    │
│  ↓           │            │  ↓               │           │  ↓               │
│ segment_rfm  │            │ plot_funnel      │           │ plot_clv         │
│  ↓           │            │                  │           │                  │
│ summarize    │            │                  │           │                  │
│  ↓           │            │                  │           │                  │
│ plot_rfm     │            │                  │           │                  │
└──────┬───────┘            └────────┬─────────┘           └────────┬─────────┘
       │                             │                              │
       │  rfm_df                     │  复用 rfm_df 的        ←────┘ 传入 rfm_df
       │  (传给 funnel)              │  Frequency/Monetary
       └──────────→──────────────────┘
```

### 关键设计决策

**为什么 funnel_attribution 和 clv_estimation 都接收 rfm_df？**

因为 `rfm_analysis.compute_rfm()` 已经对 CustomerID 做了 `groupby`，算出了每个客户的 Frequency(=订单数) 和 Monetary(=总消费)。funnel 和 CLV 都需要这两个值。如果各算各的 → 三次 groupby，CPU 浪费 3 倍。

**为什么 estimate_clv 不用 `Total_Revenue` / `Total_Orders` 重命名，而是直接用 Monetar/Frequency？**

一次 `df.merge(rfm, ...)` 直接把 9 个 RFM 列（Recency/Frequency/Monetary/Scores/Segment）全部带过来。多一次 merge + rename 是 CPU 浪费。`clv["Monetary"] / clv["Frequency"]` 直接算 AOV，语义清晰且无中间变量。

**为什么 segment_rfm 用 np.select 而不是 df.apply？**

| 方案 | 4,338 行数据 | 500,000 行数据 |
|------|-----|------|
| `df.apply(axis=1)` | ~50ms | ~6s |
| `np.select` | ~5ms | ~600ms |

---

## 模块职责边界

### src/ ─ 核心包

| 文件 | 职责 | 输入 | 输出 |
|------|------|------|------|
| `config.py` | 集中管理路径、常量、日志配置 | — | Path 对象、配置函数 |
| `schema.py` *(新增)* | 列名映射 + 输入校验 | column_mapping.toml | ColumnMapping dataclass |
| `data_preprocessing.py` | 加载 + 清洗原始数据 | Excel 文件路径 + ColumnMapping | 标准化 clean_df |
| `rfm_analysis.py` | RFM 分层全流程 | clean_df | rfm_df + segment_summary |
| `funnel_attribution.py` | 漏斗转化分析 | clean_df [+ rfm_df] | funnel_df + dropoff_insights |
| `clv_estimation.py` | CLV 估算 | clean_df + rfm_df | clv_df + clv_summary |
| `plotting.py` | 共享图表工具 | — | Agg 后端初始化、颜色调色板、save_chart |
| `main.py` | CLI 入口 + 管线编排 | sys.argv | 3 份 CSV + 3 张 PNG |

### 模块间依赖 (禁止循环引用)

```
plotting.py  ← 零依赖 (只被其他模块导入)
config.py    ← 零依赖
schema.py    ← 零依赖
data_preprocessing.py → config.py, schema.py
rfm_analysis.py       → plotting.py
funnel_attribution.py → plotting.py (可选 → rfm_analysis.py 的 rfm_df)
clv_estimation.py     → plotting.py, rfm_analysis.py (接 rfm_df)
main.py               → 以上全部 (编排者)
```

### 内部列名约定 (标准化后)

所有 `load_and_clean` 之后的 DataFrame 统一使用以下列名:

| 内部名 | 类型 | 来源 |
|--------|------|------|
| `CustomerID` | Int64 | 映射自用户配置 |
| `InvoiceNo` | str | 映射自用户配置 |
| `InvoiceDate` | datetime64 | 映射自用户配置 |
| `Quantity` | int | 映射自用户配置 |
| `UnitPrice` | float | 映射自用户配置 |
| `Revenue` | float | **计算列**: Quantity × UnitPrice |

如果用户原始数据不叫这些名字，由 `schema.py` 在加载后立即 rename。

---

## 扩展指南

### 如何添加新的分析方法 (如 Cohort Analysis)

1. 创建 `src/cohort_analysis.py`，实现 `run_cohort(df, output_dir)` 签名的入口函数
2. 在 `main.py` 的 `main()` 中增加一个步骤调用
3. 如果模块需要新的配置参数，添加到 `column_mapping.toml` 或 `business_params.toml`
4. 创建 `tests/test_cohort_analysis.py`

### 如何支持新的文件格式 (如 CSV / Parquet)

在 `data_preprocessing.py` 中增加格式检测:

```python
def load_and_clean(data_path: str, column_mapping=None):
    if data_path.endswith(".csv"):
        df = pd.read_csv(data_path, ...)
    elif data_path.endswith(".parquet"):
        df = pd.read_parquet(data_path)
    else:
        df = pd.read_excel(data_path, ...)
```

### 如何替换 CLV 模型为 BG/NBD

1. 安装 `lifetimes` 库
2. 替换 `estimate_clv` 函数体
3. 函数签名保持不变 (接收 df + rfm → 返回 clv_df)
4. 其他模块无需任何改动
