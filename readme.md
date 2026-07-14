# SkillServer

个人技能库。此仓库存储自定义技能、持久化 Agent 记忆和身份配置文件。

> 💡： 部分技能已作为元技能被[RemindAI](https://github.com/PythonnotJava/RemindAI)作为底层绑定

## 目录结构

```
SkillServer/
├── SKILLS/                  # 已安装的技能定义
│   ├── schedule-skill/      # 任务规划与防遗忘技能
│   ├── toolshell/           # 受控文件操作、Shell 执行与记忆技能
│   ├── skill_router/        # 技能元系统（路由、注入、注册表）
│   ├── system_detection/    # 系统检测技能
│   └── gurobi-expert/       # Gurobi Optimizer 13.0 专家技能
└── readme.md                # 本文件
```

## 技能列表

### schedule-skill（任务规划技能）

防止任务在长对话中被遗忘。维护一个持久化的 `SCHEDULE.md` 文件，采用 P0/P1/P2 优先级分层。会话开始时自动加载计划，跟踪任务完成情况，并在关键里程碑触发进度报告。

**核心功能：**
- ✅ 自动加载和创建 SCHEDULE.md
- ✅ P0/P1/P2 三级优先级管理
- ✅ 任务添加、完成、更新、归档
- ✅ 进度报告和智能建议
- ✅ 防遗忘检查机制

### toolshell（工具外壳技能）

基于 `memory.json` 配置授予大模型操作权限，并提供长期记忆能力（可选 Qdrant 向量检索）。

**核心功能：**
- ✅ 受控文件读写（边界检查、路径验证）
- ✅ Shell 命令执行（超时控制、输出截断）
- ✅ 记忆存储与召回（SQLite + 可选 Embedding）
- ✅ 操作审计日志
- ✅ normal/auto 两种模式（手动确认 vs 全自动）

### skill_router（技能元系统）

提供技能的自动路由、按需注入、注册管理能力。这是一个元技能，为其他技能提供基础设施。

**三大核心组件：**
1. **SkillRouter（技能路由器）**
   - 关键词匹配：技能名直接匹配 +0.5 分，双向关键词匹配
   - 语义相似度：可选 Embedding 余弦相似度（≥0.2 阈值）
   - Pinned Skills：已使用技能自动保持注入
   - 中英文分词：支持 bigram、停用词过滤

2. **SkillInjector（技能注入器）**
   - 统一注入 API：从技能池按相关性筛选
   - 加载 SKILL.md 和 tools.json
   - 拼装 system prompt 和 tools 列表
   - Prompt 缓存机制（避免重复磁盘 IO）

3. **SkillRegistry（技能注册表）**
   - 从 ZIP 和目录导入技能
   - 全局技能 vs 项目级临时技能
   - 工具定义归一化（兼容多种格式）
   - 元数据管理（排序、激活状态）

**性能优化：**
- 最多注入 10 个技能
- Prompt 缓存
- Pin 机制避免重复匹配
- 延迟加载

### system_detection（系统检测技能）

自动检测运行环境的操作系统、架构、Python 版本、可用工具等信息，为跨平台适配提供支持。

**核心功能：**
- ✅ 操作系统检测（Windows/Linux/macOS，版本，架构，WSL）
- ✅ Python 环境检测（版本，虚拟环境，pip）
- ✅ 常用工具检测（git, npm, docker, pip, cargo 等 30+ 工具）
- ✅ 环境变量读取（支持脱敏）
- ✅ 网络连通性测试（并发测试，DNS 检查）
- ✅ 智能命令推荐（根据系统和可用工具）

**使用场景：**
- 跨平台命令适配（Windows 用 `dir`，Linux 用 `ls`）
- 依赖安装引导（检测 pip/conda/poetry）
- 环境问题诊断（收集完整信息）
- 智能命令建议（自动适配系统）

### gurobi-expert（Gurobi 专家技能）

Gurobi Optimizer 13.0 的深度知识助手。涵盖 LP、MIP、QP、NLP、多目标优化、分解方法和经典 OR 问题（TSP、VRP、排程等）。包含参考文档和代码模板。


## 技能开发指南

### 技能文件结构

每个技能目录必须包含：
```
<skill-name>/
├── SKILL.md              # 必需：技能描述和指令
├── tools.json            # 可选：工具定义
├── .skill_meta.json      # 自动生成：元数据
└── runtime/              # 可选：运行时代码
    ├── __init__.py
    └── executor.py
```

### tools.json 格式

支持三种格式，自动归一化：

**格式 1：标准数组**
```json
[
  {
    "type": "function",
    "function": {
      "name": "tool_name",
      "description": "工具描述",
      "parameters": {...}
    }
  }
]
```

**格式 2：对象包裹**
```json
{
  "tools": [...]
}
```

**格式 3：扁平格式**
```json
[
  {
    "name": "tool_name",
    "description": "工具描述",
    "parameters": {...}
  }
]
```

### 使用技能元系统

```python
from SKILLS.skill_router import SkillRegistry, SkillInjector

# 初始化
registry = SkillRegistry(skills_path='./SKILLS')
injector = SkillInjector(registry=registry)

# 每轮对话
all_skills = registry.list_installed()
active_skills = [s.to_dict() for s in all_skills if s.is_active]

injection = injector.inject(
    user_input=user_message,
    skill_pool=active_skills,
    context=recent_context,
)

# 合并到 LLM 请求
system_prompt += injection.system_prompt
tools.extend(injection.tools)
```

## 使用方法

此目录在每个会话开始时由 CherryClaw Agent 自动加载。技能通过 Agent SDK 管理的符号链接被发现。记忆文件由 Agent 使用专用工具读写 — 不要手动编辑 `JOURNAL.jsonl`。

要添加新技能，使用技能管理工具 (`mcp__skills__skills`) 的 `init` 和 `register` 操作，或从市场使用 `install` 安装。

## 技术实现

### 元技能移植

本仓库的三个元技能（`skill_router`）从 RemindAI（Dart/Flutter）移植到 Python：

1. **SkillRouter** - 基于关键词和语义的相关性匹配
   - 中英文分词（bigram、停用词）
   - 三层匹配策略（关键词 + 语义 + Pin）
   - 相关性评分算法

2. **SkillInjector** - 按需注入和缓存管理
   - Prompt 缓存机制
   - 工具来源映射
   - 跨轮次状态维护

3. **SkillRegistry** - 技能生命周期管理
   - ZIP/目录导入
   - 全局/项目级技能
   - 工具定义归一化

### Python 实现特点

- ✅ 类型提示（Type Hints）
- ✅ Dataclass 数据模型
- ✅ 健壮的错误处理
- ✅ 跨平台兼容（Windows/Linux/macOS）
- ✅ 无外部依赖（仅标准库）

