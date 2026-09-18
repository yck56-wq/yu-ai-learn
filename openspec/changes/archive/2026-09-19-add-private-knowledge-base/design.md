## Context

现有后端是 FastAPI + aiomysql + LangChain，用户已经通过 JWT 归属题库和历史报告；`quiz_service` 目前把用户输入交给 DeepSeek，并通过 Tavily Agent 做可选联网检索。题库已经保存可选来源快照，但还没有文件上传、文档解析、向量数据库或私有来源。

本变更必须保留现有题目 JSON、服务端判题、XP 结算、历史读取和联网 fallback。工作区当前存在未提交的用户系统/前端变更，实施时只在相关文件上增量修改，不回退这些变更。

## Goals / Non-Goals

**Goals:**

- 为 PDF、DOCX、Markdown 建立用户隔离的持久化知识库。
- 让上传、列表、删除和检索失败可回滚、可测试且不泄露敏感信息。
- 将私有检索接入现有 Agent，并让题目来源可以在响应、数据库快照和历史页面中追溯。
- 用 TDD 覆盖解析、向量隔离、API 鉴权、Agent 降级、兼容性和前端构建。

**Non-Goals:**

- 本次不支持视频、网页抓取、OCR、图片理解、异步任务队列或多租户共享知识库。
- 本次不改变现有账号体系、报告算法、XP 规则、题型范围或 H5 仅预览约定。
- 本次不实现通用问答聊天接口，私有知识只服务于题目生成检索。

## Decisions

### 1. 文件与元数据分离保存

新增 `knowledge_documents` 表保存用户归属、文档 ID、原始名称、扩展名、大小、存储键、切片数量、状态和时间；原始文件保存到配置目录下按用户和 UUID 分层的路径。数据库不保存完整文本，Chroma 保存 chunk 文本及 metadata。这样列表和权限判断不依赖扫描文件系统，历史题库也不依赖实时知识库。

备选方案是只把文本放入 MySQL JSON，放弃向量索引；该方案无法支持语义检索且文档大小不可控，因此不采用。

### 2. 每用户 collection + metadata 双重隔离

使用一个稳定的用户 collection 名称（由用户 ID 生成）保存该用户的所有文档 chunk；每个 chunk 仍写入 `user_id`、`document_id`、文件名和页码 metadata。查询同时限定用户 collection 和 metadata `user_id`，删除按 `document_id` 删除向量。collection 规模和 Chroma 本地持久化适合当前单机部署，也避免把用户 ID直接暴露在共享集合查询中。

备选方案是全局 collection 只靠 metadata 过滤，虽然节省 collection 数量，但越权错误影响面更大；当前需求明确要求用户隔离，优先采用每用户 collection。

### 3. 同步上传和原子补偿

上传接口在一次请求内完成大小检查、格式选择、文本解析、切分、Embedding、Chroma 写入和数据库记录。先将文件写入临时路径，所有步骤成功后再转为正式存储键并写入 `ready` 记录；任何失败都删除临时/正式文件、已写入的 document IDs 和数据库记录。同步方式避免首版引入任务队列、轮询状态和跨进程 worker，接口以配置的单文档大小和 chunk 上限控制延迟。

### 4. LangChain 文档组件和 DashScope Embedding

使用当前 LangChain 集成中的 PDF/DOCX/Markdown loader 与 `RecursiveCharacterTextSplitter`。向量存储采用 `langchain_chroma.Chroma` 的 `persist_directory` 形式；Embedding 适配器封装 DashScope `text-embedding-v4`，写入使用 document 类型，查询使用 query 类型。Embedding 客户端放在后端服务层，API key 只从 settings 读取。

依赖版本在实现前通过当前 Python 环境解析并锁定；如果某个 loader 的可选依赖不可用，应用启动不因导入失败而崩溃，上传时返回脱敏配置错误。

### 5. Agent 工具使用显式用户上下文

现有联网检索 Agent 扩展为多源 Agent。私有检索工具由当前认证用户 ID 闭包生成，只接受查询文本，不接受调用方传入 user_id；工具内部返回统一来源对象和片段。Agent 的最终消息仍由服务层解析为来源列表，不把 Tavily 或 Chroma 原始响应直接交给前端。

题目生成继续使用现有结构化 JSON chain。检索成功时把私有/联网来源 ID、标题、片段和来源类型注入 Prompt，复用现有题量、题型、重复题和知识点校验，并增加来源 ID 存在性与证据覆盖校验；检索失败或无来源时不伪造来源，沿用当前 fallback。

### 6. API 与前端兼容

后端新增 `/api/v1/knowledge/documents` 资源，不改变现有题库和报告路径。来源模型新增可选 `source_type`、`document_id` 等字段，私有来源 URL 可以为空；旧客户端只读取原有字段。前端新增知识库页面和“我的”入口，上传使用微信 `chooseMessageFile` + `uploadFile`，列表与删除使用普通 Bearer 请求。H5 页面只提供预览状态，不宣称真实上传成功。

## Risks / Trade-offs

- [本地 Chroma 与文件系统不是同一事务] → 通过临时文件、记录状态、失败补偿删除和启动时清理未完成记录降低半成品风险；测试覆盖每个失败阶段。
- [大文档导致同步请求超时] → 配置单文件字节上限、最大页数/字符数和 chunk 上限；超过限制在解析前拒绝。后续如有需求再拆异步任务，不在本次引入。
- [Embedding 服务限流或费用增加] → 批量 Embedding、固定 chunk 上限、缺失/异常时返回稳定错误并记录非敏感错误类别；自动化测试不调用真实服务。
- [模型声称引用但证据不足] → 要求来源 ID，并在服务端检查来源存在和文本支持；两次质量重试后明确失败，不返回模板题。
- [用户上传恶意或伪装文件] → 扩展名白名单、大小限制、对应解析器读取校验、UUID 文件名和用户归属查询；不使用客户端文件名作为路径。
- [前端 API 上传返回字符串] → 复用现有上传封装，统一解析 JSON envelope，并对 401/413/422/503 显示稳定中文提示。

## Migration Plan

1. 新增幂等 SQL 表和配置项；旧表、旧题库和旧来源快照不变。
2. 在测试库执行迁移，先完成知识库服务与 API 的 TDD，再打开出题 Agent 的私有工具。
3. 默认没有文档时继续走原联网/fallback，因此可以回滚到旧出题服务而不影响现有题库。
4. 部署前为 Chroma 和知识库文件目录准备持久化磁盘，并限制目录访问权限；回滚代码时保留表和文件，恢复后可继续读取旧题库来源快照。
5. 微信端完成三种文件上传、删除、重启恢复和双账号隔离验收后，再视部署环境启用真实 DashScope Embedding。
