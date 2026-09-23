import logging
import sys
from typing import Optional

from src.core.config import settings


def setup_logging(log_level: Optional[str] = None) -> None:
    """初始化全局日志系统配置。

    Args:
        log_level: 日志级别（如 DEBUG, INFO, WARNING, ERROR）。若未指定，默认使用 settings.log_level。
    """
    level_name = (log_level or settings.log_level).upper()
    level = getattr(logging, level_name, logging.INFO)

    log_format = (
        "%(asctime)s | %(levelname)-7s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"

    # 配置根日志器
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )

    # 适当降低第三方库的过于嘈杂的日志输出
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取指定命名空间的 Logger 实例。

    Args:
        name: 模块名称，通常传入 __name__。

    Returns:
        logging.Logger: 命名日志记录器。
    """
    return logging.getLogger(name)
