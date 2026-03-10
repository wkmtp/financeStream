# 系统架构设计（动态直播流）

## 1. 模块图

```text
行情源/新闻源/弹幕源
        │
        ▼
[DataHub: FastAPI]
(清洗、指标计算、热点评分)
        │
        ├──────────────► [n8n 编排]
        │                     │
        │                     ▼
        │              [DeepSeek 生成脚本]
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
- 叠字文本每 2 秒刷新，持续展示讨论标的、双角色短句和风险提示
- TTS 双引擎路由：短句优先 Piper，重点段落优先 GPT-SoVITS

## 3. 容错策略

- Piper 失败 -> GPT-SoVITS
- GPT-SoVITS 失败 -> Piper
- 双引擎都失败 -> 本地 tone 回退，确保不断播
- FFmpeg 进程退出可通过外层进程管理器（systemd/docker）拉起
