from src.graph import app


def main():
    initial_input = {
        "topic": "2026年具身智能机器人量产落地的主要工程瓶颈",
        "collected_data": [],
        "messages": [],
        "retry_count": 0,
        "is_approved": False,
    }

    print("====== 开始运行 DeepResearch Agent 流程 ======")

    # 执行图调度并获取最终输出
    result = app.invoke(initial_input)

    print("\n" + "=" * 50)
    print("====== 最终研报产出 ======")
    print("=" * 50)
    print(result.get("final_report"))

    print("\n====== 执行统计 ======")
    print(f"总计收集素材段落数: {len(result.get('collected_data', []))}")
    print(f"打回重试次数: {result.get('retry_count')}")


if __name__ == "__main__":
    main()
