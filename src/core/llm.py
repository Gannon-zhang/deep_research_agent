from langchain_openai import ChatOpenAI
from src.core.config import settings


def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    """获取根据统一配置实例化的 ChatOpenAI 模型客户端。

    支持本地推理服务（如 LM Studio、Ollama、vLLM）以及 OpenAI 官方或兼容 API。

    Args:
        temperature: 采样温度值（0.0 ~ 1.0），控制生成文本的确定性与发散度。
            - 建议结构化抽取与严谨质检时使用低温度（如 0.1~0.2）；
            - 建议研报创意撰写时使用中等温度（如 0.4~0.7）。

    Returns:
        ChatOpenAI: 已配置基础 URL、模型名、API 密钥与采样温度的模型客户端。
    """
    return ChatOpenAI(
        model=settings.model_name,
        base_url=settings.openai_base_url,
        api_key=settings.openai_secret_key,
        temperature=temperature,
    )
