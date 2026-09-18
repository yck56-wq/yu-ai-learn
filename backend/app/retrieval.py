import logging
import json
from datetime import datetime, timezone

from .grounding import Source, extract_urls, normalize_sources

logger = logging.getLogger(__name__)


def retrieve_private_sources(user_id: int, query: str, k: int = 4, document_id: str | None = None) -> list[Source]:
    try:
        from .services.embedding_service import DashScopeEmbeddings
        from .vector_store import PrivateVectorStore
        store = PrivateVectorStore(user_id, DashScopeEmbeddings())
        documents = store.similarity_search(query, k=k, document_id=document_id) if document_id else store.similarity_search(query, k=k)
        result = []
        for index, document in enumerate(documents):
            metadata = document.metadata or {}
            document_id = metadata.get('document_id')
            if not document_id:
                continue
            result.append(Source(
                id=f'p{index + 1}', title=str(metadata.get('file_name') or '私有文档'),
                publisher='我的知识库', snippet=document.page_content[:2000],
                source_type='private', document_id=str(document_id),
                file_name=str(metadata.get('file_name') or '') or None,
                page=metadata.get('page'),
            ))
        return result
    except Exception as exc:
        logger.warning('private_retrieval_failed error_type=%s', type(exc).__name__)
        return []


def build_grounding_agent(llm, user_id: int | None = None, document_id: str | None = None):
    from langchain.agents import create_agent
    from langchain.agents.middleware import ToolCallLimitMiddleware
    from langchain_tavily import TavilyExtract, TavilySearch
    from .config import settings
    tavily_api_key = settings.tavily_api_key or None
    basic = TavilySearch(name='tavily_search_basic', max_results=3, include_raw_content=False,
                         tavily_api_key=tavily_api_key)
    deep = TavilySearch(name='tavily_search_deep', max_results=5, include_raw_content=True,
                        tavily_api_key=tavily_api_key)
    extract = TavilyExtract(name='tavily_extract', format='markdown', tavily_api_key=tavily_api_key)
    tools = [basic, deep, extract]
    if user_id is not None:
        from langchain_core.tools import tool

        @tool
        def private_knowledge_search(query: str) -> str:
            """Search the current user's private learning documents."""
            return '\n'.join(f'[{source.id}] {source.title}\n{source.snippet}'
                             for source in retrieve_private_sources(user_id, query, document_id=document_id)) or '未找到私有资料。'

        tools.insert(0, private_knowledge_search)
    return create_agent(model=llm, tools=tools, system_prompt=(
        '你是知识获取助手。根据用户输入选择搜索摘要、深度搜索或提取 URL。'
        '最多调用两次工具，获取足够资料后停止。只返回资料，不回答用户问题。'),
        middleware=[ToolCallLimitMiddleware(run_limit=2, exit_behavior='end')])


def retrieve_sources(user_input: str, user_id: int | None = None, document_id: str | None = None) -> list[Source]:
    """Run the optional LangChain Tavily agent. Any retrieval failure is recoverable."""
    private_sources = retrieve_private_sources(user_id, user_input, document_id=document_id) if user_id is not None else []
    if document_id:
        return private_sources
    try:
        from .llm import get_llm
        from .config import settings
        if not settings.grounding_enabled or not settings.tavily_api_key:
            return private_sources
        llm = get_llm()
        if llm is None:
            return private_sources
        agent = build_grounding_agent(llm, user_id, document_id)
        result = agent.invoke({'messages': [{'role': 'user', 'content': user_input}]})
        messages = result.get('messages', []) if isinstance(result, dict) else []
        raw_items = []
        for message in messages:
            content = getattr(message, 'content', '')
            if isinstance(content, (dict, list)):
                parsed = content
            else:
                try:
                    parsed = json.loads(content) if isinstance(content, str) else content
                except (TypeError, ValueError):
                    parsed = None
            candidates = parsed.get('results', []) if isinstance(parsed, dict) else parsed if isinstance(parsed, list) else []
            for item in candidates:
                if isinstance(item, dict) and item.get('url'):
                    raw_items.append(item)
            if isinstance(content, str):
                for url in extract_urls(content):
                    raw_items.append({'title': '检索资料', 'url': url, 'content': content})
        flattened = raw_items
        now = datetime.now(timezone.utc).isoformat()
        web_sources = [source.__class__(**{**source.__dict__, 'fetched_at': now}) for source in normalize_sources(flattened, user_input)]
        return private_sources + web_sources
    except Exception as exc:
        logger.warning('grounding_retrieval_failed error_type=%s', type(exc).__name__)
        return private_sources
