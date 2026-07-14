"""
技能注入器 - Skill Injector
===========================
统一的技能注入 API，封装完整的"技能池 + 用户输入 → 匹配 → 加载 prompt/tools → 打印日志"流程。

用法:
```python
injector = SkillInjector(registry=registry)
result = injector.inject(
    user_input='帮我写个 API 接口',
    skill_pool=all_active_skills,
    context=recent_messages,
)
system_prompt += result.system_prompt
tools.extend(result.tools)
```
"""

import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path

from .skill_router import SkillRouter, ScoredSkill
from .skill_registry import SkillRegistry


@dataclass
class SkillInjection:
    """技能注入结果 - 统一返回结构"""

    # 匹配到的技能列表（含分数）
    matched: List[ScoredSkill]

    # 拼装好的 system prompt 片段（直接追加到 system message）
    system_prompt: str

    # 所有匹配技能的工具定义（直接合并到 tools 列表）
    tools: List[Dict]

    # 工具来源映射 (toolName → "技能:xxx")
    source_mapping: Dict[str, str]

    @property
    def is_empty(self) -> bool:
        return len(self.matched) == 0

    @property
    def is_not_empty(self) -> bool:
        return len(self.matched) > 0

    @property
    def skill_count(self) -> int:
        return len(self.matched)


# 空注入（无匹配技能时）
EMPTY_INJECTION = SkillInjection(
    matched=[],
    system_prompt='',
    tools=[],
    source_mapping={},
)


class SkillInjector:
    """统一技能注入器 - 三端共享的 Skill 按需加载 API"""

    def __init__(
        self,
        registry: SkillRegistry,
        embedding_func: Optional[callable] = None,
        source: str = 'SkillInjector',
    ):
        """
        初始化注入器

        Args:
            registry: 技能注册表（用于加载 SKILL.md 和 tools.json）
            embedding_func: 可选的 embedding 函数（启用语义匹配）
            source: 调用来源标识（用于日志区分）
        """
        self.registry = registry
        self.embedding_func = embedding_func
        self.source = source

        # 内部路由器实例（跨轮次复用以维护 pin 状态）
        self._router = SkillRouter(embedding_func=embedding_func)

        # 已加载的 skill prompt 缓存（避免重复磁盘 IO）
        self._prompt_cache: Dict[str, str] = {}

    def inject(
        self,
        user_input: str,
        skill_pool: List[Dict],
        context: List[str] = None,
        force_all: bool = False,
    ) -> SkillInjection:
        """
        核心 API - 根据用户输入，从技能池中按相关性注入

        Args:
            user_input: 当前用户输入文本
            skill_pool: 可选的技能池（所有可能被注入的技能）
            context: 最近对话上下文（辅助匹配）
            force_all: 强制全量注入（忽略相关性，用于无法判断时的 fallback）

        Returns:
            SkillInjection，包含拼装好的 prompt、tools、来源映射
        """
        if not skill_pool:
            return EMPTY_INJECTION

        context = context or []

        # 预加载所有技能的 prompt（带缓存）
        skill_prompts = self._load_prompts(skill_pool)

        # 决定注入哪些技能
        if force_all or not user_input:
            # 无输入或强制模式：全量注入
            matched = [
                ScoredSkill(
                    skill_id=s['id'],
                    skill_name=s['name'],
                    score=1.0,
                    match_reason='强制全量' if force_all else '无输入(全量)',
                )
                for s in skill_pool
            ]
            self._log_injection(matched, full_mode=True)
        else:
            # 相关性路由
            matched = self._router.resolve(
                user_input=user_input,
                recent_context=context,
                all_skills=skill_pool,
                skill_prompts=skill_prompts,
            )

            # 无命中 → 不注入任何技能（不相关就不用）
            if not matched:
                print(f'[{self.source}] 本轮未命中任何技能，跳过注入')
                return EMPTY_INJECTION

        # 加载匹配技能的 tools 和 prompt
        tools = []
        source_mapping = {}
        prompt_parts = []

        for scored in matched:
            skill = next((s for s in skill_pool if s['id'] == scored.skill_id), None)
            if not skill:
                continue

            # 加载 tools.json
            skill_tools = self.registry.load_skill_tools(skill)
            for tool in skill_tools:
                name = tool.get('function', {}).get('name', '')
                if name:
                    source_mapping[name] = f"技能:{skill['name']}"
            tools.extend(skill_tools)

            # 加载 SKILL.md prompt
            prompt = skill_prompts.get(skill['id'], '')
            if prompt:
                path_line = f"> 技能目录: {skill.get('path', '')}\n" if skill.get('path') else ''
                prompt_parts.append(
                    f"\n\n---\n# 技能: {skill['name']}\n{path_line}\n{prompt}"
                )

        return SkillInjection(
            matched=matched,
            system_prompt=''.join(prompt_parts),
            tools=tools,
            source_mapping=source_mapping,
        )

    def pin_skill(self, skill_id: str):
        """将某个技能 pin 住（对话中被实际使用后，后续轮次始终注入）"""
        self._router.pin_skill(skill_id)

    def clear_pins(self):
        """清除所有 pin（新会话时调用）"""
        self._router.clear_pins()

    def clear_cache(self):
        """清除 prompt 缓存（技能文件变更后调用）"""
        self._prompt_cache.clear()

    # ─── 内部方法 ─────────────────────────────────────────────

    def _load_prompts(self, skills: List[Dict]) -> Dict[str, str]:
        """批量加载技能 prompt（带内存缓存）"""
        result = {}
        for skill in skills:
            skill_id = skill['id']
            if skill_id in self._prompt_cache:
                result[skill_id] = self._prompt_cache[skill_id]
            else:
                try:
                    prompt = self.registry.load_skill_prompt(skill)
                    self._prompt_cache[skill_id] = prompt
                    result[skill_id] = prompt
                except Exception as e:
                    print(f"[{self.source}] 加载 {skill['name']} prompt 失败: {e}")
                    result[skill_id] = ''
        return result

    def _log_injection(self, skills: List[ScoredSkill], full_mode: bool = False):
        """打印注入日志"""
        if full_mode:
            names = ', '.join(s.skill_name for s in skills)
            print(f'[{self.source}] 全量注入 {len(skills)} 个技能: {names}')
        # 相关性模式的日志由 SkillRouter._log_loaded_skills 负责
