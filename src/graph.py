from langgraph.graph import StateGraph, START, END

from src.state import State
from src.nodes import planner_node, researcher_node, evaluator_node, writer_node


def should_continue(state: State) -> str:
    """条件路由函数：根据 evaluator 的评审结果决定走向"""
    is_approved = state.is_approved
    retry_count = state.retry_count

    if is_approved or retry_count >= 2:
        return "writer"
    return "researcher"


def build_graph():
    # 1. 实例化图并传入 State 类型
    workflow = StateGraph(State)

    # 2. 注册所有节点
    workflow.add_node("planner", planner_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("writer", writer_node)

    # 3. 连接固定边
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "evaluator")

    # 4. 连接条件分支边（evaluator 执行完后的流向）
    workflow.add_conditional_edges(
        "evaluator",
        should_continue,
        {
            "researcher": "researcher",  # 打回继续调研
            "writer": "writer",  # 通过进入撰写
        },
    )

    # 5. writer 完成后流向结束
    workflow.add_edge("writer", END)

    # 6. 编译并返回可运行图
    return workflow.compile()


# 导出编译好的图对象
app = build_graph()
