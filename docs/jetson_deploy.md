# Jetson Xavier NX 部署说明（AkShare + 东方财富 + DeepSeek + OpenClaw）

## 1. 服务拆分建议

- `market-service`：AkShare + 东方财富 API 实时行情聚合
- `interaction-service`：OpenClaw（抖音/快手互动）
- `reasoning-service`：DeepSeek API（讲解与股评）
- `portfolio-service`：买卖、持仓、累计收益计算
- `tts-service`：Piper + GPT-SoVITS
- `stream-pusher`：FFmpeg 动态叠字推流

## 2. 运行建议

- 行情优先从 AkShare 拉取，东方财富补充；接口失败时快速回退，避免阻塞直播链路
- 每个交易日自动生成模拟买卖与持仓变化
- 背景叠字持续显示累计收益、当日交易、持仓摘要与股评
- DeepSeek 超时后回退规则模板，保证不间断播报
