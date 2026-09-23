from typing import Any, Optional
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.agent.nodes.evaluator import evaluator_node
from src.agent.nodes.planner import planner_node
from src.agent.nodes.researcher import researcher_node
from src.agent.nodes.writer import writer_node
from src.agent.router import should_continue
from src.schemas.domain import NodeName
from src.schemas.state import State


def create_research_graph(
    checkpointer: Optional[Any] = None,
    enable_hitl: bool = True,
    interrupt_before: Optional[list] = None,
    interrupt_after: Optional[list] = None,
) -> CompiledStateGraph:
    """创建并编译调研状态图。

    工作流拓扑结构：
        [START] -> (planner) -> 【断点拦截: interrupt_before=['researcher']】
                                     │
                                     ▼
                                (researcher) -> (evaluator)
                                     ^              |
                                     | (打回重搜)     | (通过 / 熔断)
                                     +--------------+
                                                    v
                                                (writer) -> [END]

    Args:
        checkpointer: 状态持久化检查点，若为 None 则默认使用 MemorySaver()。
        enable_hitl: 是否开启人工介入审批拦截（Human-in-the-loop），开启时在进入 researcher 节点前自动中断。
        interrupt_before: 自定义前置中断节点列表（若指定则覆盖 enable_hitl 默认行为）。
        interrupt_after: 自定义后置中断节点列表。

    Returns:
        CompiledStateGraph: 编译后支持 ainvoke()、update_state() 与 astream_events() 的图对象。
    """
    workflow = StateGraph(State)

    # 注册节点
    workflow.add_node(NodeName.PLANNER, planner_node)
    workflow.add_node(NodeName.RESEARCHER, researcher_node)
    workflow.add_node(NodeName.EVALUATOR, evaluator_node)
    workflow.add_node(NodeName.WRITER, writer_node)

    # 连接边
    workflow.add_edge(START, NodeName.PLANNER)
    workflow.add_edge(NodeName.PLANNER, NodeName.RESEARCHER)
    workflow.add_edge(NodeName.RESEARCHER, NodeName.EVALUATOR)

    workflow.add_conditional_edges(
        NodeName.EVALUATOR,
        should_continue,
        {
            NodeName.RESEARCHER: NodeName.RESEARCHER,
            NodeName.WRITER: NodeName.WRITER,
        },
    )
    workflow.add_edge(NodeName.WRITER, END)

    # 实例化检查点
    saver = checkpointer if checkpointer is not None else MemorySaver()

    # 中断拦截逻辑
    if interrupt_before is not None:
        ib = interrupt_before
    else:
        ib = [NodeName.RESEARCHER] if enable_hitl else []

    ia = interrupt_after if interrupt_after is not None else []

    return workflow.compile(
        checkpointer=saver,
        interrupt_before=ib,
        interrupt_after=ia,
    )


# 导出带全局单例持久化的图对象
graph_app: CompiledStateGraph = create_research_graph()
