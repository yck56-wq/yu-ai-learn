from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    deepseek_api_key: str = ''
    deepseek_base_url: str = 'https://api.deepseek.com'
    deepseek_model: str = 'deepseek-chat'
    tavily_api_key: str = ''
    grounding_enabled: bool = True
    grounding_timeout_seconds: int = 15
    grounding_max_tool_calls: int = 2
    mysql_host: str = 'localhost'
    mysql_port: int = 3306
    mysql_user: str = ''
    mysql_password: str = ''
    mysql_database: str = 'yu_ai_learn'
    wechat_app_id: str = ''
    wechat_app_secret: str = ''
    jwt_secret: str = ''
    avatar_storage_dir: str = str(Path(__file__).resolve().parents[1] / 'uploads' / 'avatars')
    knowledge_storage_dir: str = str(Path(__file__).resolve().parents[1] / 'uploads' / 'knowledge')
    chroma_persist_directory: str = str(Path(__file__).resolve().parents[1] / 'data' / 'chroma')
    embedding_api_key: str = ''
    embedding_model: str = 'text-embedding-v4'
    embedding_base_url: str = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    knowledge_max_file_bytes: int = 20 * 1024 * 1024
    knowledge_max_text_chars: int = 2_000_000
    knowledge_chunk_size: int = 800
    knowledge_chunk_overlap: int = 120
    knowledge_max_chunks: int = 2_000
    public_base_url: str = ''
    model_config = SettingsConfigDict(env_file=('.env','backend/.env'), extra='ignore')
settings=Settings()
