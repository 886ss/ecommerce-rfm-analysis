# 📊 E-Commerce RFM Analysis

> 基于 **UCI Online Retail** 真实交易数据的电商用户行为分析项目  
> RFM 分层 + 漏斗归因 + CLV 估算 — 完整用户价值分析链路

---

## 数据集

**UCI Machine Learning Repository — Online Retail Dataset**

| 指标 | 数值 |
|------|------|
| 原始行数 | 541,909 |
| 清洗后行数 | 397,884 |
| 唯一客户 | 4,338 |
| 唯一订单 | 18,532 |
| 时间范围 | 2010-12-01 ~ 2011-12-09 |
| 总营收 | £8,911,408 |
| 数据地址 | https://archive.ics.uci.edu/dataset/352/online+retail |

> 请将 `Online Retail.xlsx` 放入 `data/` 目录后运行。

---

## 项目结构

```text
ecommerce-rfm-analysis/
├── pyproject.toml
├── .gitignore
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── config.py                  // 路径/常量/日志集中管理
│   ├── plotting.py                // matplotlib Agg + 颜色调色板 + save_chart
│   ├── main.py                    // 主入口（一键运行全流程）
│   ├── data_preprocessing.py      // 数据加载与清洗
│   ├── rfm_analysis.py            // RFM 客户分层
│   ├── funnel_attribution.py      // 漏斗归因分析
│   └── clv_estimation.py          // CLV 生命周期价值估算
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_data_preprocessing.py
│   ├── test_rfm_analysis.py
│   ├── test_funnel_attribution.py
│   └── test_clv_estimation.py
├── data/                          // (gitignored) 原始数据
└── output/                        // (gitignored) 生成图表和CSV
```

---

## 三大分析模块

### 1. RFM 客户分层 (`rfm_analysis.py`)

**方法**：五分位评分法（1-5 分）+ 10 类标准 RFM 分段

```
R (Recency)   — 最近一次购买距今多少天？  → 越低越好 → 反向打分
F (Frequency) — 买了多少次？               → 越高越好
M (Monetary)  — 总共花了多少钱？           → 越高越好
```

**性能优化**：向量化 `np.select` 替代逐行 `apply`，~10× 加速。

**核心发现**：

| 分段 | 客户占比 | 营收贡献 |
|------|:---:|:---:|
| Champions | 21.5% | **70.2%** |
| Loyal Customers | 15.4% | 11.8% |
| Needs Attention | 4.7% | 4.1% |
| Lost | 24.5% | 3.5% |

→ **21.5% 的客户贡献了 70.2% 的营收** — 经典的 Pareto 分布。

---

### 2. 漏斗归因分析 (`funnel_attribution.py`)

**方法**：按购买频次和消费金额构建 5 层转化漏斗，复用 RFM 数据避免重复 groupby。

```
Total Customers (100%)
     ↓ 34.4% drop-off
Repeat Buyers (2+ 次购买)
     ↓ 60.8% drop-off  ← 最大流失点
Regular Buyers (5+ 次购买)
     ↓ 22.1% drop-off
High-Value Buyers (Top 20% 消费)
     ↓ 75.0% drop-off
VIP Buyers (Top 5% 消费)
```

**最大流失点**：Total → Repeat Buyers，**65.6% 的客户只买了一次就不再回来**。

→ 首次购买后的留存是增长的第一瓶颈。

---

### 3. CLV 生命周期价值估算 (`clv_estimation.py`)

**双重 CLV 指标**：

| 指标 | 计算方式 | 用途 |
|------|---------|------|
| **Historical CLV** | 历史总消费 = 实际收入 | 衡量已实现价值 |
| **Predictive CLV (12m)** | AOV × 购买频率 × 12 | 预估未来一年价值 |

> ⚠️ Predictive CLV 使用朴素线性外推模型（假设购买频率恒定），仅供演示。

**整体指标**：

| 指标 | 数值 |
|------|------|
| 人均 Historical CLV | £2,054 |
| 中位数 Historical CLV | £674 |
| 人均 AOV | £419 |
| 人均生命周期 | 142 天 |
| Champions CLV | £6,697（中位数 £3,009） |

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行全流程
python -m src.main

# 3. 运行测试（29 个用例）
pytest tests/ -v
```

---

## 技术栈

```
Python 3.12
├── pandas~=2.0      — 数据处理与分析
├── numpy~=1.24      — 数值计算
├── matplotlib~=3.7  — 可视化图表
└── openpyxl~=3.1    — Excel 文件读取
```

- 模块化架构：`preprocessing → RFM → Funnel → CLV`，各模块可独立运行
- 数据只加载一次，通过函数参数传递，避免重复 I/O
- 统一 `logging` 模块，支持日志级别和输出重定向
- 完整单元测试覆盖（29 个用例，无需真实数据集）

---

## 面试话术

> "我基于 UCI Online Retail 真实数据集，完成了一个完整的电商用户分析项目。核心技术栈：Pandas 数据清洗（541,909 → 397,884 行）、RFM 五分位分层（10 类客户分段）、漏斗归因分析（找出最大转化流失点）、CLV 预测模型（历史 CLV + 12 月预测 CLV）。
>
> 核心发现：21.5% 的 Champions 客户贡献了 70.2% 的营收；最大的流失发生在首次购买后（65.6% 用户不回购）；人均 CLV £2,054 但中位数仅 £674，收入分布极度右偏。这些发现直接指向两个业务动作：**提升首单留存率**和**培养高价值客户忠诚度**。"

---

## 简历亮点

> 基于 UCI Online Retail 数据集（54 万行真实交易），完成全链路电商用户分析：Pandas 数据清洗（处理缺失值、退货订单、异常价格）、RFM 客户分层（五分位+10 类分段）、漏斗归因分析（5 级转化漏斗）、CLV 估算（历史+预测双模型）；发现 21.5% 头部客户贡献 70.2% 营收，首购流失率达 65.6%，输出可视化报告与分段营销建议。
