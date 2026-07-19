from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "root")
    DB_NAME: str = os.getenv("DB_NAME", "appstore_vc")
    
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = bool(os.getenv("DEBUG", "true"))
    
    APP_HOST: str = HOST
    APP_PORT: int = PORT
    APP_DEBUG: bool = DEBUG
    
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    SILICONFLOW_API_KEY: str = os.getenv("SILICONFLOW_API_KEY", "")
    SILICONFLOW_BASE_URL: str = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    SILICONFLOW_LLM_MODEL: str = os.getenv("SILICONFLOW_LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "siliconflow")
    
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")
    
    CHROMADB_PATH: str = os.getenv("CHROMADB_PATH", "./chromadb")
    
    APP_STORE_COUNTRY: str = os.getenv("APP_STORE_COUNTRY", "us")
    REQUEST_DELAY: float = float(os.getenv("REQUEST_DELAY", "1.0"))
    MAX_REVIEWS_PER_FETCH: int = int(os.getenv("MAX_REVIEWS_PER_FETCH", "200"))

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+mysqlconnector://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()
