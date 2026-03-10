# 系统架构设计（动态直播流 + OpenClaw + DeepSeek）

## 1. 模块图

```text
行情源/新闻源/OpenClaw(抖音&快手)
        │
        ▼
[DataHub: FastAPI]
(清洗、指标计算、热点评分)
        │
        ├──────────────► [DeepSeek 思考模型]
        │                     │
        │                     ▼
        │              [双角色讲解脚本 JSON]
        │                     │
        ▼                     ▼
[动态叠字文本生成]      [双引擎TTS: Piper + GPT-SoVITS]
        │                     │
        └──────────► [FFmpeg 动态合成推流] ───► 抖音/快手 RTMP
```

## 2. 关键能力

- `POST /api/live/start`：启动动态直播推流
- `POST /api/live/stop`：停止推流
- `GET /api/live/stream-status`：推流状态
- OpenClaw 负责抖音/快手弹幕拉取与回复透传
- DeepSeek 负责高质量讲解生成，失败自动回退规则模板
- 叠字文本每 2 秒刷新，持续展示讨论标的、双角色短句和风险提示

## 3. 容错策略

- OpenClaw 失败 -> 本地消息队列兜底
- DeepSeek 失败 -> 本地规则文案兜底
- Piper/GPT-SoVITS 双引擎都失败 -> tone 回退，确保不断播
- FFmpeg 进程退出可通过外层进程管理器（systemd/docker）拉起
