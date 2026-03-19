# 上下文管理方案（第一版讨论稿）

## 目标

本方案用于当前多角色剧情生成系统的上下文管理，服务于与 Codex 的方案讨论。第一版的目标不是追求复杂能力，而是：

* 先做出**稳定、可跑通**的版本
* 支持**每个角色维护自己的 memory**
* 保持后续扩展空间
* 设计思路尽量贴近 **LangGraph 的 state / node / routing**，但当前**不接入框架**

本阶段最重要的是先固定三件事：

1. 系统状态怎么存
2. 事件怎么写入
3. 每轮给模型喂什么上下文

---

## 一、核心思路

当前方案不再只维护一份共享历史，而是拆成三层：

### 1. Story Context（全局状态）

保存整部剧或当前场景的公共事实，是系统的统一状态底座。

### 2. Role Memory（角色私有记忆）

每个角色维护自己的 memory，只保存“该角色知道的内容”，不共享上帝视角。

### 3. Working Context（工作上下文）

每次调用模型前，为某个角色临时拼装的输入包，不作为长期状态存储。

一句话概括：

**用“全局剧情状态 + 每个角色自己的 memory + 每轮临时工作上下文”替代单一共享历史。**

---

## 二、为什么这样设计

这样设计主要解决三个问题：

### 1. 角色信息差

不同角色只能基于自己知道的事实行动，避免所有角色共享同一份完整历史。

### 2. 上下文可控

模型每次只看到与当前角色相关的必要信息，避免上下文不断膨胀。

### 3. 后续可扩展

当前方案虽然不用 LangGraph，但已经具备了：

* 统一 state
* 节点式角色执行
* 事件提交更新
* 简单路由

后续迁移框架时，不需要推翻整体设计。

---

## 三、状态结构

## 1. Story Context（全局状态）

Story Context 用来保存公共剧情信息，建议包含：

* 剧集基础设定（题材、受众、集数、logline）
* 角色卡（静态设定）
* 当前 episode / 当前 scene
* 当前场景公共信息
* 已确认剧情事实（canon facts）
* 全局事件日志（event log）

其中：

* 世界设定、角色静态设定，可直接承接现有 `global_config.py`
* 全局事件日志是唯一完整事件来源，用于追溯与回放

---

## 2. Role Memory（角色私有记忆）

每个角色各自维护一份 memory。第一版只保留最小必要字段：

* `private_history`：该角色可见事件的 `event_id` 列表
* `private_summary`：该角色当前记忆摘要
* `current_goal`：该角色当前目标
* `beliefs_about_others`：该角色对其他角色的判断

说明：

### `private_history` 只存 event_id，不存全文

原因：

* 降低 memory 本体大小
* 减少上下文冗余
* 事件全文统一从全局 `event_log` 回查
* 更方便后续做日志追溯与调试

这意味着：

* **全局 log 是唯一事件真源**
* 角色 memory 只保存“看过哪些事件”以及“压缩后的角色状态”

---

## 3. Working Context（工作上下文）

Working Context 不是长期状态，而是每次角色执行前临时构造的输入。

给某个角色的 Working Context 只包含：

* 当前场景相关的全局信息
* 该角色的人设卡
* 该角色的 `private_summary`
* 最近若干条该角色可见事件（通过 event_id 从全局 log 回查）
* 当前集 / 当前场景对该角色的任务要求
* 输出格式要求

这样可以避免每轮都把全部历史直接塞进 prompt。

---

## 四、事件机制

本方案采用**事件驱动**，而不是直接维护大段连续文本。

事件是系统中最基础的状态更新单位。建议支持以下类型：

* `dialogue`：对话
* `action`：动作
* `thought`：内心想法
* `system`：系统调度或场景切换信息

每个事件至少包含：

* `event_id`
* `step`
* `episode`
* `scene`
* `kind`
* `speaker`
* `content`
* `visible_to`

其中 `visible_to` 很关键，它决定：

> 哪些角色能把该事件写入自己的 `private_history`

---

## 五、运行流程

第一版主循环建议保持简单，分成五步：

### 1. 初始化

系统启动时：

* 从 `global_config.py` 读取世界设定、角色卡
* 初始化 `Story Context`
* 为每个角色创建初始 `Role Memory`
* 从 planner 或 episode plan 注入当前集目标与角色指令

---

### 2. 构造角色上下文

调度器选择当前发言角色后，调用统一函数构造输入：

`build_role_context(role_name, runtime_state, episode_plan)`

它负责把当前角色需要的内容整理成 Working Context，供模型生成结构化输出。

---

### 3. 角色输出结构化结果

第一版建议角色统一输出：

```python
{
  "step": 3,
  "inner_thought": "...",
  "action": "...",
  "dialogue": "...",
  "next_speaker": "角色B"  # 或 None
}
```

说明：

* 第一版使用 `next_speaker` 单值字段
* 不使用 `next_speakers: list[str]`
* 这是为了减少调度复杂度，优先保证主循环稳定

---

### 4. 提交事件并更新状态

角色输出后，统一调用：

`commit_event(runtime_state, event)`

其职责是：

1. 写入全局 `event_log`
2. 根据 `visible_to` 分发到对应角色的 `private_history`
3. 按规则更新相关角色的 `private_summary`
4. 必要时更新 `current_goal` / `beliefs_about_others`

这一步是整个上下文管理的核心更新入口。

---

### 5. 路由到下一步

根据 `next_speaker` 决定后续流程：

* 为合法角色：进入该角色下一轮执行
* 为 `None`：结束当前轮，交还上层调度器 / 场景控制器

第一版不支持：

* 一次指定多个后继角色
* 多角色并发分支
* 复杂多路互动

---

## 六、第一版 scheduler 设计

第一版 scheduler 的目标不是“智能调度剧情”，而是：

> **做一个最小的合法性裁判和兜底器，保证流程稳定。**

### 1. scheduler 职责

角色负责：

* 生成 `inner_thought / action / dialogue`
* 提议 `next_speaker`

scheduler 负责：

* 校验 `next_speaker` 是否合法
* 不合法时做最小兜底
* 必要时把控制权交回上层调度器

也就是说：

* `next_speaker` 是角色的 proposal
* scheduler 输出的是 final decision

---

### 2. 第一版约束

第一版假设：

> `next_speaker` 只能指定当前场景中、除自己外的另一个在场角色进行对话。

因此第一版的合法性规则只保留三条：

* `next_speaker` 必须存在于角色表中
* `next_speaker` 必须属于当前 scene 的在场角色
* `next_speaker` 不能等于当前 speaker 自己

如果不满足，视为不合法。

---

### 3. fallback 规则

第一版 fallback 极简化：

* 如果当前 scene 中，除了当前 speaker 之外 **只有一个其他角色**

  * 自动把那个人设为 `next_speaker`
* 如果候选角色不止一个

  * 直接返回 `None`
  * 交还上层调度器或结束本轮
* 如果没有候选角色

  * 直接返回 `None`

这样可以最大程度减少调度混乱。

---

### 4. 为什么这样做

因为第一版的目标是稳定跑通，而不是做复杂剧情控制。

所以 scheduler：

* 不再调用 LLM 做调度判断
* 不做复杂打分
* 不做多人路由
* 不负责剧情创作

它只是一个很薄的规则层。

---

## 七、事件写入规则（第一版）

为了保证系统简单可控，第一版写入规则固定如下：

### 1. 全局日志必写

所有事件都写入 `Story Context.event_log`。

### 2. 角色 memory 按可见性写入

只有出现在 `visible_to` 中的角色，才会把该事件的 `event_id` 加入自己的 `private_history`。

### 3. 内心想法默认私有

`thought` 事件默认只写给自己：

* `visible_to = [speaker]`

### 4. 对话 / 动作按当前场景参与者分发

第一版可以采用最保守规则：

* 至少 speaker 和被点名对话对象可见
* 如果场景里其他角色默认在场旁观，也可写给所有 `scene_roles`

具体可根据场景建模精度调整，但第一版建议规则尽量固定。

### 5. summary 延迟更新

不要求每条事件都立即重写摘要，可采用简单策略：

* 每轮结束更新当前角色摘要
* 或累计若干条新事件后更新一次摘要

第一版重点不是摘要质量，而是更新链路先跑通。

---

## 八、当前阶段不做的事情

为了先稳定跑通，以下能力暂不纳入第一版：

* 向量数据库 / RAG 检索
* 复杂关系图存储
* 多级长期/短期记忆检索器
* 自动重要性打分
* 正式接入 LangGraph
* 多角色并发分支
* 复杂回滚系统

这些都可以在当前状态结构稳定后逐步加入。

---

## 九、与未来 LangGraph 的衔接方式

虽然当前不接入框架，但本方案已经尽量保持与 LangGraph 一致的抽象方式：

* `RuntimeState`：对应 graph state
* `build_role_context(...)`：对应节点执行前的输入构造
* `commit_event(...)`：对应节点输出后的状态更新
* `next_speaker`：对应最简单的路由信号

因此未来如果需要迁移：

* 不需要推翻上下文结构
* 只需要把当前主循环改写为 graph 形式
* 状态 schema 与更新逻辑可以直接复用

---

## 十、建议的最小工程模块

为了方便后续实现讨论，建议至少拆成以下几个模块：

### 1. `story_state.py`

定义：

* Story Context
* Role Memory
* Event
* RuntimeState

### 2. `context_builder.py`

负责：

* `build_role_context(...)`

### 3. `event_committer.py`

负责：

* `commit_event(...)`
* memory 分发
* summary 更新

### 4. `scheduler.py`

负责：

* `next_speaker` 合法性校验
* fallback 处理

### 5. `main_loop.py`

负责：

* 选择当前 speaker
* 构造上下文
* 调用模型
* 提交事件
* 校验路由
* 推进剧情循环

---

## 十一、一句话总结

**第一版上下文管理方案的核心，是以全局事件日志为唯一真源，以角色私有 memory 维护信息差，以临时工作上下文控制每轮输入，并用最小规则化 scheduler 保证流程稳定。**

这套方案适合作为当前 baseline：

* 结构清晰
* 可直接讨论
* 易于先跑通
* 后续可平滑扩展到更复杂的 memory 与框架化编排

如果后续系统稳定，再逐步增加：

* 更精细的可见性控制
* 更可靠的 summary 策略
* 多角色分支路由
* 回滚与分支能力
* LangGraph 接入
