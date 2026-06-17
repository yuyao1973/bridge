# 发布给其他人使用

当前项目是 Python + Streamlit Web 应用，不能直接“一键发布”为微信小程序。可以按使用目标选择下面方案。

## 方案 A：最快发布为网页

适合先让朋友、牌友或老师试用。

### 做法

1. 租一台云服务器，推荐 2 核 2G 起步。
2. 安装 Python 3.10+。
3. 上传本项目代码。
4. 安装依赖并启动：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

5. 配置域名、HTTPS 和反向代理。
6. 把网址发给其他人使用。

### 优点

- 改动最少。
- 现有代码基本可以直接用。
- 适合快速测试产品想法。

### 缺点

- 不是微信小程序原生体验。
- 如果要在微信内稳定访问，建议使用已备案域名和 HTTPS。

## 方案 B：微信小程序 web-view 嵌入网页

适合想在微信小程序入口里打开现有 Streamlit 页面。

### 要求

- 已认证的小程序主体。
- 服务器域名必须配置到小程序业务域名。
- 域名需要 HTTPS。
- 国内访问通常需要备案。

### 优点

- 可以最大程度复用现有 Streamlit 应用。
- 开发量比原生小程序少。

### 缺点

- `web-view` 能力和主体资质有限制。
- 页面体验仍是网页，不是原生小程序。
- 审核、域名和备案要求更严格。

## 方案 C：重写为原生微信小程序

适合正式发布和长期维护。

当前仓库已经开始采用此方案：

- `app.py`：保留本地 Streamlit 网页版。
- `api.py`：新增 Python ASGI 后端，复用现有 Python 叫牌规则。
- `wechat-miniprogram/`：新增原生微信小程序前端。

### 推荐架构

```text
微信小程序前端
  - 展示手牌
  - 选择训练模式
  - 选择叫品
  - 显示反馈和统计

Python 后端 API
  - 发牌
  - 牌力计算
  - 开叫推荐
  - 应叫推荐
  - 规则设置

数据库，可选
  - 用户记录
  - 训练统计
  - 错题本
```

### 技术选择

- 小程序前端：微信原生小程序、uni-app 或 Taro。
- 后端：Python ASGI API，可用 Uvicorn 运行。
- 部署：腾讯云、阿里云、轻量云服务器或云开发。
- 数据库：SQLite 起步，后续可换 MySQL/PostgreSQL。

### 迁移步骤

1. 把 `bridge_trainer` 中的发牌、评估、叫牌规则保留为 Python 后端核心逻辑。
2. 新建 Python API 服务，提供接口：
  - `GET /health`
  - `POST /api/question`
  - `POST /api/answer`
3. 新建微信小程序前端页面：
   - 首页
   - 开叫训练
   - 应叫训练
   - 规则设置
   - 统计页面
4. 小程序通过 HTTPS 调用后端 API。
5. 配置服务器域名。
6. 提交微信审核。

## 当前建议

如果只是“推送给其他人用”，可以先用 **方案 A：发布为网页** 快速试用。当前已同时保留本地网页版本，并新增 **方案 C：原生微信小程序** 的项目骨架。

## 本地调试微信小程序

1. 启动 API：

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn api:app --host 0.0.0.0 --port 8000
```

2. 使用微信开发者工具导入 `wechat-miniprogram`。
3. 本地开发阶段关闭“校验合法域名”。
4. 编译运行小程序。

## 正式发布微信小程序

1. 准备云服务器或云函数托管 API。
2. 配置 HTTPS 域名。
3. 把 `wechat-miniprogram/app.js` 中的 `apiBaseUrl` 改为正式 HTTPS API 地址。
4. 在微信公众平台配置 request 合法域名。
5. 使用真实 AppID 替换 `wechat-miniprogram/project.config.json` 中的 `touristappid`。
6. 上传代码并提交审核。
