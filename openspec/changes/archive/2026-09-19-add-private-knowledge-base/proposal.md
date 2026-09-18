## Why

当前题目生成主要依赖模型自身知识和已有联网检索，无法稳定覆盖企业内部制度、私有题库和用户上传文档等封闭知识。为让“开卷有戏”能够围绕用户自己的资料学习，需要把文档解析、用户隔离的向量检索和现有联网检索接入同一条出题链路。

## What Changes

- 新增 PDF、DOCX、Markdown 文档上传、解析、分块和持久化索引能力。
- 为每个用户建立隔离的 Chroma 私有知识库，并保存文档元数据、状态和切片统计。
- 新增当前用户知识库文档的列表、删除和越权保护接口。
- 使用 DashScope `text-embedding-v4` 生成文档与查询向量，配置与密钥仅保留在后端。
- 扩展现有 LangChain Agent，同时提供私有知识检索和 Tavily 联网检索，由 Agent 根据输入选择数据源。
- 扩展题目来源快照和证据约束，使私有文档来源可以随题库历史一起回看。
- 新增微信小程序知识库管理页面；H5 继续作为界面预览，不伪造上传成功。
- 保留现有登录、题量、题型、服务端判题、XP、报告和联网 fallback 行为。

## Capabilities

### New Capabilities

- `private-knowledge-base`: 用户文档上传、解析、索引、列表、删除、隔离检索和失败回滚。
- `agentic-multi-source-quiz-generation`: Agent 在私有知识库与联网资料之间选择检索来源，并对生成题目执行来源证据约束。

### Modified Capabilities

无。当前 `openspec/specs/` 没有已登记的能力规格；现有题库行为通过新能力规格定义兼容边界。

## Impact

- 后端 FastAPI 路由、配置、Pydantic 模型、出题服务、检索服务、文件存储和 MySQL schema。
- 新增 `langchain-community`、`langchain-text-splitters`、`langchain-chroma`、`chromadb`、DashScope SDK 及其兼容依赖。
- 前端 API 上传封装、知识库页面、资料入口、题目/历史来源展示。
- 新增后端 TDD 测试、MySQL 测试表和运行文档；现有回归测试必须保持通过。
