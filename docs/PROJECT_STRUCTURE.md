# 项目目录结构（已整理）

## 顶层

```text
AI_Playlet_Agent/
├─ backend/                # FastAPI 组装与应用工厂
├─ frontend/               # 前端页面与脚本
├─ runtime/                # 运行时引擎（会话、轮次、导演指令、runner）
├─ tests/                  # 测试
├─ docs/                   # 文档与设计草案
├─ log/                    # 运行日志与演绎轨迹
├─ api.py                  # 兼容入口（uvicorn api:app）
├─ cli.py                  # 命令行入口
└─ *.py                    # 历史核心模块（后续可继续分层迁移）
```

## docs 约定

```text
docs/
├─ PROJECT_STRUCTURE.md
└─ notes/                  # 方案草稿、调研文档
```

## log 约定

```text
log/
├─ server/                 # api_server*.log / api_server*.err.log
└─ episode_*_trace.json    # 演绎轨迹
```

## 整理原则

1. 运行入口保留在根目录（`api.py`、`cli.py`），避免破坏现有启动方式。
2. 新增功能优先放入 `backend/`、`runtime/`、`frontend/` 对应目录。
3. 日志与文档不再散落在仓库根目录。
