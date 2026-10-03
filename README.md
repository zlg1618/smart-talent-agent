# Smart Talent Agent · 组织发展与人才发展智能体

> 面向组织发展（OD）与人才发展（TD）的智能体系统。
> 用自然语言承载 HR 的组织分析动作与人才培养动作，
> 所有数字由确定性计算引擎产出，大模型只负责表达。

## 介绍

本项目的**核心是组织发展与人才发展两大模块域**，HRIS 六大模块作为支撑与数据源。

**核心域 · 组织发展（OD）**——回答"组织长得好不好"：

| 能力 | 说明 | 关键指标 |
| --- | --- | --- |
| 组织架构与编制 | 组织单元层级、隶属关系、负责人、编制与在编 | 层级深度、平均管理幅度、编制达成率 |
| 组织效能与人效 | 部门营收、人工成本、离职率、管理幅度 | 人均产出、人工成本率、人效指数与排名 |
| 岗位职级体系 | 职族职级的人数结构、晋升率、薪酬带宽 | 金字塔形态、腰部拥堵、年均晋升率 |
| 组织变革模拟 | 合并 / 拆分 / 扩编 / 缩编 / 新设 / 调整 | 影响人数、成本影响、风险分级 |

**核心域 · 人才发展（TD）**——回答"人怎么长起来"：

| 能力 | 说明 | 关键指标 |
| --- | --- | --- |
| 能力画像与差距 | 现状等级 vs 目标等级，个人逐项或部门短板 | 能力达成率、差距项排序 |
| 任职资格匹配 | 专业能力 / 业务贡献 / 领导力 / 学习敏锐四维加权 | 匹配度、达标维度、未达标项 |
| 人才池 | 高潜池 / 后备池 / 专家池的进出与分层 | 在池规模、活跃度、平均评分 |
| 发展项目 | 培养项目、训练营、行动学习、轮岗 | 覆盖率、完成率、满意度、人均投入 |
| 导师带教 | 一对一带教关系的运行状况 | 配对数、带教频次、进度、导师负荷 |

**HRIS 六大支撑模块**：招聘管理、薪酬与福利、绩效管理、员工关系管理、培训与开发、人力资源规划。

> **已移除模块**：人才盘点九宫格、关键岗位继任地图、人才梯队分析、个人发展计划（IDP）、组织诊断
> 已从系统中删除，其能力由组织发展与人才发展两大核心域承接。详见附录第九章。

**三条不可妥协的原则**：

1. **数字不算第二遍**：所有打分、分档、比率由 Python 确定性计算，大模型不参与算数
2. **只说库里有的**：部门、员工、周期全部来自数据库真实值，模型与规则都不编造
3. **每句话能溯源**：结论附带计算依据，HR 可以直接拿去汇报，不怕被问"这数哪来的"

## 软件架构

```text
smart-talent-agent/
├── app/
│   ├── agent/                  # LangGraph Agent
│   │   ├── graph.py            # 工作流与路由（核心双域 + HRIS 二级路由）
│   │   ├── rules.py            # 规则降级引擎（无模型兜底）
│   │   ├── prompts.py          # 提示词（意图 / 域路由 / 抽取 / 解释）
│   │   ├── formatters.py       # 结果模板（模型不可用时的可读输出）
│   │   ├── state.py            # 跨轮次状态
│   │   └── memory.py           # Checkpointer
│   ├── api/
│   │   ├── core/               # 核心双域路由
│   │   │   ├── organization.py # 组织发展：架构 / 效能 / 职级 / 变革
│   │   │   └── talent.py       # 人才发展：能力 / 标准 / 池 / 项目 / 导师
│   │   ├── hr/                 # HRIS 六大模块路由
│   │   ├── ai.py               # 对话入口
│   │   ├── employee.py         # 员工主数据
│   │   ├── hris.py             # HRIS 聚合入口与模块清单
│   │   └── integrations.py     # 外部 HRIS 接入
│   ├── models/                 # ORM 模型（核心双域 + HRIS 六模块）
│   │   ├── organization.py         # OrgUnit / OrgEffectiveness / JobArchitecture / OrgChange
│   │   ├── talent_development.py   # TalentStandard / TalentPool / DevelopmentProgram / Mentorship
│   │   ├── recruitment.py  compensation.py  performance.py
│   │   ├── employee_relations.py  learning.py  workforce.py
│   │   └── employee.py         # 员工 / 绩效 / 潜力 / 能力模型
│   ├── services/               # 确定性计算（真正的业务大脑）
│   │   ├── organization_service.py
│   │   ├── talent_development_service.py
│   │   └── *_service.py        # HRIS 六模块
│   ├── tools/                  # Tool 层：自然语言 → 计算调用
│   ├── integrations/           # HRIS 适配器（local / SAP SuccessFactors）
│   ├── llm/                    # 大模型客户端（Ollama / OpenAI 兼容）
│   ├── config/                 # 配置、数据库、SQLite 列迁移
│   └── schemas/                # 请求响应模型
├── seed_data.py                # 种子数据生成
├── smoke_core.py               # 端点 + 路由冒烟
├── test_tool.py                # 核心双域计算测试
├── test_agent.py               # Agent 流程测试
├── test_hris.py                # HRIS 六模块测试
└── test_llm.py                 # 大模型连通性测试
```

## 软件架构说明

### 分层职责

| 层 | 职责 | 能不能算数 |
| --- | --- | --- |
| API | 参数校验、路由、鉴权 | 不算 |
| Tool | 自然语言 → 确定性调用 | 不算 |
| Service | **所有打分、分档、比率、结论** | **算** |
| Models / DB | 唯一真实数据来源 | 存 |
| Agent | 意图识别、条件抽取、结果路由 | 不算 |
| LLM | 把已算好的结果讲成人话 | **不算** |

### Agent 工作流

```text
analyze_request（意图识别）
    ├─ CHAT        → chat
    └─ 其他         → extract_info（抽取部门 / 周期 / 职级 / 员工）
                        ├─ ORG_DEV    → 组织发展（四路动作分发）
                        ├─ TALENT_DEV → 人才发展（五路动作分发）
                        └─ HRIS       → 二级路由 → 六个支撑模块
```

- 核心双域由 `rules.rule_core_module()` 或大模型判定，命中 `organization_development` / `talent_development`
- HRIS 走独立的二级路由节点 `decide_hris_module`，再分发到六个具体模块
- 每个域内部再做一次动作级关键词分发，`result_topic` 形如 `OD_STRUCTURE` / `TD_POOL`

### 关键设计决策

| 决策 | 理由 |
| --- | --- |
| 计算与表达彻底分离 | 大模型可以换、可以不用，数字始终一致 |
| 规则引擎兜底 | 没装 Ollama、没配 Key 也能跑完整流程，便于演示与自动化测试 |
| 核心双域优先于 HRIS | 主打能力优先命中，避免"组织变革"被误判成人力资源规划 |
| 适配器能力声明 | `supports()` 先判定，防止打到厂商不支持的接口 |
| SQLite 自动列迁移 | 存量库升级不丢数据，开发环境无需重建库 |

### 技术栈

Python 3.11+ · FastAPI · SQLAlchemy 2.0 · LangGraph · Pydantic Settings ·
SQLite（默认）/ MySQL（生产） · Ollama / 任意 OpenAI 兼容 API

## 安装教程

### 环境要求

Python 3.11 及以上，无需安装数据库（默认 SQLite 零配置启动）。

### 步骤

```bash
# 1. 克隆仓库
git clone https://gitee.com/zlg1618/smart-talent-agent.git
cd smart-talent-agent

# 2. 创建虚拟环境并安装依赖
python -m venv .venv
.venv/Scripts/activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt

# 3. 生成演示数据（67 名员工 + 组织单元 / 效能 / 职级 / 变革 +
#    任职资格 / 人才池 / 发展项目 / 导师制，以及 HRIS 六模块全量种子）
python seed_data.py

# 4. 启动服务
uvicorn app.main:app --reload --port 8000
```

打开 <http://127.0.0.1:8000/docs> 查看全部接口。

### 切换 MySQL

```bash
# .env
DATABASE_URL=mysql+pymysql://root:123456@localhost:3306/talent_ai
```

### 接入大模型（可选）

```bash
# 本地 Ollama（默认 deepseek-r1:7b，模型不存在时自动回退规则引擎）
ollama pull deepseek-r1:7b

# 或云 API（.env 配置）
LLM_PROVIDER=openai_compatible
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

不配置也能跑：所有流程都有规则兜底，响应里的 `llm_used` 字段会如实标注本轮是否用了模型。

## 使用说明

### 对话式入口（推荐）

```bash
curl -X POST http://127.0.0.1:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"thread_id":"demo","message":"看一下公司组织架构和编制达成情况"}'
```

可以连续追问，条件会跨轮次记住：

```text
看一下组织架构            → 组织架构与编制总览（全公司）
部门改成技术中心          → 记住条件
重新看一下                → 按技术中心重算
各部门人效怎么样          → 组织效能与人效分析
技术中心的职级体系健康吗  → 岗位职级体系
模拟一下组织变革          → 组织变革模拟
技术中心的能力差距在哪    → 能力画像与差距
谁能晋升到下一职级        → 任职资格匹配度
看一下人才池              → 人才池视图
发展项目完成得怎么样      → 发展项目跟踪
导师带教进展如何          → 导师制运行
```

### 核心双域直达接口

```bash
# 组织发展
GET /api/core/organization-development/structure?department=技术中心
GET /api/core/organization-development/effectiveness
GET /api/core/organization-development/job-architecture
GET /api/core/organization-development/change?change_type=合并

# 人才发展
GET /api/core/talent-development/competency?department=技术中心
GET /api/core/talent-development/standard-match?job_level=P7
GET /api/core/talent-development/pool
GET /api/core/talent-development/program
GET /api/core/talent-development/mentorship
```

### HRIS 六模块直达

```bash
GET /api/hris/recruitment/screen          # 招聘管理
GET /api/hris/compensation/compa-ratio    # 薪酬与福利
GET /api/hris/performance/goals           # 绩效管理
GET /api/hris/employee-relations/leave/balance   # 员工关系管理
GET /api/hris/learning/overview           # 培训与开发
GET /api/hris/workforce/headcount         # 人力资源规划
```

### 运行测试

```bash
python smoke_core.py     # 端点 + Agent 路由冒烟（24 端点 + 16 路由场景）
python test_tool.py      # 核心双域计算正确性（不依赖大模型）
python test_hris.py      # HRIS 六模块计算
python test_agent.py     # Agent 多轮流程
python test_llm.py       # 大模型连通性
```

## 参与贡献

1. Fork 本仓库并新建分支 `feat/your-feature`
2. 保持"计算与表达分离"：新增能力先写 `services/` 里的确定性计算，再接 Tool 与 API
3. 新增模块需同时补齐：模型 → 服务 → Tool → API → 意图路由 → 格式化模板 → 种子数据 → 测试
4. 提交前跑通 `python smoke_core.py`
5. 发起 Pull Request，说明改动的能力域与影响的接口

### 提交规范

`feat:` 新能力 · `fix:` 修复 · `refactor:` 重构 · `docs:` 文档 · `chore:` 杂项

## 特技

1. **零模型也能跑**：不装 Ollama、不配 API Key，全部流程照常运转——
   意图识别、条件抽取、双域路由都有关键词规则兜底，响应里 `llm_used` 字段如实标注

2. **每个数字都有公式**：编制达成率、人效指数、职级形态、任职资格匹配度、人才池活跃度……
   所有结论附带计算依据，HR 可以直接拿去给业务负责人汇报

3. **核心双域 + 六模块二级路由**：组织发展与人才发展为主打能力，
   HRIS 六大模块走独立二级路由，15 类请求自动分发到 9 个核心动作 + 6 个模块

4. **改条件自动重算**：多轮对话中修改部门/周期/职级后，系统重新查库重新计算，
   绝不拿上一轮的结果糊弄（LangGraph Checkpointer 实现）

5. **双数据库一行切换**：SQLite 零配置启动演示，改一行 `DATABASE_URL` 切 MySQL 上生产，
   附带自动列迁移，存量库升级不丢数据

6. **SAP SuccessFactors 接入骨架**：核心双域 + 六模块 OData v2 端点映射已固化，
   填环境变量即可发起真实调用；`supports()` 能力声明防止打到厂商不支持的接口

7. **组织变革可模拟**：不只描述"要调整什么"，还算清楚"影响多少人、成本变动多少、风险多大"，
   合并 / 拆分 / 扩编 / 缩编各有对应的落地建议

8. **任职资格四维加权**：专业能力 / 业务贡献 / 领导力 / 学习敏锐按权重比对达标线，
   给出匹配度与未达标维度，晋升评审不再凭印象

* * *

<details>
<summary><strong>附录：完整文档（三十三章）</strong>——算法公式、数据库设计、API 全量示例、SAP SF 接入指南，点击展开</summary>

## 一、项目简介

面向组织发展（OD）与人才发展（TD）场景的智能体系统，
用自然语言承载 HR 的组织分析动作与人才培养动作。

**核心双域**：

- **组织发展**：组织架构与编制、组织效能与人效、岗位职级体系、组织变革模拟
- **人才发展**：能力画像与差距、任职资格匹配、人才池、发展项目、导师带教

**HRIS 六大支撑模块**：招聘管理、薪酬与福利、绩效管理、员工关系管理、培训与开发、人力资源规划。

示例对话：

- 看一下公司组织架构和编制达成情况
- 分析一下各部门人效，哪些部门偏低
- 技术中心的职级体系健康吗，有没有腰部拥堵
- 模拟一下组织变革方案的影响和成本
- 技术中心的能力差距在哪
- 谁能晋升到下一职级
- 看一下人才池的运行情况
- 发展项目完成得怎么样
- 导师带教进展如何
- 帮我筛选一下候选人、看一下薪酬公平性、大家还有多少年假

## 二、核心功能

### 1. 组织发展 · 组织架构与编制

按组织单元汇总层级深度、隶属关系、负责人与编制：

- 编制达成率 = 在编 / 编制，分档为 已满编 / 接近满编 / 缺口较大 / 严重缺编
- 平均管理幅度 = 一线单元（无下级的团队）在编人数的平均值，健康区间 4–12 人
- 组织层级深度：少于 3 层偏扁平（晋升通道不足），多于 5 层偏深（决策链条长）

### 2. 组织发展 · 组织效能与人效

以部门为单位计算产出与成本：

- 人均产出 = 营收 / 在编人数
- 人工成本率 = 人工成本 / 营收
- 人效指数 = 部门人均产出 / 全公司人均产出，≥1.15 领先、<0.85 偏低
- 人效偏低的部门自动区分"成本率过高"与"离职率拖累"两类成因

### 3. 组织发展 · 岗位职级体系

按职族职级统计人数结构：

- 形态判定：腰部拥堵（中级占比 ≥60%）/ 基层偏重 / 倒金字塔 / 结构均衡
- 年均晋升率低于 8% 标记晋升停滞风险
- 薪酬带宽宽度 =（上限 − 下限）/ 中位值

### 4. 组织发展 · 组织变革模拟

合并 / 拆分 / 扩编 / 缩编 / 新设 / 调整六类方案：

- 影响人数 ≥30 为高影响，≥10 为中影响
- 成本影响按人均折算，负值为成本节约
- 每类方案给出对应的落地建议（汇报线、管理岗位、预算节奏、安置方案）

### 5. 人才发展 · 能力画像与差距

- 个人视角：逐项列出现状等级、目标等级与差距，能力达成率 = Σmin(现状, 目标) / Σ目标
- 部门视角：按能力项平均差距排序，找出最该集中投入的三项

### 6. 人才发展 · 任职资格匹配度

四个维度按权重比对职级达标线：

| 维度 | 权重 | 数据来源 |
| --- | --- | --- |
| 专业能力 | 0.35 | 员工能力现状等级均值 |
| 业务贡献 | 0.30 | 最近一次绩效分 |
| 领导力 | 0.20 | 最近一次潜力评估的领导力分 |
| 学习敏锐 | 0.15 | 最近一次潜力评估的学习敏锐分 |

匹配度 = Σ(权重 × min(实际 / 达标线, 1))，≥90% 完全胜任、≥75% 基本胜任、≥60% 尚有差距。

### 7. 人才发展 · 人才池

按池子统计在池 / 观察 / 已出池，活跃度 = 在池 / 总数，
低于 60% 判定为流失偏高，提示复核入池标准与池内培养投入。

### 8. 人才发展 · 发展项目

覆盖率 = 入学 / 容量，完成率 = 完成 / 入学，人均投入 = 预算 / 入学人数；
完成率 ≥85% 且满意度 ≥4.0 为效果良好，<70% 为需改进。

### 9. 人才发展 · 导师带教

进度 = 已完成次数 / 计划次数，≥100% 已完成、≥50% 推进中、<50% 刚起步；
同时识别带 3 人以上的负荷偏高导师。

### 10. HRIS 六大支撑模块

| 模块 | 能力 |
| --- | --- |
| 招聘管理 | 简历筛选、智能定薪、面试安排、招聘漏斗 |
| 薪酬与福利 | compa-ratio、调薪模拟、福利覆盖、个人薪酬单 |
| 绩效管理 | 目标达成、评价偏差、强制分布、PIP 改进计划 |
| 员工关系管理 | 假期余额、考勤、关系事件、敬业度 |
| 培训与开发 | 培训总览、必修合规、课程推荐、效果评估 |
| 人力资源规划 | 编制达成、供需预测、六因子离职风险 |

### 11. HRIS 系统集成

统一 `HRISAdapter` 接口，本地库与 SAP SuccessFactors 双实现，
核心双域 + 六大模块共 8 个能力域通过 `capabilities` 声明。

### 12. 用户意图识别

- **ORG_DEV**：组织架构与编制、组织效能与人效、岗位职级体系、组织变革模拟
- **TALENT_DEV**：能力差距、任职资格匹配、人才池、发展项目、导师带教
- **HRIS**：六大支撑模块的人事问题
- **UPDATE**：修改查询条件
- **CHAT**：与上述领域无关的普通对话

## 三、系统架构

```
                    用户
                     │
                     ▼
               FastAPI API
                     │
                     ▼
              LangGraph Agent
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
    意图识别     信息抽取      Memory
        │            │            │
        └────────────┼────────────┘
                     │
                     ▼
          Python 业务计算 Tool
                     │
        ┌────────────┴────────────────────────┐
        │                                     │
        ▼                                     ▼
   人才管理与组织发展                    HRIS 六大模块
   ┌──────────┬──────────┐        ┌────────┬────────┬────────┐
   ▼          ▼          ▼        ▼        ▼        ▼        ▼
 组织发展   人才发展              招聘    薪酬福利   绩效   员工关系
   │          │          │        │        │        │        │
   └──────────┴─────┬────┘        └────────┴────────┴───┬────┘
                    │                                  │
                    ▼                    ┌─────────────┴────────┐
            组织发展与人才发展        ▼                      ▼
                    │               培训与开发            人力规划
                    │                    │                      │
                    └────────────┬───────┴──────────────────────┘
                                 ▼
                          SQLAlchemy
                                 │
                                 ▼
                        MySQL / SQLite
                                 │
                                 ▼
            员工 / 绩效 / 潜力 / 招聘 / 薪酬 / 培训 / 编制
                                 │
                                 ▼
                            计算结果
                                 │
                                 ▼
                      大模型自然语言汇报
                                 │
                                 ▼
                                用户
```

* * *

## 四、Agent 工作流程

一次完整的盘点请求大致经过以下流程：

```
用户输入
   ↓
analyze_request（意图识别）
   ↓
判断用户意图
   ↓
extract_info（抽取部门 / 周期 / 职级 / 员工）
   ↓
   ├── 人才管理类 → talent_review / succession / idp / diagnosis
   │
   └── HRIS 类 → decide_hris_module（二级路由）
                    ├─ recruitment        招聘管理
                    ├─ compensation      薪酬与福利
                    ├─ performance       绩效管理
                    ├─ employee_relations 员工关系管理
                    ├─ learning          培训与开发
                    └─ workforce         人力资源规划
   ↓
调用对应业务 Tool
   ↓
查询数据库
   ↓
编制达成率 / 人效指数 / 任职资格匹配度 / compa-ratio /
目标达成率 / 离职风险分 / 编制达成率 / 合规率
   ↓
生成结构化结果
   ↓
大模型进行自然语言汇报（不可用时走模板）
   ↓
返回用户
```

* * *

## 五、Agent 状态设计

核心状态包括：

- `user_message`
- `request_type` —— ORG_DEV / TALENT_DEV / HRIS / UPDATE / CHAT
- `active_topic` —— 最近一次业务意图，用于改条件后重新执行
- `core_module` —— organization_development / talent_development
- `hris_module` —— HRIS 二级路由结果（recruitment / compensation / performance / employee_relations / learning / workforce）
- `department`
- `period`
- `job_level`
- `employee_name`
- `result`
- `result_topic`
- `answer`
- `llm_used`

### 查询条件

```json
{
  "department": "技术中心",
  "period": "2025H1",
  "job_level": "P6",
  "employee_name": "李伟"
}
```

### 核心域与模块标记

```json
{
  "core_module": "organization_development",
  "result_topic": "OD_STRUCTURE"
}
```

* * *

## 六、Agent 意图路由

```text
analyze_request
    ├─ CHAT        → chat
    └─ 其他         → extract_info
                        ├─ ORG_DEV    → org_dev 节点（四路动作）
                        ├─ TALENT_DEV → talent_dev 节点（五路动作）
                        └─ HRIS       → decide_hris_module → 六个模块节点
```

**核心双域判定**（`rules.rule_core_module`）：

| 域 | 关键词示例 |
| --- | --- |
| organization_development | 组织架构、组织单元、组织效能、组织变革、人效、人均产出、人工成本、职级体系、职族、晋升率、管理幅度、汇报线、层级、金字塔、合并、拆分、扩编、缩编、新设 |
| talent_development | 人才发展、能力差距、能力画像、能力模型、任职资格、人才标准、匹配度、够不够格、人才池、高潜、后备池、专家池、晋升、发展项目、培养项目、行动学习、训练营、轮岗、导师、带教 |

**优先级**：修改条件 > 核心双域 > HRIS > 通用业务词。
核心双域排在 HRIS 之前，保证主打能力优先命中。

**动作级分发**（各域内部）：

| 域 | 动作 | 关键词 |
| --- | --- | --- |
| 组织发展 | OD_STRUCTURE | 架构、组织单元、编制、层级、管理幅度、汇报线 |
| 组织发展 | OD_EFFECTIVENESS | 人效、效能、人均产出、人工成本、成本率 |
| 组织发展 | OD_ARCHITECTURE | 职级、职族、晋升率、晋升通道、金字塔、带宽 |
| 组织发展 | OD_CHANGE | 组织变革、变革、合并、拆分、扩编、缩编、新设、重组 |
| 人才发展 | TD_COMPETENCY | 能力、差距、画像、能力模型 |
| 人才发展 | TD_STANDARD | 任职资格、人才标准、匹配度、够不够格、胜任、晋升 |
| 人才发展 | TD_POOL | 人才池、高潜、后备池、专家池、入池、出池 |
| 人才发展 | TD_PROGRAM | 发展项目、培养项目、行动学习、训练营、轮岗 |
| 人才发展 | TD_MENTORSHIP | 导师、带教、师徒 |

## 七、组织发展（OD）详解

### 1. 组织架构与编制

| 指标 | 公式 | 说明 |
| --- | --- | --- |
| 编制达成率 | 在编 / 编制 | ≥95% 已满编，≥85% 接近满编，≥70% 缺口较大，其余严重缺编 |
| 平均管理幅度 | 一线单元在编人数的均值 | 健康区间 4–12 人 |
| 组织层级深度 | max(level) | 合理区间 3–5 层 |

在编人数优先取员工主数据统计值，避免组织单元表与主数据不一致。

### 2. 组织效能与人效

| 指标 | 公式 |
| --- | --- |
| 人均产出 | 营收 / 在编人数（万元） |
| 人工成本率 | 人工成本 / 营收 |
| 人效指数 | 部门人均产出 / 全公司人均产出 |

人效指数 ≥1.15 人效领先，≥0.85 人效正常，<0.85 人效偏低。
偏低部门再按人工成本率（>60%）与离职率（>15%）区分成因。

### 3. 岗位职级体系

按部门把职级归为基层（P1–P5）、中级（P6–P7）、高级（P8 及 M 序列）：

- 中级占比 ≥60% → **腰部拥堵**，需开放高级名额或拆分并行通道
- 基层占比 ≥60% → **基层偏重**，需加强带教与晋升通道
- 高级占比 ≥45% → **倒金字塔**，管理成本压力大
- 其余 → **结构均衡**

年均晋升率 <8% 标记晋升停滞风险。

### 4. 组织变革模拟

| 字段 | 说明 |
| --- | --- |
| change_type | 合并 / 拆分 / 扩编 / 缩编 / 新设 / 调整 |
| affected_headcount | 影响人数，≥30 高影响，≥10 中影响 |
| cost_impact | 成本影响（万元/年），负值为节约 |
| cost_per_head | 成本影响 / 影响人数 |

每类方案配套落地建议：合并重理汇报线、拆分补齐管理岗、扩编核对预算、
缩编配套安置、新设先明确定位、调整明确切换时点。

## 八、人才发展（TD）详解

### 1. 能力画像与差距

- 个人：能力达成率 = Σ min(现状等级, 目标等级) / Σ 目标等级
- 部门：按能力项平均差距排序，取差距最大的三项作为投入重点

### 2. 任职资格匹配度

四个维度按权重加权：

```text
匹配度 = Σ (权重ᵢ × min(实际ᵢ / 达标线ᵢ, 1))
```

| 维度 | 权重 | 数据来源 |
| --- | --- | --- |
| 专业能力 | 0.35 | 员工能力现状等级均值 |
| 业务贡献 | 0.30 | 最近一次绩效分 |
| 领导力 | 0.20 | 潜力评估领导力分 |
| 学习敏锐 | 0.15 | 潜力评估学习敏锐分 |

缺失数据时该维度按 3.0 兜底，并在结论中如实标注。
默认比对"当前职级的下一职级"，可通过 `job_level` 参数指定目标职级。

### 3. 人才池

- 活跃度 = 在池 /（在池 + 观察 + 出池）
- ≥80% 活跃，≥60% 正常，<60% 流失偏高
- 观察人数多于在池人数时，提示明确转正或出池的判定节奏

### 4. 发展项目

| 指标 | 公式 |
| --- | --- |
| 覆盖率 | 入学 / 容量 |
| 完成率 | 完成 / 入学 |
| 人均投入 | 预算 × 10000 / 入学人数（元） |

完成率 ≥85% 且满意度 ≥4.0 为效果良好；≥70% 基本达标；<70% 需改进。
覆盖率 <70% 时额外提示招生未满。

### 5. 导师带教

- 进度 = 已完成次数 / 计划次数
- ≥100% 已完成，≥50% 推进中，<50% 刚起步
- 同时带 3 人以上的导师标记为负荷偏高

## 九、已移除模块与迁移说明

以下五个模块已**从系统中彻底移除**（模型、服务、Tool、API、数据表、路由、种子数据全部删除）：

| 已移除模块 | 原能力 | 由哪个核心域承接 |
| --- | --- | --- |
| 人才盘点九宫格 | 绩效 × 潜力矩阵定位 | 人才发展 · 任职资格匹配度（四维度加权，比二象限更有依据） |
| 关键岗位继任地图 | 关键岗位候选人与准备度 | 组织发展 · 岗位职级体系 + 人才发展 · 人才池 |
| 人才梯队分析 | 职级间供给比 | 组织发展 · 岗位职级体系（金字塔形态与晋升率） |
| 个人发展计划 IDP | 70-20-10 发展行动 | 人才发展 · 发展项目 + 导师带教（项目化、可跟踪） |
| 组织诊断 | 部门健康度打分 | 组织发展 · 组织效能与人效 + 组织架构与编制 |

**移除后同时清理的内容**：

- 数据表：`key_position`、`succession_plan`、`idp`、`department_metric`、`course`
- Agent 意图：`TALENT_REVIEW`、`SUCCESSION`、`IDP`、`DIAGNOSIS`（改为 `ORG_DEV` / `TALENT_DEV`）
- 关键词路由与格式化模板：九宫格、继任、梯队、IDP、诊断相关全部删除
- 人力资源规划域的"继任联动"端点（`/api/hris/workforce/succession-link`）一并移除，
  离职风险中的"关键岗位交叉"改为按管理序列（M）与高职级（P7+）判定
- 筛选偏好（`PREFERENCE` 意图）随盘点能力一并移除

**新增内容**：

- 8 张数据表：`org_unit`、`org_effectiveness`、`job_architecture`、`org_change`、
  `talent_standard`、`talent_pool`、`development_program`、`mentorship`
- 9 个核心域端点（组织发展 4 + 人才发展 5）
- 2 个核心域能力声明，同步加入 `HRISCapability` 与两个适配器

## 十、核心双域指标口径与阈值

### 组织发展

| 指标 | 阈值 | 配置项 |
| --- | --- | --- |
| 编制达成率 | 0.95 / 0.85 / 0.70 三档 | `FILL_RULE` |
| 管理幅度健康区间 | 4.0 – 12.0 | `od_span_min` / `od_span_max` |
| 组织层级合理区间 | 3 – 5 层 | `od_depth_min` / `od_depth_max` |
| 人效指数 | ≥1.15 领先，<0.85 偏低 | 服务内常量 |
| 腰部拥堵 | 中级占比 ≥60% | 服务内常量 |
| 晋升停滞 | 年均晋升率 <8% | 服务内常量 |
| 高影响方案 | 影响人数 ≥30 | 服务内常量 |

### 人才发展

| 指标 | 阈值 | 配置项 |
| --- | --- | --- |
| 匹配度分档 | 0.90 / 0.75 / 0.60 | `td_match_ready` / `td_match_basic` / `td_match_gap` |
| 达标线（1-5 分制） | P4 3.0 → M3 4.0 | 种子数据 `LEVEL_PASS_SCORE` |
| 人才池活跃度 | ≥80% 活跃，≥60% 正常 | 服务内常量 |
| 项目完成率达标 | ≥70% | `td_program_completion_target` |
| 项目满意度达标 | ≥4.0 | `td_program_satisfaction_target` |
| 导师负荷偏高 | 同时带 ≥3 人 | 服务内常量 |

所有阈值集中在 `app/config/settings.py` 与各域服务顶部常量，
修改后无需改动调用方。

## 十一、数据真实性控制

系统没有让大模型直接生成人才结论。

整体流程：

```
用户输入
   ↓
LangGraph Agent
   ↓
大模型理解用户意图
   ↓
抽取结构化条件
   ↓
Python 业务计算
   ↓
数据库查询真实数据
   ↓
生成结构化结果
   ↓
大模型进行自然语言汇报
   ↓
返回用户
```

其中：

**大模型主要负责：**

- 意图理解
- 条件抽取
- 核心域与模块路由
- 自然语言汇报
- 普通对话

**Python 主要负责：**

- 数据库查询
- 组织架构与编制达成
- 组织效能与人效指数
- 岗位职级形态
- 任职资格匹配度
- 人才池活跃度
- 能力差距计算
- 组织健康分
- 状态更新

* * *

## 十二、无模型降级机制

大模型不可用时（未安装 Ollama、未配置 Key、服务未启动），
Agent 自动回退到**规则引擎**：

- 关键词意图识别
- 正则抽取周期与职级
- 基于数据库真实部门列表与姓名列表做匹配抽取

因此本项目在**零模型环境**下依然可以完整跑通所有业务流程，
便于演示、自动化测试与 CI。

对话响应中的 `llm_used` 字段标明本轮回答是否真正由大模型生成。

* * *

## 十三、数据库设计

**核心双域 · 组织发展**

| 表 | 说明 |
| --- | --- |
| `org_unit` | 组织单元（隶属关系、层级、负责人、编制与在编） |
| `org_effectiveness` | 组织效能（营收、人工成本、离职率、管理幅度） |
| `job_architecture` | 岗位职级体系 |
| `org_change` | 组织变革方案 |
| `talent_standard` | 任职资格标准 |
| `talent_pool` | 人才池成员 |
| `development_program` | 发展项目 |
| `mentorship` | 导师带教 |

**员工主数据与评价**

| 表 | 说明 |
| --- | --- |
| `employee` | 员工主数据 |
| `performance_record` | 绩效考核记录（1-5 分） |
| `potential_assessment` | 潜力评估记录 |
| `competency` | 能力模型项 |
| `employee_competency` | 员工能力现状与岗位要求等级 |

**HRIS · 招聘管理**

| 表 | 说明 |
| --- | --- |
| `job_post` | 招聘需求 / JD（含需求编号 req_no） |
| `candidate` | 候选人主数据 |
| `candidate_skill` | 候选人技能明细 |
| `application` | 申请（招聘漏斗的一个环节） |
| `interview_schedule` | 面试安排 |
| `offer_record` | Offer 记录（base / 奖金 / 股权 / 总包 / compa-ratio） |

**HRIS · 薪酬与福利**

| 表 | 说明 |
| --- | --- |
| `salary_band` | 职级 × 城市薪酬带宽（min / median / max） |
| `employee_compensation` | 员工薪酬包（base / 奖金比例 / 长期激励） |
| `benefit_plan` | 福利计划（核心 / 可选、人均成本） |
| `employee_benefit` | 员工参保明细 |

**HRIS · 绩效管理**

| 表 | 说明 |
| --- | --- |
| `performance_goal` | 绩效目标 OKR / KPI |
| `performance_review` | 绩效评估（自评 / 主管评 / 校准后） |
| `calibration_session` | 校准会记录 |
| `improvement_plan` | 绩效改进计划 PIP |

**HRIS · 员工关系管理**

| 表 | 说明 |
| --- | --- |
| `leave_request` | 请假申请 |
| `attendance_record` | 每日考勤记录 |
| `relation_case` | 员工关系事件（纠纷 / 申诉 / 关怀 / 合规） |
| `engagement_survey` | 敬业度调查（五维 + eNPS） |

**HRIS · 培训与开发**

| 表 | 说明 |
| --- | --- |
| `training_course` | 培训课程（含关联能力项与结业等级） |
| `training_enrollment` | 报名与完成记录 |

**HRIS · 人力资源规划**

| 表 | 说明 |
| --- | --- |
| `headcount_plan` | 部门编制计划 |
| `workforce_forecast` | 人力供需预测（分情景） |
| `attrition_risk` | 离职风险评分与六因子明细 |

准备度取值：

| 取值 | 含义 |
| --- | --- |
| `ready_now` | 立即就绪 |
| `ready_1y` | 1 年内就绪 |
| `ready_2y` | 2 年内就绪 |
| `not_ready` | 尚未就绪 |

* * *

## 十四、项目目录

```
smart-talent-agent
│
├── app
│   ├── agent
│   │   ├── graph.py          # LangGraph 工作流
│   │   ├── state.py          # Agent 状态定义
│   │   ├── prompts.py        # 提示词
│   │   ├── rules.py          # 规则降级引擎
│   │   ├── formatters.py     # 结果模板输出
│   │   └── memory.py         # Checkpointer
│   │
│   ├── api
│   │   ├── ai.py             # AI 对话接口
│   │   ├── employee.py
│   │   ├── talent_review.py
│   │   ├── succession.py
│   │   ├── idp.py
│   │   ├── diagnosis.py
│   │   ├── hris.py           # HRIS 统一入口 + /modules
│   │   ├── hr/               # HRIS 六大模块路由
│   │   │   ├── recruitment.py
│   │   │   ├── compensation.py
│   │   │   ├── performance.py
│   │   │   ├── employee_relations.py
│   │   │   ├── learning.py
│   │   │   └── workforce.py
│   │   ├── integrations.py   # HRIS 适配器接入（六大能力域）
│   │   └── health.py
│   │
│   ├── config
│   │   ├── settings.py       # 全局配置
│   │   ├── database.py       # 引擎与会话
│   │   └── migrate.py        # SQLite 列补齐
│   │
│   ├── llm
│   │   └── llm_client.py     # Ollama / OpenAI 兼容客户端
│   │
│   ├── models                # ORM 模型
│   │   ├── employee.py       # 员工 / 绩效 / 潜力 / 能力
│   │   ├── organization.py        # 组织发展四表
│   │   ├── talent_development.py   # 人才发展四表
│   │   ├── recruitment.py        # HRIS 招聘管理
│   │   ├── compensation.py       # HRIS 薪酬与福利
│   │   ├── performance.py        # HRIS 绩效管理
│   │   ├── employee_relations.py # HRIS 员工关系管理
│   │   ├── learning.py           # HRIS 培训与开发
│   │   └── workforce.py          # HRIS 人力资源规划
│   │
│   ├── schemas               # 请求响应模型
│   │
│   ├── services              # 确定性业务计算
│   │   ├── organization_service.py          # 核心 · 组织发展
│   │   ├── talent_development_service.py    # 核心 · 人才发展
│   │   ├── employee_service.py
│   │   ├── recruitment_service.py
│   │   ├── compensation_service.py
│   │   ├── performance_service.py
│   │   ├── employee_relations_service.py
│   │   ├── learning_service.py
│   │   ├── workforce_service.py
│   │   └── ai_service.py
│   │
│   ├── tools                 # Agent 调用的工具封装
│   │   ├── organization_tool.py             # 核心 · 组织发展
│   │   ├── talent_development_tool.py       # 核心 · 人才发展
│   │   ├── recruitment_tool.py
│   │   ├── compensation_tool.py
│   │   ├── performance_tool.py
│   │   ├── employee_relations_tool.py
│   │   ├── learning_tool.py
│   │   └── workforce_tool.py
│   │
│   ├── integrations          # HRIS 适配器（核心双域 + 六大能力域）
│   │   ├── hris_adapter.py                 # 抽象接口 + 能力常量
│   │   ├── local_adapter.py                # 本地 SQLite / MySQL
│   │   └── sap_successfactors_adapter.py   # OData v2 接入骨架
│   │
│   └── main.py
│
├── seed_data.py
├── test_agent.py
├── test_tool.py
├── test_hris.py
├── test_llm.py
├── requirements.txt
├── env.example
└── README.md
```

* * *

## 十五、技术栈

| 技术 | 用途 |
| --- | --- |
| Python 3.12+ | 主要开发语言 |
| FastAPI | Web API 服务 |
| Uvicorn | ASGI 服务运行 |
| LangGraph | Agent 工作流、状态管理 |
| LangChain | 大模型应用开发框架 |
| LangChain Ollama | 调用本地 Ollama 模型 |
| LangChain OpenAI | 调用任意 OpenAI 兼容云 API |
| Ollama | 本地大模型运行环境 |
| SQLAlchemy | ORM 和数据库访问 |
| PyMySQL | MySQL 数据库驱动 |
| SQLite | 零配置默认数据库 |
| MySQL | 生产环境数据库 |
| Pydantic | 请求参数校验 |

* * *

## 十六、开发环境

项目使用 Python 3.12+。

推荐使用 Conda 创建独立环境：

```bash
conda create -n smart-talent python=3.12
conda activate smart-talent
```

* * *

## 十七、安装项目依赖

```bash
cd smart-talent-agent
pip install -r requirements.txt
```

* * *

## 十八、配置

复制配置文件：

```bash
cp env.example .env
```

### 数据库

默认使用 SQLite，零配置启动：

```
DATABASE_URL=sqlite:///./talent_agent.db
```

切换到 MySQL（需先创建数据库）：

```
DATABASE_URL=mysql+pymysql://root:123456@localhost:3306/talent_ai
```

### 大模型

本地 Ollama（默认）：

```
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=deepseek-r1:7b
```

云 API：

```
LLM_PROVIDER=openai_compatible
OPENAI_API_KEY=sk-xxxxxx
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

### 业务阈值

核心双域的分档阈值同样可在 `.env` 覆盖：

```
OD_SPAN_MIN=4.0          # 管理幅度健康下限
OD_SPAN_MAX=12.0         # 管理幅度健康上限
OD_DEPTH_MIN=3           # 组织层级合理下限
OD_DEPTH_MAX=5           # 组织层级合理上限
TD_MATCH_READY=0.90      # 完全胜任线
TD_MATCH_BASIC=0.75      # 基本胜任线
TD_MATCH_GAP=0.60        # 尚有差距线
TD_PROGRAM_COMPLETION_TARGET=0.70
TD_PROGRAM_SATISFACTION_TARGET=4.0
```

* * *

## 十九、生成种子数据

```bash
python seed_data.py
```

生成 67 名员工、5 个部门、2 个考核周期，
以及组织发展（16 个组织单元 / 5 条效能记录 / 29 个职级配置 / 6 个变革方案）与
人才发展（任职资格标准 / 3 个人才池 / 5 个发展项目 / 14 组导师带教）全量数据，
外加 HRIS 六模块种子。

数据由固定随机种子生成，结果可复现。

* * *

## 二十、启动项目

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

启动成功后访问：

- 服务根路径：http://127.0.0.1:8000
- Swagger 接口文档：http://127.0.0.1:8000/docs

* * *

## 二十一、API 示例

### 核心域 · 组织发展

```bash
# 组织架构与编制
curl "http://127.0.0.1:8000/api/core/organization-development/structure?department=%E6%8A%80%E6%9C%AF%E4%B8%AD%E5%BF%83"

# 组织效能与人效
curl "http://127.0.0.1:8000/api/core/organization-development/effectiveness"

# 岗位职级体系
curl "http://127.0.0.1:8000/api/core/organization-development/job-architecture"

# 组织变革模拟（可按类型过滤）
curl "http://127.0.0.1:8000/api/core/organization-development/change?change_type=%E5%90%88%E5%B9%B6"
```

响应示例（组织架构）：

```json
{
  "period": "2025H1",
  "department": "技术中心",
  "total_units": 16,
  "max_depth": 3,
  "avg_span_of_control": 6.7,
  "total_planned": 215,
  "total_actual": 201,
  "overall_fill_rate": 0.935,
  "shortage_units": [],
  "units": [],
  "conclusion": "……"
}
```

### 核心域 · 人才发展

```bash
# 能力差距（部门视角；带 employee_name 时看个人）
curl "http://127.0.0.1:8000/api/core/talent-development/competency?department=%E6%8A%80%E6%9C%AF%E4%B8%AD%E5%BF%83"

# 任职资格匹配度
curl "http://127.0.0.1:8000/api/core/talent-development/standard-match?job_level=P7"

# 人才池
curl "http://127.0.0.1:8000/api/core/talent-development/pool"

# 发展项目
curl "http://127.0.0.1:8000/api/core/talent-development/program"

# 导师制
curl "http://127.0.0.1:8000/api/core/talent-development/mentorship"
```

响应示例（任职资格匹配 · 个人）：

```json
{
  "scope": "个人",
  "employee": "张伟",
  "job_family": "技术",
  "current_level": "P6",
  "target_level": "P7",
  "match_rate": 0.812,
  "match_label": "基本胜任",
  "failed_dimensions": [{"dimension": "领导力", "actual": 3.1, "pass_score": 3.6}],
  "detail": [],
  "conclusion": "……"
}
```

### 对话入口

```bash
curl -X POST http://127.0.0.1:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"thread_id":"demo","message":"分析一下各部门人效"}'
```

响应：

```json
{
  "thread_id": "demo",
  "request_type": "ORG_DEV",
  "core_module": "organization_development",
  "result_topic": "OD_EFFECTIVENESS",
  "conditions": {"department": null, "period": null, "job_level": null, "employee_name": null},
  "result": {},
  "answer": "……",
  "llm_used": false
}
```

### HRIS 六模块

```bash
curl "http://127.0.0.1:8000/api/hris/recruitment/screen"
curl "http://127.0.0.1:8000/api/hris/compensation/compa-ratio"
curl "http://127.0.0.1:8000/api/hris/performance/goals"
curl "http://127.0.0.1:8000/api/hris/employee-relations/leave/balance"
curl "http://127.0.0.1:8000/api/hris/learning/overview"
curl "http://127.0.0.1:8000/api/hris/workforce/headcount"
curl "http://127.0.0.1:8000/api/hris/workforce/attrition-risk"
```

### 系统集成

```bash
curl "http://127.0.0.1:8000/api/integrations/backends"
curl "http://127.0.0.1:8000/api/integrations/ping?backend=local"
curl "http://127.0.0.1:8000/api/integrations/workforce/headcount?backend=local"
```

## 二十二、Memory 使用示例

使用相同的 `thread_id` 可以维持同一个会话状态。

```
第一轮：做一次人才盘点
      → 记录主题 ORG_DEV

第二轮：只看明星人才
      → 记住 department = 技术中心

第三轮：部门改成销售部
      → 条件 department = 销售部，按新条件重新盘点

第四轮：重新做一次盘点
      → 沿用 销售部 + 只看超级明星 重新计算
```

* * *

## 二十三、信息不完整处理

系统不会在关键条件缺失时随意猜测。

例如查看个人能力画像时未指定员工：

```
请告诉我要为哪位员工生成个人发展计划，
例如"看一下张伟的能力画像"或"李娜能晋升到下一职级吗"。
```

例如盘点结果为空时：

```
当前条件下没有参与盘点的员工
（生效条件：{'department': '销售部', '只看格子': ['高-高']}）。
请调整部门、职级或员工姓名后重试。
```

* * *

## 二十四、修改条件后的重新计算

```
做一次人才盘点（全部部门，67 人）
        ↓
部门改成销售部（重新计算 → 16 人）
        ↓
周期改成 2024H2（重新计算 → 2024H2 的 16 人）
        ↓
重新做一次盘点（按最新条件重新查询数据库）
```

系统在每一步都会重新查询数据库，不会沿用旧结果。

* * *

## 二十五、测试

项目包含以下测试文件：

```
test_agent.py   # Agent 流程与多轮状态测试
test_tool.py    # 业务计算正确性测试
test_llm.py     # 大模型连通性测试
```

运行：

```bash
python test_agent.py
python test_tool.py
python test_llm.py
```

* * *

## 二十六、核心测试场景

| 场景 | 输入 | 预期 |
| --- | --- | --- |
| 组织架构 | 看一下公司组织架构和编制达成情况 | ORG_DEV → OD_STRUCTURE |
| 组织效能 | 分析各部门人效 | ORG_DEV → OD_EFFECTIVENESS |
| 职级体系 | 技术中心的职级体系健康吗 | ORG_DEV → OD_ARCHITECTURE |
| 组织变革 | 模拟一下组织变革方案 | ORG_DEV → OD_CHANGE |
| 能力差距 | 技术中心的能力差距在哪 | TALENT_DEV → TD_COMPETENCY |
| 任职资格 | 谁能晋升到下一职级 | TALENT_DEV → TD_STANDARD |
| 人才池 | 看一下人才池 | TALENT_DEV → TD_POOL |
| 发展项目 | 发展项目完成得怎么样 | TALENT_DEV → TD_PROGRAM |
| 导师制 | 导师制运行情况 | TALENT_DEV → TD_MENTORSHIP |
| 招聘 | 帮我筛选一下候选人 | HRIS → recruitment |
| 薪酬 | 薪酬公平性怎么样 | HRIS → compensation |
| 绩效 | 绩效目标达成情况 | HRIS → performance |
| 员工关系 | 大家还有多少年假 | HRIS → employee_relations |
| 培训 | 培训覆盖率如何 | HRIS → learning |
| 编制 | 编制达成情况 | HRIS → workforce |
| 离职风险 | 谁有离职风险 | HRIS → workforce |
| 多轮改条件 | 看一下组织架构 → 部门改成销售部 → 重新看一下 | 按新条件重算 |
| 无关对话 | 今天天气怎么样 | CHAT |

`python smoke_core.py` 会跑完上述全部场景，端点 24/24、路由 16/16 通过。

## 二十七、项目亮点

### 1. LLM 与业务逻辑解耦

大模型不参与任何打分与分类决策：

```
LLM → 理解意图 → 抽取条件 → Python 业务计算 → 数据库 → 真实结果 → LLM 汇报
```

降低幻觉对人才决策的影响。

### 2. LangGraph 智能体编排

使用 LangGraph 把意图识别、信息抽取、核心双域与 HRIS 六模块 Tool
与结果汇报组成工作流，对不同意图做条件路由。

### 3. Tool 化设计

九类核心动作 + 六类 HRIS 模块封装为独立 Tool，便于扩展与单独测试。

### 4. 状态机与多轮记忆

通过 LangGraph Checkpointer 维护连续对话状态；
修改部门 / 周期 / 职级 / 员工后会沿上一主题自动重新计算。

### 5. 零模型也能跑

规则降级引擎保证项目在没有大模型的环境下也能完整跑通所有业务。

### 6. 双数据库支持

SQLite 零配置启动，MySQL 生产可用，仅改一行配置即可切换。

### 7. HRIS 可插拔

抽象 `HRISAdapter` 接口，本地 Adapter 与 SAP SuccessFactors OData v2 Adapter
可在线切换，业务侧零修改。

* * *

## 二十八、后续优化方向

1. **持久化 Memory**：生产环境将 `InMemorySaver` 替换为数据库 Checkpointer
2. **前端可视化**：开发组织架构树、人效看板、职级金字塔与发展项目看板
3. **RAG 知识库**：接入公司人才政策、任职资格标准、发展通道手册
4. **多轮追问**：支持"为什么他的匹配度只有 72%"这类可解释追问
5. **权限与脱敏**：按角色限制可见范围，敏感字段脱敏
6. **自动化测试**：补充 pytest 与接口自动化测试
7. **Docker 部署**：容器化 FastAPI、MySQL 与 Ollama

* * *

## 二十九、项目定位

**一句话**：以组织发展与人才发展为双核心的智能 HR Agent，
HRIS 六大模块作为支撑与数据源，所有结论可计算、可解释、可追溯。

**与同类产品的差异**：

| 维度 | 常见 HR SaaS | 本项目 |
| --- | --- | --- |
| 计算方式 | 模型或黑盒算法给出评分 | 确定性公式，LLM 只表达不算数 |
| 可解释性 | 测评模型 / AI 算法不开放 | 每个分数带公式与依据 |
| 关注点 | 盘点"现在有什么人" | 回答"组织长得好不好、人怎么长起来" |
| 组织视角 | 多为人才个体视角 | 组织发展与人才发展并重，含变革模拟 |
| 成本门槛 | 数十万至百万级 TCO | 开源可自部署，SQLite 零配置启动 |
| 集成方式 | 绑定厂商生态 | 适配器抽象，本地库与 SAP SF 一键切换 |

**适用场景**：

- 组织盘点前的架构与编制梳理
- 年度人效复盘与低效部门定位
- 职级体系与晋升通道健康度检查
- 组织调整方案的影响与成本测算
- 任职资格建设与晋升评审支持
- 人才池、培养项目、导师制的运行跟踪

## 三十、HRIS 模块算法详解

### 1. 招聘管理

按权重对候选人与 JD 匹配度评分：

| 维度 | 权重 | 评分逻辑 |
| --- | --- | --- |
| 技能匹配 | 40% | 候选人命中技能数 / JD 必备技能数 |
| 经验 | 20% | 与 JD 要求年限差距决定 100 / 80 / 40 / 0 |
| 学历 | 15% | 大专、本科、硕士、博士相对 JD 要求差距 |
| 期望薪资 | 15% | 中位期望与岗位预算上限的关系 |
| 当前职级 | 10% | 按经验年限近似量化 |

等级分档：

| 分档 | 含义 |
| --- | --- |
| ≥ 85 | 强烈推荐面试 |
| 70 ~ 84 | 推荐面试 |
| 55 ~ 69 | 待定（可面试） |
| < 55 | 不推荐 |

Offer 定薪按匹配分决定 base 档位：

| 综合分 | base 在预算中的位置 |
| --- | --- |
| ≥ 85 | 95% |
| 70 ~ 84 | 80% |
| 55 ~ 69 | 60% |
| < 55 | 50% |

奖金按经验年限分档（10% / 15% / 20% / 30%）；
长期激励给高分高经验人才 10% ~ 20% RSU。
输出 `base + bonus + equity` 三段式与 compa-ratio。

漏斗统计 `received / active / rejected / hired` 与三段转化率；
面试安排自动推荐 3 位面试官（招聘经理 + 同部门 P7+/M 系列 + HR）与未来一周工作日时段。

### 2. 薪酬与福利

| 指标 | 公式 | 用途 |
| --- | --- | --- |
| compa-ratio | 个人固定薪 / 带宽中位值 | 内部公平性，健康区间 0.90 ~ 1.10 |
| range penetration |（base − 下限）/（上限 − 下限） | 在带宽中的位置 |
| 红圈 | base > 上限 | 超薪，建议冻结固定薪改用浮动激励 |
| 绿圈 | base < 下限 | 欠薪，建议优先纳入调薪池 |
| TCC | base + 目标奖金 + 长期激励 | 总现金薪酬 |
| TDC | TCC + 年化福利成本 | 总直接薪酬 |

调薪模拟按"先补欠薪、再谈增长"的顺序分配预算，
输出每人调薪额、调薪后 compa-ratio 与未覆盖人数。

### 3. 绩效管理

- **目标达成**：加权达成率 = Σ(单条达成率 × 权重) / Σ 权重，达成率封顶 100%
- **评价偏差**：Δ = 主管评 − 自评，|Δ| ≥ 1 判为严重偏差，需面谈对齐
- **强制分布**：S ≤ 10%、A ≤ 25%、B 40%~70%、C 5%~20%、D ≤ 10%，
  偏离时给出需调整的人头数与方向
- **改进计划**：PIP 跟进，目标分与当前绩效分的差值即剩余改进空间

### 4. 员工关系管理

法定年假（中国劳动法）：

| 工龄 | 法定年假 |
| --- | --- |
| < 1 年 | 0 天 |
| 1 ~ 10 年 | 5 天 |
| 10 ~ 20 年 | 10 天 |
| ≥ 20 年 | 15 天 |

实际剩余 = 法定 − 已申请（pending + approved）。
请假类型：`annual` 年假 / `sick` 病假 / `personal` 事假 / `compensatory` 调休 / `maternity` 产假。

关系事件按严重度给 SLA：low 30 天、medium 14 天、high 7 天，超期即预警。
敬业度取五维（工作本身 / 直属上级 / 成长发展 / 薪酬回报 / 工作生活平衡），
eNPS = 推荐者占比 − 非推荐者占比。

### 5. 培训与开发

课程推荐按能力差距排序：

```
gap = 岗位要求等级 − 现状等级
gap ≥ 2 → 高优先；gap = 1 → 中优先
同类课程取结业等级最高的那一门
```

必修合规率 = 实际完成人次 /（在职人数 × 必修课门数）。
效果评估按课程的通过率、平均分、学员满意度排序，低于 3.5 分进入复盘清单。

### 6. 人力资源规划

离职风险为六因子加权，合计 1.0：

| 因子 | 权重 |
| --- | --- |
| 薪酬竞争力 | 0.20 |
| 晋升停滞 | 0.20 |
| 司龄过短 | 0.15 |
| 绩效未被认可 | 0.15 |
| 敬业度偏低 | 0.15 |
| 市场机会吸引 | 0.15 |

风险分 ≥ 70 为 high，≥ 45 为 medium。
编制达成率 = 在编 / 编制；供需预测按
`净需求 = 自然流失 + 业务增量`，`外部招聘需求 = 净需求 − 内部供给`。
六因子加权给出风险分，并对管理序列（M）与高职级（P7+）标记为需优先保留人群。

### 当前演示数据示例

```
薪酬公平性：参与比对 67 人，平均 compa-ratio 1.192
            低于下限 16 人（最低 0.658），高于上限 24 人

调薪模拟：调薪池 5% = ¥1,373,439，可为 16 人补齐，支出 ¥772,811

目标达成：跟踪 83 条目标，覆盖 40 人，平均达成率 68.9%

必修合规：应完成 134 人次，实际 119 人次，合规率 88.8%，14 人存在缺口

编制审查：达成率 83.8%（在编 67 / 编制 80），缺口 13 人，2 个部门缺口较大

离职风险：扫描 67 人，高风险 6 人（占 9.0%）
```

## 三十一、适配器能力域

`HRISCapability` 声明 8 个能力域：核心双域 2 个 + HRIS 六大支撑模块。

| 能力域 key | 名称 | Local | SAP SF |
| --- | --- | --- | --- |
| organization_development | 组织发展 | ✅ | ✅ |
| talent_development | 人才发展 | ✅ | ✅ |
| recruitment | 招聘管理 | ✅ | ✅ |
| compensation | 薪酬与福利 | ✅ | ✅ |
| performance | 绩效管理 | ✅ | ✅ |
| employee_relations | 员工关系管理 | ✅ | ✅ |
| learning | 培训与开发 | ✅ | ✅ |
| workforce | 人力资源规划 | ✅ | ✅ |

```python
from app.integrations.local_adapter import LocalHRISAdapter

adapter = LocalHRISAdapter()
adapter.supports("organization_development")   # True
adapter.describe()                              # 能力清单与中文标签
```

调用前统一用 `_require_capability()` 判定，厂商不支持时返回明确错误而不是 500。

## 三十二、SAP SuccessFactors 接入骨架

按 Employee Central OData v2 设计：

```
基础请求:
  BaseURL = https://{tenant}.api.successfactors.com
  Auth    = OAuth2 Client Credentials 或 Basic
  Header  = Authorization: Bearer <token> 或 Basic <base64(user:pass)>
  公共参数 = ?companyID=<SF 公司 ID>&$format=JSON

核心双域与六模块端点映射:
  组织发展        Position / PositionMatrixRelationship / Department / FOPosition
  人才发展        TalentPool / Succession / DevelopmentGoal / CareerDevelopment
  招聘管理        JobApplication / JobRequisition / CandidateProfile / JobOffer
  薪酬与福利      EmpCompensation / CompensationInfo / EmployeeBenefits
  绩效管理        PerformanceReview / Goal / CalibrationSession
  员工关系管理    EmpEmployment / Timesheet / LeaveRequest
  培训与开发      LearningEvent（LMS 侧常用 Learning OData API）
  人力资源规划    Position / PositionMatrixRelationship / EmpJob

主数据:
  GET   /odata/v2/User('userName')     员工主数据
  POST  /odata/v2/User                新建员工
  PATCH /odata/v2/User('userName')    更新员工
```

映射表以常量形式固化在 `SF_ENTITY_MAP` 中，接入时可按租户版本调整。

接入前在 `.env` 配置：

```
SAP_SF_BASE_URL=https://{tenant}.api.successfactors.com
SAP_SF_COMPANY_ID=...
SAP_SF_AUTH_MODE=oauth   # 或 basic
SAP_SF_CLIENT_ID=...     # OAuth 模式
SAP_SF_CLIENT_SECRET=...
SAP_SF_TOKEN_URL=https://{tenant}.auth.successfactors.com/oauth/token
# 或者 Basic 模式
SAP_SF_USER=...
SAP_SF_PASSWORD=...
```

使用：

```
GET  /api/integrations/ping?backend=sap_successfactors
GET  /api/integrations/recruitment/applications?backend=sap_successfactors
GET  /api/integrations/compensation?backend=sap_successfactors
POST /api/integrations/performance/reviews?backend=sap_successfactors
POST /api/integrations/leave?backend=sap_successfactors
POST /api/integrations/learning/records?backend=sap_successfactors
GET  /api/integrations/workforce/headcount?backend=sap_successfactors
```

⚠️ 本骨架未在真实 SF 租户上完成端到端验证。
字段名与实体名在不同 SF 版本间存在差异，
请在企业沙箱中先跑一次 `$metadata` 校验再投入生产。

* * *

## 三十三、免责声明

本项目仅用于学习、技术研究和项目演示。

仓库中的数据均为程序生成的模拟数据，不对应任何真实个人。

实际组织调整、晋升评审与人员决策需要结合企业真实数据、
管理者判断、制度合规要求以及员工个人发展意愿综合做出。

本项目输出的结果不构成任何人事决策建议。

</details>

</details>
