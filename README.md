# AI 炒股直播软件（Jetson Xavier NX）

这是一个可运行并可发布的**动态直播预览 + 推流**版本：
- 行情层采用 **东方财富 API** 批量获取实时行情（仅中国大陆A股与ETF），失败时回退本地模拟；
- 互动层采用 **OpenClaw** 对接抖音 + 快手弹幕与回复；
- 推理层采用 **DeepSeek** 进行短线分析与双角色讲解，提示词精简以减少 token；
- 交易层自动生成每日买进/卖出/持仓，并统计累计收益；
- 背景叠字实时展示：讨论标的、双角色话术、当日买卖、当前持仓、累计收益、个股股评；
- TTS 采用 Piper + GPT-SoVITS 双引擎自动路由；
- `./run.sh` 启动后可直接访问 `/live` 查看带图像与语音的直播预览；同时保留 FFmpeg RTMP 推流能力。
- 当本地 Piper / GPT-SoVITS 不可用时，页面会自动切换为浏览器语音播报，避免只播放嗡嗡声。
- 语音文件采用循环槽位（如 `female_slot_0.wav` ~ `female_slot_2.wav`），避免播放未完成就被重写，并节约磁盘空间。
- 系统时间与展示时间统一为北京时间（UTC+8）。
- 直播页改为手机优先布局，并去掉“主播语音播报”“资讯/互动”模块，仅保留买卖建议与持仓收益。

## 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

## 行情层配置状态

当前已补齐：
- 程序通过东方财富批量接口优先拉取A股与ETF；
- 当实时接口异常时自动回退本地模拟数据，保证直播不断流；
- 可通过 `GET /api/market/status` 或 `GET /health/ready` 查看行情源状态；
- `GET /api/market/snapshot` 返回 `source_status`，每只股票快照也会返回 `source`。

启动后打开：`http://127.0.0.1:8000/live`

## 核心接口

- `GET /api/market/snapshot`：A股与ETF实时行情快照（东方财富优先）
- `GET /api/market/status`：行情源状态与命中来源统计
- `GET /api/recommendations`：今日加仓/减仓推荐 + 每只入选股票股评
- `GET /api/portfolio`：当日买卖、当前持仓、累计收益
- `GET /api/live/state`：直播完整运行态（含股评与组合）
- `GET /api/live/preview`：直播图像、语音、资讯、交易与持仓预览数据
- `POST /api/live/start`：启动 RTMP 动态直播
- `POST /api/live/stop`：停止 RTMP 动态直播

## 生产环境变量

```bash
# OpenClaw
export OPENCLAW_API_URL="http://127.0.0.1:9000"
export OPENCLAW_TIMEOUT="8"

# DeepSeek
export DEEPSEEK_API_URL="https://api.deepseek.com/chat/completions"
export DEEPSEEK_API_KEY="your-deepseek-key"
export DEEPSEEK_MODEL="deepseek-chat"
export DEEPSEEK_TIMEOUT="18"

# TTS
export TTS_DEFAULT_ENGINE="auto"
export TTS_AUTO_SHORT_TEXT_THRESHOLD="56"
```

## 合规说明

系统内置风险提示模板：
> 仅供学习交流，不构成投资建议。
