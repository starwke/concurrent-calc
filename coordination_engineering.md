## 概念与区别
**Harness Engineering = 驾驭单个 Agent 的工程。**

Harness Engineering 可以理解为“给单个 Agent 装上工程化外骨骼”。

一个裸模型本身只是会生成文本。要让它成为能执行任务的 Agent，就需要给它配套一整套 harness：

- 明确任务目标和边界
- 提供必要上下文
- 接入工具和 API
- 设置权限和安全限制
- 记录执行过程
- 提供测试、反馈和验证
- 在失败时帮助定位原因

所以，Harness Engineering 的核心不是“让模型更聪明”，而是**通过环境、工具、上下文、权限、反馈和验证机制，让 Agent 的能力可控、可测、可复现**。



**Coordination Engineering = 协调多个 Agent 的工程。**

Coordination Engineering 可以理解为“给多个 Agent 设计组织结构和协作机制”。它关注的是：当不止一个 Agent 参与任务时，怎样做团队编排、任务分解、角色分工、通信协议、共享状态、隔离机制、故障恢复、协作流程沉淀和团队级可观测性。

当任务变复杂时，一个 Agent 往往不够。可能需要多个 Agent 分工合作：

- Planner Agent 负责拆解任务
- Research Agent 负责资料检索
- Coding Agent 负责实现
- Testing Agent 负责测试
- Review Agent 负责审查
- Manager Agent 负责调度和合并结果

这时问题就不再只是“每个 Agent 是否能干活”，而是：

- 谁来分配任务？
- Agent 之间怎么沟通？
- 共享状态放在哪里？
- 任务依赖如何管理？
- 冲突结果如何裁决？
- 某个 Agent 失败后谁来接手？
- 团队经验如何沉淀成流程？

这些就是 Coordination Engineering 要解决的问题。

所以，Coordination Engineering 的核心不是单个 Agent 的能力增强，而是**多 Agent 团队的组织、调度、通信、协作、治理和演进**。

| 对比项   | Harness Engineering                                          | Coordination Engineering                                |
| -------- | ------------------------------------------------------------ | ------------------------------------------------------- |
| 关注对象 | 单个 Agent                                                   | 多个 Agent / Agent Team                                 |
| 核心问题 | “怎么让一个 Agent 靠谱干活？”                                | “怎么让一组 Agent 高效协作？”                           |
| 工程重点 | 工具、上下文、记忆、权限、验证、反馈                         | 编排、分工、通信、冲突处理、共享状态、故障恢复          |
| 类比     | 给一个员工配好电脑、流程、工具和验收标准                     | 设计一个团队的组织结构、协作机制和项目管理体系          |
| 典型产物 | Agent运行环境、工具接口、测试脚本、权限规则、验证脚本、执行日志 | AgentTeam架构、任务调度器、通信协议、协作流程、团队记忆 |
| 目标     | 单兵可靠性                                                   | 团队协同性                                              |

一句话总结：Harness解决“单兵可靠性”；Coordination解决“团队协作性”, 未来的 AI Agent 工程，很可能不是二选一，而是两层叠加：

> 每个 Agent 都需要 Harness；多个 Agent 之间需要 Coordination。



## SubAgent VS Agent Team (以Claude为例)

### 一、SubAgents：通过隔离实现并行性

SubAgent可以理解为“主Agent临时派出去的专用助手”，通常用于处理一个相对独立的任务，比如代码审查、日志分析等。

![image-20260607153927095](./../AppData/Roaming/Typora/typora-user-images/image-20260607153927095.png)

核心机制：subagent完成任务只会将结果返回父agent，不会污染父agent的上下文。

关键约束：subagent不能生成其他子智能体，不能相互通信，每个结果必须流回父Agent。父Agent是唯一的协调者。

### 二、Agent Team: 持久 + 通信，核心[持续协作]

Agent Team是多个会话组成的协作团队，不是一个主Agent派几个助手做一次任务，而是由一个Team Lead和多个Teammates组成。每个teammate都是一个独立的实例，拥有自己的上下文、工具执行和任务状态，他们之间通过共享任务列表和消息系统相互协作。

![image-20260607154724441](./../AppData/Roaming/Typora/typora-user-images/image-20260607154724441.png)

Agent Team包含三部分：

1、Team Lead: 协调工作、分配任务、综合结果

2、Teammates: 独立的Agent实例，各自拥有自己的上下文窗口，并行工作。

3、Shared Task List：追踪待办、进行中、已完成的任务，以及任务之间的依赖关系。

其他：MailBox: 代理之前互相发消息的通道

Teammates 之间可以直接通信，不用经过 lead。一个 teammate 发消息，对方自动收到，不需要 lead 中转。任务有三个状态：pending、in progress、completed

三、对比

![image-20260607113849041](./../AppData/Roaming/Typora/typora-user-images/image-20260607113849041.png)



核心区别：一次性任务 Vs 持续协作

| 维度      | Subagents            | Agent Teams              |
| --------- | -------------------- | ------------------------ |
| 生命周期  | 短期，任务完成就消失 | 长期，持续存在           |
| 通信方式  | 只和父 Agent 通信    | Agent 之间可以直接通信   |
| 状态共享  | 无共享状态           | 共享任务列表和状态       |
| 协调方式  | 父 Agent 集中协调    | 分布式协调               |
| 适用场景  | 独立任务、并行探索   | 需要持续协商的任务       |
| Token成本 | 低，结果摘要返回     | 高，每个teammate独立实例 |

SubAgents: 任务可以独立完成，只需要最终结果。

AgentTeams：任务之间有依赖，中途需要协调
