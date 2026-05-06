# vid-maker 环境配置与 Key 申请指南

---

## 一、本机环境检查（当前状态）

运行以下命令验证所有工具就绪：

```bash
node -v        # 需要 >= 22，当前 v25.9.0 ✅
pnpm -v        # 当前 10.33.2 ✅
python3 -V     # 需要 >= 3.9，当前 3.9.6 ✅
ffmpeg -version | head -1   # 当前 8.1 ✅
docker -v      # 当前 20.10.24 ✅
```

**全部就绪，无需额外安装工具。**

---

## 二、需要你提供的 Key 清单

按优先级分三档：**MVP 必须** / **MVP 可 mock 跳过** / **上线前必须**

---

### 🔴 MVP 必须（不填写无法本地开发）

#### 1. Anthropic Claude API Key

- **用途**：脚本生成（Step 1 → Step 2）
- **申请地址**：[https://console.anthropic.com](https://console.anthropic.com) → API Keys
- **费用**：按 token 计费，开发阶段 $5 够用
- **填写位置**：`.env` 第 10 行

```
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxx
```

---

#### 2. Replicate API Token

- **用途**：FLUX.1 分镜图生成（Step 3 并行出图）
- **申请地址**：[https://replicate.com](https://replicate.com) → Account Settings → API tokens
- **费用**：$0.04/张图，新账号有免费额度
- **填写位置**：`.env` 第 11 行

```
REPLICATE_API_TOKEN=r8_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

### 🟡 MVP 可 mock 跳过（开发期间可用假数据代替）

#### 3. ElevenLabs API Key

- **用途**：TTS 旁白生成（Step 4 生产阶段）
- **申请地址**：[https://elevenlabs.io](https://elevenlabs.io) → Profile → API Key
- **费用**：免费 10,000 字符/月，够初期开发
- **填写位置**：`.env` 第 12 行
- **Mock 方案**：Worker 检测到无 Key 时，生成静音 mp3 文件

```
ELEVENLABS_API_KEY=sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

#### 4. Kling API Key + Secret

- **用途**：AI 视频生成（Step 4 最耗时步骤）
- **申请地址**：[https://klingai.com](https://klingai.com) → 开发者中心 → 申请 API
- **费用**：$0.05/秒，5s 视频 = $0.25/条，需要企业认证
- **填写位置**：`.env` 第 13-14 行
- **Mock 方案**：Worker 无 Key 时用 FFmpeg 把分镜图转成 5s 静止视频

```
KLING_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KLING_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

#### 5. Better Auth Secret（自己生成，不需要申请）

- **用途**：JWT session 签名密钥
- **生成方式**：运行下面命令，复制输出
  ```bash
  node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
  ```
- **填写位置**：`.env` 第 52 行

```
BETTER_AUTH_SECRET=（粘贴上面命令的输出，32字节hex字符串）
```

---

### 🔵 上线前必须（开发期间不需要，MVP 可跳过）

#### 6. 阿里云 AccessKey（OSS 存储 + 内容安全 + 短信）

**可以用同一个 AccessKey 覆盖三个服务**，只需开通对应的阿里云产品。

- **申请地址**：[https://ram.console.aliyun.com](https://ram.console.aliyun.com) → 创建用户 → 编程访问
- **需要开通的产品**：
  - 对象存储 OSS（用于存视频图片）
  - 内容安全（用于审核用户输入）
  - 短信服务 SMS（用于手机验证码）
- **填写位置**：`.env` 第 17-33 行
- **OSS 还需要**：
  - 创建 Bucket，获取 Bucket 名称
  - 配置 CDN 域名（可选，开发期间直接用 OSS 域名）

```
OSS_ACCESS_KEY_ID=LTAI5txxxxxxxxxxxxxxxxxxxx
OSS_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OSS_BUCKET=vid-maker-dev
OSS_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com
OSS_CDN_DOMAIN=https://cdn.vid-maker.com（可暂时填 OSS 域名）

ALIYUN_ACCESS_KEY_ID=LTAI5txxxxxxxxxxxxxxxxxxxx（与 OSS 相同的 AK）
ALIYUN_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ALIYUN_CONTENT_SAFETY_REGION=cn-shanghai

ALIYUN_SMS_ACCESS_KEY_ID=LTAI5txxxxxxxxxxxxxxxxxxxx（同上）
ALIYUN_SMS_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ALIYUN_SMS_SIGN_NAME=（申请短信签名，如：vid-maker）
ALIYUN_SMS_TEMPLATE_CODE=SMS_xxxxxxxxx（申请短信模板后获得）
```

---

#### 7. 微信开放平台（微信登录）

- **申请地址**：[https://open.weixin.qq.com](https://open.weixin.qq.com) → 管理中心 → 网站应用
- **需要**：已认证的公司账号（个人无法申请）+ 网站已备案
- **获得**：AppID + AppSecret
- **填写位置**：`.env` 第 36-38 行

```
WECHAT_APP_ID=wx_xxxxxxxxxxxxxxxx
WECHAT_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

#### 8. 微信支付商户号

- **申请地址**：[https://pay.weixin.qq.com](https://pay.weixin.qq.com) → 申请开通微信支付
- **需要**：营业执照 + 银行账户（个人工商户可以）
- **获得**：商户号 + API v3 密钥 + 证书文件
- **证书文件**：下载后放到 `certs/` 目录（不提交 git）
- **填写位置**：`.env` 第 41-44 行

```
WECHAT_PAY_MCH_ID=xxxxxxxxxx（10位数字）
WECHAT_PAY_CERT_SERIAL=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx（40位）
WECHAT_PAY_PRIVATE_KEY_PATH=./certs/wechat-pay-private-key.pem
WECHAT_PAY_API_V3_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx（32位）
```

---

#### 9. 支付宝

- **申请地址**：[https://open.alipay.com](https://open.alipay.com) → 控制台 → 创建应用
- **需要**：营业执照
- **获得**：AppID + 应用私钥/公钥文件
- **填写位置**：`.env` 第 47-49 行

```
ALIPAY_APP_ID=xxxxxxxxxxxxxxxxxx（16位）
ALIPAY_PRIVATE_KEY_PATH=./certs/alipay-private-key.pem
ALIPAY_PUBLIC_KEY_PATH=./certs/alipay-public-key.pem
```

---

#### 10. GitHub Token（可选，用于 MCP github 服务）

- **申请地址**：[https://github.com](https://github.com) → Settings → Developer Settings → Personal access tokens
- **权限**：repo + read:org
- **填写位置**：`.env` 第 65 行

```
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 三、立即填写（MVP 阶段最小配置）

只填这 5 个，其余保持 placeholder，即可跑通完整流程（有 mock 兜底）：

```bash
# 复制 .env.example 为 .env
cp .env.example .env
```

然后编辑 `.env`，只改这 5 行：

```
ANTHROPIC_API_KEY=sk-ant-...         # ← 必填，脚本生成
REPLICATE_API_TOKEN=r8_...           # ← 必填，分镜图
ELEVENLABS_API_KEY=sk_...            # ← 建议填，TTS（无则 mock 静音）
KLING_API_KEY=...                    # ← 建议填（无则 mock 静图视频）
KLING_API_SECRET=...                 # ← 同上
BETTER_AUTH_SECRET=（运行生成命令）   # ← 必填，认证
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/vidmaker_dev  # ← 改密码
PMR_SRC_PATH=/Users/kerwin/Desktop/workspace/AI自动化课件/课件资料/3 核心技术落地/toolkit/project-memory-rag/src
```

---

## 四、环境安装提示词

> 以下提示词发到 Cursor Composer 执行环境安装。

### Prompt E-0：验证环境并生成本地配置

```
帮我验证 vid-maker 的本机开发环境并完成初始配置。

运行以下检查（报告每项状态）：
1. node -v（需要 >= 22）
2. pnpm -v（需要 >= 8）
3. python3 -V（需要 >= 3.9，用于 project-memory-rag hooks）
4. ffmpeg -version（需要已安装）
5. docker compose version（需要已安装）
6. 检查 .env 文件是否存在（不存在则从 .env.example 复制）

然后：
a. 生成 BETTER_AUTH_SECRET：
   node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
   将生成的值写入 .env 的 BETTER_AUTH_SECRET 字段

b. 确认 .env 中 DATABASE_URL 和 REDIS_URL 使用本地 docker-compose 的值：
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/vidmaker_dev
   REDIS_URL=redis://localhost:6379

c. 将 PMR_SRC_PATH 设置为：
   /Users/kerwin/Desktop/workspace/AI自动化课件/课件资料/3 核心技术落地/toolkit/project-memory-rag/src

输出：所有检查的结果 + .env 已修改的字段列表（不输出 Key 值，只输出字段名）
```

---

### Prompt E-1：启动本地服务并初始化数据库

> 发送前确认已填好 ANTHROPIC_API_KEY

```
启动 vid-maker 本地开发环境。

步骤：
1. docker compose up -d（启动 PostgreSQL + Redis）
2. 等待健康检查通过（docker compose ps 确认 healthy）
3. 安装所有 workspace 依赖：pnpm install
4. 运行数据库迁移：pnpm --filter @vid-maker/db drizzle-kit migrate
5. 初始化测试数据（在 DB 写入一个测试用户，credit_balance=100积分）：
   psql $DATABASE_URL -c "INSERT INTO users (id, phone, credit_balance, plan_id) 
   VALUES ('00000000-0000-0000-0000-000000000001', '13800138000', 100, 'basic')
   ON CONFLICT DO NOTHING;"
6. 验证：psql $DATABASE_URL -c "SELECT id, phone, credit_balance FROM users;"

如果遇到 Migration 报错，先检查 packages/db/migrations/ 目录是否有迁移文件，
没有则先运行 pnpm --filter @vid-maker/db drizzle-kit generate。
```

---

### Prompt E-2：验证 Key 可用性

> 发送前已填写 ANTHROPIC_API_KEY 和 REPLICATE_API_TOKEN

```
帮我验证已配置的 API Key 是否可以正常调用。

编写并运行 scripts/verify-keys.ts（tsx 执行）：

1. 验证 Anthropic：
   发送最简单的 messages.create 请求（max_tokens:10，只问"hi"）
   成功 → ✅ Anthropic OK（model: claude-sonnet-4-6）
   失败 → ❌ 错误信息

2. 验证 Replicate：
   调用 replicate.models.get("black-forest-labs/flux-kontext-pro")
   成功 → ✅ Replicate OK（模型可访问）
   失败 → ❌ 错误信息

3. 验证 ElevenLabs（如果已填写）：
   调用 voices.getAll()，列出前3个 voice
   成功 → ✅ ElevenLabs OK（voices: N个）
   失败 → ⚠️  跳过（使用 mock）

4. 验证数据库连接：
   SELECT NOW() 查询
   成功 → ✅ PostgreSQL OK

5. 验证 Redis：
   PING 命令
   成功 → ✅ Redis OK

输出所有验证结果，最后一行显示：
"可以开始开发：[已就绪的服务列表]"
"需要 Mock 的服务：[未配置 Key 的服务列表]"
```

---

### Prompt E-3：安装 Cursor Marketplace Plugins

> 在 Cursor 聊天框中直接发送（不是 Composer）

```
/add-plugin shadcn
```

（等安装完成后再发）

```
/add-plugin frontend-design
```

（等安装完成后再发）

```
/add-plugin web-design-guidelines
```

安装完成后验证：向 Agent 提问"你有哪些可用的 skills 和 plugins？"

---

## 五、Key 申请优先级与时间预估


| Key                | 难度   | 预计申请时间         | 是否影响 MVP        |
| ------------------ | ---- | -------------- | --------------- |
| Anthropic          | 简单   | 5分钟（注册即得）      | **必须**          |
| Replicate          | 简单   | 5分钟（GitHub 登录） | **必须**          |
| ElevenLabs         | 简单   | 5分钟（邮件注册）      | 可 mock          |
| Kling              | 中等   | 1-3天（需企业审核）    | 可 mock          |
| Better Auth Secret | 自动生成 | 1秒             | **必须**          |
| 阿里云 AK             | 中等   | 30分钟（实名认证）     | 可 mock（OSS/SMS） |
| 微信开放平台             | 困难   | 7-14天（企业审核）    | 可 mock          |
| 微信支付               | 困难   | 7-14天（企业资质）    | 推迟到 Phase 4     |
| 支付宝                | 困难   | 7-14天（企业资质）    | 推迟到 Phase 4     |


**建议：先申请 Anthropic + Replicate + ElevenLabs（3个都能当天拿到），即可开始 MVP 开发。**

---

## 六、Key 填写位置速查表


| Key                      | 文件     | 行号  |
| ------------------------ | ------ | --- |
| ANTHROPIC_API_KEY        | `.env` | 10  |
| REPLICATE_API_TOKEN      | `.env` | 11  |
| ELEVENLABS_API_KEY       | `.env` | 12  |
| KLING_API_KEY            | `.env` | 13  |
| KLING_API_SECRET         | `.env` | 14  |
| OSS_ACCESS_KEY_ID        | `.env` | 17  |
| OSS_ACCESS_KEY_SECRET    | `.env` | 18  |
| OSS_BUCKET               | `.env` | 19  |
| OSS_ENDPOINT             | `.env` | 20  |
| ALIYUN_ACCESS_KEY_ID     | `.env` | 25  |
| ALIYUN_ACCESS_KEY_SECRET | `.env` | 26  |
| ALIYUN_SMS_ACCESS_KEY_ID | `.env` | 30  |
| ALIYUN_SMS_TEMPLATE_CODE | `.env` | 33  |
| WECHAT_APP_ID            | `.env` | 37  |
| WECHAT_APP_SECRET        | `.env` | 38  |
| WECHAT_PAY_MCH_ID        | `.env` | 42  |
| WECHAT_PAY_API_V3_KEY    | `.env` | 44  |
| ALIPAY_APP_ID            | `.env` | 48  |
| BETTER_AUTH_SECRET       | `.env` | 52  |
| GITHUB_TOKEN             | `.env` | 65  |
| PMR_SRC_PATH             | `.env` | 68  |


证书文件（下载后放到 `certs/` 目录，不提交 git）：


| 文件                                 | 来源         |
| ---------------------------------- | ---------- |
| `certs/wechat-pay-private-key.pem` | 微信支付商户后台下载 |
| `certs/alipay-private-key.pem`     | 支付宝开放平台生成  |
| `certs/alipay-public-key.pem`      | 支付宝开放平台获取  |


