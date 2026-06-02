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
| 唯一订单 | 22,190 |
| 时间范围 | 2010-12-01 ~ 2011-12-09 |
| 总营收 | £8,911,408 |
| 数据地址 | https://archive.ics.uci.edu/dataset/352/online+retail |

这是一个英国在线零售商从 2010 年 12 月到 2011 年 12 月的真实交易记录，包含订单号、商品、数量、单价、客户 ID、国家等字段，是电商分析领域最经典的公开数据集之一。

---

## 项目结构

```
ecommerce-rfm-analysis/
├── data/
│   └── Online Retail.xlsx      # UCI 原始数据
├── src/
│   ├── main.py                  # 主入口（一键运行全流程）
│   ├── data_preprocessing.py    # 数据加载与清洗
│   ├── rfm_analysis.py          # RFM 客户分层
│   ├── funnel_attribution.py    # 漏斗归因分析
│   └── clv_estimation.py        # CLV 生命周期价值估算
├── output/
│   ├── rfm_table.csv            # RFM 分层明细
│   ├── rfm_segments.png         # RFM 可视化
│   ├── funnel_table.csv         # 漏斗数据
│   ├── funnel_attribution.png   # 漏斗可视化
│   ├── clv_table.csv            # CLV 明细
│   └── clv_analysis.png         # CLV 可视化
├── requirements.txt
└── README.md
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

**10 类分段映射**：

| RFM 总分 | 分段 |
|:---:|------|
| ≥13 | 🟢 Champions（王者客户） |
| 11-12 | 🔵 Loyal Customers（忠诚客户） |
| 9-10 | 🟣 Potential Loyalists / At Risk |
| 7-8 | 🟠 New Customers / About to Sleep |
| 5-6 | 🟡 Promising / Hibernating |
| <5 | 🔴 Lost（流失客户） |

**核心发现**：

| 分段 | 客户占比 | 营收贡献 |
|------|:---:|:---:|
| Champions | 21.5% | **70.2%** |
| Loyal Customers | 17.6% | 14.8% |
| At Risk | 13.6% | 7.6% |
| Lost | 12.1% | 0.8% |

→ **21.5% 的客户贡献了 70% 的营收** — 经典的 Pareto 分布。

---

### 2. 漏斗归因分析 (`funnel_attribution.py`)

**方法**：按购买频次和消费金额构建 5 层转化漏斗

```
Total Customers (100%)
     ↓ 34.4%
Repeat Buyers (2+ 次购买)
     ↓ 40.6%
Regular Buyers (5+ 次购买)
     ↓ 20.0%
High-Value Buyers (Top 20% 消费)
     ↓ 25.0%
VIP Buyers (Top 5% 消费)
```

**最大流失点**：Total → Repeat Buyers，**65.6% 的客户只买了一次就不再回来**。

→ 这是电商经典问题：**首次购买后的留存**是增长的第一瓶颈。

---

### 3. CLV 生命周期价值估算 (`clv_estimation.py`)

**双重 CLV 指标**：

| 指标 | 计算方式 | 用途 |
|------|---------|------|
| **Historical CLV** | 历史总消费 = 实际收入 | 衡量已实现价值 |
| **Predictive CLV (12m)** | AOV × 购买频率 × 12 | 预估未来一年价值 |

**CLV 公式**：
```
Predictive_CLV_12m = AOV × Purchase_Frequency(月均) × 12
```

**整体指标**：

| 指标 | 数值 |
|------|------|
| 人均 Historical CLV | £2,054 |
| 中位数 Historical CLV | £674 |
| 人均 AOV | £20.42 |
| 人均生命周期 | 132 天 |
| Champions CLV | £2,545（中位数 £1,033） |
| Lost CLV | £323（中位数 £254） |

---

## 快速开始

```bash
# 1. 安装依赖
pip install pandas matplotlib openpyxl

# 2. 运行全流程
python src/main.py

# 输出文件在 output/ 目录
```

**注意**：数据文件 `data/Online Retail.xlsx` 需从 UCI 下载（约 45MB），放入 `data/` 目录。

---

## 面试话术

> "我基于 UCI Online Retail 真实数据集，完成了一个完整的电商用户分析项目。核心技术栈：Pandas 数据清洗（541,909 → 397,884 行）、RFM 五分位分层（10 类客户分段）、漏斗归因分析（找出最大转化流失点）、CLV 预测模型（历史 CLV + 12 月预测 CLV）。
>
> 核心发现：21.5% 的 Champions 客户贡献了 70.2% 的营收；最大的流失发生在首次购买后（65.6% 用户不回购）；人均 CLV £2,054 但中位数仅 £674，收入分布极度右偏。这些发现直接指向两个业务动作：**提升首单留存率**和**培养高价值客户忠诚度**。"

---

## 简历亮点

> 基于 UCI Online Retail 数据集（54 万行真实交易），完成全链路电商用户分析：Pandas 数据清洗（处理缺失值、退货订单、异常价格）、RFM 客户分层（五分位+10 类分段）、漏斗归因分析（5 级转化漏斗）、CLV 估算（历史+预测双模型）；发现 21.5% 头部客户贡献 70% 营收，首购流失率达 65.6%，输出可视化报告与分段营销建议。

---

## 技术栈

```
Python 3.x
├── Pandas      — 数据处理与分析
├── NumPy       — 数值计算
├── Matplotlib  — 可视化图表
└── openpyxl    — Excel 文件读取
```
