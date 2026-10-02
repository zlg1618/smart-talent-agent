# Smart Talent Agent · 智能人才发展与 HRIS Agent

面向 HR 业务的多 Agent 智能体系统：大模型只承担语言层的理解与表达，
所有人才盘点、继任分析、组织诊断，以及 HRIS 六大模块的打分逻辑，
都在 Python 与数据库里完成。

## HRIS 六大模块

| 模块 | 关键能力 | 算法核心 |
| --- | --- | --- |
| **招聘管理** | 简历筛选、Offer 定薪、面试安排、招聘漏斗 | 技能 40 + 经验 20 + 学历 15 + 薪资 15 + 职级 10；定薪按分数档 + 经验奖金比 + RSU |
| **薪酬与福利** | 薪酬公平性、调薪预算、福利覆盖、薪酬单 | compa-ratio、带宽渗透率、红绿圈判定、TCC / TDC |
| **绩效管理** | 目标达成、评价偏差、强制分布、改进计划 | 加权达成率、自评-主管评偏差、S/A/B/C/D 分布校验 |
| **员工关系管理** | 假期、考勤、关系事件、敬业度 | 法定年假按工龄分档、SLA 超期、五维敬业度与 eNPS |
| **培训与开发** | 培训总览、必修合规、课程推荐、培训效果 | 能力差距排序、必修人次合规率、按满意度排课 |
| **人力资源规划** | 编制审查、供需预测、离职风险、继任联动 | 编制达成率、内外部供给缺口、六因子加权风险分 |

## 为什么这样设计

HR 场景对**结果可解释、可审计、可复现**的要求远高于一般聊天场景。
LLM 在数字与推理上容易失真，直接让模型"算九宫格"、"算 compa-ratio"会持续产生幻觉。
本系统把这两类工作切开：

| 角色 | 职责 |
| --- | --- |
| **大模型** | 意图识别、HRIS 模块路由、结构化条件抽取、自然语言汇报 |
| **Python 服务** | 九宫格定位、继任覆盖、梯队供给、组织健康分，以及 HRIS 六大模块的打分与统计 |
| **数据库** | 员工、绩效、潜力、能力、招聘、薪酬、培训、编制等真实数据来源 |
| **HRIS Adapter** | 按六大模块隔离本地与外部系统（SAP SuccessFactors 等），可热插拔 |

这套范式把"语言"与"计算"在工程上分离，模型可以被替换，
业务规则仍然独立演化、可以独立测试。

## 核心能力

**人才管理与组织发展**

- 人才盘点九宫格：绩效 × 潜力定位 + 9 类管理动作
- 关键岗位继任地图：覆盖率、立即就绪率、候选深度与风险识别
- 人才梯队分析：P/M 双通道供给比与断层诊断
- 个人发展计划 IDP：能力差距 × 课程形式的 70-20-10 配比
- 组织诊断：扣分制健康分 + 11 类触发问题清单

**HRIS 六大模块**

- 招聘管理：五维加权打分 + 三段式 Offer + 面试推荐 + 漏斗
- 薪酬与福利：compa-ratio 公平性、调薪预算模拟、福利覆盖、薪酬单
- 绩效管理：目标达成、评价偏差、强制分布校验、PIP 跟进
- 员工关系管理：法定年假、考勤、关系事件 SLA、敬业度与 eNPS
- 培训与开发：培训总览、必修合规、能力差距驱动课程推荐、效果评估
- 人力资源规划：编制达成、供需预测、六因子离职风险、继任联动

**系统集成**

- 抽象 `HRISAdapter`：按六大模块声明能力，业务侧零修改切换
- `LocalHRISAdapter`：直接读写本地 SQLite / MySQL（默认）
- `SAPSuccessFactorsAdapter`：Employee Central OData v2 接入骨架

## 技术栈

```
FastAPI · SQLAlchemy · Pydantic · LangGraph · LangChain Ollama/OpenAI · MySQL/SQLite
```

## 运行

```bash
pip install -r requirements.txt
python seed_data.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# 浏览器打开 http://127.0.0.1:8000/docs
```

更多章节、能力图谱、算法说明与接口示例，请参见
[docs/README.zh-CN](https://d5e62e0ec8b748a6a21d91c905d30cea.app.workbuddy.host/downloads/README.html)。

* * *

## 一、项目简介

面向组织发展（OD）与人才发展（TD）场景的智能体系统，
用自然语言承载 HR 的盘点、继任、诊断、招聘与员工事务五类日常动作。

示例对话：

- 对技术中心做一次人才盘点
- 只看明星人才
- 部门改成销售部，重新做一次盘点
- 看一下关键岗位继任地图
- 分析一下人才梯队有没有断层
- 给李伟生成一份个人发展计划
- 做一次组织诊断

系统在 LangGraph 状态机里持续维护盘点条件（部门、周期、职级、员工、筛选偏好），
条件变化后立即重新查询数据库与重新计算，不沿用上一次的结果。

* * *

## 二、核心功能

### 1. 人才盘点九宫格

以绩效为横轴、潜力为纵轴，将员工定位到九个格子，并给出对应的管理动作建议。

### 2. 关键岗位继任地图

展示每个关键岗位的现任者、候选人及其准备度，计算继任覆盖率、立即就绪率与候选深度，
识别高风险岗位。

### 3. 人才梯队分析

按专业通道（P）与管理通道（M）分别计算相邻职级的梯队供给比，判断储备充足、偏薄或断层。

### 4. 个人发展计划 IDP

基于员工能力差距（目标等级 − 现状等级）匹配学习资源，遵循 70-20-10 发展法则生成发展计划。

### 5. 组织诊断

基于部门级指标（离职率、平均绩效、高潜占比、管理幅度、平均司龄）计算健康分，
输出问题清单与改进建议。

### 6. HRIS · 招聘管理

- 简历筛选：技能 / 经验 / 学历 / 期望薪资 / 职级五维加权打分，自动分档
- Offer 定薪：按匹配分与经验年限给出 base + 奖金 + 长期激励三段式建议
- 面试安排：推荐面试官与未来一周可预约时段
- 招聘漏斗：各阶段候选人数量与转化率统计
- 录用转换：通过的候选人落库为正式员工

### 7. HRIS · 薪酬与福利

- 薪酬公平性：compa-ratio 分布、带宽渗透率、红圈（超薪）/ 绿圈（欠薪）判定
- 调薪预算：按调薪池比例模拟，优先补齐低于带宽下限的人
- 福利覆盖：核心福利参保率、人均年成本、未覆盖排查
- 薪酬单：TCC 总现金薪酬、TDC 总直接薪酬、带宽位置

### 8. HRIS · 绩效管理

- 目标达成：OKR / KPI 加权达成率、风险目标识别
- 评价偏差：自评与主管评的差值分析，识别认知落差
- 强制分布：S / A / B / C / D 校准前后分布校验与调整建议
- 改进计划：PIP 跟进与未达标人员清单

### 9. HRIS · 员工关系管理

- 假期：按中国劳动法工龄计算法定年假、已用与剩余
- 考勤：出勤率、迟到、缺勤、累计工时
- 关系事件：纠纷 / 申诉 / 关怀 / 合规台账，SLA 超期与升级风险预警
- 敬业度：五维得分、eNPS 推荐者占比、低分预警

### 10. HRIS · 培训与开发

- 培训总览：覆盖率、完课率、学时、人均成本
- 必修合规：必修课应完成 / 实际完成人次、缺口人员清单
- 课程推荐：按能力差距（要求等级 − 现状等级）匹配课程与优先级
- 培训效果：按课程的通过率、满意度与投入产出

### 11. HRIS · 人力资源规划

- 编制审查：编制达成率、在招缺口、预算执行率
- 供需预测：自然流失 + 业务增量，测算内部供给与外部招聘需求
- 离职风险：六因子加权风险分、分级与保留建议
- 继任联动：高风险在岗 × 无继任覆盖的交叉风险

### 12. HRIS 系统集成

- 抽象 `HRISAdapter`：按六大模块声明能力，业务侧零修改切换
- `LocalHRISAdapter`：直接读写本地 SQLite / MySQL（默认）
- `SAPSuccessFactorsAdapter`：Employee Central OData v2 接入骨架

### 13. 用户意图识别

| 意图 | 说明 |
| --- | --- |
| TALENT_REVIEW | 人才盘点、九宫格、人才分布 |
| SUCCESSION | 继任地图、接班人、人才梯队 |
| IDP | 个人发展计划、培养方案 |
| DIAGNOSIS | 组织诊断、组织健康度 |
| HRIS | HRIS 六大模块（招聘 / 薪酬福利 / 绩效 / 员工关系 / 培训 / 人力规划） |
| UPDATE | 修改部门、周期、职级、员工 |
| PREFERENCE | 设置筛选偏好（只看某类人才、排除某些情况） |
| CHAT | 普通对话 |

命中 `HRIS` 后会进入二级路由 `decide_hris_module`，再分发到六个具体业务节点：

| hris_module | 业务节点 | 典型问法 |
| --- | --- | --- |
| `recruitment` | 招聘管理 | 简历筛选、定 Offer、面试安排、招聘漏斗 |
| `compensation` | 薪酬与福利 | 薪酬公平性、调薪预算、福利覆盖、薪酬单 |
| `performance` | 绩效管理 | 目标达成、评价偏差、强制分布、改进计划 |
| `employee_relations` | 员工关系管理 | 年假、考勤、关系事件、敬业度 |
| `learning` | 培训与开发 | 培训总览、必修合规、课程推荐、培训效果 |
| `workforce` | 人力资源规划 | 编制达成、供需预测、离职风险、继任联动 |

### 7. 多轮对话 Memory

基于 LangGraph Checkpointer 保存同一个 `thread_id` 下的对话状态。

### 8. 条件修改后重新计算

修改部门、周期或职级后，系统会基于最新条件重新查询数据库，
而不是返回修改前的结果。

### 9. 偏好筛选与取消

支持"只看明星人才""只看高潜""排除未就绪候选人"，也支持"不限""取消筛选"清空偏好。

### 10. HRIS 模块间上下文复用

在招聘域里带上部门条件后，再问"这个部门的编制达成情况"，
部门上下文会继续生效，模块从 `recruitment` 切到 `workforce`。

### 11. 数据真实性控制

所有人才数据、评级与建议均来自数据库与确定性计算，
系统中不存在的员工与岗位不会被虚构出来。

* * *

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
 九宫格    继任/梯队    IDP     招聘    薪酬福利   绩效   员工关系
   │          │          │        │        │        │        │
   └──────────┴─────┬────┘        └────────┴────────┴───┬────┘
                    │                                  │
                    ▼                    ┌─────────────┴────────┐
                组织诊断                ▼                      ▼
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
九宫格定位 / 继任覆盖 / 梯队供给比 / compa-ratio /
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
- `request_type`
- `active_topic`
- `hris_module` —— HRIS 二级路由结果（recruitment / compensation / performance / employee_relations / learning / workforce）
- `department`
- `period`
- `job_level`
- `employee_name`
- `preferences`
- `result`
- `result_topic`
- `answer`
- `llm_used`

### 盘点条件

```json
{
  "department": "技术中心",
  "period": "2025H1",
  "job_level": "P6",
  "employee_name": "李伟"
}
```

### 筛选偏好

```json
{
  "only_grid": ["高-高"],
  "criticality": "高",
  "exclude_readiness": ["not_ready"]
}
```

* * *

## 六、Agent 意图路由

```
                  analyze_request
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
      CHAT          PREFERENCE         extract_info
       │                 │                 │
       ▼                 │                 │
      chat               │                 │
                         ▼                 │
              extract_preferences          │
                         │                 │
                         ▼                 │
              沿用 active_topic ───────────┤
                         │                 │
       ┌─────────────────┴─────────────────┤
       │                                   │
       ▼                                   ▼
 talent_review / succession / idp       decide_hris_module
 / diagnosis / diagnose                     （二级路由）
       │                                   │
       │            ┌──────────┬───────────┼──────────┬──────────┐
       │            ▼          ▼           ▼          ▼          ▼
       │      recruitment compensation performance  learning  workforce
       │            │          │           │          │          │
       │            │          │           ▼          │          │
       │            │          │     employee_relations          │
       │            │          │           │          │          │
       └────────────┴──────────┴───────────┴──────────┴──────────┘
                                │
                                ▼
                         generate_answer
```

主要处理逻辑：

- `TALENT_REVIEW`：九宫格盘点
- `SUCCESSION`：继任地图或人才梯队
- `IDP`：个人发展计划
- `DIAGNOSIS`：组织诊断
- `HRIS`：进入 `decide_hris_module` 二级路由，分发到六个业务节点
- `UPDATE`：更新盘点条件后**沿用上一主题重新计算**
- `PREFERENCE`：更新筛选偏好后**沿用上一主题重新计算**
- `CHAT`：普通对话

二级路由优先由大模型判断，模型不可用时回退到关键词规则表
（`rules.HRIS_MODULE_KEYWORDS`）。

* * *

## 七、人才盘点九宫格

绩效与潜力各分三档，阈值可在配置中调整（默认 3.0 / 4.0）：

- `低`：低于 3.0
- `中`：3.0 ~ 4.0
- `高`：4.0 及以上

九个格子与管理动作：

|  | 低绩效 | 中绩效 | 高绩效 |
| --- | --- | --- | --- |
| **高潜力** | 待激活错配<br>诊断错配原因，尝试调岗重新激发 | 潜力之星<br>补齐关键经历，横向轮岗，指定导师 | 超级明星<br>加速晋升，纳入继任池，交付战略项目 |
| **中潜力** | 待改进<br>启动 PIP，明确改进期限 | 核心骨干<br>聚焦一项能力突破，目标上浮 | 中坚力量<br>扩大职责范围，重点激励保留 |
| **低潜力** | 待优化<br>转岗或依法依规淘汰 | 稳定贡献者<br>维持现状，管理晋升预期 | 业务骨干<br>专家序列晋升，沉淀方法论带教 |

种子数据下的实际盘点结果（67 人）：

|  | 低绩效 | 中绩效 | 高绩效 |
| --- | --- | --- | --- |
| **高潜力** | 待激活错配 4 | 潜力之星 11 | 超级明星 5 |
| **中潜力** | 待改进 7 | 核心骨干 13 | 中坚力量 4 |
| **低潜力** | 待优化 1 | 稳定贡献者 14 | 业务骨干 8 |

* * *

## 八、继任地图与人才梯队

### 继任指标

| 指标 | 含义 |
| --- | --- |
| 继任覆盖率 | 有候选人的关键岗位占比 |
| 立即就绪率 | 有 `ready_now` 候选人的关键岗位占比 |
| 平均候选深度 | 每个关键岗位的平均候选人数 |

风险判定规则：

- 无候选人 → 高风险
- 无立即就绪候选人 → 中风险
- 仅单一候选人 → 中风险
- 其余 → 低风险

### 梯队供给比

```
供给比 = 下一层级人数 / 上一层级人数
```

- `≥ 1.5`：储备充足
- `1.0 ~ 1.5`：储备偏薄
- `< 1.0`：梯队断层

专业通道（P）与管理通道（M）**分别计算**，避免跨通道比较导致的错误结论。

* * *

## 九、个人发展计划 IDP

遵循 70-20-10 发展法则：

| 比例 | 形式 | 说明 |
| --- | --- | --- |
| 70% | 项目历练 | 在岗实践、挑战性任务 |
| 20% | 导师辅导 | 上级或专家带教 |
| 10% | 正式培训 | 线上 / 线下课程 |

生成逻辑：

```
能力差距 = 目标等级 − 现状等级
   ↓
按差距降序取前 N 项能力
   ↓
每项能力按 项目 / 导师 / 培训 各匹配一条最接近目标等级的资源
   ↓
汇总投入时长与 70-20-10 分布
```

数据库中没有匹配资源时，明确标注"暂无匹配资源"，不虚构课程。

* * *

## 十、组织诊断

健康分采用扣分制，满分 100：

| 问题 | 扣分 | 触发条件 |
| --- | --- | --- |
| 离职率过高 | 25 | ≥ 20% |
| 离职率偏高 | 12 | ≥ 10% |
| 整体绩效偏低 | 15 | 平均绩效 < 3.0 |
| 绩效表现偏弱 | 8 | 平均绩效 < 3.3 |
| 高潜人才断层 | 15 | 高潜占比 < 10% |
| 高潜储备不足 | 8 | 高潜占比 < 15% |
| 管理幅度过宽 | 10 | > 15 人 |
| 管理幅度过窄 | 8 | < 3 人 |
| 团队稳定性弱 | 10 | 平均司龄 < 1.5 年 |
| 人员净流出 | 5 | 净变化 ≤ −5 人 |
| 继任准备不足 | 10 | 立即就绪率 < 50% |

等级划分：`≥ 85` 健康，`70 ~ 85` 关注，`< 70` 预警。

种子数据下的诊断结果：

| 部门 | 健康分 | 等级 | 主要问题 |
| --- | --- | --- | --- |
| 销售部 | 30.0 | 预警 | 离职率 26%、平均绩效 2.92、高潜占比 7%、司龄 1.4 年、人员净流出 |
| 财务部 | 64.0 | 预警 | 高潜储备不足、管理幅度 2.5 人过窄、司龄 1.2 年、继任准备不足 |
| 产品部 | 80.0 | 关注 | 离职率 13% 偏高、高潜占比 12% 不足 |
| 人力资源部 | 90.0 | 健康 | 继任准备不足 |
| 技术中心 | 90.0 | 健康 | 继任准备不足 |

组织整体健康分 70.8，等级"关注"。

关键岗位 11 个，继任覆盖 81.8%，立即就绪率 36.4%，平均候选深度 1.73 人。

* * *

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
- 偏好抽取
- 自然语言汇报
- 普通对话

**Python 主要负责：**

- 数据库查询
- 九宫格定位
- 继任覆盖率与风险判定
- 梯队供给比
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

**人才管理与组织发展**

| 表 | 说明 |
| --- | --- |
| `employee` | 员工主数据 |
| `performance_record` | 绩效考核记录（1-5 分） |
| `potential_assessment` | 潜力评估记录 |
| `competency` | 能力模型项 |
| `employee_competency` | 员工能力现状与岗位要求等级 |
| `key_position` | 关键岗位 |
| `succession_plan` | 继任计划（含准备度） |
| `course` | 学习资源（项目 / 导师 / 线上 / 线下） |
| `idp` | 个人发展计划 |
| `department_metric` | 部门级组织诊断指标 |

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
│   │   ├── talent.py         # 关键岗位 / 继任
│   │   ├── development.py    # IDP / 课程 / 部门指标
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
│   │   ├── employee_service.py
│   │   ├── talent_review_service.py
│   │   ├── succession_service.py
│   │   ├── idp_service.py
│   │   ├── diagnosis_service.py
│   │   ├── recruitment_service.py
│   │   ├── compensation_service.py
│   │   ├── performance_service.py
│   │   ├── employee_relations_service.py
│   │   ├── learning_service.py
│   │   ├── workforce_service.py
│   │   └── ai_service.py
│   │
│   ├── tools                 # Agent 调用的工具封装
│   │   ├── talent_review_tool.py
│   │   ├── succession_tool.py
│   │   ├── idp_tool.py
│   │   ├── diagnosis_tool.py
│   │   ├── recruitment_tool.py
│   │   ├── compensation_tool.py
│   │   ├── performance_tool.py
│   │   ├── employee_relations_tool.py
│   │   ├── learning_tool.py
│   │   └── workforce_tool.py
│   │
│   ├── integrations          # HRIS 适配器（六大能力域）
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

* * *

## 十九、生成种子数据

```bash
python seed_data.py
```

生成 67 名员工、5 个部门、2 个考核周期、11 个关键岗位及配套继任关系与学习资源。

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

### 1. AI 对话接口

```bash
curl -X POST http://127.0.0.1:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"thread_id":"test-001","message":"对技术中心做一次人才盘点"}'
```

### 2. 修改部门

```json
{"thread_id":"test-001","message":"部门改成销售部"}
```

### 3. 修改周期与职级

```json
{"thread_id":"test-001","message":"看一下 2024H2 的 P6 人才盘点"}
```

### 4. 设置筛选偏好

```json
{"thread_id":"test-001","message":"只看明星人才"}
```

### 5. 继任地图

```json
{"thread_id":"test-001","message":"看一下关键岗位继任地图"}
```

### 6. 人才梯队

```json
{"thread_id":"test-001","message":"分析一下人才梯队有没有断层"}
```

### 7. 个人发展计划

```json
{"thread_id":"test-001","message":"给李伟生成一份个人发展计划"}
```

### 8. 组织诊断

```json
{"thread_id":"test-001","message":"做一次组织诊断"}
```

### 9. 直接调用计算接口（不经过大模型）

```
GET /api/talent/review?department=技术中心
GET /api/talent/locate?name=李伟
GET /api/succession/map
GET /api/succession/pipeline
GET /api/idp?name=李伟
GET /api/diagnosis

# HRIS · 招聘管理
GET  /api/hris/recruitment/jobs
GET  /api/hris/recruitment/funnel
POST /api/hris/recruitment/screen?job=高级前端开发工程师
POST /api/hris/recruitment/offer?candidate=曹聪&job=高级前端开发工程师
POST /api/hris/recruitment/interview/proposal?job=高级前端开发工程师

# HRIS · 薪酬与福利
GET /api/hris/compensation/compa-ratio
GET /api/hris/compensation/adjustment?budget_pct=5
GET /api/hris/compensation/benefits
GET /api/hris/compensation/summary?name=李伟

# HRIS · 绩效管理
GET /api/hris/performance/goals
GET /api/hris/performance/deviation
GET /api/hris/performance/distribution
GET /api/hris/performance/improvement

# HRIS · 员工关系管理
GET  /api/hris/employee-relations/leave/balance?name=韩磊
POST /api/hris/employee-relations/leave/submit?name=韩磊&days=3
POST /api/hris/employee-relations/leave/approve?leave_id=8&approve=true
GET  /api/hris/employee-relations/leave/pending
GET  /api/hris/employee-relations/attendance?name=韩磊&days=30
GET  /api/hris/employee-relations/cases
GET  /api/hris/employee-relations/engagement

# HRIS · 培训与开发
GET /api/hris/learning/overview
GET /api/hris/learning/compliance
GET /api/hris/learning/recommend?name=李伟
GET /api/hris/learning/effectiveness

# HRIS · 人力资源规划
GET /api/hris/workforce/headcount
GET /api/hris/workforce/forecast?scenario=baseline
GET /api/hris/workforce/attrition-risk
GET /api/hris/workforce/succession-link

# HRIS 集成
GET  /api/hris/modules
GET  /api/integrations/backends
GET  /api/integrations/ping?backend=local
GET  /api/integrations/employee/E0001?backend=local
POST /api/integrations/employee?backend=local
GET  /api/integrations/recruitment/applications?backend=local
GET  /api/integrations/compensation?backend=local
POST /api/integrations/performance/reviews?backend=local
POST /api/integrations/leave?backend=local
POST /api/integrations/learning/records?backend=local
GET  /api/integrations/workforce/headcount?backend=local
```

### 10. 查看与清空会话记忆

```
GET  /api/ai/state/{thread_id}
POST /api/ai/reset/{thread_id}
```

* * *

## 二十二、Memory 使用示例

使用相同的 `thread_id` 可以维持同一个会话状态。

```
第一轮：做一次人才盘点
      → 记录主题 TALENT_REVIEW

第二轮：只看明星人才
      → 记录偏好 only_grid = ["高-高"]

第三轮：部门改成销售部
      → 条件 department = 销售部，按新条件重新盘点

第四轮：重新做一次盘点
      → 沿用 销售部 + 只看超级明星 重新计算
```

* * *

## 二十三、信息不完整处理

系统不会在关键条件缺失时随意猜测。

例如生成 IDP 时未指定员工：

```
请告诉我要为哪位员工生成个人发展计划，
例如"给张伟做一份 IDP"或"生成李娜的发展计划"。
```

例如盘点结果为空时：

```
当前条件下没有参与盘点的员工
（生效条件：{'department': '销售部', '只看格子': ['高-高']}）。
请调整部门、职级或取消筛选偏好后重试。
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

| 场景 | 验证点 |
| --- | --- |
| 正常盘点 | 意图识别、条件抽取、九宫格计算 |
| 多轮记忆 + 偏好筛选 | 偏好保存、过滤生效、重新计算 |
| 修改条件后重新盘点 | 状态更新、旧结果失效、重新查询 |
| 指定周期与职级 | 多条件组合过滤 |
| 继任地图 | 覆盖率、风险岗位识别 |
| 人才梯队 | 分通道供给比、断层识别 |
| 个人发展计划 | 能力差距、70-20-10 资源匹配 |
| 组织诊断 | 健康分、问题清单 |
| 无关对话 | 无关意图拦截 |

* * *

## 二十七、项目亮点

### 1. LLM 与业务逻辑解耦

大模型不参与任何打分与分类决策：

```
LLM → 理解意图 → 抽取条件 → Python 业务计算 → 数据库 → 真实结果 → LLM 汇报
```

降低幻觉对人才决策的影响。

### 2. LangGraph 智能体编排

使用 LangGraph 把意图识别、信息抽取、七个业务 Tool 与结果汇报组成工作流，
对不同意图做条件路由。

### 3. Tool 化设计

十类业务能力封装为独立 Tool（人才管理四路 + HRIS 六路），便于扩展与单独测试。

### 4. 状态机与多轮记忆

通过 LangGraph Checkpointer 维护连续对话状态；
修改条件或筛选偏好后会沿上一主题自动重新计算。

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
2. **前端可视化**：开发九宫格拖拽、继任地图、组织健康看板
3. **RAG 知识库**：接入公司人才政策、任职资格标准、发展通道手册
4. **多轮追问**：支持"为什么他被评为超级明星"这类可解释追问
5. **权限与脱敏**：按角色限制可见范围，敏感字段脱敏
6. **自动化测试**：补充 pytest 与接口自动化测试
7. **Docker 部署**：容器化 FastAPI、MySQL 与 Ollama

* * *

## 二十九、项目定位

本项目属于：

- 大模型应用开发
- Agent
- 结构化数据查询
- 人才盘点与组织发展
- HRIS 六大模块（招聘 / 薪酬福利 / 绩效 / 员工关系 / 培训 / 人力规划）
- 多轮对话

核心技术路线：

```
FastAPI
   ↓
LangGraph
   ↓
DeepSeek-R1 / Ollama 或云 API
   ↓
Python 业务逻辑
   ↓
SQLAlchemy
   ↓
MySQL / SQLite
```

项目重点体现：

- 大模型应用
- Agent 工作流
- Memory 状态管理
- Tool 调用
- 数据库查询
- 业务规则控制
- 多轮对话

* * *

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
继任联动则把"高风险在岗"与"无继任候选人"两个集合求交，取最高优先级。

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

## 三十一、HRIS 适配器六大能力域

### 能力声明

`HRISCapability` 定义六个常量，适配器通过 `capabilities` 声明自己支持哪些模块：

```python
class HRISCapability:
    RECRUITMENT = "recruitment"            # 招聘管理
    COMPENSATION = "compensation"          # 薪酬与福利
    PERFORMANCE = "performance"            # 绩效管理
    EMPLOYEE_RELATIONS = "employee_relations"  # 员工关系管理
    LEARNING = "learning"                  # 培训与开发
    WORKFORCE = "workforce"                # 人力资源规划
```

调用前用 `adapter.supports(capability)` 判定，避免打到厂商不支持的端点。

### 各模块的方法契约

| 模块 | 方法 |
| --- | --- |
| 招聘管理 | `pull_applications(req_no)` |
| 薪酬与福利 | `pull_compensation(employee_nos)` / `push_compensation(records)` |
| 绩效管理 | `push_performance_review(records)` |
| 员工关系管理 | `push_attendance(records)` / `push_leave_request(dto)` |
| 培训与开发 | `push_training_record(records)` |
| 人力资源规划 | `pull_headcount(department)` |

必选实现只有 `ping` / `get_employee` / `upsert_employee` 三个（主数据是集成前提），
其余模块未实现时抛 `NotImplementedError`，由 `supports()` 在调用前拦截。

### 本地适配器（默认）

直接读写本地 SQLite / MySQL，六大模块全部落地为库表读写。

## 三十二、SAP SuccessFactors 接入骨架

按 Employee Central OData v2 设计：

```
基础请求:
  BaseURL = https://{tenant}.api.successfactors.com
  Auth    = OAuth2 Client Credentials 或 Basic
  Header  = Authorization: Bearer <token> 或 Basic <base64(user:pass)>
  公共参数 = ?companyID=<SF 公司 ID>&$format=JSON

六模块端点映射:
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

实际人才盘点、继任安排与人员决策需要结合企业真实数据、
管理者判断、制度合规要求以及员工个人发展意愿综合做出。

本项目输出的结果不构成任何人事决策建议。
