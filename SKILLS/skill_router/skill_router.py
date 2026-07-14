"""
技能路由器 - Skill Router
=========================
基于用户输入的相关性匹配，按需注入技能。

三层策略：
1. 关键词触发（快速，0ms）
2. 语义相似度（embedding，需要配置）
3. Agent 运行时自主拉取（load_skill 工具）

每轮对话匹配一次，最多注入 [max_active_skills] 个技能。
"""

import re
import math
import json
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ScoredSkill:
    """技能相关性匹配结果"""
    skill_id: str
    skill_name: str
    score: float
    match_reason: str


class SkillRouter:
    """技能路由器 - 根据用户输入匹配最相关的技能"""

    # 单轮最多注入的技能数量
    MAX_ACTIVE_SKILLS = 10

    # 相关性分数阈值（低于此值不注入）
    RELEVANCE_THRESHOLD = 0.2

    # 中英文停用词
    STOP_WORDS = {
        '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
        '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
        '自己', '这', '他', '她', '它', '们', '那', '些', '帮我', '请', '怎么', '如何',
        '什么', '哪个', '能不能', '可以',
        'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but', 'in',
        'with', 'to', 'for', 'of', 'not', 'no', 'can', 'do', 'be', 'this', 'that',
        'it', 'you', 'we', 'they', 'he', 'she', 'my', 'your', 'have', 'has', 'had',
        'will', 'would', 'could', 'should', 'may',
    }

    def __init__(self, embedding_func: Optional[callable] = None):
        """
        初始化路由器

        Args:
            embedding_func: 可选的 embedding 函数，用于语义匹配
        """
        self.embedding_func = embedding_func
        self._pinned_skill_ids: Set[str] = set()

    def pin_skill(self, skill_id: str):
        """将技能 pin 住（对话中被触发后调用）"""
        self._pinned_skill_ids.add(skill_id)

    def clear_pins(self):
        """清除所有 pin（新对话开始时调用）"""
        self._pinned_skill_ids.clear()

    def resolve(
        self,
        user_input: str,
        recent_context: List[str],
        all_skills: List[Dict],
        skill_prompts: Dict[str, str],
    ) -> List[ScoredSkill]:
        """
        对技能池进行相关性匹配，返回本轮应注入的技能列表。

        Args:
            user_input: 当前用户输入
            recent_context: 最近对话内容（辅助匹配）
            all_skills: 全部激活状态的技能列表
                       每个技能: {"id": str, "name": str, "description": str, ...}
            skill_prompts: 技能 id → SKILL.md 内容的映射

        Returns:
            按相关性排序的技能列表（最多 MAX_ACTIVE_SKILLS 个）
        """
        if not all_skills:
            return []

        results: List[ScoredSkill] = []
        context_text = ' '.join([user_input] + recent_context)

        # ─── 1. Pinned skills 直接注入（满分） ───
        for skill in all_skills:
            if skill['id'] in self._pinned_skill_ids:
                results.append(ScoredSkill(
                    skill_id=skill['id'],
                    skill_name=skill['name'],
                    score=1.0,
                    match_reason='pinned（会话中已使用）'
                ))

        # ─── 2. 关键词匹配 ───
        unpinned = [s for s in all_skills if s['id'] not in self._pinned_skill_ids]

        for skill in unpinned:
            score = self._keyword_score(
                skill=skill,
                prompt=skill_prompts.get(skill['id'], ''),
                context_text=context_text,
            )
            if score >= self.RELEVANCE_THRESHOLD:
                results.append(ScoredSkill(
                    skill_id=skill['id'],
                    skill_name=skill['name'],
                    score=score,
                    match_reason='关键词匹配'
                ))

        # ─── 3. 语义匹配（如果配置了 embedding 且关键词匹配不足）───
        if len(results) < self.MAX_ACTIVE_SKILLS and self.embedding_func:
            matched_ids = {r.skill_id for r in results}
            unmatched = [s for s in unpinned if s['id'] not in matched_ids]
            if unmatched:
                semantic_results = self._semantic_match(
                    context_text=context_text,
                    candidates=unmatched,
                    skill_prompts=skill_prompts,
                )
                results.extend(semantic_results)

        # ─── 4. 排序 + 截断 ───
        results.sort(key=lambda x: x.score, reverse=True)
        selected = results[:self.MAX_ACTIVE_SKILLS]

        # ─── 5. 打印载入日志 ───
        self._log_loaded_skills(selected)

        return selected

    def _keyword_score(self, skill: Dict, prompt: str, context_text: str) -> float:
        """
        关键词匹配评分

        双向匹配 + 固定增量：
        - 技能名在输入中出现：+0.5（强信号）
        - 反向匹配（技能侧关键词出现在输入中）：每命中一个 +0.08（上限 0.5）
        - 正向匹配（输入关键词出现在技能侧）：每命中一个 +0.06（上限 0.4）
        """
        input_lower = context_text.lower()
        name_lower = skill['name'].lower()
        desc_lower = skill.get('description', '').lower()
        prompt_lower = prompt[:300].lower() if len(prompt) > 300 else prompt.lower()

        score = 0.0

        # ── 技能名直接出现在用户输入中（强信号）──
        if name_lower in input_lower:
            score += 0.5

        # ── 反向匹配：技能侧关键词在用户输入中出现 ──
        skill_text = f'{name_lower} {desc_lower} {prompt_lower}'
        skill_keywords = self._extract_keywords(skill_text)
        reverse_score = sum(0.08 for kw in skill_keywords if kw in input_lower)
        score += min(reverse_score, 0.5)

        # ── 正向匹配：用户输入关键词在技能侧出现 ──
        input_keywords = self._extract_keywords(input_lower)
        forward_score = sum(
            0.06 for kw in input_keywords
            if kw in name_lower or kw in desc_lower or kw in prompt_lower
        )
        score += min(forward_score, 0.4)

        return min(score, 1.0)

    def _extract_keywords(self, text: str) -> List[str]:
        """
        分词：按空格/标点分割 + 中文 bigram 拆分

        策略：
        - 英文/数字按空格分割，保留 >= 2 字符的 token
        - 连续中文字符额外做 bigram（2 字一组滑动窗口）
        - 过滤停用词
        """
        # 先按非词字符分割
        raw_tokens = re.split(r'[^\w\u4e00-\u9fff]+', text)
        raw_tokens = [w for w in raw_tokens if w]

        result = set()

        for token in raw_tokens:
            if len(token) < 2 or token in self.STOP_WORDS:
                continue

            # 英文/数字 token 直接加入
            if re.match(r'^[a-z0-9_]+$', token):
                result.add(token)
                continue

            # 提取英文部分
            en_parts = re.findall(r'[a-z0-9_]+', token)
            for part in en_parts:
                if len(part) >= 2:
                    result.add(part)

            # 提取中文部分并做 bigram
            zh_matches = re.finditer(r'[\u4e00-\u9fff]+', token)
            for match in zh_matches:
                chars = match.group(0)
                if len(chars) >= 2:
                    result.add(chars)  # 原始中文串
                    # bigram 滑动窗口
                    for i in range(len(chars) - 1):
                        bigram = chars[i:i+2]
                        if bigram not in self.STOP_WORDS:
                            result.add(bigram)

        return list(result)

    def _semantic_match(
        self,
        context_text: str,
        candidates: List[Dict],
        skill_prompts: Dict[str, str],
    ) -> List[ScoredSkill]:
        """
        语义匹配（基于 embedding 相似度）

        将用户输入 embed，与各技能描述的 embedding 比较余弦相似度。
        """
        if not self.embedding_func:
            return []

        try:
            input_embedding = self.embedding_func(context_text)
            if not input_embedding:
                return []

            results = []
            for skill in candidates:
                # 用技能名 + 描述做 embedding（不用完整 SKILL.md，太长）
                skill_text = f"{skill['name']}: {skill.get('description', '')}"
                skill_embedding = self.embedding_func(skill_text)
                if not skill_embedding:
                    continue

                similarity = self._cosine_similarity(input_embedding, skill_embedding)
                if similarity >= self.RELEVANCE_THRESHOLD:
                    results.append(ScoredSkill(
                        skill_id=skill['id'],
                        skill_name=skill['name'],
                        score=similarity,
                        match_reason=f'语义匹配({int(similarity * 100)}%)'
                    ))

            return results
        except Exception as e:
            print(f'[SkillRouter] 语义匹配失败(降级到关键词): {e}')
            return []

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """余弦相似度"""
        if len(a) != len(b) or not a:
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def _log_loaded_skills(self, skills: List[ScoredSkill]):
        """打印载入的技能日志"""
        if not skills:
            return

        print(f'[SkillRouter] ╭─ 本轮载入 {len(skills)} 个技能 ─────────')
        for scored in skills:
            pct = int(scored.score * 100)
            print(f'[SkillRouter] │ 载入 {scored.skill_name} '
                  f'(相关度:{pct}%, {scored.match_reason})')
        print('[SkillRouter] ╰────────────────────────────────────────')
