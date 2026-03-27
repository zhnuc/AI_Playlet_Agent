# AI Playlet Agent

一个短剧多智能体创作系统，包含：
- 后端 API（FastAPI）
- 前端创作控制台（模式选择 / 大纲 / 群聊式推演 / 导出）
- 运行时引擎（会话、轮次推进、导演指令、监制观察、导出）

## 1. 技术栈

- Python 3.11
- FastAPI + Uvicorn
- OpenAI Python SDK（兼容 OpenAI 风格接口）
- 原生前端（HTML/CSS/JS）

## 2. 项目结构

```text
AI_Playlet_Agent/
├─ api.py                      # 兼容入口：uvicorn api:app
├─ backend/
│  └─ app_factory.py           # FastAPI 路由组装
├─ runtime/                    # 运行时核心（session engine / turn executor 等）
├─ frontend/
│  ├─ index.html
│  ├─ styles.css
│  ├─ app.js
│  └─ js/
│     ├─ config.js
│     ├─ bind-events.js
│     ├─ runtime-actions.js
│     └─ workflow-mode.js
├─ playlet_service.py          # 会话服务层
├─ Agent_model.py              # 模型调用封装（planner/role/summary）
├─ input_adapter.py            # runtime config 校验 + free 模式最小 planner 输出
├─ main_loop.py                # 兼容导出入口（核心实现在 runtime/）
├─ docs/
└─ tests/
```

## 3. 环境变量

在项目根目录创建 `.env`（或使用系统环境变量）：

```env
base_url=你的模型网关地址
api_key=你的密钥
model=你的模型名
```

说明：
- 后端在启动时会读取上述变量初始化模型客户端。
- 缺失任意字段会导致模型初始化失败（500）。

## 4. 安装与启动

## 4.1 安装依赖

```bash
pip install -U fastapi uvicorn openai python-dotenv
```

或按 `pyproject.toml` 使用你自己的环境管理方式安装。

## 4.2 启动 API

在 `AI_Playlet_Agent` 根目录执行：

```bash
python -m uvicorn api:app --host 0.0.0.0 --port 8013
```

访问：
- 健康检查：`/health`
- 前端页面：`/ui/`

## 5. 主要运行模式

## 5.1 大纲驱动（planned）

典型顺序：
1. `POST /sessions/planned`
2. `POST /sessions/{id}/outline/generate`
3. `POST /sessions/{id}/outline/approve`
4. `POST /sessions/{id}/episode/start`
5. `POST /sessions/{id}/episode/step`（循环）

注意：
- planned 模式必须先通过 `outline/approve`，否则 `episode/start` 会返回 400。

## 5.2 自由开场（free）

`POST /sessions/free` 时后端会基于输入构造“最小可运行 planner_output”，直接可开演。

说明：
- 这个最小 planner 输出是规则生成，不是 planner 模型产出。
- 适合快速开场试戏，不经过完整大纲审核。

## 6. 一句话智能生成接口

新增接口（模型调用）：
- `POST /assist/one-line/background`
- `POST /assist/one-line/role`

## 6.1 一句话背景

输入：
```json
{ "text": "一句话背景描述" }
```

输出（示例）：
```json
{
  "result": {
    "genre": "职场博弈",
    "scene": "董事会会议室",
    "logline": "......",
    "expected_episodes": 5
  }
}
```

## 6.2 一句话角色（多角色）

输入：
```json
{ "text": "末日少女、中二少年、冷酷男" }
```

输出（示例）：
```json
{
  "result": {
    "roles": [
      { "name": "...", "role_position": "supporting", "gender": "女", "age": 20, "identity": "...", "appearance_tags": ["..."], "personality_tags": ["..."], "catchphrase": "..." }
    ]
  }
}
```

前端行为：
- 一句话角色现在是“追加角色卡”，不覆盖已有角色。
- 接口失败时回退本地规则（不中断流程）。

## 7. 导演控制

当前支持的主要导演命令（通过 `/sessions/{id}/director`）：
- `inject_instruction`
- `rollback`
- `pause`
- `resume`
- `cut`

前端“暂停”按钮当前走 `pause`，便于继续注入指令后恢复推演。

## 8. 导出与日志

- 导出接口：`POST /sessions/{id}/export`
- 前端阶段 4 会自动触发导出，并支持下载台本文本。
- 运行日志建议放在 `log/server/`

## 9. CLI（可选）

```bash
python cli.py planned-demo --config your_runtime_config.json
python cli.py free-demo --config your_runtime_config.json
```

说明：
- `--config` 必填，不再使用全局默认配置文件兜底。

## 10. 当前状态说明

近期做过较大重构（前后端结构拆分、模式首页、workflow 新模块、one-line 生成接口）。  
如果你从旧分支迁移，请优先确认：
- 使用的是最新后端进程（新增路由需重启服务）
- 前端资源已刷新（避免旧 JS 缓存）
