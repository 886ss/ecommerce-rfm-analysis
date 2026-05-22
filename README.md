# E-commerce RFM Analysis
基于 UCI Online Retail 数据集的电商用户行为分析项目。实现数据清洗、RFM 分层、漏斗归因、CLV 估算。

## 数据来源
UCI Machine Learning Repository - Online Retail Dataset

## 运行
`ash
pip install pandas matplotlib
python src/main.py
`

## 核心指标
- 清洗后：397,884 行 / 4,338 用户
- 总营收：£8,911,408
- Champions（21.5% 用户）贡献 70.2% 营收
- 复购→常客流失率 60.8%
- 人均 CLV：£2,054（中位数 £674）
