# 阶段 3 群聊与角色卡后端字段清单

最新修改：2026-04-13 14:11

## 0. P0 落地状态（2026-04-17）

当前分支已完成 P0 范围内的后端与前端联动（兼容旧字段，不破坏既有链路）：

- 后端快照新增字段（来源：`PlayletService.get_episode_snapshot`）：
  - `status_label`
  - `chat_messages`
  - `control_events`
  - `role_profiles`
  - `current_episode_records_by_role`
- 旧字段继续保留（如 `event_log`、`turn_trace`），前端可平滑迁移。
- 前端主页面已支持：
  - 群聊头像/角色名点击打开角色卡
  - 角色卡展示静态信息 + 当前集最近记录（thought/action/dialogue）

### 0.1 前端当前映射（P0）

| 前端展示位 | 当前读取字段 | 回退策略 |
|---|---|---|
| 群聊三段式消息 | `chat_messages[].segments[]` | 回退到 `event_log` 分组 |
| 角色卡基础信息 | `role_profiles[role_name].static_profile` | 回退到前端角色草稿 |
| 角色卡动态摘要 | `role_profiles[role_name].dynamic_profile` | 空态文案 |
| 角色卡当集记录 | `current_episode_records_by_role[role_name]` | 回退到 `chat_messages` 反推 |
| 状态栏文案 | `status_label` | 由本地状态推导 |

### 0.2 本轮未落地（仍属后续范围）

- 完整“聊天记录二级窗口”搜索筛选（关键词 + kind + 按集展开）
- 监控控制区结构化卡片（仅保留现有列表展示）
- 测试全绿（当前分支已有历史测试基线问题，见项目计划中的风险项）

说明：面向后端对接的可交付字段清单，用于统一阶段 3 群聊窗口、右下角监控控制区、角色卡和聊天记录窗口的数据口径。

## 1. 文档目标

本文档只解决一件事：

- 当前前端原型要显示什么
- 后端理论上需要提供什么字段

本文档不展开：

- 真实接口 URL 最终命名
- 存储层实现
- 搜索服务实现细节
- 关系图字段

当前只覆盖以下 4 个前端区域：

1. 主聊天窗口
2. 右下角监控控制窗口
3. 角色卡弹窗
4. 角色完整聊天记录窗口

## 2. 总体约束

### 2.1 当前页面行为约束

- 主聊天窗口按“集”组织
- 当前主聊天窗口右上角需要显示：
  - 当前集数
  - 最新推进到的轮次
- 主聊天窗口显示角色的：
  - `thought`
  - `action`
  - `dialogue`
- 主聊天窗口当前不显示导演指令
- 导演指令、监制提示、系统控制信息统一放到右下角“监控控制”窗口

### 2.2 角色卡约束

角色卡分为两块：

- 角色基本信息
- 角色聊天历史

其中角色基本信息再分为：

- 静态字段
- 动态字段

### 2.3 历史记录约束

- 角色卡首屏支持查看当集内容
- 点击“聊天记录”后查看完整历史会话
- 完整历史按“集”分组
- 支持关键词搜索
- 支持按 `thought / action / dialogue` 筛选

## 3. 字段分层

当前建议把后端提供的数据分成 4 层：

1. 顶部与当前集状态层
2. 主聊天事件层
3. 角色档案层
4. 角色历史记录层

## 4. 顶部与当前集状态层

这部分服务于：

- 页面顶部状态栏
- 主聊天窗口右上角状态信息

建议字段：

| 字段名 | 类型 | 必填 | 说明 | 前端用途 |
|---|---|---:|---|---|
| `session_id` | `string` | 是 | 当前会话唯一标识 | 顶部状态栏 |
| `run_mode` | `string` | 是 | `planned` / `free` | 顶部状态栏 |
| `status_label` | `string` | 是 | 当前状态文案，如“推演进行中” | 顶部状态栏 |
| `current_episode` | `number` | 是 | 当前正在查看或运行的集数 | 主聊天窗口右上角 |
| `current_turn` | `number` | 是 | 当前集已推进到的最新轮次 | 主聊天窗口右上角 |
| `current_scene` | `string` | 是 | 当前场景名称 | 聊天消息和角色卡上下文 |

建议最小结构：

```json
{
  "session_id": "sess_xxx",
  "run_mode": "planned",
  "status_label": "推演进行中",
  "current_episode": 2,
  "current_turn": 18,
  "current_scene": "直播后台"
}
```

## 5. 主聊天窗口字段

### 5.1 目标

主聊天窗口展示的是当前集聊天流。

它需要满足：

- 角色消息按时间顺序追加
- 角色消息包含 `thought / action / dialogue`
- 用户滚动查看上下文
- 不混入导演指令

### 5.2 消息层建议字段

建议后端为前端提供 `chat_messages[]`。

每条记录建议字段如下：

| 字段名 | 类型 | 必填 | 说明 | 前端用途 |
|---|---|---:|---|---|
| `event_id` | `string` | 是 | 单条事件唯一标识 | 列表 key、历史追溯 |
| `episode` | `number` | 是 | 所属集数 | 校验当前集、历史分组 |
| `scene` | `string` | 是 | 所属场景名 | 消息元信息 |
| `turn` | `number` | 是 | 所属轮次 | 消息元信息、右上角最新轮次 |
| `speaker_id` | `string` | 是 | 发言角色唯一标识 | 关联角色卡 |
| `speaker_name` | `string` | 是 | 发言角色名称 | 群聊消息头部 |
| `kind` | `string` | 是 | `thought` / `action` / `dialogue` | 分段显示 |
| `content` | `string` | 是 | 事件文本内容 | 消息正文 |

### 5.3 前端分组方式

由于主聊天 UI 会把同一角色同一轮内的 `thought / action / dialogue` 合并显示，因此后端可以有两种支持方式：

#### 方案 A：后端返回扁平事件流

前端按以下规则自己分组：

- `episode`
- `turn`
- `speaker_id`

这是最薄方案。

#### 方案 B：后端直接返回已合并的聊天组

建议结构：

```json
{
  "chat_messages": [
    {
      "message_group_id": "msg_001",
      "episode": 2,
      "scene": "直播后台",
      "turn": 18,
      "speaker_id": "char_linruoxue",
      "speaker_name": "林若雪",
      "segments": [
        { "kind": "thought", "content": "..." },
        { "kind": "action", "content": "..." },
        { "kind": "dialogue", "content": "..." }
      ]
    }
  ]
}
```

当前从前端实现成本看，更推荐 `方案 B`。

## 6. 右下角监控控制窗口字段

### 6.1 目标

该区域显示：

- 导演指令
- 监制 / 监控提示
- 必要的系统控制信息

该区域当前不负责：

- 完整控制表单回填
- 复杂回档参数展示

### 6.2 建议字段

建议后端提供 `control_events[]`。

| 字段名 | 类型 | 必填 | 说明 | 前端用途 |
|---|---|---:|---|---|
| `event_id` | `string` | 是 | 控制事件唯一标识 | 列表 key |
| `episode` | `number` | 是 | 所属集数 | 与主聊天保持同步 |
| `turn` | `number` | 是 | 关联轮次 | 辅助定位 |
| `source_type` | `string` | 是 | `director` / `monitor` / `system` | 区分卡片样式 |
| `title` | `string` | 否 | 控制标题 | 右下角卡片头部 |
| `content` | `string` | 是 | 指令或观察正文 | 右下角卡片正文 |
| `target_role_id` | `string` | 否 | 目标角色 ID | 可用于后续高亮或筛选 |
| `target_role_name` | `string` | 否 | 目标角色名 | 可直接显示 |

建议结构：

```json
{
  "control_events": [
    {
      "event_id": "ctrl_001",
      "episode": 2,
      "turn": 18,
      "source_type": "director",
      "title": "导演指令",
      "content": "让林若雪下一句先抛证据，不做解释。",
      "target_role_id": "char_linruoxue",
      "target_role_name": "林若雪"
    }
  ]
}
```

## 7. 角色卡字段

### 7.1 目标

点击角色头像后，角色卡展示两类信息：

1. 静态基本信息
2. 动态角色状态

### 7.2 静态字段

这部分尽量跨集稳定。

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `character_id` | `string` | 是 | 角色唯一标识 |
| `name` | `string` | 是 | 角色名称 |
| `age` | `number` | 否 | 年龄 |
| `gender` | `string` | 否 | 性别 |
| `identity` | `string` | 是 | 角色身份 |
| `role_position` | `string` | 否 | 如 `female_lead_1` / `supporting` |
| `role_type` | `string` | 否 | 如 `主角` / `反派` / `配角` |
| `appearance_tags` | `string[]` | 否 | 外形标签 |
| `personality_tags` | `string[]` | 否 | 性格标签 |

### 7.3 动态字段

这部分会随着剧情推进不断变化。

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `current_goal` | `string` | 否 | 当前目标 |
| `beliefs_about_others` | `object` | 否 | 对其他角色的判断 |
| `unresolved_hook` | `string` | 否 | 当前未解决钩子 |
| `episode_digest_public` | `string` | 否 | 当前集公开摘要 |
| `episode_digest_private` | `string` | 否 | 当前集私有摘要 |

建议角色卡数据结构：

```json
{
  "character_id": "char_linruoxue",
  "static_profile": {
    "name": "林若雪",
    "age": 24,
    "gender": "女",
    "identity": "林家真千金，重生归来",
    "role_position": "female_lead_1",
    "role_type": "主角",
    "appearance_tags": ["冷艳", "黑长发"],
    "personality_tags": ["克制", "锋利"]
  },
  "dynamic_profile": {
    "current_goal": "让董事会先看到证据",
    "beliefs_about_others": {
      "char_guhanting": "暂时中立，但在观察局势",
      "char_qinman": "会优先争夺舆论主动权"
    },
    "unresolved_hook": "财务总监是否参与篡改协议"
  }
}
```

## 8. 角色卡首屏“当集聊天历史”字段

### 8.1 目标

角色卡首屏只展示该角色在当前集内的聊天记录。

### 8.2 建议字段

建议后端提供 `recent_records[]` 或 `current_episode_records[]`。

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `event_id` | `string` | 是 | 唯一标识 |
| `episode` | `number` | 是 | 当前集数 |
| `scene` | `string` | 是 | 场景名 |
| `turn` | `number` | 是 | 所属轮次 |
| `kind` | `string` | 是 | `thought` / `action` / `dialogue` |
| `content` | `string` | 是 | 内容正文 |

建议结构：

```json
{
  "character_id": "char_linruoxue",
  "current_episode_records": [
    {
      "event_id": "evt_2001",
      "episode": 2,
      "scene": "直播后台",
      "turn": 18,
      "kind": "dialogue",
      "content": "你要直播，那就别删掉开场前那通电话。"
    }
  ]
}
```

## 9. 角色完整聊天记录窗口字段

### 9.1 目标

点击“聊天记录”后，展示该角色完整历史会话。

要求：

- 按集分组
- 支持关键词搜索
- 支持按 `kind` 筛选

### 9.2 最小记录字段

单条记录至少需要：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `event_id` | `string` | 是 | 唯一标识 |
| `episode` | `number` | 是 | 所属集数 |
| `scene` | `string` | 是 | 场景名 |
| `turn` | `number` | 是 | 所属轮次 |
| `kind` | `string` | 是 | `thought` / `action` / `dialogue` |
| `content` | `string` | 是 | 内容正文 |

### 9.3 推荐返回结构

建议后端直接按集分组返回：

```json
{
  "character_id": "char_linruoxue",
  "history_by_episode": [
    {
      "episode": 2,
      "records": [
        {
          "event_id": "evt_2001",
          "scene": "直播后台",
          "turn": 18,
          "kind": "dialogue",
          "content": "你要直播，那就别删掉开场前那通电话。"
        }
      ]
    },
    {
      "episode": 1,
      "records": [
        {
          "event_id": "evt_1008",
          "scene": "董事会会议室",
          "turn": 11,
          "kind": "dialogue",
          "content": "今天这份协议，我不签。"
        }
      ]
    }
  ]
}
```

## 10. 后端最小可交付清单

如果后端要支持前端先开始联调，最小需要提供以下 4 组数据：

1. `session_meta`
   - `session_id`
   - `run_mode`
   - `status_label`
   - `current_episode`
   - `current_turn`
   - `current_scene`

2. `chat_messages`
   - 当前集聊天流
   - 至少能支持 `thought / action / dialogue`

3. `role_profile`
   - 静态字段
   - 动态字段

4. `role_history`
   - 当前集记录
   - 完整历史记录

## 11. 当前推荐的字段优先级

### P0：没有这些字段就无法联调

- `session_id`
- `run_mode`
- `status_label`
- `current_episode`
- `current_turn`
- `chat_messages[]`
- `character_id`
- `speaker_id`
- `speaker_name`
- `turn`
- `kind`
- `content`

### P1：角色卡首屏强依赖

- `name`
- `age`
- `gender`
- `identity`
- `role_position`
- `appearance_tags`
- `personality_tags`
- `current_goal`
- `beliefs_about_others`

### P2：完整历史窗口增强

- `history_by_episode[]`
- `scene`
- `event_id`
- `target_role_id`
- `target_role_name`
- `unresolved_hook`

## 12. 当前建议

前端如果要尽快进入真实联调，建议后端先优先落以下两块：

1. 当前集聊天流
2. 单角色资料 + 历史记录

这样就能先把：

- 主聊天窗口
- 角色卡
- 聊天记录窗口

三块核心能力接起来。
