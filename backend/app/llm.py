from .config import settings

def get_llm():
    if not settings.deepseek_api_key: return None
    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=settings.deepseek_model,base_url=settings.deepseek_base_url,api_key=settings.deepseek_api_key,temperature=0.6,timeout=45,max_tokens=4000,max_retries=0)
    except ImportError:
        return None
