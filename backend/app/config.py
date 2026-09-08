from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    deepseek_api_key: str = ''
    deepseek_base_url: str = 'https://api.deepseek.com'
    deepseek_model: str = 'deepseek-chat'
    mysql_host: str = 'localhost'
    mysql_port: int = 3306
    mysql_user: str = ''
    mysql_password: str = ''
    mysql_database: str = 'yu_ai_learn'
    wechat_app_id: str = ''
    wechat_app_secret: str = ''
    jwt_secret: str = ''
    model_config = SettingsConfigDict(env_file=('.env','backend/.env'), extra='ignore')
settings=Settings()
