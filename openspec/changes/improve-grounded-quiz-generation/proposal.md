## Why

当前出题链路只把用户输入交给模型，并依赖模型自身训练知识。对于 Harness Engineering 等较新的主题，模型可能无法识别知识空白，进而生成偏离主题或事实过时的题目。引入联网检索和来源约束，可以让题目建立在近期可核验资料上，并在资料不足时明确阻止不可靠出题。

## What Changes

- 在生成题目前由 LangChain Agent 判断输入形态和检索意图，选择 Tavily 关键词搜索或 URL 页面提取；Search 支持轻量摘要与深度原文两种配置。
- 允许 Agent 根据主题复杂度动态设置搜索深度、时间范围、结果主题、日期和国家/地区范围；不承诺 Tavily 原生城市级参数。
- 对检索结果进行去重、相关性筛选和最小来源质量校验，保留标题、URL、发布时间（若可得）及摘要/摘录。
- 让模型只能基于经过筛选的资料生成题目、解析和知识摘要，禁止把未获来源支持的内容写成确定事实。
- 为题库增加来源与时效信息，便于前端展示“依据哪些资料出题”。
- 搜索或页面提取异常时捕获错误并记录非敏感日志，继续使用原 Prompt、无搜索上下文生成题目；来源不足或生成结果质量不合格时仍执行质量校验和明确失败。
- 保留现有题型、题量、重复题校验、服务端鉴权和报告接口兼容性。

## Capabilities

### New Capabilities

- `grounded-quiz-generation`: 基于联网检索资料、来源校验和证据约束生成可追溯题库，并在无法可靠生成时返回可识别失败状态。

### Modified Capabilities

无。本项目当前没有已登记的主规格文件；相关行为由上面的新能力规格覆盖。

## Impact

- 后端出题服务、Prompt、Pydantic 题库模型和 `/api/v1/quiz/generate` 响应结构。
- 新增 `langchain-tavily`/Agent 适配层、来源规范化/去重/相关性校验和可配置超时、结果数、时间范围；Search 的 `max_results` 与 `include_raw_content` 按官方约束通过不同实例配置。
- 前端题库类型、生成状态和题目/报告页面的来源展示。
- 新增检索及证据约束相关测试；需要为检索服务配置外部 API 凭证和限流策略。
- 继续使用现有 FastAPI、Pydantic、LangChain、`langchain-openai` 和 Taro 技术栈；新增 LangChain Agent 运行时、`langchain-tavily` 和其所需的 `langgraph`，但不引入完整 RAG 私有知识库。
