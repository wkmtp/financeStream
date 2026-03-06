# Jetson Xavier NX 部署说明

## 1. 基础环境

```bash
sudo nvpmodel -m 2
sudo jetson_clocks
```

- 安装 Docker / Docker Compose
- 建议开启 8~16GB swap（防 OOM）

## 2. 服务拆分建议

- `orchestrator`：n8n + Dify
- `market-service`：FastAPI 指标服务
- `tts-service`：双引擎（Piper + GPT-SoVITS）
- `overlay-ui`：图表与字幕叠层
- `stream-pusher`：FFmpeg 推流

## 3. 性能优化

- TTS 路由：短句走 Piper，重点段落走 GPT-SoVITS
- GPT-SoVITS 模型量化（FP16/INT8）
- 音频分段合成，边合成边播放
- 将图表刷新率控制在 2~5 FPS（减少 GPU 争用）

## 4. 监控项

- 端到端延迟（弹幕 -> 出声）
- 推流丢帧率
- GPU 显存占用峰值
- 单位小时异常恢复次数
