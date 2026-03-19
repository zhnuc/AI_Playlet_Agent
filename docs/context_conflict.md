# 角色冲突与队列化回应设计（V2.0 实现稿）

## 目标

在 V1 单人串行路由的基础上，支持“一个角色同时点名多个在场角色”的冲突场景，同时继续保证：

- 主流程稳定可跑通
- 事件顺序清晰可追溯
- 角色 memory 更新顺序明确
- Working Context 仍然只基于角色可见信息构造

本设计用于指导后续代码实现，优先服务于 `story_state.py`、`scheduler.py`、`context_builder.py`、`main_loop.py`、`log_writer.py` 的改造。

---

## 一、核心结论

V2 不做真正并发，只做：

> 多目标点名 + 待回应队列 + 受控串行回应

也就是说：

- 允许角色 A 一次点名多个角色
- 系统不会同时调用多个角色 Agent
- 系统会把这些被点名角色放入一个待回应队列，按顺序逐个执行
- 队列清空后，控制权回到发起者 A

这是一种“伪并发”的戏剧表现，不是工程意义上的并行执行。

---

## 二、适用范围与非目标

### 适用范围

- 群体对峙
- 一人点名多人表态
- 冲突场景中的连续回应
- 多人围绕同一触发事件依次表态

### 本版非目标

- 不支持真正并行调用多个角色 Agent
- 不支持队列中的角色临时发起新的多人队列
- 不支持队列嵌套队列
- 不支持“多个 initiator 同时争夺控制权”

一句话说：

> 第一版 V2 只支持“一人发起，多人按队列回应，发起者收束”的固定结构。

---

## 三、术语约定

- `initiator`
  - 发起多人点名的角色，例如 A
- `responder`
  - 当前在队列中被要求回应 initiator 的角色，例如 B、C
- `pending reply queue`
  - 待回应队列，保存尚未完成回应的角色顺序
- `trigger event`
  - 触发当前队列的原始事件，通常是 initiator 刚刚说出的对白或动作

---

## 四、路由语义

### 1. 普通模式

与 V1 基本一致：

- 当前角色正常生成一轮输出
- scheduler 校验路由是否合法
- 下一轮进入单一角色

### 2. 队列模式

当角色一次点名多名角色时：

- 系统切换到 `pending_replies` 模式
- 被点名角色进入待回应队列
- 队列中的角色逐个回应 initiator
- 队列未清空前，普通自由路由暂停
- 队列清空后，控制权回到 initiator

关键约束：

> 队列模式下，路由权由队列控制器接管，不再由当前 responder 决定。

---

## 五、对当前输出格式的增量改造

为了兼容 V1，建议采用“归一化”策略，而不是一步改死所有调用。

### 角色输出推荐结构

```python
{
  "角色名": {
    "Inner_Thought": "...",
    "Action": "...",
    "Dialogue": "...",
    "next_speaker": "角色B",
    "next_speakers": ["角色B", "角色C"]
  }
}
```

### 实现约定

- V1 旧字段 `next_speaker` 继续兼容
- V2 新增 `next_speakers`
- 进入 scheduler 前统一做归一化：
  - 若只有 `next_speaker`，转成长度为 0 或 1 的列表
  - 若有 `next_speakers`，以列表为准
  - 去重、去空值、去掉当前 speaker 自己

### 第一版 V2 的推荐规则

- `next_speakers == []`
  - 视为无后继或等待上层兜底
- `len(next_speakers) == 1`
  - 走 V1 单人路由
- `len(next_speakers) > 1`
  - 进入待回应队列

这样可以最大限度减少对现有主流程的破坏。

---

## 六、运行时状态补充

建议在 `RuntimeState` 中新增一个交互控制状态。

```python
@dataclass
class InteractionState:
    mode: str = "normal"
    initiator: str | None = None
    pending_queue: list[str] = field(default_factory=list)
    trigger_event_id: str | None = None
```

### 字段含义

- `mode`
  - `normal`：普通单人路由
  - `pending_replies`：多人回应队列处理中
- `initiator`
  - 当前队列的发起者
- `pending_queue`
  - 尚未完成回应的角色顺序列表
- `trigger_event_id`
  - 触发当前队列的原始事件，用于回溯和 prompt 构造

### 为什么只需要这四个字段

因为第一版 V2 只做一层队列控制，不做嵌套、不做分支合并、不做复杂仲裁。这个状态已经足够支撑实现。

---

## 七、主流程设计

以下以 A 点名 B、C 为例。

### Step 1：A 正常发言

A 生成：

```python
{
  "Inner_Thought": "...",
  "Action": "...",
  "Dialogue": "...",
  "next_speakers": ["B", "C"]
}
```

随后：

- 正常提交事件到 `event_log`
- 正常按 `visible_to` 更新角色 `private_history`

### Step 2：scheduler 识别多人点名

如果归一化后的 `next_speakers` 长度大于 1：

- 创建 `interaction_state`
- `mode = "pending_replies"`
- `initiator = "A"`
- `pending_queue = ["B", "C"]`
- `trigger_event_id = A 本轮的主触发事件 id`

这里的“主触发事件”建议优先取：

1. `dialogue` 事件
2. 若无对话，则取 `action`
3. 若仍无，则退化为本轮最后一个事件

### Step 3：B 回应 initiator

系统从 `pending_queue` 取出 B。

B 的 prompt 要明确写入：

- 当前处于多人回应阶段
- initiator 是 A
- 你本轮必须优先回应 A
- 你的输出仍然要生成标准字段
- 但你本轮的 `next_speaker / next_speakers` 不参与主路由

B 生成后：

- 事件正常提交
- `pending_queue` 移除 B

### Step 4：C 回应 initiator

如果 `pending_queue` 还有 C：

- 下一轮固定为 C
- 不经过普通自由路由

C 的上下文在 B 提交事件之后再构造，因此：

- 若 B 的事件对 C 可见，C 可以看到
- 若 B 的事件对 C 不可见，C 不应看到

### Step 5：队列清空

当 `pending_queue == []` 时：

- `mode` 切回 `normal`
- `initiator` 清空
- `trigger_event_id` 清空
- 下一轮固定回到 A

这代表一次多人回应轮次完成。

---

## 八、Working Context 规则

V2 的核心不只是 scheduler，而是上下文构造规则要随模式切换。

### 1. normal 模式

与 V1 一致，仍使用：

- 当前场景信息
- 角色 profile
- 角色 goal
- `private_summary`
- 最近可见事件

### 2. pending_replies 模式

在 normal 模式基础上，额外注入：

- 当前 `initiator`
- 当前 `trigger_event`
- 你是被点名的 responder
- 你必须优先回应 initiator
- 你的路由字段本轮不会生效

建议在 prompt 中用硬约束写明：

> 你当前处于多人回应阶段。你必须优先回应 `{initiator}` 刚刚发起的冲突，不得转移话题，不得尝试接管主路由。

---

## 九、`visible_to` 规则

`visible_to` 在 V2 中继续保持统一语义：

> 是否可见，取决于事件本身，而不是取决于队列顺序。

这意味着：

- 后发言角色是否能看到前面角色的回应，不由“先后顺序”自动决定
- 仍然由事件的 `visible_to` 决定

### 推荐默认规则

为了保证冲突场景可读性，第一版建议：

- initiator 的触发事件，对所有被点名角色可见
- responder 的 `action` / `dialogue` 默认对 `scene_roles` 可见
- responder 的 `thought` 仍只对自己可见

这样可以最大程度复用现有事件分发逻辑。

---

## 十、scheduler 与 queue controller 的职责划分

建议把路由控制分成两层，不要混在一个函数里。

### 1. scheduler

负责：

- 归一化 `next_speaker / next_speakers`
- 校验角色是否合法
- 判断进入普通单人路由还是队列模式

### 2. queue controller

负责：

- 读取 `interaction_state`
- 决定当前 responder 是谁
- responder 完成后推进队列
- 队列清空后把控制权交还 initiator

一句话：

- 普通模式：角色提议，scheduler 裁决
- 队列模式：队列接管，角色只负责回应

---

## 十一、日志要求

为了方便调试，建议在日志中增加队列控制信息。

### 推荐新增的系统日志事件

```python
{
  "type": "queue_open",
  "initiator": "A",
  "pending_queue": ["B", "C"],
  "trigger_event_id": "e12"
}
```

```python
{
  "type": "queue_pop",
  "current_responder": "B",
  "remaining_queue": ["C"]
}
```

```python
{
  "type": "queue_close",
  "initiator": "A"
}
```

这些信息可以写入结构化日志，但不一定需要喂给模型。

---

## 十二、第一版 V2 的硬约束

为了保证实现可控，建议把以下规则写死：

1. responder 的路由字段在队列模式下忽略
2. 队列清空后，控制权一定回到 initiator
3. 不支持队列中的角色再发起新队列
4. 不支持嵌套队列
5. 队列成员必须来自当前 `scene_roles`
6. 队列成员去重后按原顺序保留

这些约束不是长期方案，但非常适合作为第一版落地边界。

---

## 十三、建议的代码改造顺序

### Phase 1：补状态结构

涉及文件：

- `story_state.py`

任务：

- 新增 `InteractionState`
- 挂到 `RuntimeState`

### Phase 2：补路由归一化和队列控制

涉及文件：

- `scheduler.py`
- `main_loop.py`

任务：

- 增加 `next_speakers` 归一化
- 增加进入队列、推进队列、关闭队列的控制逻辑

### Phase 3：补队列模式下的上下文构造

涉及文件：

- `context_builder.py`

任务：

- 支持 normal / pending_replies 两种 prompt 构造
- 给 responder 注入 initiator 和 trigger event 约束

### Phase 4：补日志与调试信息

涉及文件：

- `log_writer.py`

任务：

- 增加 queue_open / queue_pop / queue_close 记录

### Phase 5：补模型输出校验

涉及文件：

- `Agent_model.py`

任务：

- 校验 `next_speakers` 的类型是否合法
- 对 `next_speaker` 和 `next_speakers` 做统一归一化入口

---

## 十四、验收标准

满足以下条件即可认为第一版 V2 跑通：

1. A 可以一次点名多个在场角色
2. 系统不会并发调用多个角色 Agent
3. 被点名角色会按队列顺序逐个回应 A
4. responder 的输出会正常写入 `event_log` 和 `private_history`
5. 后发言 responder 是否能看到前面 responder 的内容，严格由 `visible_to` 决定
6. 队列清空后，下一轮会稳定回到 initiator
7. 结构化日志能明确反映队列打开、推进和关闭过程

---

## 十五、当前建议确认项

这版实现稿默认以下口径，如需调整，应先改这里再动代码：

1. 术语统一用“队列化回应”，不再叫“并发”
2. 第一版只支持“一人发起，多人回应，发起者收束”
3. responder 在队列模式下不拥有主路由控制权
4. 队列模式下是否可见，仍由 `visible_to` 决定
5. `next_speaker` 保持兼容，`next_speakers` 作为 V2 增量字段引入

如果以上 5 点确认无误，Codex 就可以直接按本文件进入代码实现。
