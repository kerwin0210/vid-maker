# vid-maker 环境配置与 Key 申请指南

> 版本：v1.1 · 2026-05
> 模型选型原则：该环节全球最优效果，不区分国内/国外

---

## 一、本机环境检查

```bash
node -v        # 需要 >= 22，当前 v25.9.0 ✅
pnpm -v        # 当前 10.33.2 ✅
python3 -V     # 需要 >= 3.9，当前 3.9.6 ✅（Faster-Whisper 依赖）
ffmpeg -version | head -1   # 当前 8.1 ✅
docker -v      # 当前 20.10.24 ✅
```

**全部就绪，无需额外安装工具。**

---

## 二、AI 模型选型说明（2026 Benchmark 数据）

| 环节 | 主选 | 为什么选这个 |
|------|------|------------|
| 脚本生成 | Claude Sonnet 4.6 | 生产 JSON 合规 98%+，GPT-5 同场景失败率 15-20% |
| 图片生成 | FLUX 2 Pro | $0.03/张（比 Kontext Pro 便宜 25%），真实感更好 |
| 视频生成 | Kling 3.0 | 原生 4K + 内置音频，$0.112/秒，Replicate/fal.ai 可用 |
| TTS 配音 | MiniMax Speech-02 | 全球 TTS Arena #1，中文 WER 2.252%（ElevenLabs 是 16%），价格 1/4 |
| ASR 转写 | Faster-Whisper large-v3 | WER 1.5%（优于 OpenAI API 2.8%），本地运行零成本 |
| 视频理解 | Claude 3.5 Sonnet Vision | 共用 Anthropic Key，帧内容理解最强 |

---

## 三、Key 申请清单（按优先级）

### 🔴 MVP 必须（今天可以拿到）

#### 1. Anthropic API Key（Claude 脚本生成 + 视频理解）
- **申请**：https://console.anthropic.com → API Keys
- **费用**：Claude Sonnet 4.6 约 $0.003/1K tokens，开发阶段 $10 够用
- **填写**：`.env` → `ANTHROPIC_API_KEY`

```
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxx
```

---

#### 2. Replicate API Token（FLUX 2 Pro 图片生成）
- **申请**：https://replicate.com → Account Settings → API tokens
- **费用**：$0.03/张图，新账号有免费额度
- **填写**：`.env` → `REPLICATE_API_TOKEN`

```
REPLICATE_API_TOKEN=r8_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

#### 3. fal.ai API Key（Kling 3.0 视频生成）
- **申请**：https://fal.ai → Dashboard → API Keys
- **费用**：Kling 3.0 约 $0.112/秒，5秒 ≈ $0.56
- **填写**：`.env` → `FAL_KEY`

```
FAL_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

#### 4. MiniMax API Key（TTS 配音）
- **申请**：https://platform.minimaxi.com → API Key 管理
- **费用**：$50/1M字符（ElevenLabs 的 1/4），中文质量全球第一
- **同时需要**：Group ID（同一页面获取）
- **填写**：`.env` → `MINIMAX_API_KEY` + `MINIMAX_GROUP_ID`

```
MINIMAX_API_KEY=xxxxxxxxxxxxxxxxxxxx
MINIMAX_GROUP_ID=xxxxxxxxxxxxxxxxxxxx
```

---

#### 5. Better Auth Secret（自动生成）
```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```
- **填写**：`.env` → `BETTER_AUTH_SECRET`

---

### 🟡 推荐补充（提升质量和可靠性）

#### 6. OpenAI API Key（Whisper 备用 ASR）
- **申请**：https://platform.openai.com → API Keys
- **用途**：无 GPU 时 Faster-Whisper 的云端备选，Whisper-1 $0.36/小时
- **注意**：与 Anthropic 是不同公司，两个 Key 都需要
- **填写**：`.env` → `OPENAI_API_KEY`

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
```

---

#### 7. Runway API Key（视频生成备选）
- **申请**：https://runwayml.com → Dashboard → API
- **费用**：$0.12-0.50/秒，质感更好但更贵
- **用途**：Kling 不可用时自动降级
- **填写**：`.env` → `RUNWAY_API_KEY`

```
RUNWAY_API_KEY=key_xxxxxxxxxxxxxxxxxxxx
```

---

#### 8. ElevenLabs API Key（TTS 备选，多语言场景）
- **申请**：https://elevenlabs.io → Profile → API Key
- **费用**：免费 10,000 字符/月
- **用途**：非中文内容或需要声音克隆时使用
- **填写**：`.env` → `ELEVENLABS_API_KEY`

```
ELEVENLABS_API_KEY=sk_xxxxxxxxxxxxxxxxxxxx
```

---

### 🔵 上线前必须（运营阶段）

#### 9. 阿里云 AccessKey（OSS + 内容安全 + 短信）

同一个 AK 可覆盖三个服务，需开通对应产品。

- **申请**：https://ram.console.aliyun.com → 创建用户 → 编程访问
- **需开通**：OSS / 内容安全 / 短信 SMS
- **OSS 额外**：创建 Bucket，配置 CDN 域名

```
OSS_ACCESS_KEY_ID=LTAI5txxxxxxxxxxxxxxxxxxxx
OSS_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxx
OSS_BUCKET=vid-maker-dev
OSS_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com
ALIYUN_ACCESS_KEY_ID=LTAI5txxxxxxxxxxxxxxxxxxxx（与 OSS 相同）
ALIYUN_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxx
ALIYUN_SMS_SIGN_NAME=vid-maker
ALIYUN_SMS_TEMPLATE_CODE=SMS_xxxxxxxxx
```

---

#### 10. 微信开放平台（微信登录）
- **申请**：https://open.weixin.qq.com → 网站应用（需认证企业账号）
- **预计**：7-14 天审核

```
WECHAT_APP_ID=wx_xxxxxxxxxxxxxxxx
WECHAT_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

#### 11. 微信支付商户号
- **申请**：https://pay.weixin.qq.com（需营业执照）
- **预计**：7-14 天审核
- **证书文件**：下载后放 `certs/`（不提交 git）

```
WECHAT_PAY_MCH_ID=xxxxxxxxxx
WECHAT_PAY_API_V3_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

#### 12. 支付宝
- **申请**：https://open.alipay.com（需营业执照）
- **预计**：7-14 天审核

```
ALIPAY_APP_ID=xxxxxxxxxxxxxxxxxx
```

---

## 四、MVP 最小配置（立刻可以开始开发）

只需填这 5 项：

```bash
cp .env.example .env
# 然后编辑 .env 填入以下 5 个值：
```

| 变量 | 来源 | 耗时 |
|------|------|------|
| `ANTHROPIC_API_KEY` | console.anthropic.com | 5 分钟 |
| `REPLICATE_API_TOKEN` | replicate.com | 5 分钟 |
| `FAL_KEY` | fal.ai | 5 分钟 |
| `MINIMAX_API_KEY` + `MINIMAX_GROUP_ID` | platform.minimaxi.com | 10 分钟 |
| `BETTER_AUTH_SECRET` | 本地生成 | 1 秒 |

无法立刻获取的服务，Worker 都有 mock 降级逻辑：视频生成 → 静图视频；TTS → 静音 mp3；ASR → Faster-Whisper 本地。

---

## 五、Key 申请优先级与时间预估

| Key | 难度 | 预计时间 | MVP 必须 |
|-----|------|---------|---------|
| Anthropic | 简单 | 5 分钟 | 是 |
| Replicate（FLUX 2 Pro）| 简单 | 5 分钟 | 是 |
| fal.ai（Kling 3.0）| 简单 | 5 分钟 | 是 |
| MiniMax Speech-02 | 简单 | 10 分钟 | 是 |
| Better Auth Secret | 自动生成 | 1 秒 | 是 |
| OpenAI（Whisper 备用）| 简单 | 5 分钟 | 可跳过 |
| Runway（视频备选）| 简单 | 5 分钟 | 可跳过 |
| ElevenLabs（TTS 备选）| 简单 | 5 分钟 | 可跳过 |
| 阿里云 AK | 中等 | 30 分钟（实名）| 上线前 |
| 微信开放平台 | 困难 | 7-14 天 | 上线前 |
| 微信支付 | 困难 | 7-14 天 | 上线前 |
| 支付宝 | 困难 | 7-14 天 | 上线前 |

---

## 六、Key 填写位置速查表

| Key | `.env` 变量名 |
|-----|-------------|
| Claude API | `ANTHROPIC_API_KEY` |
| FLUX 2 Pro | `REPLICATE_API_TOKEN` |
| Kling 3.0 | `FAL_KEY` |
| Runway Gen-4（备）| `RUNWAY_API_KEY` |
| MiniMax TTS | `MINIMAX_API_KEY` + `MINIMAX_GROUP_ID` |
| ElevenLabs（备）| `ELEVENLABS_API_KEY` |
| OpenAI Whisper（备）| `OPENAI_API_KEY` |
| OSS | `OSS_ACCESS_KEY_ID` + `OSS_ACCESS_KEY_SECRET` |
| 内容安全 | `ALIYUN_ACCESS_KEY_ID`（与 OSS 同）|
| 短信 | `ALIYUN_SMS_ACCESS_KEY_ID`（与 OSS 同）|
| 微信登录 | `WECHAT_APP_ID` + `WECHAT_APP_SECRET` |
| 微信支付 | `WECHAT_PAY_MCH_ID` + `WECHAT_PAY_API_V3_KEY` |
| 支付宝 | `ALIPAY_APP_ID` |
| 认证密钥 | `BETTER_AUTH_SECRET` |
| AI Provider 开关 | `IMAGE_PROVIDER` / `VIDEO_PROVIDER` / `TTS_PROVIDER` |

证书文件（`certs/` 目录，不提交 git）：
- `wechat-pay-private-key.pem`
- `alipay-private-key.pem` + `alipay-public-key.pem`
