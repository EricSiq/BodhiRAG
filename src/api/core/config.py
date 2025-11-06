#BodhiRAG-main\src\core\config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "password"
    
    # Vector DB
    chroma_path: str = "./data/chroma"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
