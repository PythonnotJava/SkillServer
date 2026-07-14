"""
Schedule Skill Runtime
======================
任务计划管理的运行时实现
"""

import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class ScheduleExecutor:
    """SCHEDULE.md 文件的解析和操作执行器"""

    def __init__(self, project_root: str):
        self.root = Path(project_root).resolve()
        self.default_path = self.root / "SCHEDULE.md"

    def run(self, tool_name: str, args: dict) -> str:
        """统一工具执行入口"""
        dispatch = {
            "schedule_load": self._load,
            "schedule_add_task": self._add_task,
            "schedule_complete": self._complete,
            "schedule_update": self._update,
            "schedule_review": self._review,
            "schedule_archive": self._archive,
        }
        fn = dispatch.get(tool_name)
        if not fn:
            return self._err(f"未知工具: {tool_name}")
        try:
            return fn(args)
        except Exception as e:
            return self._err(str(e))

    # ─── 工具实现 ─────────────────────────────────────────────

    def _load(self, args: dict) -> str:
        """加载计划文件"""
        path = self._resolve_path(args.get("path", "SCHEDULE.md"))

        if not path.exists():
            # 创建模板
            template = self._create_template()
            path.write_text(template, encoding="utf-8")
            return self._ok(
                message="已创建 SCHEDULE.md 模板",
                pending_count=0,
                completed_count=0,
                tasks={"P0": [], "P1": [], "P2": [], "Done": []},
            )

        content = path.read_text(encoding="utf-8")
        tasks = self._parse_schedule(content)

        # 统计信息
        pending = sum(len(tasks[p]) for p in ["P0", "P1", "P2"])
        completed = len(tasks["Done"])

        # 最高优先级任务
        top_task = None
        if tasks["P0"]:
            top_task = tasks["P0"][0]["text"]
        elif tasks["P1"]:
            top_task = tasks["P1"][0]["text"]

        # 最近完成任务
        recent_done = tasks["Done"][-1]["text"] if tasks["Done"] else None

        return self._ok(
            pending_count=pending,
            completed_count=completed,
            top_priority_task=top_task,
            recent_completed=recent_done,
            tasks=tasks,
            suggestion=self._generate_suggestion(tasks),
        )

    def _add_task(self, args: dict) -> str:
        """添加新任务"""
        path = self._resolve_path(args.get("path", "SCHEDULE.md"))
        task = args["task"]
        priority = args["priority"]
        after = args.get("after")
        tags = args.get("tags", [])
        note = args.get("note", "")

        content = path.read_text(encoding="utf-8") if path.exists() else self._create_template()
        tasks = self._parse_schedule(content)

        # 构造任务行
        tag_str = " ".join(f"`#{t}`" for t in tags) if tags else ""
        note_str = f" — {note}" if note else ""
        task_line = f"- [ ] {task} {tag_str}{note_str}".strip()

        # 插入到指定位置
        target_list = tasks[priority]
        insert_index = len(target_list)

        if after:
            for i, existing in enumerate(target_list):
                if after.lower() in existing["text"].lower():
                    insert_index = i + 1
                    break

        target_list.insert(insert_index, {"text": task, "raw": task_line})

        # 重新生成文件
        new_content = self._rebuild_schedule(tasks, content)
        path.write_text(new_content, encoding="utf-8")

        return self._ok(
            message=f"已添加任务到 {priority}",
            task=task,
            position=insert_index + 1,
        )

    def _complete(self, args: dict) -> str:
        """标记任务完成"""
        path = self._resolve_path(args.get("path", "SCHEDULE.md"))
        task_match = args["task_match"]
        summary = args.get("summary", "")

        content = path.read_text(encoding="utf-8")
        tasks = self._parse_schedule(content)

        # 查找匹配任务
        found = None
        found_priority = None

        for priority in ["P0", "P1", "P2"]:
            for task in tasks[priority]:
                if task_match.lower() in task["text"].lower():
                    found = task
                    found_priority = priority
                    break
            if found:
                break

        if not found:
            return self._err("未找到匹配的任务", task_match)

        # 移动到已完成
        tasks[found_priority].remove(found)
        completed_text = found["text"]
        if summary:
            completed_text += f" — {summary}"

        now = datetime.now().strftime("%Y-%m-%d")
        completed_line = f"- [x] {completed_text} — 完成于 {now}"
        tasks["Done"].append({"text": completed_text, "raw": completed_line})

        # 重新生成文件
        new_content = self._rebuild_schedule(tasks, content)
        path.write_text(new_content, encoding="utf-8")

        return self._ok(
            message="任务已标记完成",
            task=found["text"],
            priority=found_priority,
        )

    def _update(self, args: dict) -> str:
        """更新任务"""
        path = self._resolve_path(args.get("path", "SCHEDULE.md"))
        task_match = args["task_match"]
        new_priority = args.get("new_priority")
        new_text = args.get("new_text")
        new_note = args.get("new_note")

        content = path.read_text(encoding="utf-8")
        tasks = self._parse_schedule(content)

        # 查找匹配任务
        found = None
        found_priority = None

        for priority in ["P0", "P1", "P2"]:
            for i, task in enumerate(tasks[priority]):
                if task_match.lower() in task["text"].lower():
                    found = (i, task)
                    found_priority = priority
                    break
            if found:
                break

        if not found:
            return self._err("未找到匹配的任务", task_match)

        idx, task = found

        # 更新文本
        if new_text:
            task["text"] = new_text

        # 更新备注
        if new_note:
            task["text"] = re.sub(r' — .*$', '', task["text"])
            task["text"] += f" — {new_note}"

        # 更新原始行
        task["raw"] = f"- [ ] {task['text']}"

        # 更新优先级
        if new_priority and new_priority != found_priority:
            tasks[found_priority].pop(idx)
            tasks[new_priority].append(task)

        # 重新生成文件
        new_content = self._rebuild_schedule(tasks, content)
        path.write_text(new_content, encoding="utf-8")

        return self._ok(
            message="任务已更新",
            old_priority=found_priority,
            new_priority=new_priority or found_priority,
            updated_task=task["text"],
        )

    def _review(self, args: dict) -> str:
        """生成进度报告"""
        path = self._resolve_path(args.get("path", "SCHEDULE.md"))
        content = path.read_text(encoding="utf-8")
        tasks = self._parse_schedule(content)

        stats = {
            "P0": len(tasks["P0"]),
            "P1": len(tasks["P1"]),
            "P2": len(tasks["P2"]),
            "Done": len(tasks["Done"]),
        }

        # 生成报告
        report_lines = [
            f"## 📊 进度报告",
            f"- 🔴 P0 紧急: {stats['P0']} 个待办",
            f"- 🟡 P1 重要: {stats['P1']} 个待办",
            f"- 🟢 P2 一般: {stats['P2']} 个待办",
            f"- ✅ 已完成: {stats['Done']} 个",
            "",
        ]

        # 下一步建议
        if tasks["P0"]:
            report_lines.append(f"**下一步**: 优先处理 P0 任务 — {tasks['P0'][0]['text']}")
        elif tasks["P1"]:
            report_lines.append(f"**下一步**: 处理 P1 任务 — {tasks['P1'][0]['text']}")
        elif tasks["P2"]:
            report_lines.append(f"**下一步**: 处理 P2 任务 — {tasks['P2'][0]['text']}")
        else:
            report_lines.append("**状态**: 所有任务已完成 🎉")

        report = "\n".join(report_lines)

        return self._ok(
            report=report,
            stats=stats,
            suggestion=self._generate_suggestion(tasks),
        )

    def _archive(self, args: dict) -> str:
        """归档旧的完成任务"""
        path = self._resolve_path(args.get("path", "SCHEDULE.md"))
        days = args.get("days", 7)

        content = path.read_text(encoding="utf-8")
        tasks = self._parse_schedule(content)

        # 筛选需要归档的任务
        cutoff = datetime.now().timestamp() - (days * 86400)
        to_archive = []
        to_keep = []

        for task in tasks["Done"]:
            # 提取完成日期
            match = re.search(r'完成于 (\d{4}-\d{2}-\d{2})', task["text"])
            if match:
                date_str = match.group(1)
                task_time = datetime.strptime(date_str, "%Y-%m-%d").timestamp()
                if task_time < cutoff:
                    to_archive.append(task)
                else:
                    to_keep.append(task)
            else:
                to_keep.append(task)

        if not to_archive:
            return self._ok(
                message="没有需要归档的任务",
                archived_count=0,
            )

        # 写入归档文件
        archive_path = path.parent / "SCHEDULE_ARCHIVE.md"
        archive_content = ""
        if archive_path.exists():
            archive_content = archive_path.read_text(encoding="utf-8") + "\n\n"

        archive_content += f"## 归档于 {datetime.now().strftime('%Y-%m-%d')}\n\n"
        for task in to_archive:
            archive_content += task["raw"] + "\n"

        archive_path.write_text(archive_content, encoding="utf-8")

        # 更新主文件
        tasks["Done"] = to_keep
        new_content = self._rebuild_schedule(tasks, content)
        path.write_text(new_content, encoding="utf-8")

        return self._ok(
            message=f"已归档 {len(to_archive)} 个任务",
            archived_count=len(to_archive),
            archive_file=str(archive_path),
        )

    # ─── 辅助方法 ─────────────────────────────────────────────

    def _resolve_path(self, path: str) -> Path:
        """解析路径"""
        if Path(path).is_absolute():
            return Path(path)
        return self.root / path

    def _create_template(self) -> str:
        """创建模板"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"""# Work Plan
> Last updated: {now}

## 🔴 P0 - Urgent


## 🟡 P1 - Important


## 🟢 P2 - General


## ✅ Done

"""

    def _parse_schedule(self, content: str) -> Dict[str, List[Dict]]:
        """解析 SCHEDULE.md"""
        tasks = {"P0": [], "P1": [], "P2": [], "Done": []}
        current_section = None

        for line in content.split("\n"):
            # 检测区域标题
            if "P0" in line and ("Urgent" in line or "紧急" in line):
                current_section = "P0"
            elif "P1" in line and ("Important" in line or "重要" in line):
                current_section = "P1"
            elif "P2" in line and ("General" in line or "一般" in line):
                current_section = "P2"
            elif "Done" in line or "已完成" in line or "✅" in line:
                current_section = "Done"
            # 解析任务行
            elif current_section and (line.startswith("- [ ]") or line.startswith("- [x]")):
                text = re.sub(r'^- \[[x ]\] ', '', line).strip()
                tasks[current_section].append({"text": text, "raw": line})

        return tasks

    def _rebuild_schedule(self, tasks: Dict[str, List[Dict]], original: str) -> str:
        """重建 SCHEDULE.md 内容"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 保留头部
        lines = original.split("\n")
        header_end = 0
        for i, line in enumerate(lines):
            if "P0" in line or "P1" in line or "P2" in line:
                header_end = i
                break

        header = "\n".join(lines[:header_end])
        # 更新时间戳
        header = re.sub(r'Last updated:.*', f'Last updated: {now}', header)

        sections = [
            header,
            "",
            "## 🔴 P0 - Urgent",
            *[t["raw"] for t in tasks["P0"]],
            "",
            "## 🟡 P1 - Important",
            *[t["raw"] for t in tasks["P1"]],
            "",
            "## 🟢 P2 - General",
            *[t["raw"] for t in tasks["P2"]],
            "",
            "## ✅ Done",
            *[t["raw"] for t in tasks["Done"]],
            "",
        ]

        return "\n".join(sections)

    def _generate_suggestion(self, tasks: Dict[str, List[Dict]]) -> str:
        """生成建议"""
        if tasks["P0"]:
            return f"建议优先处理 P0 紧急任务: {tasks['P0'][0]['text']}"
        elif tasks["P1"]:
            return f"建议处理 P1 重要任务: {tasks['P1'][0]['text']}"
        elif tasks["P2"]:
            return f"可以处理 P2 一般任务: {tasks['P2'][0]['text']}"
        else:
            return "所有任务已完成，干得好！"

    def _ok(self, **kwargs) -> str:
        return json.dumps({"status": "ok", **kwargs}, ensure_ascii=False, default=str)

    def _err(self, msg: str, detail: str = "") -> str:
        return json.dumps({"status": "error", "message": msg, "detail": detail}, ensure_ascii=False)
