# Deep Research Agent

基于 **LangGraph**、**FastAPI** 与 **Tavily Search** 构建的工业级深度研究智能体（Deep Research Agent）。系统模拟首席行业智库分析团队的运作机制，通过「课题拆解 $\rightarrow$ 事实检索 $\rightarrow$ 严格质检 $\rightarrow$ 定向补漏 $\rightarrow$ 引用研报撰写」的闭环自反思（Self-Correction）工作流，自动产出具备事实依据与来源角标的深度研报。

---

## 目录

- [核心特性](#核心特性)
- [工作流拓扑架构](#工作流拓扑架构)
- [项目工程目录](#项目工程目录)
- [环境依赖与配置](#环境依赖与配置)
- [快速开始](#快速开始)
  - [1. 本地命令行调试](#1-本地命令行调试)
  - [2. 启动 FastAPI Web 服务](#2-启动-fastapi-web-服务)
- [API 接口与 SSE 流式协议](#api-接口与-sse-流式协议)
- [自动化测试与代码规范](#自动化测试与代码规范)

---

## 核心特性

- **全系统原生异步化与并发检索**：工作流所有节点（Planner, Researcher, Evaluator, Writer）均采用 `async def` 协程驱动，其中 `Researcher` 采用 `asyncio.gather` 并发分发多个关键词网络检索，显著降低 I/O 等待时延。
- **高可用多搜索引擎与自动兜底**：支持 **Tavily**（同步/异步）与免密钥的 **DuckDuckGo**；具备 `FallbackSearchEngine` 自动兜底机制，主引擎故障或额度耗尽时自动无缝降级，全链路保障稳定性。
- **严格的事实角标引用**：`Writer` 节点在陈述事实与数据时强制添加 `[1]`、`[2]` 角标，并在文末输出结构化参考来源。
- **全链路 SSE 实时流式传输**：基于 FastAPI 与 LangGraph `astream_events`，支持前端逐字流式打字效果与工作流节点状态追踪。
- **工程化日志体系**：全链路采用标准 `logging` 模块，统一时间格式、日志级别与模块溯源，告别原始 `print`。

---

## 工作流拓扑架构

```mermaid
flowchart TD
    Start([START]) --> Planner[Planner: 课题多维度规划]
    Planner --> Researcher[Researcher: 外部事实检索\n(Tavily / DuckDuckGo 自动兜底)]
    Researcher --> Evaluator[Evaluator: 深度质量审查]

    Evaluator -- "评分 < 7 且未达重试上限\n(打回补漏)" --> Researcher
    Evaluator -- "评分 >= 7 (通过) 或 达重试上限 (熔断)" --> Writer[Writer: 附带角标深度研报撰写]

    Writer --> EndNode([END: 产出最终 Markdown 研报])

    classDef nodeStyle fill:#f9f9f9,stroke:#333,stroke-width:1.5px;
    class Planner,Researcher,Evaluator,Writer nodeStyle;
```

---

## 项目工程目录

```text
deep_research_agent/
├── .env.example                       # 环境变量配置模板
├── pyproject.toml                     # 项目依赖与元数据管理
├── README.md                          # 项目工程文档
├── run_dev.py                         # 本地快速体验与调度脚本
├── tests/                             # 自动化测试套件 (28 个单元测试)
│   ├── __init__.py
│   ├── test_schemas.py                # 领域实体、去重与状态测试
│   ├── test_graph.py                  # 工作流图编译与条件路由决策测试
│   ├── test_api.py                    # FastAPI 路由与 OpenAPI 规范测试
│   └── test_search.py                 # 同步/异步检索、多引擎与自动兜底测试
└── src/
    ├── __init__.py
    ├── core/                          # [核心基础设施层]
    │   ├── __init__.py
    │   ├── config.py                  # Settings 配置管理中心
    │   ├── llm.py                     # ChatOpenAI 模型客户端统一工厂
    │   └── logger.py                  # 全局日志系统配置 (setup_logging / get_logger)
    ├── schemas/                       # [数据契约与模型层]
    │   ├── __init__.py
    │   ├── domain.py                  # 领域实体 (Evidence, Plan, EvaluationResult, merge_evidences)
    │   ├── state.py                   # LangGraph 工作流全局 State 状态
    │   └── api.py                     # API 协议请求体 (ResearchRequest)
    ├── prompts/                       # [提示词资产管理层]
    │   ├── __init__.py
    │   ├── planner.py                 # Planner 课题拆解 Prompt 模板
    │   ├── evaluator.py               # Evaluator 智能质检 Prompt 模板
    │   └── writer.py                  # Writer 研报撰写 Prompt 模板
    ├── tools/                         # [外部能力扩展层]
    │   ├── __init__.py
    │   ├── base.py                    # 搜索提供者抽象基类 (BaseSearchProvider)
    │   ├── tavily.py                  # Tavily 同步与异步检索实现 (TavilySearchProvider)
    │   ├── duckduckgo.py              # 免 Key 的 DuckDuckGo 搜索实现 (DuckDuckGoSearchProvider)
    │   └── search.py                  # Fallback 自动兜底调度引擎与主入口函数
    ├── agent/                         # [智能体编排核心层]
    │   ├── __init__.py
    │   ├── router.py                  # NodeName 枚举与 should_continue 条件路由
    │   ├── workflow.py                # LangGraph 状态机编排与 app 编译
    │   └── nodes/                     # 各节点独立业务实现
    │       ├── __init__.py
    │       ├── planner.py             # 规划节点
    │       ├── researcher.py          # 检索节点
    │       ├── evaluator.py           # 质检节点
    │       └── writer.py              # 撰写节点
    └── api/                           # [Web 接口与通信服务层]
        ├── __init__.py
        ├── app.py                     # FastAPI 实例工厂 create_app() 与服务启动入口
        ├── routes.py                  # API 路由注册 (/api/research/stream)
        └── streaming.py               # SSE 异步事件流生成器
```

---

## 环境依赖与配置

### 1. 基础要求
- Python $\ge$ 3.13
- [uv](https://github.com/astral-sh/uv) 包管理器（推荐）或 pip

### 2. 环境变量配置
在项目根目录下创建 `.env` 文件（参考以下配置）：

```env
# 大模型配置（支持本地 LM Studio / vLLM / Ollama 或 OpenAI 兼容端点）
OPENAI_BASE_URL=http://127.0.0.1:1234/v1
OPENAI_API_KEY=your-openai-or-local-key
MODEL_NAME=google/gemma-4-e4b

# 搜索工具配置（Tavily 专为 LLM 设计）
TAVILY_API_KEY=tvly-your-tavily-api-key
SEARCH_PROVIDER=auto              # 优先策略: auto (优先 Tavily，失败兜底 DuckDuckGo) | tavily | duckduckgo
SEARCH_FALLBACK_ENABLED=true      # 是否开启故障自动兜底降级
SEARCH_TIMEOUT=10.0               # 搜索超时时间（秒）

# 工作流与服务配置
MAX_RETRY_COUNT=2
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
LOG_LEVEL=INFO
```

---

## 快速开始

### 1. 本地命令行调试
通过 `run_dev.py` 即可一键运行内置课题的调研全流程，终端将输出节点执行日志以及最终的 Markdown 研报：

```bash
uv run python run_dev.py
```

### 2. 启动 FastAPI Web 服务
启动 Web API 服务，提供 HTTP 与 SSE 实时数据流支持：

```bash
# 方式一：直接运行 app 模块
uv run python -m src.api.app

# 方式二：使用 uvicorn 启动
uv run uvicorn src.api.app:api --host 0.0.0.0 --port 8000 --reload
```

服务就绪后，可访问交互式 API 文档：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## API 接口与人机协同流式协议

系统原生支持 **Human-in-the-loop（人机协同审核）** 两阶段模式：

```mermaid
sequenceDiagram
    autonumber
    actor User as 用户 / 前端
    participant API as FastAPI 接口
    participant Graph as LangGraph (Checkpointer)
    
    Note over User,Graph: 【第一阶段：启动课题规划与断点挂起】
    User->>API: POST /api/research/start (topic)
    API->>Graph: ainvoke(input, config={"configurable": {"thread_id": task_id}})
    Graph-->>Graph: 执行 planner 节点后触发 interrupt_after 自动挂起
    API->>User: 返回 task_id 与生成的 plan 检索大纲 (queries, rationale)

    Note over User,Graph: 【第二阶段：人工审核提纲、状态覆盖与恢复执行】
    User->>API: POST /api/research/resume (task_id, 修正后 queries/plan)
    API->>Graph: aupdate_state(config, {"plan": revised_plan}) 覆盖状态
    API->>Graph: astream_events(None, config=config) 从断点恢复流转
    Graph-->>API: 调度 researcher (并发检索) -> evaluator -> writer
    API-->>User: 以 SSE 流式逐字推送节点状态与最终 Markdown 研报
```

### 1. 第一阶段启动：`POST /api/research/start`
- **Content-Type**: `application/json`

#### 请求体示例
```json
{
  "topic": "2026年具身智能机器人量产落地的主要工程瓶颈",
  "task_id": "可选自定义UUID"
}
```

#### 响应示例
```json
{
  "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "topic": "2026年具身智能机器人量产落地的主要工程瓶颈",
  "plan": {
    "queries": [
      "具身智能 旋转执行器 成本",
      "人形机器人 灵巧手 传感器瓶颈",
      "具身智能 2026 量产交付预期"
    ],
    "rationale": "围绕执行器核心硬件、末端感知与产业落地周期拆解"
  },
  "status": "awaiting_approval",
  "message": "Planner 规划已生成，工作流在断点处成功挂起，等待人工确认或修改检索大纲。"
}
```

### 2. 第二阶段恢复：`POST /api/research/resume`
- **Content-Type**: `application/json`
- **Accept**: `text/event-stream`

#### 请求体示例
```json
{
  "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "queries": [
    "具身智能 谐波减速器 国产替代率 2026",
    "人形机器人 灵巧手 触觉传感器量产",
    "具身智能 算力与车载芯片对比"
  ]
}
```

#### SSE 事件响应格式
服务通过 Server-Sent Events 流式下发消息，每条消息为标准的 `data: <JSON>\n\n` 格式：

| 事件类型 (`type`) | 说明 | 载荷示例 (`data`) |
| :--- | :--- | :--- |
| `node_start` | 工作流节点启动 | `{"type": "node_start", "node": "researcher"}` |
| `status_update` | 节点完成阶段性任务 | `{"type": "status_update", "node": "researcher", "message": "新增 4 条事实素材"}` |
| `report_token` | Writer 节点研报 Token 逐字增量 | `{"type": "report_token", "content": "近年来，人形机器人..."}` |
| `complete` | 全流程正常结束信号 | `{"type": "complete"}` |
| `error` | 异常报错信息 | `{"type": "error", "message": "未找到 task_id"}` |

---

## 自动化测试与代码规范

### 1. 执行静态代码检查
```bash
uv run ruff check .
```

### 2. 执行自动化单元测试
套件包含数据契约去重、图编译结构校验、质检打回熔断分支、FastAPI 端点探测等：
```bash
uv run python -m unittest discover tests
```
