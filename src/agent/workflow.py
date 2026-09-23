from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from src.schemas.state import State
from src.agent.router import NodeName, should_continue
from src.agent.nodes.planner import planner_node
from src.agent.nodes.researcher import researcher_node
from src.agent.nodes.evaluator import evaluator_node
from src.agent.nodes.writer import writer_node


def build_graph() -> CompiledStateGraph:
    """构建、编排并编译 Deep Research Agent 的 LangGraph 状态图。

    工作流拓扑结构：
        [START] -> (planner) -> (researcher) -> (evaluator)
                                     ^              |
                                     | (打回重搜)     | (通过 / 熔断)
                                     +--------------+
                                                    v
                                                (writer) -> [END]

    Returns:
        CompiledStateGraph: 原生支持 ainvoke() 与 astream_events() 的编译后异步执行图。
    """
    workflow = StateGraph(State)

    # 1. 注册工作流节点
    workflow.add_node(NodeName.PLANNER, planner_node)
    workflow.add_node(NodeName.RESEARCHER, researcher_node)
    workflow.add_node(NodeName.EVALUATOR, evaluator_node)
    workflow.add_node(NodeName.WRITER, writer_node)

    # 2. 连接确定性初始边
    workflow.add_edge(START, NodeName.PLANNER)
    workflow.add_edge(NodeName.PLANNER, NodeName.RESEARCHER)
    workflow.add_edge(NodeName.RESEARCHER, NodeName.EVALUATOR)

    # 3. 连接条件决策分支（根据 Evaluator 质检结论动态路由）
    workflow.add_conditional_edges(
        NodeName.EVALUATOR,
        should_continue,
        {
            NodeName.RESEARCHER: NodeName.RESEARCHER,  # 审核不合格：返工定向补充检索
            NodeName.WRITER: NodeName.WRITER,  # 审核合格或达重试上限：放行撰写研报
        },
    )

    # 4. 研报生成完毕后终止工作流
    workflow.add_edge(NodeName.WRITER, END)

    return workflow.compile()


# 导出编译完毕的全局单例应用
app: CompiledStateGraph = build_graph()
