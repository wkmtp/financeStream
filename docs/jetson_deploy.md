# Jetson Xavier NX 部署说明（OpenClaw + DeepSeek 动态直播版）

## 1. 基础环境

```bash
sudo nvpmodel -m 2
sudo jetson_clocks
```

- 安装 Docker / Docker Compose / FFmpeg
- 建议开启 8~16GB swap（防 OOM）

## 2. 服务拆分建议

- `orchestrator`：n8n + Dify
- `market-service`：FastAPI 指标服务
- `interaction-service`：OpenClaw（抖音/快手互动）
- `reasoning-service`：DeepSeek API
- `tts-service`：双引擎（Piper + GPT-SoVITS）
- `stream-pusher`：FFmpeg 动态叠字合成推流

## 3. 性能优化

- TTS 路由：高频短句走 Piper，重点段落走 GPT-SoVITS
- GPT-SoVITS 模型量化（FP16/INT8）
- 叠字文本刷新 2 秒一次，避免频繁重绘
- 降低推流分辨率/码率以保证稳定（如 720p）
- DeepSeek 请求超时后立即回退本地模板，避免卡住播报链路

## 4. 监控项

- 端到端延迟（弹幕 -> 出声）
- 推流丢帧率、推流进程重启次数
- GPU 显存占用峰值
- TTS `engine_used` 命中率（piper/gpt_sovits/tone_fallback）
- OpenClaw 请求成功率、DeepSeek 请求成功率
