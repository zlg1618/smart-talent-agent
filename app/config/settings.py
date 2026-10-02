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
    # 九宫格绩效 / 潜力分档阈值
    talent_score_low: float = 3.0
    talent_score_high: float = 4.0

    # 组织诊断阈值
    diagnosis_turnover_warning: float = 0.10
    diagnosis_turnover_danger: float = 0.20
    diagnosis_hp_ratio_warning: float = 0.10
    diagnosis_span_narrow: float = 3.0
    diagnosis_span_wide: float = 15.0
    diagnosis_tenure_short: float = 1.5

    # ---------------- 服务 ----------------
    app_host: str = "127.0.0.1"
    app_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
