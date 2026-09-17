import logging
import json
from datetime import datetime, timezone

from .grounding import Source, extract_urls, normalize_sources

logger = logging.getLogger(__name__)


def build_grounding_agent(llm):
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
    return create_agent(model=llm, tools=[basic, deep, extract], system_prompt=(
        '你是知识获取助手。根据用户输入选择搜索摘要、深度搜索或提取 URL。'
        '最多调用两次工具，获取足够资料后停止。只返回资料，不回答用户问题。'),
        middleware=[ToolCallLimitMiddleware(run_limit=2, exit_behavior='end')])


def retrieve_sources(user_input: str) -> list[Source]:
    """Run the optional LangChain Tavily agent. Any retrieval failure is recoverable."""
    try:
        from .llm import get_llm
        from .config import settings
        if not settings.grounding_enabled or not settings.tavily_api_key:
            return []
        llm = get_llm()
        if llm is None:
            return []
        agent = build_grounding_agent(llm)
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
        return [source.__class__(**{**source.__dict__, 'fetched_at': now}) for source in normalize_sources(flattened, user_input)]
    except Exception as exc:
        logger.warning('grounding_retrieval_failed error_type=%s', type(exc).__name__)
        return []
