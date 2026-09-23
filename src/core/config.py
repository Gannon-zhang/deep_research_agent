import os
from typing import Optional
from pydantic import SecretStr


class Settings:
    """应用程序统一配置类。

    优先读取操作系统环境变量；若未配置则加载项目根目录下的 `.env` 文件。
    提供核心服务地址、模型配置、API 密钥与运行调优参数。
    """

    def __init__(self) -> None:
        """初始化配置，加载环境变量并设定工程默认值。"""
        from dotenv import load_dotenv

        load_dotenv()

        # LLM 模型与 OpenAI 兼容网关配置
        self.openai_base_url: str = os.getenv(
            "OPENAI_BASE_URL", "http://127.0.0.1:1234/v1"
        )
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.model_name: str = os.getenv("MODEL_NAME", "google/gemma-4-e4b")

        # 外部搜索服务配置 (Tavily, DuckDuckGo 等)
        self.tavily_api_key: Optional[str] = os.getenv("TAVILY_API_KEY")
        self.search_provider: str = os.getenv("SEARCH_PROVIDER", "auto").lower()
        self.search_fallback_enabled: bool = (
            os.getenv("SEARCH_FALLBACK_ENABLED", "true").lower() == "true"
        )
        self.search_timeout: float = float(os.getenv("SEARCH_TIMEOUT", "10.0"))

        # 工作流调度与业务熔断参数
        self.max_retry_count: int = int(os.getenv("MAX_RETRY_COUNT", "2"))

        # Web API 服务参数
        self.server_host: str = os.getenv("SERVER_HOST", "0.0.0.0")
        self.server_port: int = int(os.getenv("SERVER_PORT", "8000"))

        # 日志系统参数
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")

    @property
    def openai_secret_key(self) -> SecretStr:
        """获取包装为 SecretStr 的 OpenAI API 密钥，避免在日志与堆栈中意外明文泄露。

        Returns:
            SecretStr: 密钥安全包裹对象。
        """
        return SecretStr(self.openai_api_key)


# 全局配置单例
settings = Settings()
