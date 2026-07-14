"""
技能注册表 - Skill Registry
===========================
管理技能的导入、删除、加载。

支持：
- 从 ZIP 和目录导入技能
- 全局技能和项目级临时技能
- 管理技能元数据和排序
"""

import json
import shutil
import zipfile
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class Skill:
    """技能数据模型"""
    id: str
    name: str
    description: str
    path: str
    tool_count: int
    is_active: bool = True
    is_built_in: bool = False
    installed_at: str = ""
    sort_index: int = 0
    is_project_level: bool = False

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


class SkillRegistry:
    """技能注册表 - 管理技能的导入、删除、加载"""

    # 项目级临时技能目录的相对路径
    PROJECT_SKILLS_REL_PATH = '.toolshell/skills'

    def __init__(self, skills_path: str = ""):
        """
        初始化注册表

        Args:
            skills_path: 技能存放目录。为空时使用默认位置
        """
        self.skills_path = Path(skills_path) if skills_path else None

    def get_skills_dir(self) -> Path:
        """获取技能目录"""
        if self.skills_path:
            skills_dir = self.skills_path
        else:
            # 默认：当前工作目录的 SKILLS 文件夹
            skills_dir = Path.cwd() / 'SKILLS'

        skills_dir.mkdir(parents=True, exist_ok=True)
        return skills_dir

    def list_installed(self) -> List[Skill]:
        """列出所有已安装的技能"""
        skills_dir = self.get_skills_dir()
        skills = []

        if not skills_dir.exists():
            return skills

        for entity in skills_dir.iterdir():
            if entity.is_dir():
                skill = self._load_skill_from_dir(entity)
                if skill:
                    skills.append(skill)

        # 按 sort_index 升序排序（相同则按安装时间倒序）
        skills.sort(key=lambda s: (s.sort_index, -self._parse_timestamp(s.installed_at)))
        return skills

    def list_project_skills(self, work_dir: str) -> List[Skill]:
        """
        扫描工作目录下的项目级临时技能

        Args:
            work_dir: 工作目录路径

        Returns:
            项目级技能列表
        """
        if not work_dir:
            return []

        skills_dir = Path(work_dir) / '.toolshell' / 'skills'
        if not skills_dir.exists():
            return []

        skills = []
        for entity in skills_dir.iterdir():
            if not entity.is_dir():
                continue

            skill_md = entity / 'SKILL.md'
            if not skill_md.exists():
                continue

            name = entity.name

            # 统计工具数量
            tool_count = self._count_tools(entity / 'tools.json')

            # 获取安装时间
            try:
                installed_at = datetime.fromtimestamp(skill_md.stat().st_mtime).isoformat()
            except:
                installed_at = datetime.now().isoformat()

            skills.append(Skill(
                id=f'project:{name}',
                name=name,
                description='',
                path=str(entity),
                tool_count=tool_count,
                is_active=True,  # 项目技能恒定激活
                installed_at=installed_at,
                sort_index=0,
                is_project_level=True,
            ))

        skills.sort(key=lambda s: s.name)
        return skills

    def import_from_zip(self, zip_path: str) -> Skill:
        """
        从 ZIP 文件导入技能

        Args:
            zip_path: ZIP 文件路径

        Returns:
            导入的技能对象
        """
        zip_file = Path(zip_path)
        if not zip_file.exists():
            raise FileNotFoundError(f'ZIP 文件不存在: {zip_path}')

        with zipfile.ZipFile(zip_file, 'r') as zf:
            # 检测公共顶层目录前缀
            common_prefix = self._detect_common_prefix(zf.namelist())

            # 验证必需文件
            has_skill_md = any(
                self._strip_prefix(name, common_prefix) == 'SKILL.md'
                for name in zf.namelist() if not name.endswith('/')
            )

            if not has_skill_md:
                raise ValueError('压缩包根目录缺少 SKILL.md 文件')

            # 确定技能名称
            skill_name = zip_file.stem
            skill_id = self._generate_id()
            skills_dir = self.get_skills_dir()
            skill_dir = skills_dir / skill_name

            # 如果已存在同名目录则覆盖
            if skill_dir.exists():
                shutil.rmtree(skill_dir)
            skill_dir.mkdir(parents=True)

            # 解压文件（剥离公共顶层目录前缀）
            for name in zf.namelist():
                if name.endswith('/'):
                    continue
                rel_path = self._strip_prefix(name, common_prefix)
                if not rel_path:
                    continue
                out_path = skill_dir / rel_path
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(name) as src, open(out_path, 'wb') as dst:
                    dst.write(src.read())

        # 写入元数据
        meta = {
            'id': skill_id,
            'installed_at': datetime.now().isoformat(),
            'is_active': True,
            'sort_index': self._next_sort_index(),
        }
        meta_file = skill_dir / '.skill_meta.json'
        meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2))

        skill = self._load_skill_from_dir(skill_dir)
        if not skill:
            raise RuntimeError('技能加载失败')
        return skill

    def install_from_directory(self, source_dir: str, name: Optional[str] = None) -> Skill:
        """
        从普通目录安装技能到全局技能库

        Args:
            source_dir: 源技能目录，必须直接包含 SKILL.md
            name: 可选的目标技能名（默认取源目录名）

        Returns:
            安装的技能对象
        """
        src = Path(source_dir)
        if not src.exists():
            raise FileNotFoundError(f'源目录不存在: {source_dir}')

        src_skill_md = src / 'SKILL.md'
        if not src_skill_md.exists():
            raise FileNotFoundError(f'源目录缺少 SKILL.md: {source_dir}')

        skill_name = name.strip() if name and name.strip() else src.name
        skill_id = self._generate_id()
        skills_dir = self.get_skills_dir()
        skill_dir = skills_dir / skill_name

        # 已存在同名目录则覆盖
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
        skill_dir.mkdir(parents=True)

        # 递归复制源目录内容（跳过 .skill_meta.json）
        for item in src.rglob('*'):
            rel = item.relative_to(src)
            if str(rel) == '.skill_meta.json':
                continue
            out_path = skill_dir / rel
            if item.is_dir():
                out_path.mkdir(parents=True, exist_ok=True)
            elif item.is_file():
                out_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, out_path)

        # 写入元数据
        meta = {
            'id': skill_id,
            'installed_at': datetime.now().isoformat(),
            'is_active': True,
            'sort_index': self._next_sort_index(),
        }
        meta_file = skill_dir / '.skill_meta.json'
        meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2))

        skill = self._load_skill_from_dir(skill_dir)
        if not skill:
            raise RuntimeError('技能加载失败')
        return skill

    def remove(self, skill_id: str):
        """删除技能"""
        skills = self.list_installed()
        skill = next((s for s in skills if s.id == skill_id), None)
        if not skill:
            raise ValueError('技能不存在')

        skill_dir = Path(skill.path)
        if skill_dir.exists():
            shutil.rmtree(skill_dir)

    def set_active(self, skill_id: str, active: bool):
        """切换技能激活状态"""
        skills = self.list_installed()
        skill = next((s for s in skills if s.id == skill_id), None)
        if not skill:
            raise ValueError('技能不存在')

        meta_file = Path(skill.path) / '.skill_meta.json'
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            meta['is_active'] = active
            meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    def set_description(self, skill_id: str, description: str):
        """更新技能描述"""
        skills = self.list_installed()
        skill = next((s for s in skills if s.id == skill_id), None)
        if not skill:
            raise ValueError('技能不存在')

        meta_file = Path(skill.path) / '.skill_meta.json'
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
        else:
            meta = {
                'id': skill.id,
                'installed_at': skill.installed_at,
                'is_active': skill.is_active,
                'sort_index': skill.sort_index,
            }
        meta['description'] = description
        meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    def reorder(self, ordered_ids: List[str]):
        """按给定 id 顺序重写各技能的 sort_index"""
        skills = self.list_installed()
        by_id = {s.id: s for s in skills}

        for i, skill_id in enumerate(ordered_ids):
            skill = by_id.get(skill_id)
            if not skill:
                continue

            meta_file = Path(skill.path) / '.skill_meta.json'
            if meta_file.exists():
                meta = json.loads(meta_file.read_text())
            else:
                meta = {
                    'id': skill.id,
                    'installed_at': skill.installed_at,
                    'is_active': skill.is_active,
                }
            meta['sort_index'] = i
            meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    def load_skill_prompt(self, skill: Dict) -> str:
        """读取技能的 SKILL.md 内容"""
        skill_path = Path(skill.get('path', ''))
        skill_md = skill_path / 'SKILL.md'
        if not skill_md.exists():
            return ''
        return skill_md.read_text(encoding='utf-8', errors='ignore')

    def load_skill_tools(self, skill: Dict) -> List[Dict]:
        """
        解析技能的 tools.json

        健壮处理多种顶层形态：
        - 数组 `[ {...}, {...} ]`（标准）
        - 对象包裹 `{ "tools": [ ... ] }`
        - 单个工具对象

        归一化为 OpenAI 标准嵌套格式
        """
        skill_path = Path(skill.get('path', ''))
        tools_json = skill_path / 'tools.json'
        if not tools_json.exists():
            return []

        try:
            content = tools_json.read_text(encoding='utf-8')
            if not content.strip():
                return []

            decoded = json.loads(content)

            raw_list = None
            if isinstance(decoded, list):
                raw_list = decoded
            elif isinstance(decoded, dict):
                inner = decoded.get('tools')
                if isinstance(inner, list):
                    raw_list = inner
                elif any(k in decoded for k in ['function', 'name', 'type']):
                    raw_list = [decoded]

            if raw_list is None:
                print(f"[SKILL] ⚠ 技能「{skill.get('name')}」tools.json 顶层格式无法识别，已跳过")
                return []

            # 归一化每个工具为 OpenAI 标准嵌套格式
            result = []
            for item in raw_list:
                if not isinstance(item, dict):
                    continue
                normalized = self._normalize_tool_def(item)
                if normalized:
                    result.append(normalized)

            return result
        except Exception as e:
            print(f"[SKILL] ⚠ 技能「{skill.get('name')}」tools.json 解析失败: {e}")
            return []

    # ─── 内部方法 ─────────────────────────────────────────────

    def _load_skill_from_dir(self, dir_path: Path) -> Optional[Skill]:
        """从目录加载技能信息"""
        skill_md = dir_path / 'SKILL.md'
        if not skill_md.exists():
            return None

        # 读取元数据
        skill_id = dir_path.name
        is_active = True
        installed_at = datetime.now().isoformat()
        sort_index = 0
        description = ''

        meta_file = dir_path / '.skill_meta.json'
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text())
                skill_id = meta.get('id', skill_id)
                is_active = meta.get('is_active', True)
                sort_index = meta.get('sort_index', 0)
                description = meta.get('description', '').strip()
                installed_at = meta.get('installed_at', installed_at)
            except:
                pass

        # 统计工具数量
        tool_count = self._count_tools(dir_path / 'tools.json')

        return Skill(
            id=skill_id,
            name=dir_path.name,
            description=description,
            path=str(dir_path),
            tool_count=tool_count,
            is_active=is_active,
            installed_at=installed_at,
            sort_index=sort_index,
        )

    def _count_tools(self, tools_json: Path) -> int:
        """统计工具数量"""
        if not tools_json.exists():
            return 0

        try:
            content = tools_json.read_text(encoding='utf-8')
            if not content.strip():
                return 0

            decoded = json.loads(content)
            if isinstance(decoded, list):
                return len(decoded)
            elif isinstance(decoded, dict):
                inner = decoded.get('tools')
                if isinstance(inner, list):
                    return len(inner)
                elif any(k in decoded for k in ['function', 'name', 'type']):
                    return 1
            return 0
        except:
            return 0

    def _normalize_tool_def(self, tool: Dict) -> Optional[Dict]:
        """
        归一化工具定义为 OpenAI 标准嵌套格式
        `{ "type":"function", "function":{ "name","description","parameters" } }`
        """
        # 已是标准嵌套格式
        fn = tool.get('function')
        if isinstance(fn, dict) and isinstance(fn.get('name'), str):
            return tool

        # 扁平格式 → 包装
        if isinstance(tool.get('name'), str):
            return {
                'type': 'function',
                'function': {
                    'name': tool['name'],
                    'description': tool.get('description', ''),
                    'parameters': tool.get('parameters', {'type': 'object', 'properties': {}}),
                },
            }

        return None  # 无 name，无法识别

    def _detect_common_prefix(self, namelist: List[str]) -> str:
        """检测压缩包内是否所有文件都包裹在同一个顶层目录下"""
        prefix = None
        for name in namelist:
            if name.endswith('/'):
                continue
            name = name.replace('\\', '/')
            slash = name.find('/')
            if slash < 0:
                return ''  # 存在顶层文件
            top = name[:slash + 1]
            if prefix is None:
                prefix = top
            elif prefix != top:
                return ''  # 顶层目录不一致
        return prefix or ''

    def _strip_prefix(self, name: str, prefix: str) -> str:
        """剥离文件名的公共顶层目录前缀"""
        normalized = name.replace('\\', '/')
        if prefix and normalized.startswith(prefix):
            return normalized[len(prefix):]
        return normalized

    def _generate_id(self) -> str:
        """生成唯一 ID"""
        return hashlib.md5(f'{datetime.now().isoformat()}'.encode()).hexdigest()[:16]

    def _next_sort_index(self) -> int:
        """计算下一个 sort_index"""
        skills = self.list_installed()
        if not skills:
            return 0
        return max(s.sort_index for s in skills) + 1

    def _parse_timestamp(self, timestamp: str) -> float:
        """解析时间戳为浮点数"""
        try:
            return datetime.fromisoformat(timestamp).timestamp()
        except:
            return 0.0
