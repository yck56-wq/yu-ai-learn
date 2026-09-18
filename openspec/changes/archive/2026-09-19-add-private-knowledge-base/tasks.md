## 1. 配置、依赖与数据库迁移

- [x] 1.1 在 `backend/requirements.txt` 增加与当前 LangChain 版本兼容的 `langchain-community`、`langchain-text-splitters`、`langchain-chroma`、`chromadb`、DashScope SDK 和文档解析依赖；运行 `..\.venv-user\Scripts\python.exe -m pip install -r backend/requirements.txt` 并确认现有后端导入测试仍通过。
- [x] 1.2 在 `backend/app/config.py` 与 `.env.example` 增加 Embedding、Chroma、知识库目录、单文件大小、最大文本和最大 chunk 配置；写配置缺失测试，验证应用可启动且上传请求返回稳定配置错误，不输出凭证。
- [x] 1.3 新增 `sql/002_private_knowledge_base.sql` 和测试库准备逻辑，建立 `knowledge_documents` 表、用户索引和状态字段；在独立 MySQL 测试库重复执行迁移，验证幂等、外键和唯一约束。

## 2. 文档解析、切分与向量隔离（先红后绿）

- [x] 2.1 新增 `backend/tests/test_knowledge_service.py` 的失败测试，覆盖 PDF、DOCX、Markdown 选择对应 loader，错误扩展名、空文本、超限和解析异常均拒绝；先运行 `..\.venv-user\Scripts\python.exe -m pytest tests/test_knowledge_service.py -q` 确认测试按预期失败。
- [x] 2.2 实现 `backend/app/services/knowledge_service.py` 的扩展名白名单、临时文件生命周期、文本解析、`RecursiveCharacterTextSplitter` 分块和 chunk 上限；重新运行 2.1 测试确认通过。
- [x] 2.3 在 `backend/tests/test_knowledge_service.py` 增加两个用户 collection、metadata `user_id/document_id` 过滤、删除向量和服务重启持久化的失败测试；确认隔离断言先失败。
- [x] 2.4 实现 `backend/app/services/embedding_service.py` 与 `backend/app/vector_store.py`，封装 DashScope `text-embedding-v4` 的 document/query 批量调用和 `langchain_chroma.Chroma` 持久化；用假的 embedding 函数和临时目录运行隔离、删除、重启测试，禁止测试调用真实 API。
- [x] 2.5 为上传流程增加每个失败阶段的补偿测试，验证解析、Embedding、Chroma 写入或数据库写入失败后没有孤立文件、向量或 `knowledge_documents` 记录；运行该文件全量测试确认通过。

## 3. 知识库 API 与权限边界（先红后绿）

- [x] 3.1 在 `backend/tests/test_knowledge_api.py` 先写未登录 401、三种文件上传、错误扩展名、超限、列表、删除、重复删除和两个用户隔离的失败测试；运行该文件确认新增断言失败而现有测试不受影响。
- [x] 3.2 新增 `backend/app/schemas/knowledge.py`、`backend/app/repositories/knowledge_repository.py` 和 `backend/app/api/v1/routes/knowledge.py`，实现 `POST/GET/DELETE /api/v1/knowledge/documents`，所有查询绑定 `current_user`，未知或他人文档按不存在处理；让 3.1 全部通过。
- [x] 3.3 在 `backend/app/main.py` 注册路由并增加知识库异常到固定响应的映射；验证错误响应不含绝对路径、完整文件内容、凭证或上游异常原文。
- [x] 3.4 更新 `backend/tests/prepare_mysql.py`、运行说明和测试 fixture；执行 `..\.venv-user\Scripts\python.exe -m pytest -q`，确认现有用户、出题、结算和头像测试与新增知识库测试一起通过。

## 4. 多源 Agent 与题目证据约束（先红后绿）

- [x] 4.1 在 `backend/tests/test_retrieval.py` 先增加私有工具只返回当前用户 chunk、无文档空结果、私有/联网来源合并和检索异常降级测试；运行测试确认新断言失败。
- [x] 4.2 扩展 `backend/app/retrieval.py`，为当前用户创建私有检索 tool，与已有 Tavily Search/Extract tool 一起交给 `create_agent`；解析 tool message 为统一来源对象，私有来源带 `source_type`、`document_id`、文件名和页码，异常只记脱敏日志。
- [x] 4.3 在 `backend/app/models.py`、`backend/app/services/quiz_service.py` 和 `backend/app/repositories/quiz_repository.py` 增加可选私有来源字段与快照；保持已有单参数 `generate_quiz(req)` 测试兼容，通过请求上下文传递认证用户，不把 user_id 放入客户端模型字段。
- [x] 4.4 为私有来源 ID、来源支持度、无来源 fallback、未知 source ID 和证据不足重试增加 `backend/tests/test_quiz_generation.py` 测试；实现 Prompt 注入和服务端证据闸门，确认现有质量重试、题量、重复题、答案和知识点校验全部保持通过。
- [x] 4.5 在 API 生成路由传递当前用户知识库上下文并保存来源快照；运行后端全量测试，确认两个用户生成题目不会引用对方文档，历史详情不依赖再次检索。

## 5. 前端知识库管理页面（先红后绿）

- [x] 5.1 在 `frontend/tests/knowledge.test.cjs` 先增加上传请求 Bearer、JSON envelope 解析、401/413/422/503 提示和文档列表归属的失败测试；运行 `npm test` 确认新断言失败。
- [x] 5.2 扩展 `frontend/src/api.ts` 的通用上传封装，保留现有头像上传行为，同时支持知识库文件上传、状态码和稳定中文错误映射；让 5.1 通过并运行 `npm run typecheck`。
- [x] 5.3 新增 `frontend/src/domain/knowledge.ts`、`frontend/src/pages/knowledge/index.tsx`、页面配置和样式，微信端使用 `Taro.chooseMessageFile` 选择 PDF/DOCX/Markdown，调用上传、列表和删除接口；H5 显示预览说明而不伪造成功。
- [x] 5.4 在 `frontend/src/pages/profile/index.tsx` 增加“我的知识库”入口，私有来源在题目页和历史报告页显示文件名/页码，联网来源继续显示标题/URL；运行 `npm test` 和 `npm run typecheck` 确认旧答题流程兼容。
- [x] 5.5 执行 `npm run build:weapp` 与 `npm run build:h5`，检查新增页面路由、上传 API 和来源展示无编译错误；记录 H5 仅预览限制。

## 6. 端到端验证与交付文档

- [x] 6.1 使用 mock loader、embedding、Chroma 和模型完成“上传 → 列表 → 私有检索出题 → 来源快照 → 删除”的后端集成测试；验证失败回滚、跨用户隔离和服务重启读取。
- [x] 6.2 在可用测试环境运行 MySQL 迁移、后端 pytest、前端测试/typecheck/build 全套命令；对失败项先定位修复，再重复完整验证，不以单元测试替代构建检查。
- [x] 6.3 更新 `docs/用户系统开发与运行说明.md` 或新增知识库运行说明，写明目录持久化、环境变量、迁移顺序、上传限制、H5 预览边界和真实 DashScope/微信联调要求，禁止写入真实凭证。
- [x] 6.4 完成微信开发者工具验收：两个账号分别上传资料，确认互不可见；删除后无法检索；重启后列表和索引仍在；将脱敏验证结果写入文档，并确认 `git diff` 只包含本次需求相关文件及用户已有未提交改动。



