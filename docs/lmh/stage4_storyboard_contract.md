# 阶段4A：分镜生成接口契约

更新时间：2026-04-17

## 1. 目标
- 将已完成推演的当前集事件，转换为结构化分镜（shots）。
- 输出可直接用于：
  - 前端分镜列表展示
  - 文生图/视频提示词输入（prompt_draft）
  - 导出 JSON

## 2. 接口

### 2.1 生成分镜
- 方法：`POST /sessions/{session_id}/storyboard/generate`
- Body：
```json
{
  "force_fallback": false
}
```
- 说明：
  - `force_fallback=true`：跳过 AI，直接规则拆分。
  - `force_fallback=false`：AI 优先，失败自动回退规则。

- 响应：
```json
{
  "storyboard": {
    "episode": 1,
    "scene": "董事会会议室",
    "source": "ai",
    "shots": [
      {
        "shot_id": "S01",
        "turn": 1,
        "speaker": "林若雪",
        "shot_type": "CU",
        "camera_move": "push",
        "duration_sec": 3,
        "visual": "画面描述",
        "dialogue_focus": "对白焦点",
        "sound": "环境音",
        "prompt_draft": "可用于文生图/视频的提示词"
      }
    ]
  }
}
```

### 2.2 导出结果（已并入分镜）
- 方法：`POST /sessions/{session_id}/export`
- 响应新增字段：`storyboard`

## 3. 字段规范

### 3.1 枚举字段
- `shot_type` 允许值：`WS/MS/CU/OTS/ECU`
- `camera_move` 允许值：`static/push/pull/pan/tilt/handheld`

### 3.2 自动纠偏
后端会将 AI 的非标准表达自动归一：
- `特写/close/closeup` -> `CU`
- `中景/medium` -> `MS`
- `全景/远景/wide` -> `WS`
- `过肩/over the shoulder` -> `OTS`
- `推进` -> `push`
- `拉远` -> `pull`
- `平移/摇镜` -> `pan`
- `俯仰` -> `tilt`
- `手持` -> `handheld`
- 无法识别时：`shot_type=MS`，`camera_move=static`

## 4. 回退策略
- AI 请求异常、JSON 结构异常或 shots 为空时，自动使用规则兜底。
- 兜底源标识：`source=fallback`。
- AI 失败回退时附加：`ai_failed=true`。

## 5. 前端约定
- 分镜展示使用 `state.storyboardPayload`。
- 导出 JSON 统一包含 `storyboard` 字段（优先使用最新分镜结果）。

## 6. 下一步建议（阶段4B）
- 增加 `style_pack`（镜头风格包）影响 `shot_type/camera_move/prompt_draft`。
- 增加 `seed` 与 `continuity_tags`，用于跨镜头风格一致性。
- 增加 `character_visual_lock`，固定角色外观关键词。
