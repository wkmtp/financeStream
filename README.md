# AI 炒股直播软件（Jetson Xavier NX）

这是一个可运行的 MVP：
- 双角色（男/女）自动解说；
- 根据行情热度自动选股，并可插入观众点名股票；
- 提供实时曲线直播看板（Web）；
- TTS 已接入 GPT-SoVITS（本地 HTTP 服务），异常时自动回退示例音频，保障不断播；
- 面向 Jetson Xavier NX 的部署建议。

## 1. 项目结构

```text
app/
  main.py                # FastAPI API + 页面入口
  models.py              # 数据模型
  services/
    market.py            # 行情模拟与热点评分
    script_engine.py     # DeepSeek 脚本生成适配层（当前为可运行模板逻辑）
    tts_engine.py        # GPT-SoVITS 适配层（失败自动回退）
  templates/index.html   # 直播控制台页面
  static/                # JS/CSS
tests/test_api.py        # API 测试
```

## 2. 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

打开：<http://localhost:8000>

## 3. GPT-SoVITS 环境变量

```bash
export GPT_SOVITS_API_URL="http://127.0.0.1:9880/tts"
export GPT_SOVITS_TIMEOUT="20"
export GPT_SOVITS_TEXT_LANG="zh"
export GPT_SOVITS_PROMPT_LANG="zh"

# 男声参考
export GPT_SOVITS_REF_AUDIO_MALE="/data/voices/male_ref.wav"
export GPT_SOVITS_PROMPT_TEXT_MALE="这是男主播参考音"

# 女声参考
export GPT_SOVITS_REF_AUDIO_FEMALE="/data/voices/female_ref.wav"
export GPT_SOVITS_PROMPT_TEXT_FEMALE="这是女主播参考音"
```

## 4. 核心 API

- `GET /api/market/snapshot`：返回实时行情快照
- `GET /api/hot`：返回热门股票
- `POST /api/audience/request`：观众点股
- `GET /api/script`：生成双角色解说稿
- `POST /api/tts`：调用 GPT-SoVITS 并返回音频文件路径
- `GET /api/live/state`：看板轮询接口

## 5. Jetson Xavier NX 落地建议

1. DeepSeek 使用云 API；
2. GPT-SoVITS 在本地 GPU 运行，API 暴露给 `TTSEngine`；
3. 直播导播建议 OBS + FFmpeg，页面作为叠层源。

详细见：
- `docs/architecture.md`
- `docs/jetson_deploy.md`
- `prompts/deepseek_stock_commentary.md`
- `workflows/n8n_workflow_template.json`

## 6. 合规说明

系统内置风险提示模板：
> 以上内容仅供学习交流，不构成投资建议，请独立决策并控制仓位。

上线前请根据当地平台与法规补充投资相关合规策略。
