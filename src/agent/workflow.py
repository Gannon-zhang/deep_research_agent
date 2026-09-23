from typing import Any, List, Optional
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.agent.nodes.evaluator import evaluator_node
from src.agent.nodes.planner import planner_node
from src.agent.nodes.researcher import researcher_node
from src.agent.nodes.writer import writer_node
from src.agent.router import NodeName, should_continue
from src.schemas.state import State


def build_graph(
    checkpointer: Optional[Any] = None,
    interrupt_after: Optional[List[str]] = None,
) -> CompiledStateGraph:
    """构建、编排并编译 Deep Research Agent 的 LangGraph 状态图。

    支持基于 Checkpointer 的持久化与人机协同（Human-in-the-loop）断点机制。
    默认在 `planner` 节点执行完毕后挂起中断，等待人工审核确认或修改关键词提纲。

    工作流拓扑结构：
        [START] -> (planner) -> [断点中断: 等待人工审核 Plan]
                                     |
                                     v
                                (researcher) -> (evaluator)
                                     ^              |
                                     | (打回重搜)     | (通过 / 熔断)
                                     +--------------+
                                                    v
                                                (writer) -> [END]

    Args:
        checkpointer: 检查点持久化存储器，默认使用 MemorySaver()。
        interrupt_after: 需执行后挂起的节点名称列表，默认在 planner 后中断。

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

    # 5. 挂载检查点机制与断点中断
    if checkpointer is None:
        checkpointer = MemorySaver()
    if interrupt_after is None:
        interrupt_after = [NodeName.PLANNER]

    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_after=interrupt_after,
    )


# 导出编译完毕的全局单例应用（具备 MemorySaver 记忆与 Planner 后中断能力）
app: CompiledStateGraph = build_graph()
