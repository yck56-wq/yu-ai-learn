## Context

当前后端 `quiz_service` 已使用 LangChain 的 `ChatPromptTemplate`、`ChatOpenAI.with_structured_output(..., method="json_mode")` 和 Pydantic 校验，并对重复题、答案、选项和知识点覆盖做有限重试。题库目前没有来源字段，也没有检索层；前端按现有 `questions` 结构渲染。详见 `proposal.md` 与 `specs/grounded-quiz-generation/spec.md`。

Context7 核对结果：Taro 继续使用 `Taro.request()` 和既有导航 API；LangChain 当前文档支持 `ChatPromptTemplate`、`langchain_openai.ChatOpenAI`、`with_structured_output`，并可用 `include_raw=True` 获取解析错误；LangChain 当前 Agent 路径使用 `create_agent`，运行时基于 LangGraph；DeepSeek 官方文档要求 JSON 输出时使用 `response_format: {type: "json_object"}`，并在提示词中明确要求 JSON，同时注意截断风险。现有项目依赖版本与原有用法兼容；新增 Agent 依赖需在实现阶段锁定并验证兼容版本。

## Goals / Non-Goals

**Goals:**

- 在出题前增加基于 LangChain Agent 的联网检索编排，支持搜索和 URL 提取。
- 根据主题时效性决定是否必须检索，并把来源证据注入出题 Prompt。
- 在模型输出后增加证据覆盖校验，保留现有结构化输出和重复题校验。
- 扩展题库响应和持久化快照，支持前端展示来源与失败状态。
- 让检索超时、来源不足和证据不一致成为可测试、可观测的稳定错误。

**Non-Goals:**

- 不在本次引入私有 RAG、向量数据库或多模态输入；Agent 仅负责获取资料，不负责最终出题。
- 不把检索结果直接当作答案；最终题目仍须经过模型结构校验和业务质量校验。
- 不改变现有答题、报告结算、JWT 鉴权和 XP 规则。
- 不承诺“联网后绝对正确”；来源质量和模型判断仍需持续评估。

## Decisions

### 1. 采用 LangChain Agent + Tavily Search/Extract 工具获取资料

使用 `langchain-tavily` 提供 Tavily Search 与 Tavily Extract 两类工具，并将 Search 实例化为轻量摘要和深度原文两个配置变体，由 `create_agent` 根据用户输入选择。轻量 Search 固定较小 `max_results` 且不含原文，深度 Search 固定较大 `max_results` 并包含原文；这是因为官方工具对影响响应体大小的参数存在实例化约束。Agent 在运行时动态传入 `query`、`search_depth`、`time_range`、`start_date`、`end_date`、`include_domains`、`exclude_domains`、`topic` 和 `country`；Extract 接收 `urls`，并可传入 `extract_depth`。Tavily 原生提供国家/地区范围，不提供可靠的城市字段；城市需求通过查询词地理限定或后续专用服务处理。工具结果统一转换为来源对象（标题、URL、发布者、时间、摘要、抓取时间），服务层不依赖 Tavily 原始响应。

备选方案是直接在 Prompt 中要求模型“自己联网”，但无法获得稳定来源、无法测试检索失败，也无法保证历史可追溯，因此不采用。

### 2. 使用两级证据闸门

第一层在检索后做 URL 规范化、去重、主题相关性和最低来源数量校验；第二层在模型输出后检查每题是否引用/对应至少一个来源证据，并复用现有题量、选项、答案、重复题和知识点覆盖校验。证据关系可先以来源 ID 列表或题目级 `source_ids` 实现，避免要求复杂的自动事实核验系统。

备选方案是只做文本相似度，但相似度不能证明事实正确；本设计把相似度当筛选信号，不当作真实性证明。

### 3. 两阶段串行与分级检索策略

第一阶段运行知识获取 Agent，最多调用两次工具并在获得足够资料后停止；结果不足时允许一次更保守的查询重写/补检索。第二阶段继续使用现有出题 chain，将不超过 3000 字符的资料摘要、来源元数据和来源 ID 注入 Prompt。检索异常按降级策略处理；检索成功但证据冲突或出题结果不受支持时仍拒绝相关结果。

### 4. 兼容现有 JSON 模式和结构化输出

继续使用现有 `json_mode`，因为 DeepSeek 官方 JSON Output 明确支持 `json_object`；Prompt 中同时要求合法 JSON。未来当目标模型和供应商稳定支持 JSON Schema 时，可切换 `method="json_schema"`，但不把该迁移作为本次前置条件。

### 5. 来源字段采用可选扩展

在 `Quiz` 增加可选的 `sources` 和检索状态元数据，在 `Question` 增加可选的 `source_ids`。旧客户端忽略这些字段即可继续答题；持久化时保存完整来源快照，历史回看不依赖再次联网。

### 6. 明确降级策略

搜索或 URL 提取异常时，Agent 编排层捕获异常，记录检索类型、错误类别、耗时和是否降级等非敏感日志，然后继续使用原有出题 Prompt，不注入搜索上下文。降级结果仍必须通过现有题量、选项、答案、重复题、知识点覆盖和安全校验；模型调用失败或质量校验失败时仍按原有有限重试与明确失败处理。来源不足但检索请求本身成功时，视为检索增强不可用并采用同一无上下文降级路径，响应中的来源字段为空或省略；该路径与搜索异常使用同一日志和质量校验规则。

## Risks / Trade-offs

- [检索结果含垃圾或 SEO 页面] → 域名/内容质量过滤、去重、最低来源数和来源快照；后续可增加白名单。
- [Agent 调用增加出题延迟] → Agent 设置总超时、最多两次工具调用和结果上限；超时捕获后记录日志并立即走原 Prompt，前端保持 loading 状态。
- [来源之间冲突] → 将冲突标记注入 Prompt；无法限定时拒绝生成相关题目。
- [模型声称有来源但实际未支持] → 要求题目级 `source_ids`，并做来源 ID 存在性与证据片段覆盖校验；无法验证则重试/失败。
- [响应结构变化影响旧客户端] → 新字段可选，保留原 `questions` 字段和现有错误外层结构。
- [检索凭证或用户输入泄露] → 凭证仅在后端环境变量；日志只记录错误类型、耗时和来源数量，不记录完整输入、完整响应或密钥。
- [第三方服务费用与限流] → 固定 basic/deep 工具的结果上限，限制每轮最多两次工具调用，记录非敏感用量；额度或限流异常时走无上下文降级，并增加模拟 Agent/Tavily 测试。

## Migration Plan

1. 先部署后端兼容字段、Agent/Tavily 适配器和功能开关，默认关闭时效主题强制检索以便回滚。
2. 在测试环境启用时效主题识别、来源校验和题目级证据约束，运行现有回归测试及新增检索模拟测试。
3. 前端增加来源折叠展示和稳定错误提示；旧客户端可继续答题。
4. 生产逐步开启；若检索服务异常，将开关切回旧路径，仅保留现有结构化题目校验。

## Open Questions

- 首版 Tavily 账户、白名单域名、费用上限和 Agent 依赖的具体兼容版本需在实现前依据部署环境确认；这些不改变本规格的用户可见行为。
