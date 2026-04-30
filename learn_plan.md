# AgentChat 一周学习计划（中文）

本计划适合用 7 天时间（每天 2-4 小时）系统吃透项目：架构、请求链路、工具调用、对象存储、Docker 部署与排障。

## 使用方式

- 按天执行，建议不要跳过前 3 天。
- 每天都包含：
  - **学习目标**（当天要搞懂什么）
  - **必看文件**（必须读的代码）
  - **实践任务**（要动手做什么）
  - **当日产出**（要沉淀什么）
  - **自检问题**（是否真正掌握）
- 建议每天写学习笔记：`notes/dayX.md`。

---

## 第 1 天：启动流程与整体架构

### 学习目标
搞懂后端如何启动、配置如何加载、路由如何注册，以及 Docker 中各服务如何协作。

### 必看文件
- `src/backend/agentchat/main.py`
- `src/backend/agentchat/settings.py`
- `src/backend/agentchat/config.yaml`
- `docker/docker_config.yaml`
- `docker/docker-compose.yml`
- `docker/Dockerfile`
- `docker/Dockerfile.frontend`

### 实践任务
1. 画出启动时序：
   - app 启动 -> 初始化 settings -> 初始化数据库 -> 注册路由 -> 健康检查。
2. 对比 `config.yaml` 与 `docker/docker_config.yaml`：
   - 列出关键差异（`mysql`、`redis`、`storage`、`vector_db`、`langfuse`）。
3. 解释为什么 Docker 内前后端要用 service name 通信（而不是 `127.0.0.1`）。

### 当日产出
- 一页架构图（手绘或电子均可），包含：
  - frontend
  - backend
  - mysql
  - redis
  - milvus
  - minio
  - 主请求流向

### 自检问题
- 你能解释 `settings.py` 中 `setattr(app_settings, key, value)` 的作用吗？
- 为什么容器内的 `127.0.0.1` 不适合服务间通信？

---

## 第 2 天：API 层与 Schema 数据模型

### 学习目标
搞懂请求如何被校验、解析，并进入服务层逻辑。

### 必看文件
- `src/backend/agentchat/api/v1/workspace.py`
- `src/backend/agentchat/schemas/workspace.py`
- `src/backend/agentchat/schemas/common.py`
- `src/backend/agentchat/api/responses/builder.py`
- `src/backend/agentchat/api/services/user.py`

### 实践任务
1. 端到端追一条接口：
   - `POST /api/v1/workspace/simple/chat`
2. 标出输入校验点（Pydantic、Depends、鉴权）。
3. 写出该接口的响应结构（尤其 SSE 流式格式）。

### 当日产出
- 一份 Markdown 说明：
  - 请求字段含义
  - 鉴权依赖路径
  - SSE 响应格式（`data: {...}\n\n`）

### 自检问题
- `BaseModel` 在这个项目里解决了什么问题？
- 为什么接口参数可以直接是对象而不是 dict？

---

## 第 3 天：工作区核心执行链（最关键）

### 学习目标
吃透工作区对话主链路：模型选择、插件/MCP 加载、工具执行、结果流式返回。

### 必看文件
- `src/backend/agentchat/services/workspace/simple_agent.py`
- `src/backend/agentchat/core/models/manager.py`
- `src/backend/agentchat/core/callbacks/langfuse.py`
- `src/backend/agentchat/tools/__init__.py`

### 实践任务
1. 梳理 `WorkSpaceSimpleAgent.__init__` 的对象构造过程。
2. 追踪 `init_simple_agent()` 执行顺序。
3. 解释下列对象差异：
   - `plugin_tools`
   - `mcp_tools`
   - `tools`
4. 解释为什么“前端选了工具”仍可能运行失败（id->name->函数映射问题）。

### 当日产出
- 一份链路清单：
  - 前端请求
  - 后端 schema 解析
  - 工具列表构建
  - agent 执行
  - SSE 返回

### 自检问题
- 如果日志是 `Loaded 0 plugin tools`，最可能的 3 个原因是什么？
- `tools/__init__.py` 中做别名映射解决了什么问题？

---

## 第 4 天：工具系统与文件转换链路

### 学习目标
搞懂工具配置如何从数据库映射到具体代码，及文件转换工具如何处理 MinIO/OSS 链接。

### 必看文件
- `src/backend/agentchat/api/services/tool.py`
- `src/backend/agentchat/database/dao/tool.py`
- `src/backend/agentchat/database/models/tool.py`
- `src/backend/agentchat/tools/docx_to_pdf/action.py`
- `src/backend/agentchat/tools/pdf_to_docx/action.py`
- `src/backend/agentchat/config/tool.json`

### 实践任务
1. 解释完整映射路径：
   - `tool_id` -> DB 记录 -> `name` -> `WorkSpacePlugins[name]` -> Python callable。
2. 吃透 `_get_object_name_from_storage_url` 如何兼容 MinIO/OSS。
3. 验证转换依赖：LibreOffice 对 doc/xls/ppt -> pdf 的作用。

### 当日产出
- 一份转换工具排障清单：
  - 选了工具但没调用
  - 调用了但转换失败
  - 转换成功但下载链接不可用

### 自检问题
- 为什么 `convert_to_pdf` 与 `docx_to_pdf` 不一致会导致运行失败？
- 兼容历史工具名应改在哪一层最合适？

---

## 第 5 天：上传与对象存储（MinIO）链路

### 学习目标
彻底搞懂上传接口、对象存储、URL 策略在 Docker 部署下的行为。

### 必看文件
- `src/backend/agentchat/api/v1/upload.py`
- `src/backend/agentchat/services/storage/minio.py`
- `src/backend/agentchat/services/storage/__init__.py`
- `src/backend/agentchat/utils/file_utils.py`
- `docker/docker_config.yaml`（storage 段）

### 实践任务
1. 跟踪上传流程：
   - 前端文件 -> `/api/v1/upload` -> storage client -> 返回 URL。
2. 解释：
   - 内部访问地址（`minio:9000`） vs 外部访问地址（`localhost:9000/...`）。
3. 验证 bucket policy、签名 URL、公共 URL 策略。

### 当日产出
- 一份 URL 使用规范：
  - 后端容器内部用什么 URL
  - 浏览器展示用什么 URL
  - 工具执行下载用什么 URL

### 自检问题
- 为什么某个链接在浏览器能打开，但在容器中不可达？
- 什么时候必须用 `storage_client.download_file(object_name, file_path)` 而不是 HTTP 下载？

---

## 第 6 天：前端页面行为与请求参数正确性

### 学习目标
搞清楚你实际使用的是哪个页面，工具/附件参数是否真的传到后端。

### 必看文件
- `src/frontend/src/router/index.ts`
- `src/frontend/src/apis/workspace.ts`
- `src/frontend/src/apis/chat.ts`
- `src/frontend/src/pages/workspace/defaultPage/defaultPage.vue`
- `src/frontend/src/pages/conversation/chatPage/chatPage.vue`
- `src/frontend/vite.config.ts`

### 实践任务
1. 确认当前真实路由页面（`workspace/defaultPage` 还是 `conversation/chatPage`）。
2. 跟踪工具选中 ID 构造、payload 序列化与发送。
3. 验证附件上传与附件链接注入 query 的行为。
4. 验证 Vite 代理（`/api` -> backend）是否一致。

### 当日产出
- 一张映射表：
  - 用户操作
  - 触发的方法
  - 调用的 API 方法
  - 对应后端接口

### 自检问题
- 你如何证明“你改的页面就是当前正在渲染的页面”？
- 为什么“代码改了但页面没变化”在 Docker 前端里很常见？

---

## 第 7 天：观测、排障与小改进收官

### 学习目标
建立可复用的生产级排障方法，并完成一个安全的小优化。

### 必看文件
- `src/backend/agentchat/middleware/trace_id_middleware.py`
- `src/backend/agentchat/core/callbacks/langfuse.py`
- `src/backend/agentchat/services/workspace/simple_agent.py`
- `docker/docker-compose.yml`
- `docker/README.md`

### 实践任务
1. 写出自己的排障剧本：
   - 前端无请求
   - 后端收到请求但无工具调用
   - 工具调用失败
   - 链接不可访问
2. 做 1 个小改进（任选其一）：
   - 增强插件 id->name 日志
   - 工具名缺失时报错更友好
   - 文档补充 LibreOffice 依赖说明
3. 跑一遍完整验证：
   - 上传文件
   - 勾选转换工具
   - 得到可下载链接

### 当日产出
- `WEEK_SUMMARY.md`：
  - 你对架构的理解
  - 遇到的 3 个关键坑
  - 你做的改进与价值
  - 接下来 2 周进阶计划

### 自检问题
- 你能在 10 分钟内定位“选了工具但没生效”的原因吗？
- 你能在 5 分钟内向新人讲清项目主链路吗？

---

## 每日时间分配建议

- 45 分钟：读代码并做注释
- 45 分钟：追一条真实请求/日志链路
- 30 分钟：整理笔记与图
- 30-60 分钟：做一次实操验证（接口、日志、页面）

---

## 一周结束验收清单

- [ ] 能解释后端启动与配置注入路径
- [ ] 能完整追踪 workspace 对话链路
- [ ] 能解释 tool_id/name/function 映射与常见失败点
- [ ] 能排查 MinIO 内外网 URL 问题
- [ ] 能确认前端真实生效页面与真实 payload
- [ ] 能通过日志快速定位故障阶段（10 分钟内）
- [ ] 能完成一个安全改动并在 Docker 中验证

