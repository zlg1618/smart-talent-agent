"""全局配置。

数据库与大模型均可切换：
- 数据库：默认 SQLite（零配置启动），生产环境改为 MySQL 连接串即可
- 大模型：默认本地 Ollama，也可切换到任意 OpenAI 兼容的云 API
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------------- 数据库 ----------------
    # SQLite（默认）：sqlite:///./talent_agent.db
    # MySQL：mysql+pymysql://root:123456@localhost:3306/talent_ai
    database_url: str = "sqlite:///./talent_agent.db"
    db_echo: bool = False

    # ---------------- 大模型 ----------------
    # ollama：本地模型；openai_compatible：任意 OpenAI 兼容云 API
    llm_provider: str = "ollama"

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "deepseek-r1:7b"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.deepseek.com"
    openai_model: str = "deepseek-chat"

    llm_temperature: float = 0.1
    llm_timeout: int = 120

    # 大模型不可用（未装 Ollama / 未配 Key）时是否回退到规则引擎。
    # 开启后项目在无模型环境下依然能跑通完整流程，便于演示与自动化测试。
    llm_fallback_to_rule: bool = True

    # ---------------- 业务阈值 ----------------
    # 组织发展：管理幅度与组织层级健康区间
    od_span_min: float = 4.0
    od_span_max: float = 12.0
    od_depth_min: int = 3
    od_depth_max: int = 5

    # 人才发展：任职资格匹配度分档（完全胜任 / 基本胜任 / 尚有差距）
    td_match_ready: float = 0.90
    td_match_basic: float = 0.75
    td_match_gap: float = 0.60

    # 人才发展：发展项目完成率与满意度达标线
    td_program_completion_target: float = 0.70
    td_program_satisfaction_target: float = 4.0

    # ---------------- 服务 ----------------
    app_host: str = "127.0.0.1"
    app_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
