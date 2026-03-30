# 系统架构设计（AkShare + 东方财富 + DeepSeek + OpenClaw）

## 1. 模块图

```text
AkShare / 东方财富API / OpenClaw(抖音&快手)
                │
                ▼
        [DataHub: FastAPI]
   (实时行情、热点评分、交易组合)
                │
                ├──────────────► [DeepSeek 思考模型]
                │                     │
                │                     ├──► 双角色讲解脚本
                │                     └──► 每只入选股票股评
                ▼
      [Portfolio Engine]
(买入/卖出/持仓/累计收益)
                │
                ▼
[动态叠字文本生成 + 双引擎TTS] ───► [FFmpeg 动态合成推流] ───► 抖音/快手 RTMP
```

## 2. 关键能力

- AkShare / 东方财富 API 优先获取实时行情，失败时回退本地模拟
- `GET /api/market/status` 暴露行情源状态、AkShare 安装情况和命中来源统计
- `GET /api/market/snapshot` 返回每只股票 `source`
- OpenClaw 负责抖音/快手互动
- DeepSeek 负责双角色脚本和个股股评
- Portfolio Engine 负责每天买卖、持仓和累计收益统计
- 背景实时展示累计收益、当日买卖和持仓
