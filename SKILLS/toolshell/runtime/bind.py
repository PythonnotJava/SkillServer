"""
ToolShell 绑定器
================
核心职责: 读取 SKILL.md (行为规范) + tools.json (工具定义)
         组装成完整的 Agent 套给任意大模型。

用法:
    from toolshell.runtime import bind

    agent = bind(
        llm_url="https://api.minimaxi.com/v1",
        llm_key="sk-...",
        llm_model="MiniMax-M3",
        project_root="."
    )
    agent.run()
"""

import json
from pathlib import Path
from openai import OpenAI

from .executor import Executor
from .memory import MemoryManager

# Skill 根目录 (SKILL.md 和 tools.json 所在位置)
SKILL_ROOT = Path(__file__).parent.parent.resolve()


def _load_skill_prompt(project_root: Path, config: dict, memory: MemoryManager) -> str:
    """
    读取 SKILL.md 作为行为规范，拼接运行时状态生成最终 system prompt。
    SKILL.md 是 single source of truth。
    """
    skill_md = SKILL_ROOT / "SKILL.md"
    base_prompt = skill_md.read_text(encoding="utf-8")

    # 拼接运行时上下文
    runtime_ctx = f"""

---
## 运行时状态 (自动注入)

- 项目目录: {project_root}
- 当前模式: {config.get('MODE', 'normal')}
- 记忆策略: {'长期记忆' if config.get('MIND') else '短期记忆'}
- 记忆召回: {'启用' if config.get('REMIND') else '禁用'}
- 存储后端: {'SQLite + Embedding向量' if memory.qdrant_ok else 'SQLite'}
- 会话ID: {memory.session_id[:8]}
"""

    # 如果 REMIND=true，附加召回的记忆
    if config.get("REMIND"):
        recalled = memory.recall("项目 上下文 决策 重要", limit=5)
        if recalled:
            runtime_ctx += "\n## 已召回的历史记忆\n"
            for i, m in enumerate(recalled, 1):
                runtime_ctx += f"{i}. [{m['type']}] (重要性:{m.get('importance',0):.1f}) {m['content'][:200]}\n"

    return base_prompt + runtime_ctx


def _load_tools() -> list:
    """从 tools.json 加载工具定义"""
    tools_path = SKILL_ROOT / "tools.json"
    with open(tools_path, encoding="utf-8") as f:
        return json.load(f)


class ToolShellAgent:
    """
    绑定了 ToolShell 技能的 Agent 实例。

    技能 = SKILL.md(行为) + tools.json(能力) + runtime(执行)
    大模型 = 任意支持 function calling 的 LLM API
    """

    def __init__(self, llm_url: str, llm_key: str, llm_model: str, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.llm_model = llm_model

        # 加载项目配置
        config_path = self.project_root / "memory.json"
        if not config_path.exists():
            raise FileNotFoundError(f"未找到 memory.json: {config_path}")
        with open(config_path, encoding="utf-8") as f:
            self.config = json.load(f)

        # 初始化各层
        self.memory = MemoryManager(self.project_root, self.config)
        self.executor = Executor(self.project_root, self.memory, self.config)
        self.client = OpenAI(base_url=llm_url, api_key=llm_key)

        # 从 skill 文件加载
        self.tools = _load_tools()
        self.system_prompt = _load_skill_prompt(self.project_root, self.config, self.memory)
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def run(self):
        """交互式对话循环"""
        c = self.config
        print("=" * 60)
        print("  ToolShell Agent")
        print(f"  模型: {self.llm_model}")
        print(f"  模式: {c.get('MODE','normal')} | 记忆: {'长期' if c.get('MIND') else '短期'} | 召回: {'开' if c.get('REMIND') else '关'}")
        print(f"  存储: {'SQLite + Qdrant' if self.memory.qdrant_ok else 'SQLite'}")
        print(f"  技能: {SKILL_ROOT / 'SKILL.md'}")
        print("=" * 60)
        print("  /quit 退出 | /recall <query> 手动召回")
        print()

        while True:
            try:
                user_input = input("你: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not user_input:
                continue
            if user_input == "/quit":
                break
            if user_input.startswith("/recall "):
                self._handle_recall(user_input[8:])
                continue

            self.chat(user_input)

        self._shutdown()

    def chat(self, user_input: str) -> str:
        """单轮对话: 输入 → LLM → 工具调用循环 → 回复"""
        self.messages.append({"role": "user", "content": user_input})

        while True:
            try:
                response = self.client.chat.completions.create(
                    model=self.llm_model,
                    messages=self.messages,
                    tools=self.tools,
                    tool_choice="auto",
                )
            except Exception as e:
                print(f"\n[ToolShell] LLM 错误: {e}\n")
                self.messages.pop()
                return ""

            msg = response.choices[0].message
            self.messages.append(msg.model_dump())

            if not msg.tool_calls:
                if msg.content:
                    print(f"\n助手: {msg.content}\n")
                return msg.content or ""

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)
                print(f"  [工具] {fn_name}({self._brief(fn_args)})")
                result = self.executor.run(fn_name, fn_args)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

    def _handle_recall(self, query: str):
        results = self.memory.recall(query)
        print(f"\n[ToolShell] 召回 {len(results)} 条:")
        for r in results:
            print(f"  [{r['type']}] score={r.get('score',0):.2f} | {r['content'][:100]}")
        print()

    def _shutdown(self):
        self.memory.store("会话正常结束", "context", 0.3)
        print("\n[ToolShell] 会话结束。")

    def _brief(self, args: dict) -> str:
        s = json.dumps(args, ensure_ascii=False)
        return s[:80] + "..." if len(s) > 80 else s


def bind(llm_url: str, llm_key: str, llm_model: str, project_root: str = ".") -> ToolShellAgent:
    """
    将 ToolShell 技能绑定到一个大模型。

    这是对外的核心 API。一行调用完成绑定:
        agent = bind(llm_url="...", llm_key="...", llm_model="...")
        agent.run()
    """
    return ToolShellAgent(llm_url, llm_key, llm_model, project_root)
