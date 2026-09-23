from typing import Optional

from langchain_openai import ChatOpenAI

from src.core.config import settings


def get_llm(
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> ChatOpenAI:
    """获取根据统一配置实例化的 ChatOpenAI 模型客户端。

    支持本地推理服务（如 LM Studio、Ollama、vLLM）以及 OpenAI 官方或兼容 API。

    Args:
        temperature: 采样温度值（0.0 ~ 1.0），控制生成文本的确定性与发散度。
        max_tokens: 允许模型生成的最大 Token 数量，避免长输出被中途阶段引发解析异常。

    Returns:
        ChatOpenAI: 已配置基础 URL、模型名、API 密钥、采样温度与最大生成长度的模型客户端。
    """
    return ChatOpenAI(
        model=settings.model_name,
        base_url=settings.openai_base_url,
        api_key=settings.openai_secret_key,
        temperature=temperature,
        max_tokens=max_tokens or settings.max_tokens,
    )
