"""
ToolShell 工具执行器
===================
接收工具名和参数，执行实际操作，返回结果。
"""

import json
import shutil
import subprocess
import re
import fnmatch
import sys
from pathlib import Path
from typing import Optional

from .memory import MemoryManager

# 延迟导入 schedule 执行器
_schedule_executor = None


def _get_schedule_executor(project_root):
    global _schedule_executor
    if _schedule_executor is None:
        # 尝试从同级目录加载
        skill_dir = Path(__file__).parent.parent
        schedule_skill = skill_dir.parent / "schedule-skill" / "runtime"
        if schedule_skill.exists():
            sys.path.insert(0, str(schedule_skill))
            from schedule_executor import ScheduleExecutor
            _schedule_executor = ScheduleExecutor(str(project_root))
        else:
            # 内联简易实现
            from .schedule_inline import ScheduleExecutor as InlineSchedule
            _schedule_executor = InlineSchedule(str(project_root))
    return _schedule_executor


# 受保护路径 (即使 auto 模式也不能动)
PROTECTED = [".git", "node_modules", ".env", ".env.local", ".env.production"]


class Executor:
    """工具执行层"""

    def __init__(self, project_root: Path, memory: MemoryManager, config: dict = None):
        self.root = Path(project_root).resolve()
        self.memory = memory
        self.config = config or {}

    def run(self, tool_name: str, args: dict) -> str:
        """统一入口: 执行工具并返回 JSON 结果字符串"""
        # Schedule 工具路由
        if tool_name.startswith("schedule_"):
            try:
                sched = _get_schedule_executor(self.root)
                return sched.run(tool_name, args)
            except Exception as e:
                return self._err(f"Schedule 执行失败: {e}")

        dispatch = {
            "toolshell_read": self._read,
            "toolshell_write": self._write,
            "toolshell_delete": self._delete,
            "toolshell_search": self._search,
            "toolshell_exec": self._exec,
            "toolshell_memory_store": self._mem_store,
            "toolshell_memory_recall": self._mem_recall,
        }
        fn = dispatch.get(tool_name)
        if not fn:
            return self._err(f"未知工具: {tool_name}")
        try:
            return fn(args)
        except Exception as e:
            return self._err(str(e))

    # ─── 路径安全 ────────────────────────────────────────────

    def _resolve(self, path: str) -> Path:
        target = (self.root / path).resolve()
        if not str(target).startswith(str(self.root)):
            raise ValueError(f"路径越界: {path}")
        return target

    def _is_protected(self, path: Path) -> bool:
        try:
            rel = path.relative_to(self.root)
        except ValueError:
            return True
        for part in rel.parts:
            if part in PROTECTED:
                return True
        return False

    # ─── 文件操作 ────────────────────────────────────────────

    def _read(self, args: dict) -> str:
        path = self._resolve(args["path"])
        if not path.exists():
            self.memory.log_op("read", args["path"], "not found", "error")
            return self._err("FILE_NOT_FOUND", args["path"])
        encoding = args.get("encoding", "utf-8")
        content = path.read_text(encoding=encoding, errors="replace")
        lines = content.splitlines(keepends=True)
        total = len(lines)

        start = args.get("start_line")
        end = args.get("end_line")
        if start or end:
            s = max(0, (start or 1) - 1)
            e = min(total, end or total)
            content = "".join(lines[s:e])

        self.memory.log_op("read", args["path"], f"lines={total}", "success")
        return self._ok(content=content, total_lines=total, size=path.stat().st_size)

    def _write(self, args: dict) -> str:
        path = self._resolve(args["path"])
        if self._is_protected(path):
            self.memory.log_op("write", args["path"], "protected", "error")
            return self._err("PROTECTED_PATH", args["path"])

        write_mode = args.get("mode", "create")
        content = args["content"]
        path.parent.mkdir(parents=True, exist_ok=True)

        if write_mode == "create" and path.exists():
            return self._err("PATH_EXISTS", args["path"])
        if write_mode == "append":
            with open(path, "a", encoding="utf-8") as f:
                f.write(content)
        else:
            path.write_text(content, encoding="utf-8")

        self.memory.log_op("write", args["path"], f"mode={write_mode}", "success")
        return self._ok(path=args["path"], size=path.stat().st_size, mode=write_mode)

    def _delete(self, args: dict) -> str:
        path = self._resolve(args["path"])
        if self._is_protected(path):
            self.memory.log_op("delete", args["path"], "protected", "error")
            return self._err("PROTECTED_PATH", args["path"])
        if not path.exists():
            return self._err("FILE_NOT_FOUND", args["path"])

        recursive = args.get("recursive", False)
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            if recursive:
                shutil.rmtree(path)
            else:
                if any(path.iterdir()):
                    return self._err("NOT_EMPTY", args["path"])
                path.rmdir()

        self.memory.log_op("delete", args["path"], f"recursive={recursive}", "success")
        return self._ok(deleted=args["path"])

    def _search(self, args: dict) -> str:
        pattern = args["pattern"]
        scope = args.get("scope", ".")
        content_re = args.get("content")
        max_results = args.get("max_results", 20)

        search_root = self._resolve(scope)
        if not search_root.is_dir():
            return self._err("SCOPE_NOT_FOUND", scope)

        matches = []
        for item in search_root.rglob(pattern):
            if self._is_protected(item):
                continue
            try:
                rel = str(item.relative_to(self.root))
            except ValueError:
                continue
            if content_re and item.is_file():
                try:
                    text = item.read_text(encoding="utf-8", errors="ignore")
                    if not re.search(content_re, text):
                        continue
                except (PermissionError, OSError):
                    continue
            matches.append({
                "path": rel,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
            })
            if len(matches) >= max_results:
                break

        self.memory.log_op("search", pattern, f"found={len(matches)}", "success")
        return self._ok(matches=matches, total=len(matches))

    # ─── Shell 执行 ──────────────────────────────────────────

    def _exec(self, args: dict) -> str:
        command = args["command"]
        cwd = args.get("cwd", ".")
        timeout = args.get("timeout", 120)

        work_dir = self._resolve(cwd)
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            result = subprocess.run(
                command, shell=True, cwd=str(work_dir),
                capture_output=True, text=True,
                timeout=timeout, encoding="utf-8", errors="replace",
            )
            stdout = result.stdout[-8000:] if len(result.stdout) > 8000 else result.stdout
            stderr = result.stderr[-4000:] if len(result.stderr) > 4000 else result.stderr
            status = "success" if result.returncode == 0 else "error"
            self.memory.log_op("exec", command, f"exit={result.returncode}", status)
            return self._ok(
                exit_code=result.returncode, stdout=stdout, stderr=stderr,
                truncated=len(result.stdout) > 8000 or len(result.stderr) > 4000,
            )
        except subprocess.TimeoutExpired:
            self.memory.log_op("exec", command, f"timeout={timeout}s", "error")
            return self._err("TIMEOUT", f"{command} (>{timeout}s)")

    # ─── 记忆操作 ────────────────────────────────────────────

    def _mem_store(self, args: dict) -> str:
        mid = self.memory.store(args["content"], args["type"], args["importance"])
        return self._ok(memory_id=mid)

    def _mem_recall(self, args: dict) -> str:
        results = self.memory.recall(args["query"], args.get("limit", 5))
        return json.dumps({"memories": results}, ensure_ascii=False, default=str)

    # ─── 工具方法 ────────────────────────────────────────────

    def _ok(self, **kwargs) -> str:
        return json.dumps({"status": "ok", **kwargs}, ensure_ascii=False, default=str)

    def _err(self, code: str, detail: str = "") -> str:
        return json.dumps({"status": "error", "code": code, "detail": detail}, ensure_ascii=False)
