# Smart Talent Agent · 组织发展与人才发展智能体

> 面向组织发展（OD）与人才发展（TD）的完整体系化智能体。
> OD 管"组织能力"，TD 管"人的能力"。
> 所有数字由确定性计算引擎产出，每个结论都附计算依据，大模型只负责表达。

## 介绍

### 一、组织发展 OD（Organization Development）

**对象**：组织、团队、架构、机制、文化　**关注**：组织能力

| 工作内容 | 本项目能力 | 关键输出 |
| --- | --- | --- |
| 组织诊断 | 组织健康度调研 + 组织扫描（7S / 6-BOX / 五维框架） | 健康分、维度差距、痛点与瓶颈排序 |
| 组织架构与管控设计 | 组织模式、权责划分、分权集权、层级优化、定岗定编 | 层级深度、管理幅度、编制达成、管控模式分布 |
| 组织变革管理 | 扩张 / 并购 / 转型的变革推进与阻力处理 | 影响人数、成本影响、阶段（宣贯→试点→推广→固化）、阻力等级 |
| 战略解码 | 公司战略拆解为组织目标与部门目标 | 三层目标树、加权达成率、滞后目标 |
| 企业文化与氛围 | 文化建设、组织氛围、员工敬业度调研 | 六维度得分、敬业度、文化举措建议 |
| 组织效能分析 | 人效与人力成本分析，输出组织层面改进方案 | 人均产出、人工成本率、人效指数与排名 |
| 岗位职级体系 | 职族职级的金字塔结构、晋升率与薪酬带宽 | 结构形态、腰部拥堵、晋升停滞 |

### 二、人才发展 TD（Talent Development）

**对象**：人、个体与人才梯队　**关注**：人的能力

| 工作内容 | 本项目能力 | 关键输出 |
| --- | --- | --- |
| 人才盘点 | 九宫格（绩效 × 潜力）+ 360 度评估 | 九宫格矩阵、高潜名单、待优化名单、自评认知偏差 |
| 胜任力模型 | 能力项、等级行为描述、岗位能力要求 | 模型覆盖度、岗位要求矩阵、员工符合度 |
| 任职资格 / 职级体系 | 四维度加权达标线比对 | 匹配度、达标维度、未达标项 |
| 继任者计划与梯队建设 | 关键岗位继任者与准备度 | 覆盖率、立即就绪率、梯队深度、风险岗位 |
| 高潜人才项目 / 管理干部培养 | 高潜项目、管理者训练营、行动学习 | 覆盖率、完成率、满意度、人均投入 |
| 学习发展体系 | 内训、轮岗、导师制、个人发展计划 IDP | IDP 完成率、70-20-10 分布、带教进度、导师负荷 |
| 人才任用建议 | 结合盘点结果输出人员调整与晋升建议 | 晋升 / 保留 / 激活换岗 / 调整淘汰 / 观察 五分群 |

**HRIS 六大支撑模块**：招聘管理、薪酬与福利、绩效管理、员工关系管理、培训与开发、人力资源规划。

### 三条不可妥协的原则

1. **数字不算第二遍**：所有打分、分档、比率由 Python 确定性计算，大模型不参与算数
2. **只说库里有的**：部门、员工、周期全部来自数据库真实值，模型与规则都不编造
3. **每句话能溯源**：结论附带 `basis` 计算依据，HR 可以直接拿去汇报

## 软件架构

```text
smart-talent-agent/
├── app/
│   ├── agent/                  # LangGraph Agent
│   │   ├── graph.py            # 工作流与路由（核心双域 16 路动作 + HRIS 二级路由）
│   │   ├── rules.py            # 规则降级引擎（无模型兜底）
│   │   ├── prompts.py          # 提示词（意图 / 域路由 / 抽取 / 解释）
│   │   ├── formatters.py       # 结果模板（模型不可用时的可读输出）
│   │   ├── state.py            # 跨轮次状态
│   │   └── memory.py           # Checkpointer
│   ├── api/
│   │   ├── core/               # 核心双域路由
│   │   │   ├── organization.py # OD：架构 / 效能 / 职级 / 变革 / 诊断 / 战略 / 文化
│   │   │   └── talent.py       # TD：能力 / 标准 / 池 / 项目 / 导师 / 盘点 / 胜任力 / 继任 / IDP / 任用
│   │   ├── hr/                 # HRIS 六大模块路由
│   │   ├── ai.py               # 对话入口
│   │   ├── employee.py         # 员工主数据
│   │   ├── hris.py             # HRIS 聚合入口与模块清单
│   │   └── integrations.py     # 外部 HRIS 接入
│   ├── models/                 # ORM 模型（核心双域 18 张表 + HRIS）
│   │   ├── organization.py         # OD 八表
│   │   ├── talent_development.py   # TD 十表
│   │   ├── recruitment.py  compensation.py  performance.py
│   │   ├── employee_relations.py  learning.py  workforce.py
│   │   └── employee.py         # 员工 / 绩效 / 潜力 / 能力模型
│   ├── services/               # 确定性计算（真正的业务大脑）
│   │   ├── organization_service.py        # OD 七类计算
│   │   ├── talent_development_service.py  # TD 十类计算
│   │   └── *_service.py                   # HRIS 六模块
│   ├── tools/                  # Tool 层：自然语言 → 计算调用
│   ├── integrations/           # HRIS 适配器（local / SAP SuccessFactors）
│   ├── llm/                    # 大模型客户端（Ollama / OpenAI 兼容）
│   ├── config/                 # 配置、数据库、SQLite 列迁移
│   └── schemas/                # 请求响应模型
├── seed_data.py                # 种子数据生成
├── smoke_core.py               # 端点 + 路由冒烟（34 端点 + 24 场景）
├── test_tool.py                # 核心双域 17 项计算测试
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
                        ├─ ORG_DEV    → 组织发展（七路动作分发）
                        ├─ TALENT_DEV → 人才发展（十路动作分发）
                        └─ HRIS       → 二级路由 → 六个支撑模块
```

- 核心双域由 `rules.rule_core_module()` 或大模型判定
- HRIS 走独立的二级路由节点 `decide_hris_module`，再分发到六个具体模块
- 每个域内部再做一次动作级关键词分发，`result_topic` 形如 `OD_DIAGNOSIS` / `TD_REVIEW`

### 关键设计决策

| 决策 | 理由 |
| --- | --- |
| 计算与表达彻底分离 | 大模型可以换、可以不用，数字始终一致 |
| 每个结果带 basis 字段 | 分数怎么算的直接写进响应，可审计、可复盘 |
| 规则引擎兜底 | 没装 Ollama、没配 Key 也能跑完整流程 |
| 核心双域优先于 HRIS | 主打能力优先命中 |
| 适配器能力声明 | `supports()` 先判定，防止打到厂商不支持的接口 |
| SQLite 自动列迁移 | 存量库升级不丢数据 |

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

# 3. 生成演示数据（67 名员工 + OD/TD 全量种子 + HRIS 六模块种子）
python seed_data.py

# 4. 启动服务
uvicorn app.main:app --reload --port 8000
```

打开 <http://127.0.0.1:8000/docs> 查看全部 67 个接口。

### 切换 MySQL

```bash
# .env
DATABASE_URL=mysql+pymysql://root:123456@localhost:3306/talent_ai
```

### 接入大模型（可选）

```bash
# 本地 Ollama（默认 deepseek-r1:7b）
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
  -d '{"thread_id":"demo","message":"做一次组织诊断"}'
```

支持的问法（OD）：

```text
做一次组织诊断                  → 健康度调研 + 组织扫描
用 7S 框架扫一下技术中心        → 麦肯锡 7S 扫描
公司文化氛围怎么样              → 文化与敬业度
战略解码做得怎么样              → 三层目标与达成率
看一下组织架构和编制达成         → 架构与管控设计
分析各部门人效                  → 组织效能
技术中心的职级体系健康吗         → 岗位职级体系
模拟一下组织变革方案             → 变革影响与阻力
```

支持的问法（TD）：

```text
做一次人才盘点                  → 九宫格 + 360 评估
胜任力模型搭得怎么样             → 能力项与岗位要求
谁能晋升到下一职级              → 任职资格匹配度
关键岗位继任情况                → 继任者计划与梯队
看一下人才池                    → 人才池视图
发展项目完成得怎么样             → 高潜项目与训练营
IDP 进展如何                    → 个人发展计划
有哪些人可以提拔                → 人才任用建议
导师带教进展如何                → 导师制
技术中心的能力差距在哪           → 能力画像
```

### 核心双域直达接口

```bash
# 组织发展 OD
GET /api/core/organization-development/structure?department=技术中心
GET /api/core/organization-development/effectiveness
GET /api/core/organization-development/job-architecture
GET /api/core/organization-development/change?change_type=合并
GET /api/core/organization-development/diagnosis?framework=seven_s
GET /api/core/organization-development/strategy
GET /api/core/organization-development/culture

# 人才发展 TD
GET /api/core/talent-development/review?department=技术中心
GET /api/core/talent-development/competency-model?job_level=P7
GET /api/core/talent-development/standard-match?job_level=P7
GET /api/core/talent-development/succession
GET /api/core/talent-development/pool
GET /api/core/talent-development/program
GET /api/core/talent-development/idp
GET /api/core/talent-development/mentorship
GET /api/core/talent-development/placement
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
python smoke_core.py     # 端点 + Agent 路由冒烟（34 端点 + 24 场景）
python test_tool.py      # 核心双域 17 项计算（不依赖大模型）
python test_hris.py      # HRIS 六模块计算
python test_agent.py     # Agent 多轮流程
python test_llm.py       # 大模型连通性
```

## 参与贡献

1. Fork 本仓库并新建分支 `feat/your-feature`
2. 保持"计算与表达分离"：新增能力先写 `services/` 里的确定性计算，再接 Tool 与 API
3. 新增能力需同时补齐：模型 → 服务 → Tool → API → 动作路由 → 格式化模板 → 种子数据 → 测试
4. 每个计算函数必须在返回结果里带上 `basis` 字段
5. 提交前跑通 `python smoke_core.py`
6. 发起 Pull Request，说明改动的能力域与影响的接口

### 提交规范

`feat:` 新能力 · `fix:` 修复 · `refactor:` 重构 · `docs:` 文档 · `chore:` 杂项

## 特技

1. **零模型也能跑**：不装 Ollama、不配 API Key，全部流程照常运转，
   响应里 `llm_used` 字段如实标注本轮是否用了模型

2. **每个数字都有公式**：每个计算结果的 `basis` 字段写明算法口径，
   HR 可以直接拿去给业务负责人汇报，不怕被问"这数哪来的"

3. **组织诊断三框架齐备**：麦肯锡 7S、Weisbord 6-BOX、五维诊断框架
   按维度给出现状分、目标分、差距与痛点，自动排出瓶颈优先级

4. **人才盘点九宫格 + 360 认知偏差**：绩效 × 潜力定位高潜与待优化人员，
   同时用 360 数据算出"自评 vs 他评"的认知偏差，面谈前先知道谁会不服

5. **变革阻力显性化**：不只算影响人数与成本，还记录变革阶段
   （宣贯→试点→推广→固化）与阻力等级、阻力来源，给出对应的推进动作

6. **双域 17 路动作路由**：组织发展 7 路 + 人才发展 10 路，
   HRIS 六大模块走独立二级路由，24 类问法自动分发

7. **任职资格四维加权**：专业能力 / 业务贡献 / 领导力 / 学习敏锐按权重比对达标线，
   并可直接输出晋升 / 保留 / 激活换岗 / 调整淘汰的任用分群

8. **SAP SuccessFactors 接入骨架**：核心双域 + 六模块 OData v2 端点映射已固化，
   `supports()` 能力声明防止打到厂商不支持的接口

* * *

<details>
<summary><strong>附录：完整文档（三十三章）</strong>——算法公式、数据库设计、API 全量示例、SAP SF 接入指南，点击展开</summary>

## 一、项目简介

面向组织发展（OD）与人才发展（TD）场景的完整体系化智能体系统。
OD 的对象是组织、团队、架构、机制与文化，关注"组织能力"；
TD 的对象是人、个体与人才梯队，关注"人的能力"。

**组织发展 OD**：组织诊断（健康度调研 + 7S / 6-BOX / 五维扫描）、
组织架构与管控设计、组织变革管理、战略解码、企业文化与氛围、
组织效能分析、岗位职级体系。

**人才发展 TD**：人才盘点（九宫格 + 360）、胜任力模型、任职资格与职级体系、
继任者计划与梯队建设、高潜人才项目与管理干部培养、
学习发展体系（内训 / 轮岗 / 导师制 / IDP）、人才任用建议。

**HRIS 六大支撑模块**：招聘管理、薪酬与福利、绩效管理、员工关系管理、培训与开发、人力资源规划。

示例对话：

- 做一次组织诊断，用 7S 框架扫一下技术中心
- 公司文化氛围怎么样，敬业度多少
- 战略解码做得怎么样，哪些目标滞后了
- 看一下公司组织架构和编制达成情况
- 分析一下各部门人效，哪些部门偏低
- 模拟一下组织变革方案的影响、成本和阻力
- 做一次人才盘点，谁是高潜
- 胜任力模型搭得怎么样
- 关键岗位继任情况如何
- IDP 进展如何，有哪些人可以提拔
- 帮我筛选一下候选人、看一下薪酬公平性、大家还有多少年假

## 二、核心功能

### OD 1 · 组织诊断

组织健康度调研按七个维度（战略清晰 / 组织架构 / 流程效率 / 人才供给 /
文化氛围 / 激励机制 / 协同效率）收集评分并与行业基准比对，
同时支持三种框架的组织扫描：

| 框架 | 维度 |
| --- | --- |
| 麦肯锡 7S | 战略 / 结构 / 制度 / 共同价值观 / 风格 / 人员 / 技能 |
| Weisbord 6-BOX | 使命目标 / 组织 / 关系 / 激励 / 领导 / 支持 |
| 五维诊断框架 | 战略 / 组织 / 人才 / 机制 / 文化 |

维度差距 ≤ −0.5 判定为明显短板，扫描差距 ≤ −1.0 判定为瓶颈。

### OD 2 · 组织架构与管控设计

组织单元上直接记录组织模式（职能制 / 事业部制 / 矩阵制 / 项目制 / 平台制）、
管控模式（战略管控 / 财务管控 / 操作管控）、集权分权与权责说明，
输出层级深度、管理幅度、编制达成率与三种分布（组织模式 / 管控模式 / 集权分权）。

### OD 3 · 组织变革管理

覆盖合并、拆分、扩编、缩编、新设、调整、并购、转型八类方案，
输出影响人数、成本影响、人均成本、变革阶段与阻力等级，
每类方案与每个阻力等级配套对应的推进动作。

### OD 4 · 战略解码

公司战略 → 组织目标 → 部门目标三层拆解，每项目标带衡量指标、
目标值、当前值、权重与责任部门，输出加权达成率与滞后目标清单。

### OD 5 · 企业文化与组织氛围

六个维度（价值观认同 / 协作氛围 / 心理安全 / 管理风格 / 成长空间 / 敬业度）
调研评分，每个维度配套一条文化举措建议。

### OD 6 · 组织效能与职级体系

人均产出、人工成本率、人效指数与排名；职族职级的金字塔形态、
腰部拥堵与晋升率，输出组织层面改进方案。

### TD 1 · 人才盘点（九宫格 + 360）

绩效 × 潜力双档定位九宫格，识别（高-高）超级明星与（中-高）潜力之星为高潜，
（低-低）为待优化；360 度评估按上级 / 同级 / 下级 / 自评分角色汇总，
自评与他人均分差值 |Δ| ≥ 0.5 判定为认知偏差。

### TD 2 · 胜任力模型

能力项 + 1-5 级行为描述与可观察证据，岗位能力要求按职族职级配置要求等级与权重，
可算单个员工对照岗位的符合度。

### TD 3 · 任职资格与职级体系

专业能力 0.35 / 业务贡献 0.30 / 领导力 0.20 / 学习敏锐 0.15 四维加权比对达标线，
匹配度 ≥90% 完全胜任、≥75% 基本胜任、≥60% 尚有差距。

### TD 4 · 继任者计划与梯队建设

关键岗位记录重要级别与空缺风险，候选人记录准备度
（立即就绪 / 1 年内 / 2 年内 / 尚未就绪）与来源（内部 / 外部储备），
输出覆盖率、立即就绪率、梯队深度与风险岗位。

### TD 5 · 高潜人才项目与管理干部培养

高潜项目、管理者训练营、行动学习、轮岗、内训统一管理，
输出覆盖率、完成率、满意度与人均投入。

### TD 6 · 学习发展体系

内训、轮岗、导师制、个人发展计划 IDP 四条线：
IDP 按 70-20-10 分布统计行动项与完成率，导师制统计带教进度与导师负荷。

### TD 7 · 人才任用建议

综合绩效、潜力、任职资格匹配度与离职风险，输出五个分群：

| 分群 | 判定条件 |
| --- | --- |
| 晋升提拔 | 绩效高 且 潜力高 且 下一职级匹配度 ≥75% |
| 重点保留 | 绩效高 且 离职风险高 |
| 激活换岗 | 潜力高 但 绩效低 |
| 调整或淘汰 | 绩效低 且 潜力低 |
| 持续观察 | 其余中间档 |

### HRIS 六大支撑模块

| 模块 | 能力 |
| --- | --- |
| 招聘管理 | 简历筛选、智能定薪、面试安排、招聘漏斗 |
| 薪酬与福利 | compa-ratio、调薪模拟、福利覆盖、个人薪酬单 |
| 绩效管理 | 目标达成、评价偏差、强制分布、PIP 改进计划 |
| 员工关系管理 | 假期余额、考勤、关系事件、敬业度 |
| 培训与开发 | 培训总览、必修合规、课程推荐、效果评估 |
| 人力资源规划 | 编制达成、供需预测、六因子离职风险 |

### HRIS 系统集成

统一 `HRISAdapter` 接口，本地库与 SAP SuccessFactors 双实现，
核心双域 + 六大模块共 8 个能力域通过 `capabilities` 声明。

### 用户意图识别

- **ORG_DEV**：组织诊断、架构管控、战略解码、组织变革、文化氛围、组织效能、职级体系
- **TALENT_DEV**：人才盘点、胜任力模型、任职资格、继任梯队、高潜项目、学习发展、任用建议
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
                        ├─ ORG_DEV    → org_dev 节点（七路动作）
                        ├─ TALENT_DEV → talent_dev 节点（十路动作）
                        └─ HRIS       → decide_hris_module → 六个模块节点
```

**核心双域判定**（`rules.rule_core_module`）：

| 域 | 关键词示例 |
| --- | --- |
| organization_development | 组织架构、管控、权责、定岗定编、组织诊断、健康度、痛点、瓶颈、7S、6-BOX、五维、战略解码、目标拆解、文化、氛围、敬业度、价值观、人效、人均产出、人工成本、职级体系、晋升率、管理幅度、合并、拆分、扩编、缩编 |
| talent_development | 盘点、九宫格、人才地图、高潜、360、胜任力、素质模型、能力模型、任职资格、人才标准、匹配度、晋升、继任、接班、梯队、后备、关键岗位、人才池、发展项目、训练营、轮岗、内训、IDP、个人发展计划、任用、提拔、导师、带教 |

**优先级**：修改条件 > 核心双域 > HRIS > 通用业务词。

**组织发展域动作分发**（自上而下匹配）：

| 动作 | 关键词 |
| --- | --- |
| OD_DIAGNOSIS | 组织诊断、诊断、健康度、痛点、瓶颈、组织扫描、7S、6-BOX、六盒、五维 |
| OD_CULTURE | 文化、氛围、敬业度、价值观、心理安全 |
| OD_STRATEGY | 战略解码、战略、目标拆解、目标对齐、解码 |
| OD_CHANGE | 组织变革、变革、合并、拆分、扩编、缩编、新设、重组、并购、转型、调整 |
| OD_ARCHITECTURE | 职级、职族、晋升率、晋升通道、金字塔、带宽 |
| OD_EFFECTIVENESS | 人效、效能、人均产出、人工成本、成本率 |
| OD_STRUCTURE | 架构、组织单元、编制、层级、管理幅度、汇报线、管控、权责 |

**人才发展域动作分发**（自上而下匹配）：

| 动作 | 关键词 |
| --- | --- |
| TD_MENTORSHIP | 导师、带教、师徒 |
| TD_IDP | IDP、个人发展计划、发展计划 |
| TD_PLACEMENT | 任用、晋升建议、调整建议、人员调整、晋升名单、提拔、淘汰、保留方案 |
| TD_SUCCESSION | 继任、接班、梯队、后备、关键岗位 |
| TD_POOL | 人才池、池子、入池、出池 |
| TD_PROGRAM | 发展项目、培养项目、行动学习、训练营、轮岗、内训 |
| TD_MODEL | 胜任力、素质模型、能力模型、能力项 |
| TD_REVIEW | 盘点、九宫格、人才地图、高潜、360、明星、短板 |
| TD_STANDARD | 任职资格、人才标准、匹配度、够不够格、晋升、下一职级、晋升评审 |
| TD_COMPETENCY | 能力、差距、画像 |

## 七、组织发展（OD）详解

### 1. 组织诊断

| 指标 | 公式 | 分档 |
| --- | --- | --- |
| 维度得分 | 该维度调研均分 | — |
| 维度差距 | 实际分 − 行业基准 | ≤−0.5 明显短板，<0 低于基准，<0.3 基本达标，否则优于基准 |
| 扫描差距 | 现状分 − 目标分 | ≤−1.5 严重瓶颈，≤−1.0 瓶颈，<0 有差距，否则达标 |
| 组织健康分 | 各维度得分均值 | ≥4.2 健康，≥3.6 基本健康，≥3.0 亚健康，否则预警 |

支持按 `framework` 过滤（seven_s / six_box / five_dim），
输出痛点维度与瓶颈项并给出责任方与改进建议。

### 2. 组织架构与管控设计

| 指标 | 公式 | 说明 |
| --- | --- | --- |
| 编制达成率 | 在编 / 编制 | ≥95% 已满编，≥85% 接近满编，≥70% 缺口较大，其余严重缺编 |
| 平均管理幅度 | 一线单元在编人数均值 | 健康区间 4–12 人 |
| 组织层级深度 | max(level) | 合理区间 3–5 层 |

同时输出组织模式、管控模式、集权分权三张分布表，支撑架构与管控设计决策。

### 3. 组织变革管理

| 字段 | 说明 |
| --- | --- |
| change_type | 合并 / 拆分 / 扩编 / 缩编 / 新设 / 调整 / 并购 / 转型 |
| affected_headcount | 影响人数，≥30 高影响，≥10 中影响 |
| cost_impact | 成本影响（万元/年），负值为节约 |
| stage | 宣贯 → 试点 → 推广 → 固化 |
| resistance | 变革阻力 高 / 中 / 低，附阻力来源描述 |

高阻力方案给出"高管站台 + 关键人群一对一"的推进动作。

### 4. 战略解码

| 指标 | 公式 |
| --- | --- |
| 目标达成率 | 当前值 / 目标值 |
| 加权达成率 | Σ(达成率 × 权重) / Σ权重 |

≥1.0 已达成，≥0.8 进展良好，≥0.6 有风险，否则严重滞后。
按公司 / 组织 / 部门三层输出，并列出滞后目标。

### 5. 企业文化与组织氛围

维度分 = 该维度调研均分（1-5）：≥4.2 氛围优良，≥3.6 健康，≥3.0 需关注，否则预警。
单独输出敬业度得分，每个需关注维度配套一条文化举措。

### 6. 组织效能与职级体系

| 指标 | 公式 |
| --- | --- |
| 人均产出 | 营收 / 在编人数（万元） |
| 人工成本率 | 人工成本 / 营收 |
| 人效指数 | 部门人均产出 / 全公司人均产出 |

职级形态：中级占比 ≥60% 腰部拥堵，基层 ≥60% 基层偏重，
高级 ≥45% 倒金字塔，其余结构均衡；年均晋升率 <8% 标记晋升停滞。

## 八、人才发展（TD）详解

### 1. 人才盘点

| 指标 | 公式 |
| --- | --- |
| 绩效档 | ≥3.8 高，≥3.0 中，否则低 |
| 潜力档 | 同上阈值 |
| 九宫格 | 绩效档 × 潜力档，共九格 |
| 高潜 | （高-高）超级明星 +（中-高）潜力之星 |
| 360 认知偏差 | 自评分 − 他人均分，\|Δ\| ≥ 0.5 判定认知不一致 |

九宫格矩阵按"行=绩效 高→低、列=潜力 低→高"输出每格人数与名单，
同时给出高潜名单与待优化名单。

### 2. 胜任力模型

- 能力项 + 1-5 级行为描述与可观察证据
- 岗位能力要求：职族 × 职级 × 能力项 × 要求等级 × 权重
- 模型覆盖度 = 已被岗位要求引用的能力项 / 能力项总数
- 员工符合度 = Σ(权重 × min(现状等级 / 要求等级, 1)) / Σ权重

### 3. 任职资格匹配度

```text
匹配度 = Σ (权重ᵢ × min(实际ᵢ / 达标线ᵢ, 1))
```

| 维度 | 权重 | 数据来源 |
| --- | --- | --- |
| 专业能力 | 0.35 | 员工能力现状等级均值 |
| 业务贡献 | 0.30 | 最近一次绩效分 |
| 领导力 | 0.20 | 潜力评估领导力分 |
| 学习敏锐 | 0.15 | 潜力评估学习敏锐分 |

≥90% 完全胜任，≥75% 基本胜任，≥60% 尚有差距。默认比对下一职级。

### 4. 继任者计划与梯队建设

| 指标 | 公式 |
| --- | --- |
| 覆盖率 | 有候选人的关键岗位 / 关键岗位总数 |
| 立即就绪率 | 有 ready_now 人选的岗位 / 总数 |
| 梯队深度 | 岗位候选人数 |

风险岗位分两类：完全没有继任人选、缺少立即就绪人选，结论分别给出动作。

### 5. 高潜项目与管理者训练营

覆盖率 = 入学 / 容量，完成率 = 完成 / 入学，人均投入 = 预算 × 10000 / 入学人数。
完成率 ≥85% 且满意度 ≥4.0 效果良好，≥70% 基本达标，<70% 需改进。

### 6. 学习发展体系

| 线路 | 载体 | 关键指标 |
| --- | --- | --- |
| 内训 | TrainingCourse / TrainingEnrollment | 覆盖率、必修合规 |
| 轮岗 | DevelopmentProgram（轮岗类型） | 完成率 |
| 导师制 | Mentorship | 带教进度、导师负荷 |
| IDP | DevelopmentPlan | 完成率、70-20-10 分布、平均进度 |

IDP 的 70 = 在职历练，20 = 他人辅导，10 = 正式培训。

### 7. 人才任用建议

综合盘点结果、任职资格匹配度与离职风险输出五分群，
每分群给出判定理由与具体动作建议，并标注每个人的匹配度与风险分。

## 九、模块演进说明

### 第一版：五个独立模块（已下线）

项目最初把以下五项做成彼此独立的顶层模块：人才盘点九宫格、
关键岗位继任地图、人才梯队分析、个人发展计划 IDP、组织诊断。
问题是它们各自为政，缺少体系归属，也无法回答"组织层面怎么改"。

### 第二版：按 OD / TD 体系重建

五个模块的能力**没有被丢弃**，而是按专业框架重建进两大核心域：

| 原独立模块 | 现在归属 | 重建后的变化 |
| --- | --- | --- |
| 人才盘点九宫格 | TD · 人才盘点 | 保留九宫格，新增 360 度评估与自评认知偏差分析 |
| 关键岗位继任地图 | TD · 继任者计划 | 新增空缺风险、候选人来源、准备度分档与梯队深度 |
| 人才梯队分析 | TD · 继任与梯队 | 与继任计划合并，输出覆盖率、立即就绪率与风险岗位 |
| 个人发展计划 IDP | TD · 学习发展体系 | 与内训、轮岗、导师制合并为体系，按 70-20-10 统计 |
| 组织诊断 | OD · 组织诊断 | 从单一健康分扩展为健康度调研 + 7S / 6-BOX / 五维三框架扫描 |

### 同时新增的能力

组织发展侧新增：架构与管控设计（组织模式、管控模式、集权分权、权责）、
战略解码（三层目标树）、组织变革管理（阶段与阻力）、文化与组织氛围。

人才发展侧新增：胜任力模型（等级行为 + 岗位要求）、人才任用建议（五分群）。

### 数据表演进

| 变化 | 表 |
| --- | --- |
| 第一版删除 | key_position、succession_plan、idp、department_metric、course |
| 第二版新增 | org_unit（扩管控字段）、org_health_survey、org_scan、strategic_goal、culture_survey、org_change（扩阶段阻力）、review_360、competency_level、position_competency、key_position（新结构）、succession_candidate、development_plan |

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
| 组织健康分 | ≥4.2 健康，≥3.6 基本健康，≥3.0 亚健康 | 服务内常量 |
| 诊断维度差距 | ≤−0.5 明显短板 | 服务内常量 |
| 扫描瓶颈 | 差距 ≤−1.0 | 服务内常量 |
| 文化维度分 | ≥4.2 优良，≥3.6 健康，≥3.0 需关注 | 服务内常量 |
| 战略达成率 | ≥1.0 已达成，≥0.8 良好，≥0.6 有风险 | 服务内常量 |

### 人才发展

| 指标 | 阈值 | 配置项 |
| --- | --- | --- |
| 九宫格绩效 / 潜力档 | ≥3.8 高，≥3.0 中 | `REVIEW_SCORE_HIGH` / `REVIEW_SCORE_LOW` |
| 360 认知偏差 | \\|自评 − 他人\\| ≥ 0.5 | 服务内常量 |
| 匹配度分档 | 0.90 / 0.75 / 0.60 | `td_match_ready` / `td_match_basic` / `td_match_gap` |
| 达标线（1-5 分制） | P4 3.0 → M3 4.0 | 种子数据 `LEVEL_PASS_SCORE` |
| 继任准备度 | ready_now / ready_1y / ready_2y / not_ready | `READINESS_ORDER` |
| 人才池活跃度 | ≥80% 活跃，≥60% 正常 | 服务内常量 |
| 项目完成率达标 | ≥70% | `td_program_completion_target` |
| 项目满意度达标 | ≥4.0 | `td_program_satisfaction_target` |
| IDP 停滞 | 平均进度 <50% | 服务内常量 |
| 导师负荷偏高 | 同时带 ≥3 人 | 服务内常量 |
| 任用分群 | 晋升需匹配度 ≥75% | 服务内常量 |

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
| `org_unit` | 组织单元（隶属关系、层级、负责人、编制与在编、组织模式、管控模式、集权分权、权责说明） |
| `org_health_survey` | 组织健康度调研（七维度评分与行业基准） |
| `org_scan` | 组织扫描（7S / 6-BOX / 五维框架的维度现状分、目标分与痛点） |
| `strategic_goal` | 战略解码目标树（公司 / 组织 / 部门三层，含指标、目标值、权重） |
| `culture_survey` | 企业文化与氛围调研（六维度评分与对应举措） |
| `org_effectiveness` | 组织效能（营收、人工成本、离职率、管理幅度） |
| `job_architecture` | 岗位职级体系 |
| `org_change` | 组织变革方案（含变革阶段与阻力） |

**核心双域 · 人才发展**

| 表 | 说明 |
| --- | --- |
| `review_360` | 360 度评估（评价角色 × 维度打分） |
| `competency_level` | 胜任力等级行为描述与可观察证据 |
| `position_competency` | 岗位能力要求（职族 × 职级 × 能力项 × 要求等级 × 权重） |
| `talent_standard` | 任职资格标准（职族 × 职级 × 四维达标线） |
| `key_position` | 关键岗位（重要级别、空缺风险） |
| `succession_candidate` | 继任候选人（准备度、来源） |
| `talent_pool` | 人才池成员 |
| `development_program` | 发展项目（高潜项目 / 训练营 / 行动学习 / 轮岗 / 内训） |
| `development_plan` | 个人发展计划 IDP（70-20-10 行动项与进度） |
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

生成 67 名员工、5 个部门、2 个考核周期，外加：

**组织发展 OD**：16 个组织单元（含组织模式 / 管控模式 / 集权分权）、
5 条组织效能记录、29 个职级配置、8 个变革方案（含阶段与阻力）、
35 条健康度调研（7 维度 × 5 部门）、110 条组织扫描（三框架）、
11 个战略解码目标、30 条文化氛围调研（6 维度 × 5 部门）。

**人才发展 TD**：能力模型 9 项 + 45 条等级行为描述、岗位能力要求、
任职资格标准（4 职族 × 8 职级 × 4 维度）、24 人 × 4 角色 × 4 维度 360 评估、
10 个关键岗位 + 继任候选人、3 个人才池、5 个发展项目、
12 人个人发展计划 IDP、14 组导师带教。

另有 HRIS 六模块全量种子。数据由固定随机种子生成，结果可复现。

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
| 组织架构与管控 | 看一下公司组织架构和编制达成情况 | ORG_DEV → OD_STRUCTURE |
| 组织效能 | 分析各部门人效 | ORG_DEV → OD_EFFECTIVENESS |
| 职级体系 | 技术中心的职级体系健康吗 | ORG_DEV → OD_ARCHITECTURE |
| 组织变革 | 模拟一下组织变革方案 | ORG_DEV → OD_CHANGE |
| 组织诊断 | 做一次组织诊断 | ORG_DEV → OD_DIAGNOSIS |
| 战略解码 | 战略解码做得怎么样 | ORG_DEV → OD_STRATEGY |
| 文化与氛围 | 公司文化氛围怎么样 | ORG_DEV → OD_CULTURE |
| 能力差距 | 技术中心的能力差距在哪 | TALENT_DEV → TD_COMPETENCY |
| 任职资格 | 谁能晋升到下一职级 | TALENT_DEV → TD_STANDARD |
| 人才盘点 | 做一次人才盘点 | TALENT_DEV → TD_REVIEW |
| 胜任力模型 | 胜任力模型搭得怎么样 | TALENT_DEV → TD_MODEL |
| 继任梯队 | 关键岗位继任情况 | TALENT_DEV → TD_SUCCESSION |
| 人才池 | 看一下人才池 | TALENT_DEV → TD_POOL |
| 发展项目 | 发展项目完成得怎么样 | TALENT_DEV → TD_PROGRAM |
| 个人发展计划 | IDP 进展如何 | TALENT_DEV → TD_IDP |
| 导师制 | 导师制运行情况 | TALENT_DEV → TD_MENTORSHIP |
| 任用建议 | 有哪些人可以提拔 | TALENT_DEV → TD_PLACEMENT |
| 招聘 | 帮我筛选一下候选人 | HRIS → recruitment |
| 薪酬 | 薪酬公平性怎么样 | HRIS → compensation |
| 绩效 | 绩效目标达成情况 | HRIS → performance |
| 员工关系 | 大家还有多少年假 | HRIS → employee_relations |
| 培训 | 培训覆盖率如何 | HRIS → learning |
| 编制 | 编制达成情况 | HRIS → workforce |
| 离职风险 | 谁有离职风险 | HRIS → workforce |
| 多轮改条件 | 看一下组织架构 → 部门改成销售部 → 重新看一下 | 按新条件重算 |
| 无关对话 | 今天天气怎么样 | CHAT |

`python smoke_core.py` 会跑完上述全部场景，端点 34/34、路由 24/24 通过。
`python test_tool.py` 覆盖 17 项核心双域计算。

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

17 类核心动作（OD 7 路 + TD 10 路）+ 六类 HRIS 模块封装为独立 Tool，
便于扩展与单独测试。

### 3.1 计算结果自带依据

每个计算函数都在返回值里带 `basis` 字段，写清分数与分档的算法口径，
配合 `advice` 行动建议，形成"数字 → 依据 → 动作"的完整链条。

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
| 体系完整性 | 模块各自为政，缺 OD 体系 | OD 六类 + TD 七类工作全覆盖，含 7S / 6-BOX / 五维诊断框架 |
| 关注点 | 盘点"现在有什么人" | 回答"组织长得好不好、人怎么长起来" |
| 组织视角 | 多为人才个体视角 | 组织发展与人才发展并重，含变革阻力与战略解码 |
| 前瞻性 | 事后记录为主 | 预测驱动：离职风险、继任缺口、晋升匹配度、变革影响测算 |
| 成本门槛 | 数十万至百万级 TCO | 开源可自部署，SQLite 零配置启动 |
| 集成方式 | 绑定厂商生态 | 适配器抽象，本地库与 SAP SF 一键切换 |

**适用场景**：

- 组织诊断与组织健康度年度调研
- 组织架构与管控模式调整、定岗定编
- 战略解码与部门目标对齐
- 并购 / 转型 / 扩编的变革影响与阻力管理
- 年度人效复盘与低效部门定位
- 职级体系与晋升通道健康度检查
- 人才盘点、高潜识别与 360 度评估
- 胜任力模型与任职资格体系建设
- 关键岗位继任与梯队建设
- 人才池、培养项目、导师制、IDP 的运行跟踪
- 晋升评审与人员调整建议

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
