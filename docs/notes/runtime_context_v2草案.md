# Runtime Context V2 草案

这份草案用于明确短剧创作 Agent 在运行时的上下文分层、字段结构和裁剪原则。

目标不是直接替代现有实现，而是作为后续重构的讨论基线，用来统一：

- `Planner` 到底输出什么
- `Beat / Controller` 到底负责什么
- 角色 Agent 每轮到底应该看到什么
- 哪些信息属于长期记忆，哪些信息只属于当前集，哪些信息只属于当前轮


## 1. 设计目标

当前运行时上下文的主要问题不是“信息不足”，而是“信息分层不清 + 集内压缩失效”，导致：

- prompt 随轮次线性膨胀
- 角色重复消费旧事件，而不是推进新剧情
- `Planner` 输出过细，开始替 runtime 写戏
- `Beat` 只是提示器，不足以承担上下文裁剪和结束判定
- 集末摘要过重，但集内缺少滚动摘要

`runtime_context_v2` 的目标是：

- 用户可见的大纲保持精简
- runtime 私有的 beat / controller 保持结构化
- 角色 prompt 保持固定层级，不随轮次失控膨胀
- 集内旧历史不再原文重放
- 结束权收回到 controller，而不是角色直接决定


## 2. 总体架构

运行时上下文拆成 6 层：

1. `Identity Layer`
2. `Season Layer`
3. `Episode Layer`
4. `Scene State Layer`
5. `Control Layer`
6. `Output Contract`

其中：

- `Planner Output` 给用户看
- `Episode Beats` 给 runtime / controller 看
- `Runtime Context` 给角色 Agent 看


## 3. Planner Output V2

`Planner` 只负责用户可读、可审的大纲骨架，不承担运行时细节规划。

### 3.1 字段定义

```json
{
  "episodes": [
    {
      "episode_number": 1,
      "title": "真假千金第一次正面交锋",
      "global_plot": "真千金回归，当众撕开假千金与渣男的第一层伪装。",
      "place": "家宴现场",
      "scene_roles": ["林若雪", "顾寒霆", "林白莲"],
      "core_conflict": "林若雪要夺回身份与话语权，林白莲试图继续维持既得位置。",
      "hook": "林若雪抛出一份足以动摇林家的关键证据。",
      "first_speaker": "林若雪",
      "character_directives": {
        "林若雪": "主动夺回场面控制权",
        "顾寒霆": "优先稳场并压制风险",
        "林白莲": "伪装无辜并转移焦点"
      }
    }
  ]
}
```

### 3.2 约束原则

- `global_plot` 只写本集主线，不写完整桥段
- `core_conflict` 只写冲突本质，不写动作编排
- `hook` 只写本集末尾钩子，不写具体台词
- `character_directives` 只允许一句目标性描述，不允许扩写为完整场景设计


## 4. Episode Beats V2

`Episode Beats` 是 runtime 私有结构，用于把用户大纲转成可执行节奏。

### 4.1 字段定义

```json
{
  "episode_number": 1,
  "beats": [
    {
      "beat_id": "b1",
      "label": "身份亮相",
      "goal": "让主要冲突公开化",
      "must_land": "所有在场角色都意识到林若雪不是来示弱的",
      "allowed_speakers": ["林若雪", "林白莲"],
      "exit_condition": "有人被迫正面回应林若雪的身份或来意",
      "fallback_push": "停止铺垫，直接公开挑明关系"
    },
    {
      "beat_id": "b2",
      "label": "对抗升级",
      "goal": "把情绪冲突升级为利益冲突",
      "must_land": "至少一方暴露真实动机",
      "allowed_speakers": ["林白莲", "顾寒霆", "林若雪"],
      "exit_condition": "场面已无法维持表面和平",
      "fallback_push": "引入利益、证据、身份、站队"
    },
    {
      "beat_id": "b3",
      "label": "钩子落地",
      "goal": "落下本集悬念",
      "must_land": "关键证据或关键信息被明确抛出",
      "allowed_speakers": ["林若雪", "顾寒霆"],
      "exit_condition": "观众已明确下一集的问题",
      "fallback_push": "不要继续争吵，直接亮证据或公开立场"
    }
  ]
}
```

### 4.2 Beat 层职责

- 将 `planner_output` 转为 runtime 可执行节奏
- 给 controller 提供当前目标和卡顿时的修复依据
- 为结束判定提供“是否已走到 hook beat”的结构条件

### 4.3 Beat 层非职责

- 不直接写对白
- 不替角色决定具体动作
- 不直接作为用户主视图显示


## 5. Runtime Context V2

角色 Agent 每轮看到的上下文固定拆成 6 层。

```json
{
  "identity_layer": {},
  "season_layer": {},
  "episode_layer": {},
  "scene_state_layer": {},
  "control_layer": {},
  "output_contract": {}
}
```


## 6. Identity Layer

`Identity Layer` 是第一阶段角色卡就应该确定的稳定人设层。

### 6.1 字段定义

```json
{
  "role_name": "林若雪",
  "role_type": "主角",
  "identity": "真千金",
  "public_persona": "冷静、强势、不轻易示弱",
  "speaking_style": "短句、直接、压迫感强",
  "core_desire": "夺回身份、产业和场面控制权",
  "bottom_line": "不能再次被羞辱或被夺走正当身份",
  "taboo": "不主动示弱，不轻易解释自己"
}
```

### 6.2 约束原则

- 只放长期稳定的人设
- 不放本集目标
- 不放当前现场状态
- 最好控制在 6 至 8 个字段


## 7. Season Layer

`Season Layer` 用于跨集承接。

### 7.1 字段定义

```json
{
  "carryover_summary": "上一集林若雪当众公开质疑林白莲身份，并逼迫顾寒霆站队。",
  "beliefs_about_others": {
    "林白莲": "极度擅长装弱和操控他人",
    "顾寒霆": "更在意局面控制而非真相"
  },
  "unresolved_hook": "顾寒霆是否提前知道林白莲身份有问题？"
}
```

### 7.2 约束原则

- `carryover_summary` 只保留上集最影响下一集行动的事实
- `beliefs_about_others` 每个角色一句话足够
- `unresolved_hook` 只保留最值钱的一条悬念


## 8. Episode Layer

`Episode Layer` 是本集任务层。

### 8.1 字段定义

```json
{
  "episode_number": 1,
  "episode_objective": "夺回第一轮场面控制权",
  "core_conflict": "身份、利益与站队公开对撞",
  "role_episode_goal": "迫使对方失去体面反击空间",
  "current_beat": {
    "label": "对抗升级",
    "goal": "把情绪冲突升级为利益冲突",
    "must_land": "至少一方暴露真实动机",
    "exit_condition": "场面已无法维持表面和平"
  }
}
```

### 8.2 约束原则

- 角色只需要看到当前 beat，不需要看到完整 beat 列表
- 这一层负责“这集要做什么”，不负责“现场刚刚发生了什么”


## 9. Scene State Layer

`Scene State Layer` 是最需要严格做轻量化的层。

### 9.1 推荐窗口

推荐只保留：

- 最近 3 到 5 个有效交换
- 当前必须回应的一个触发点
- 一句当前张力说明
- 如有多人点名，再给出 queue state

### 9.2 字段定义

```json
{
  "recent_public_exchanges": [
    "林若雪当众质疑林白莲身份",
    "林白莲哭诉自己只是无辜受害者",
    "顾寒霆要求所有人先冷静"
  ],
  "latest_trigger": "林白莲刚把焦点从身份争议转到情感绑架",
  "tension_state": "场面表面克制，但已经进入公开撕破脸边缘",
  "queue_state": {
    "mode": "pending_replies",
    "initiator": "林若雪",
    "you_are_responding_to": "林若雪",
    "allowed_action": "直接回应，不转移话题"
  }
}
```

### 9.3 约束原则

- `recent_public_exchanges` 默认 3 条，最多 5 条
- 不应把本集全部事件原文继续堆进来
- `thought` 不进入公共 `scene_state_layer`
- 若角色需要私有判断，应先压成一句短的角色视角结论，而不是回放私有事件全文


## 10. Control Layer

`Control Layer` 只放一次性调控信息。

### 10.1 字段定义

```json
{
  "director_instruction": "下一轮不要解释，直接逼对方表态",
  "repair_hint": "当前 beat 还没落到真实动机暴露",
  "end_pressure": "若关键证据已落地，可申请本集收束",
  "monitor_note": null
}
```

### 10.2 约束原则

- `director_instruction` 用完即失效
- `repair_hint` 只在偏航、停滞、重复时注入
- `monitor_note` 可选，现阶段可以关闭
- 这一层不写入长期 memory


## 11. Output Contract

`Output Contract` 是角色输出的协议层。

### 11.1 字段定义

```json
{
  "allowed_next_speakers": ["林白莲", "顾寒霆", "end_request"],
  "end_allowed": false,
  "response_schema": {
    "Inner_Thought": "string",
    "Action": "string",
    "Dialogue": "string",
    "next_speakers": ["string"]
  }
}
```

### 11.2 约束原则

- 角色不能直接决定结束
- `end` 建议改为 `end_request`
- 是否真正结束由 controller 裁决


## 12. Controller / 中间编辑层

中间编辑层建议承担 4 个职责：

1. 把 `planner_output` 转成 `episode_beats`
2. 每轮后判断当前 beat 是否完成
3. 在停滞或偏航时生成 `repair_hint`
4. 裁决 `end_request` 是否允许生效

### 12.1 状态结构示例

```json
{
  "beat_state": {
    "current_beat_index": 1,
    "status": "active",
    "stall_count": 2,
    "completion_signals": ["出现站队", "暴露真实动机"]
  },
  "end_decision": {
    "role_requested_end": false,
    "hook_landed": false,
    "can_end": false,
    "reason": "当前还没落下本集钩子"
  }
}
```

### 12.2 Controller 的裁决原则

controller 应当综合判断：

- 当前 beat 是否完成
- hook 是否落地
- 情绪是否进入可切点
- 是否接近安全上限

角色只能“申请结束”，controller 才能“批准结束”。


## 13. 轻量化硬规则

建议将运行时上下文约束为以下硬规则：

- `Identity Layer` 不超过 250 tokens
- `Season Layer` 不超过 250 tokens
- `Episode Layer` 只保留当前 beat，不给完整 beat 列表
- `Scene State Layer` 只保留最近 3 至 5 个有效交换
- `Control Layer` 只保留当前轮有效提示
- 本集旧历史不再全文回放

真正关键的是：

- 需要引入 `episode_digest`
- 集内持续更新，而不是只在集末生成 summary


## 14. Episode Digest 建议

当前集内应增加一份滚动摘要，例如：

```json
{
  "episode_digest": {
    "public_progress": "林若雪已经公开挑明身份冲突，林白莲尝试通过情感绑架转移焦点，顾寒霆两次出手稳场。",
    "role_private_take": "林若雪判断林白莲已经开始慌乱，但顾寒霆仍优先保护局面而非真相。",
    "open_threads": [
      "顾寒霆是否会继续强行控场",
      "林若雪是否会直接亮出证据"
    ]
  }
}
```

### 14.1 使用原则

- 每 3 至 4 轮更新一次
- 或在 beat 切换时更新一次
- 更新后，旧事件原文从 prompt 中退出
- 角色下一轮只吃 `episode_digest + tail_events`


## 15. 讨论结论

当前运行时需要从“事件堆叠式 prompt”转向“固定层 + 滚动摘要 + 短窗口现场状态”。

具体结论如下：

- `Planner` 只做用户可审的大纲
- `Beat / Controller` 只做 runtime 节奏与结束裁决
- `Identity Layer` 对应第一阶段角色卡
- `Scene State Layer` 应当非常短，推荐 3 至 5 个有效交换
- `Control Layer` 只保留临时调控，不进入长期记忆
- `Output Contract` 负责机械协议，不负责剧情推进
- 集内旧历史必须被 `episode_digest` 替代，而不是持续原文堆叠


## 16. 后续实现优先级建议

建议按以下顺序实施：

1. 缩 `Planner Output`
2. 正式引入 `episode_beats_v2`
3. 定义 `runtime_context_v2`
4. 增加 `episode_digest`
5. 将结束权收回 controller

