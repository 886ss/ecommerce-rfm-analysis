# 沟通纪要

> 目的: 防止 AI 上下文窗口溢出导致意图漂移。每次重大决策记录于此。
> 格式: 时间戳 + 决策 + 理由。

---

## 2026-07-12 会话启动

**用户需求**: 给了一份外部 AI 审查报告 (`code-review-handoff-ecommerce-rfm-analysis.md`)，要求:
1. 先独立审查项目代码
2. 与外部报告逐条比对
3. 挑选最优方案实施优化

**[已交付] 审查结果**: 外部报告 17/17 属实 (0 误判)，额外发现 3 个遗漏 (Lifespan_Days=1、Recency 未 rank、零异常处理)

---

## 2026-07-12 第一轮优化

**决策**: 按 P0→P1→P2→P3 优先级分批修复，共 20 项

**关键决策**:
1. 数据加载架构: 从 3 次 → 1 次 (main 中加载，传入各函数)
2. segment 算法: `df.apply(axis=1)` → `np.select` (性能 10×)
3. 消除重复: 创建 `config.py` / `plotting.py` 共享模块
4. 不创建 `setup.py`，用 `pyproject.toml` (PEP 621 标准)

**[已交付]**: commit `743df94`，22 文件变更，29 测试用例

---

## 2026-07-12 /simplify 审查

**4 个 agent 并行**: Reuse / Simplification / Efficiency / Altitude

**采纳的关键建议**:
- ✅ 创建 `plotting.py` 消除 3 处 matplotlib 样板
- ✅ 创建 `config.py` 消除 5 处路径硬编码
- ✅ `estimate_clv` 双 merge → 单 merge
- ✅ 漏斗复用 RFM 的 Frequency/Monetary 避免重复 groupby

**否决的建议 (有记录的理由)**:
- ❌ `score_rfm` dict 循环 → 否决: R_Score 反向标签是核心业务逻辑，显式 > 隐式
- ❌ `main.py` try/except ImportError → 否决: 唯一入口 `python -m`，相对导入永不失败

**[已交付]**: commit `1884cf3`

---

## 2026-07-12 README 完善

**用户要求**: 删除面试话术/简历亮点

**[已交付]**: commit `02ffe69`

---

## 2026-07-12 添加结果图表

**用户要求**: GitHub 仓库界面展示结果图表

**实现**: `docs/images/` 目录 (独立于 gitignored 的 `output/`)，README 中插入 3 张图表

**[已交付]**: commit `59a6bde`

---

## 2026-07-12 创建优化技能

**用户要求**: 将本次优化流程固化为可复用的 Claude Code 技能

**技能名**: `项目优化` (`project-optimizer`)
**触发**: 用户提供外部审查报告路径
**适用范围**: Python / JS / TS / Go / Rust / Java
**输出**: 修复代码 + 测试 + README + 图表 (推送由用户决定)

**技能结构**:
```
~/.claude/skills/project-optimizer/
├── SKILL.md
└── workspace/iteration-1/
    ├── code-review-report.md
    └── test-project/ (测试验证项目)
```

**测试验证**: 用 1 文件 + 5 条报告的项目成功走通全流程 (7 测试用例全绿)

**[已交付]**: SKILL.md 已写入 `~/.claude/skills/project-optimizer/`

---

## 2026-07-12 校招标准改造计划 (当前)

**用户最新需求**: "项目深度达到全国校招/春招/秋招标准"

**诊断结论**:
- ✅ 分析逻辑: 通用
- ✅ 代码架构: 模块化
- ✅ 测试覆盖: 29 用例
- ❌ 数据接入: 列名全程硬编码 (换数据需改 5 个文件)
- ❌ 入口方式: 文件名写死，无 CLI
- ❌ 业务参数: 漏斗阈值/CLV 参数硬编码
- ❌ CI/CD: 无
- ❌ 类型检查: mypy 未跑
- ❌ 架构文档: 无

**改造目标**: 8 项改造 → 产品级项目 → 面试可讲 30min+

### 确认的改造方案

| # | 改造项 | 面试信号 |
|---|--------|---------|
| 1 | argparse CLI (`--data` / `--output`) | "我知道代码要给别人用" |
| 2 | `column_mapping.toml` 列名映射 | "我理解数据与代码应该解耦" |
| 3 | `business_params.toml` 参数外置 | "我知道硬编码假设是项目毒药" |
| 4 | mypy strict 模式 + 修复 | "我写类型注解不是走过场" |
| 5 | `src/schema.py` 数据校验 | "我想过数据出错时会发生什么" |
| 6 | GitHub Actions CI | "我见过真正的开发流程" |
| 7 | `ARCHITECTURE.md` + `MODULES.md` | "我能讲清楚我的设计" |
| 8 | README 升级 (badge + 使用指南) | "我能把复杂事情说简单" |

### 文档先行

**用户要求**: "做好详细的计划书，一个模块一个模块来，给项目的优化写架构、结构、模块功能文档以及沟通纪要"

**已创建 4 份文档**:
- `docs/PLAN.md` ─ 分阶段执行计划 (Phase 1-6 + 验收标准)
- `docs/ARCHITECTURE.md` ─ 架构设计 (数据流图 + 设计决策 + 扩展指南)
- `docs/MODULES.md` ─ 模块索引 (每个函数签名 + 职责)
- `docs/MEETING_NOTES.md` ─ 本文档 (防意图漂移)

---

## 待确认

当前 4 份文档已落盘。用户审阅后按 Phase 顺序执行代码改造。

**不推送**: 代码改造完成后由用户决定是否推送。
