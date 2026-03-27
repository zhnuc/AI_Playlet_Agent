对，我同意你的判断。现在更合理的方向应该是：

- `Planner` 给用户看，所以要精简
- `beat / 中间编剧层` 给运行时看，所以要结构化
- `max_turns` 不该直接决定“本集结束”，而该退化成“安全上限”
- 上下文结构值得重构，而且最好按“固定层 + 动态层”拆开

**Planner**
你现在的 `Planner` 输出确实太细了，细到开始替 runtime 写戏了。像 [prompt.py](c:/Users/haonan_zhang/Desktop/AI_PLAY/AI_Playlet_Agent/prompt.py) 现在要求的 `character_directives`、`plot_twist_or_hook` 经常已经接近“半个场景脚本”。

更合理的是让 `Planner` 只保留用户可读的分集骨架，比如：
- `episode_number`
- `title`
- `global_plot`
- `place`
- `scene_roles`
- `core_conflict`
- `hook`
- `first_speaker`

`character_directives` 也可以保留，但要压缩成一句目标，而不是写成详细动作计划。

**中间编剧层**
它不应该“再写一遍完整情节”，而应该做两件事：

1. 演绎前把单集变成 `beats`
例如：
- `beat_1`: 主角亮身份
- `beat_2`: 反派卖惨转移焦点
- `beat_3`: 男主强行控场
- `beat_4`: 录音钩子落地

每个 beat 只需要：
- `goal`
- `must_land`
- `allowed_speakers`
- `exit_condition`
- `fallback_push`

2. 演绎中调控
不是每轮都重写 prompt，而是在 beat 卡住、重复、偏航时注入“修复性提示”。
这个提示更像：
- 当前还没完成 `must_land`
- 下一轮优先把证据拿出来
- 不要继续重复争吵
- 把发言权切给某个角色

所以它是“轻规划 + 过程调控”，不是“第二次写剧本”。

**运行时怎么按 beat 推进**
我建议不是让角色自己凭空自由推进，而是让 runtime 多一个 `BeatState`：

- `current_beat_index`
- `beat_status = pending | active | satisfied | failed`
- `beat_completion_signals`
- `stall_count`

每轮后检查：
1. 本轮事件是否命中当前 beat 的 `must_land`
2. 如果命中，切下一个 beat
3. 如果连续几轮没推进，触发 `beat nudger`
4. 如果到最后一个 beat 且 hook 已落地，才允许自然结束

也就是说，结束不是看“聊了几轮”，而是看“beat 走完没有”。

**谁决定这一集结束**
现在代码里是两层：
- 角色自己输出 `end`
- 然后 [main_loop.py](c:/Users/haonan_zhang/Desktop/AI_PLAY/AI_Playlet_Agent/main_loop.py) 里的 `should_end_episode(...)` 再判一次
- 以及 `max_turns` 可以硬切
- `monitor_agent` 还能 `cut`

这套现在太分散了。

更合理的是统一成：
- 主决定者：`episode controller / 中间编剧层`
- 角色可以提 `end_request`
- monitor 可以提 `cut_suggestion`
- 但最终是否结束，由 controller 判断：
  - 当前 beat 是否完成
  - hook 是否落地
  - 情绪是否收束到可切点
  - 是否已接近安全上限

这样角色不再直接“决定剧终”，而只是“申请收束”。

**max_turns 要不要保留**
要保留，但不该是当前这个硬逻辑。

现在 [main_loop.py](c:/Users/haonan_zhang/Desktop/AI_PLAY/AI_Playlet_Agent/main_loop.py) 里是：
- 一到 `current_turn >= max_turns`
- 直接 `finalize("max_turns_reached", ...)`

这确实太硬了。

更合理的是：
- 把 `max_turns` 改名成 `turn_budget` 或 `soft_limit`
- 作为传给中间编剧层的预算指标
- 到预算附近时，优先触发收束策略
- 实在收不住，再用 `hard_cap` 兜底

也就是两层：
- `soft_limit`: 给中间编剧层参考
- `hard_cap`: 防死循环

这样才符合产品语义。

**现在的上下文结构有什么问题**
你现在的角色 prompt 在 [context_builder.py](c:/Users/haonan_zhang/Desktop/AI_PLAY/AI_Playlet_Agent/context_builder.py) 里，已经把很多东西塞在一起了：

- 全局故事核
- 当前集信息
- 当前角色卡
- 本集 directive
- 跨集摘要
- 对他人的判断
- unresolved hook
- 当前集 private summary
- 未压缩旧事件
- tail events
- director / monitor 注入
- routing rules
- queue mode 说明

这套最大的问题不是“信息少”，而是“分层不清”。

我建议重构成 6 块，固定顺序，不混用：

1. `Identity Layer`
角色是谁，只含稳定人设
- role profile
- speaking style
- core desire
- taboo / bottom line

2. `Season Layer`
跨集承接
- carryover_summary
- beliefs_about_others
- unresolved_hook

3. `Episode Layer`
本集目标
- episode objective
- current episode arc
- current beat
- beat must_land

4. `Scene State Layer`
当前现场事实
- visible event tail
- current tension
- latest trigger event
- pending queue / initiator

5. `Control Layer`
外部调控
- director instruction
- monitor suggestion
- repair hint
- ending pressure

6. `Output Contract`
只保留 schema 和 routing 规则
- allowed next speakers
- whether end is allowed
- output JSON schema

这样做的好处是：
- 模型知道什么是“长期身份”
- 什么是“本集目标”
- 什么是“当前必须完成的 beat”
- 什么只是临时注入的修复提示

**我对你现在这套的直接建议**
如果要重构，我建议按下面顺序来，不要一次推翻全部：

1. 缩 `Planner` schema
让它只做“用户可读骨架”

2. 增加 `episode_beats`
由中间编剧层生成给 runtime 使用，不给用户主视图

3. 重构 [context_builder.py](c:/Users/haonan_zhang/Desktop/AI_PLAY/AI_Playlet_Agent/context_builder.py)
把 prompt 改成我上面那 6 层结构

4. 改 [main_loop.py](c:/Users/haonan_zhang/Desktop/AI_PLAY/AI_Playlet_Agent/main_loop.py)
把 `max_turns` 从“直接结束条件”改成：
- soft limit 提示
- hard cap 兜底

5. 把结束权收回给 controller
角色只能申请结束，不能直接决定结束

如果你愿意，我下一步可以直接帮你写一版新的 schema，具体到：
- `planner_output_v2`
- `episode_beats`
- `runtime_context_v2`
- `end_decision` 规则  
这样你就可以直接拿去改代码。