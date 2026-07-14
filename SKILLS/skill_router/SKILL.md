# Skill Meta System - 技能元系统

> 提供技能的自动路由、按需注入、注册管理能力。这是一个元技能，为其他技能提供基础设施。

## 核心组件

### 1. SkillRouter - 技能路由器

基于用户输入的相关性匹配，决定注入哪些技能。

**三层匹配策略：**
1. **关键词触发**（快速，0ms）
   - 技能名直接出现：+0.5 分
   - 反向匹配（技能关键词在输入中）：每个 +0.08，上限 0.5
   - 正向匹配（输入关键词在技能中）：每个 +0.06，上限 0.4

2. **语义相似度**（需要 embedding 配置）
   - 使用余弦相似度计算输入与技能描述的匹配度
   - 阈值：≥ 0.2 才注入

3. **Pinned Skills**
   - 对话中已使用的技能自动 pin 住
   - 后续轮次始终注入（满分 1.0）

**分词策略：**
- 英文/数字：按空格分割，保留 ≥2 字符
- 中文：bigram 滑动窗口（2字一组）
- 过滤停用词（中英文）

**配置参数：**
- `MAX_ACTIVE_SKILLS = 10`：单轮最多注入技能数
- `RELEVANCE_THRESHOLD = 0.2`：最低相关性分数

### 2. SkillInjector - 技能注入器

统一的技能注入 API，封装完整流程。

**主要功能：**
- 从技能池中按相关性筛选技能
- 加载匹配技能的 SKILL.md 和 tools.json
- 拼装 system prompt 和 tools 列表
- 维护工具来源映射（`toolName → "技能:xxx"`）
- 支持强制全量注入模式

**缓存机制：**
- 内存缓存 SKILL.md 内容，避免重复磁盘 IO
- 跨轮次复用路由器实例，维护 pin 状态

**用法示例：**
```python
injector = SkillInjector(registry=registry, embedding_func=embed_func)
result = injector.inject(
    user_input='帮我写个 API 接口',
    skill_pool=all_active_skills,
    context=recent_messages,
)
system_prompt += result.system_prompt
tools.extend(result.tools)
```

### 3. SkillRegistry - 技能注册表

管理技能的生命周期：导入、删除、加载、排序。

**支持的技能类型：**
- **全局技能**：安装到 `SKILLS/` 目录，持久化
- **项目级临时技能**：存放在 `<工作目录>/.toolshell/skills/`，跟随项目

**导入方式：**
- `import_from_zip(zip_path)`：从 ZIP 包导入
- `install_from_directory(source_dir)`：从目录安装到全局

**元数据管理：**
- `.skill_meta.json`：存储 id、安装时间、激活状态、排序索引
- 支持自定义描述（不从 SKILL.md 自动解析）

**工具定义归一化：**
- 兼容扁平格式 `{ "name", "description", "parameters" }`
- 兼容嵌套格式 `{ "type":"function", "function":{...} }`
- 兼容对象包裹 `{ "tools": [...] }`
- 统一输出为 OpenAI 标准嵌套格式

## 技能文件结构

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

### SKILL.md 格式
Markdown 格式，包含：
- 技能功能描述
- 触发条件
- 使用方式
- 配置参数
- 边界和限制

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

## 使用场景

### 1. 对话系统集成
在每轮对话前，根据用户输入动态注入相关技能：
```python
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

### 2. API Server 集成
三端共享（对话页、API Server、在线服务）：
```python
class AgentSession:
    def __init__(self):
        self.injector = SkillInjector(...)
    
    def process_message(self, user_input):
        injection = self.injector.inject(
            user_input=user_input,
            skill_pool=self.get_active_skills(),
        )
        return self.llm_call(injection.system_prompt, injection.tools)
```

### 3. 项目级技能
工作目录下的临时技能，恒定激活：
```python
# 扫描项目技能
project_skills = registry.list_project_skills(work_dir='/path/to/project')

# 合并全局和项目技能
all_skills = global_skills + project_skills
```

## 性能优化

1. **Prompt 缓存**：避免重复读取 SKILL.md
2. **Pin 机制**：已使用技能自动保持注入
3. **延迟加载**：只加载匹配技能的文件
4. **截断策略**：最多注入 10 个技能

## 扩展点

### 自定义 Embedding 函数
```python
def my_embed(text: str) -> List[float]:
    # 调用你的 embedding API
    return [0.1, 0.2, ...]

injector = SkillInjector(
    registry=registry,
    embedding_func=my_embed,
)
```

### 自定义相关性算法
继承 `SkillRouter` 并重写 `_keyword_score` 或 `_semantic_match`。

## 边界

- 不处理工具执行（由各技能的 runtime 负责）
- 不处理对话历史管理
- 不处理 LLM 调用
- 单个技能最多 100 个工具（超过则截断）

## 依赖

- Python 3.8+
- 标准库：`json`, `re`, `math`, `pathlib`, `zipfile`, `shutil`
- 可选：embedding 函数（语义匹配）
