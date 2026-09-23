"""Deep Research Agent 本地开发调试运行脚本。

通过 LangGraph invoke 接口端到端执行一次完整的调研研报生成流程，
并在终端输出执行统计与最终产出的 Markdown 研报。
"""

import sys
from src.agent import app
from src.core.logger import get_logger, setup_logging

logger = get_logger("run_dev")


def main() -> None:
    """初始化运行环境并执行深度调研任务。"""
    # 1. 初始化标准日志输出
    setup_logging()

    initial_input = {
        "topic": "2026年具身智能机器人量产落地的主要工程瓶颈",
        "collected_data": [],
        "messages": [],
        "retry_count": 0,
        "is_approved": False,
    }

    logger.info("====== 开始运行 DeepResearch Agent 流程 ======")
    logger.info("调研目标课题: %s", initial_input["topic"])

    # 2. 执行图调度并获取最终输出
    result = app.invoke(initial_input)

    # 3. 输出执行统计信息
    collected_count = len(result.get("collected_data", []))
    retry_count = result.get("retry_count", 0)

    logger.info(
        "工作流执行完毕 | 收集事实段落数: %d | 打回重试次数: %d",
        collected_count,
        retry_count,
    )

    # 4. 打印最终 Markdown 深度研报
    sys.stdout.write("\n" + "=" * 60 + "\n")
    sys.stdout.write("                      最终研报产出                      \n")
    sys.stdout.write("=" * 60 + "\n\n")

    final_report = result.get("final_report", "未生成研报内容")
    sys.stdout.write(f"{final_report}\n\n")
    sys.stdout.write("=" * 60 + "\n")


if __name__ == "__main__":
    main()
