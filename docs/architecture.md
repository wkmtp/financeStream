# 系统架构设计

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
[图表服务 Web]         [TTS 服务 GPT-SoVITS]
        │                     │
        └──────────► [导播合成 OBS/FFmpeg] ───► 抖音/快手
```

## 2. 关键数据对象

- `stock_snapshot`
  - `symbol`
  - `price`
  - `change_pct`
  - `volume_ratio`
  - `indicators`（MA/MACD/KDJ...）
  - `ts`

- `comment_task`
  - `source`: `auto|audience`
  - `symbol`
  - `priority`
  - `requested_by`
  - `deadline`

- `script_packet`
  - `male_script`
  - `female_script`
  - `risk_disclaimer`
  - `chart_focus_points`

## 3. 调度策略

- 自动任务：每 45 秒触发
- 观众请求：实时入队，优先级高于自动任务
- 播报并发：
  - 只允许一个 TTS 合成任务执行
  - 下游导播采用队列播放，防止音轨冲突

## 4. 容错

- DeepSeek 超时：回退到模板化规则播报
- TTS 失败：使用备用 speaker 或预录提示音
- 行情源失败：切换到备用供应商并标注“数据延迟”
