# 模块索引

> 最后更新: 2026-07-12

---

## src/

### `config.py` ─ 全局配置

| 符号 | 类型 | 说明 |
|------|------|------|
| `ROOT` | `Path` | 项目根目录 (自动检测) |
| `DATA_DIR` | `Path` | `ROOT / "data"` |
| `OUTPUT_DIR` | `Path` | `ROOT / "output"` |
| `DATA_FILE` | `str` | 默认数据文件名 |
| `MIN_LIFESPAN_DAYS` | `int` | 单次购买客户生命周期底限 (30) |
| `LOG_FORMAT` | `str` | 日志格式模板 |
| `setup_logging(level)` | `() → None` | 配置 root logger |

---

### `schema.py` *(新增)* ─ 列名映射与校验

| 符号 | 类型 | 说明 |
|------|------|------|
| `ColumnMapping` | `dataclass` | 必填 + 可选列的原始名称映射 |
| `load_column_mapping(path)` | `(str) → ColumnMapping` | 从 TOML 加载映射配置 |
| `validate_columns(df, mapping)` | `(DataFrame, ColumnMapping) → None` | 检查必填列是否存在，缺列抛 KeyError + 友好信息 |
| `apply_mapping(df, mapping)` | `(DataFrame, ColumnMapping) → DataFrame` | 将原始列名 rename 为内部标准名 |

---

### `data_preprocessing.py` ─ 数据加载与清洗

| 函数 | 签名 | 说明 |
|------|------|------|
| `load_and_clean` | `(data_path: str, *, mapping: ColumnMapping \| None = None) → DataFrame` | 加载 Excel → 去空 CustomerID → 去取消订单 → 去非正 Quantity/UnitPrice → 创建 Revenue → 统一 InvoiceDate 类型 → rename 到内部列名 |

**清洗步骤 (5 步)**:
1. `dropna(subset=["CustomerID"])` — 无客户 ID 的行无法归属
2. `~InvoiceNo.str.startswith("C")` — 取消订单 (可配置)
3. `Quantity > 0 & UnitPrice > 0` — 退货/异常价格
4. `Revenue = Quantity * UnitPrice` — 创建金额列
5. `pd.to_datetime(InvoiceDate)` — 确保时间类型

---

### `rfm_analysis.py` ─ RFM 客户分层

| 函数 | 签名 | 说明 |
|------|------|------|
| `compute_rfm` | `(df, reference_date) → DataFrame` | CustomerID groupby → Recency(天)/Frequency(订单数)/Monetary(总消费) |
| `score_rfm` | `(rfm) → DataFrame` | 五分位评分 (1-5)，Recency 反向标签 [5,4,3,2,1] |
| `segment_rfm` | `(rfm) → DataFrame` | 10 类标准 RFM 分段，`np.select` 向量化 |
| `summarize_segments` | `(rfm) → DataFrame` | 按 Segment 汇总: 客户数/平均指标/营收贡献比 |
| `plot_rfm` | `(rfm, output_dir) → None` | 饼图(段占比) + 柱状图(段营收) |
| `run_rfm` | `(df, output_dir) → (rfm_df, summary_df)` | 编排上述 5 步，保存 CSV + PNG |

**10 段映射规则 (np.select, first-match)**:

| 条件 | 段名 |
|------|------|
| RFM_Score ≥ 13 | Champions |
| RFM_Score ≥ 11 | Loyal Customers |
| RFM_Score ≥ 9 & R_Score ≥ 4 | Potential Loyalists |
| RFM_Score ≥ 9 & F_Score ≥ 4 | At Risk |
| RFM_Score ≥ 9 | Needs Attention |
| RFM_Score ≥ 7 & R_Score ≥ 4 | New Customers |
| RFM_Score ≥ 7 & F_Score ≥ 3 | About to Sleep |
| RFM_Score ≥ 7 | Hibernating |
| RFM_Score ≥ 5 & R_Score ≥ 3 | Promising |
| RFM_Score ≥ 5 | Lost |
| 其他 | Lost (default) |

---

### `funnel_attribution.py` ─ 漏斗归因分析

| 函数 | 签名 | 说明 |
|------|------|------|
| `build_funnel` | `(df[, rfm]) → DataFrame` | 5 层转化漏斗: Total → Repeat(2+) → Regular(5+) → High-Value(Top20%) → VIP(Top5%) |
| `analyze_dropoff` | `(funnel_df) → dict` | 逐层计算流失率、流失人数 |
| `plot_funnel` | `(funnel_df, output_dir) → None` | 漏斗图 + 流失率柱状图 |
| `run_funnel` | `(df, output_dir[, rfm]) → (funnel_df, insights)` | 编排上述 3 步 |

**设计优化**: `rfm` 参数可选。传入时直接复用 RFM 表的 Frequency/Monetary 列，避免重复 groupby。

---

### `clv_estimation.py` ─ CLV 估算

| 函数 | 签名 | 说明 |
|------|------|------|
| `estimate_clv` | `(df, rfm, *, min_lifespan_days, freq_cap, projection_months) → DataFrame` | 历史 CLV + 预测 CLV(12月) |
| `summarize_clv_by_segment` | `(clv) → DataFrame` | 按 Segment 汇总 CLV 指标 |
| `plot_clv` | `(clv, output_dir) → None` | 箱线图(CLV 分布) + 散点图(Recency vs CLV) |
| `run_clv` | `(df, rfm, output_dir) → (clv_df, summary_df)` | 编排上述 3 步 |

**CLV 公式**:
```
Historical_CLV = Monetary (实际历史消费)
Predictive_CLV_12m = AOV × Purchase_Freq(月均, capped at freq_cap) × projection_months
```

**已知局限** (docstring 中有完整说明):
- 假设购买频率恒定 (无流失/无季节性)
- 月购买频率硬截断
- 无折现率/生命周期阶段
- 生产环境应使用 BG/NBD 或 Pareto/NBD

---

### `plotting.py` ─ 共享图表

| 符号 | 类型 | 说明 |
|------|------|------|
| `SEGMENT_COLORS` | `dict[str, str]` | 10 段 → hex 颜色映射 |
| `PALETTE_10` | `list[str]` | 10 色调色板 (非段特定场景) |
| `save_chart(fig, output_dir, filename, dpi)` | `(Figure, str\|Path, str, int) → Path` | 统一保存: `tight_layout` → `savefig` → `close` |

**设计**: matplotlib Agg 后端在此文件设置一次，所有分析模块通过 import 共享 plt 对象。

---

### `main.py` ─ CLI 入口

| 函数 | 签名 | 说明 |
|------|------|------|
| `main()` | `() → None` | argparse → 加载配置 → 加载数据 → RFM → Funnel → CLV (数据只加载一次) |

**CLI 参数 (Phase 2 新增)**:
```
--data PATH       数据文件路径 (必填)
--output PATH     输出目录 (默认 output/)
--mapping PATH    列名映射配置 (默认 column_mapping.toml)
--params PATH     业务参数配置 (默认 business_params.toml)
--no-plot         跳过图表生成
--only {rfm,funnel,clv}  仅运行指定模块
```

---

## tests/

| 文件 | 测试范围 | 用例数 |
|------|---------|--------|
| `conftest.py` | 自动注入 src/ 到 sys.path | — |
| `test_data_preprocessing.py` | 清洗逻辑: 去空/去退/去异常/Revenue 列/datetime | 5 |
| `test_rfm_analysis.py` | compute/score(qcut)/segment(np.select 正确性) | 8 |
| `test_funnel_attribution.py` | 漏斗计数/阶段完整性/转化率/流失分析 | 7 |
| `test_clv_estimation.py` | Historical_CLV=Monetary/AOV 计算/lifespan 底限/预测>0/段汇总 | 8 |

**总计: 29 用例** (修复前: 0)
