"""
系统检测器实现
=============
提供跨平台的系统信息检测功能
"""

import os
import sys
import json
import platform
import subprocess
import socket
import time
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout


class SystemDetector:
    """系统检测器"""

    # 常用工具列表
    COMMON_TOOLS = [
        'git', 'svn', 'hg',
        'npm', 'yarn', 'pnpm', 'pip', 'conda', 'cargo', 'go',
        'make', 'cmake', 'gcc', 'clang', 'rustc',
        'docker', 'podman', 'kubectl',
        'psql', 'mysql', 'redis-cli', 'mongo',
        'code', 'vim', 'emacs', 'nano',
    ]

    # 工具版本检测命令映射
    VERSION_COMMANDS = {
        'git': ['git', '--version'],
        'node': ['node', '--version'],
        'npm': ['npm', '--version'],
        'python': ['python', '--version'],
        'pip': ['pip', '--version'],
        'docker': ['docker', '--version'],
        'cargo': ['cargo', '--version'],
        'go': ['go', 'version'],
        'gcc': ['gcc', '--version'],
        'make': ['make', '--version'],
    }

    def __init__(self):
        self._tool_cache = {}
        self._cache_time = {}
        self._cache_ttl = 300  # 5 分钟缓存

    def detect_os(self, anonymize: bool = False) -> Dict:
        """检测操作系统信息"""
        try:
            os_name = platform.system()
            os_version = platform.release()
            architecture = platform.machine()
            hostname = platform.node()
            username = os.getenv('USER') or os.getenv('USERNAME') or 'unknown'

            # 检测 WSL
            is_wsl = False
            if os_name == 'Linux':
                try:
                    with open('/proc/version', 'r') as f:
                        is_wsl = 'microsoft' in f.read().lower()
                except:
                    pass

            # 脱敏处理
            if anonymize:
                hostname = hostname[:3] + '***' if len(hostname) > 3 else hostname
                username = username[:3] + '***' if len(username) > 3 else username

            return {
                'status': 'ok',
                'os': os_name,
                'version': os_version,
                'architecture': architecture,
                'is_wsl': is_wsl,
                'hostname': hostname,
                'username': username,
                'platform': sys.platform,
            }
        except Exception as e:
            return {
                'status': 'error',
                'code': 'DETECTION_FAILED',
                'detail': str(e),
                'fallback': {'os': 'unknown', 'version': 'unknown'}
            }

    def detect_python(self) -> Dict:
        """检测 Python 环境"""
        try:
            # Python 版本
            py_version = '.'.join(map(str, sys.version_info[:3]))
            py_executable = sys.executable

            # 虚拟环境检测
            venv_active = hasattr(sys, 'real_prefix') or (
                hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
            )
            venv_path = sys.prefix if venv_active else None

            # pip 版本
            pip_version = None
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', '--version'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    # 从输出提取版本号
                    parts = result.stdout.split()
                    if len(parts) >= 2:
                        pip_version = parts[1]
            except:
                pass

            # site-packages 路径
            import site
            site_packages = site.getsitepackages()[0] if site.getsitepackages() else None

            return {
                'status': 'ok',
                'version': py_version,
                'executable': py_executable,
                'venv_active': venv_active,
                'venv_path': venv_path,
                'pip_version': pip_version,
                'site_packages': site_packages,
            }
        except Exception as e:
            return {
                'status': 'error',
                'code': 'DETECTION_FAILED',
                'detail': str(e),
            }

    def detect_tools(self, tools: List[str] = None, timeout: int = 5) -> Dict:
        """批量检测工具可用性"""
        tools = tools or self.COMMON_TOOLS
        available = {}
        unavailable = []

        # 检查缓存
        now = time.time()
        for tool in tools:
            if tool in self._tool_cache:
                if now - self._cache_time.get(tool, 0) < self._cache_ttl:
                    # 使用缓存
                    cached = self._tool_cache[tool]
                    if cached:
                        available[tool] = cached
                    else:
                        unavailable.append(tool)
                    continue

            # 检测工具
            version = self._detect_single_tool(tool, timeout)
            self._tool_cache[tool] = version
            self._cache_time[tool] = now

            if version:
                available[tool] = version
            else:
                unavailable.append(tool)

        return {
            'status': 'ok',
            'available': available,
            'unavailable': unavailable,
        }

    def _detect_single_tool(self, tool: str, timeout: int) -> Optional[str]:
        """检测单个工具"""
        # 首先检测是否在 PATH 中
        if not self._is_in_path(tool):
            return None

        # 尝试获取版本
        cmd = self.VERSION_COMMANDS.get(tool, [tool, '--version'])
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode == 0:
                # 提取版本号（第一行，去除工具名）
                output = result.stdout.strip().split('\n')[0]
                # 简单的版本号提取
                import re
                match = re.search(r'\d+\.\d+(?:\.\d+)?', output)
                return match.group(0) if match else 'installed'
            return None
        except:
            return None

    def _is_in_path(self, tool: str) -> bool:
        """检测工具是否在 PATH 中"""
        # Windows 需要检测 .exe, .cmd, .bat 等后缀
        if sys.platform == 'win32':
            pathext = os.getenv('PATHEXT', '.COM;.EXE;.BAT;.CMD').split(';')
            for ext in pathext:
                if shutil.which(tool + ext.lower()) or shutil.which(tool + ext.upper()):
                    return True
            return shutil.which(tool) is not None
        else:
            import shutil
            return shutil.which(tool) is not None

    def get_env(self, keys: List[str], anonymize_paths: bool = False) -> Dict:
        """读取环境变量"""
        result = {}
        for key in keys:
            value = os.getenv(key)
            if value and anonymize_paths:
                # 脱敏路径中的用户名
                username = os.getenv('USER') or os.getenv('USERNAME')
                if username:
                    value = value.replace(username, username[:3] + '***')
            result[key] = value
        return {'status': 'ok', 'env': result}

    def test_network(self, targets: List[str] = None, timeout: int = 3) -> Dict:
        """测试网络连通性"""
        targets = targets or ['github.com', 'pypi.org', 'npmjs.com']
        results = {}
        dns_working = True
        proxy_detected = bool(os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY'))

        def test_single(target: str) -> Dict:
            try:
                start = time.time()
                # DNS 解析
                ip = socket.gethostbyname(target)
                # 尝试连接 HTTP 端口
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect((ip, 80))
                sock.close()
                latency = int((time.time() - start) * 1000)
                return {'reachable': True, 'latency_ms': latency, 'ip': ip}
            except socket.gaierror:
                return {'reachable': False, 'error': 'DNS resolution failed'}
            except:
                return {'reachable': False, 'error': 'Connection failed'}

        # 并发测试
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(test_single, t): t for t in targets}
            for future in futures:
                target = futures[future]
                try:
                    results[target] = future.result(timeout=timeout + 1)
                    if 'DNS resolution failed' in results[target].get('error', ''):
                        dns_working = False
                except:
                    results[target] = {'reachable': False, 'error': 'Timeout'}

        connected = any(r.get('reachable') for r in results.values())

        return {
            'status': 'ok',
            'connected': connected,
            'results': results,
            'dns_working': dns_working,
            'proxy_detected': proxy_detected,
        }

    def recommend_commands(self, task: str, context: Dict = None) -> Dict:
        """根据任务推荐命令"""
        context = context or {}
        os_info = self.detect_os()
        os_name = os_info.get('os', 'unknown')

        # 简单的规则引擎
        recommendations = {
            '安装 Python 包': self._recommend_python_install(os_name, context),
            '查看进程': self._recommend_process_list(os_name),
            '清理缓存': self._recommend_cache_clean(os_name),
            '启动服务': self._recommend_service_start(os_name, context),
        }

        # 模糊匹配任务
        for key, value in recommendations.items():
            if key in task or task in key:
                return {'status': 'ok', 'task': task, **value}

        return {
            'status': 'ok',
            'task': task,
            'recommended': '未找到推荐命令',
            'alternatives': [],
            'notes': f'当前系统: {os_name}',
        }

    def _recommend_python_install(self, os_name: str, context: Dict) -> Dict:
        """推荐 Python 包安装命令"""
        package = context.get('package_name', 'package_name')
        tools = self.detect_tools(['pip', 'conda', 'poetry'])

        if 'pip' in tools['available']:
            return {
                'recommended': f'pip install {package}',
                'alternatives': [
                    f'pip install --upgrade {package}',
                    f'python -m pip install {package}',
                ],
                'notes': '检测到 pip 可用',
            }
        elif 'conda' in tools['available']:
            return {
                'recommended': f'conda install {package}',
                'alternatives': [f'pip install {package}'],
                'notes': '检测到 conda 环境',
            }
        else:
            return {
                'recommended': '请先安装 pip',
                'alternatives': [],
                'notes': '未检测到 Python 包管理器',
            }

    def _recommend_process_list(self, os_name: str) -> Dict:
        """推荐进程查看命令"""
        if os_name == 'Windows':
            return {
                'recommended': 'tasklist',
                'alternatives': ['Get-Process (PowerShell)', '任务管理器 (Ctrl+Shift+Esc)'],
                'notes': 'Windows 系统',
            }
        else:
            return {
                'recommended': 'ps aux',
                'alternatives': ['top', 'htop', 'pgrep -l <name>'],
                'notes': 'Unix-like 系统',
            }

    def _recommend_cache_clean(self, os_name: str) -> Dict:
        """推荐缓存清理命令"""
        if os_name == 'Windows':
            return {
                'recommended': 'pip cache purge',
                'alternatives': ['npm cache clean --force', 'yarn cache clean'],
                'notes': '清理包管理器缓存',
            }
        else:
            return {
                'recommended': 'sudo apt clean && sudo apt autoclean',
                'alternatives': ['pip cache purge', 'npm cache clean --force'],
                'notes': '清理系统和包管理器缓存',
            }

    def _recommend_service_start(self, os_name: str, context: Dict) -> Dict:
        """推荐服务启动命令"""
        service = context.get('service_name', 'service_name')
        if os_name == 'Windows':
            return {
                'recommended': f'net start {service}',
                'alternatives': [f'Start-Service {service} (PowerShell)'],
                'notes': '需要管理员权限',
            }
        else:
            return {
                'recommended': f'sudo systemctl start {service}',
                'alternatives': [f'sudo service {service} start'],
                'notes': '需要 root 权限',
            }

    def run(self, tool_name: str, args: Dict) -> str:
        """统一工具执行入口"""
        dispatch = {
            'system_detect_os': lambda a: self.detect_os(a.get('anonymize', False)),
            'system_detect_python': lambda a: self.detect_python(),
            'system_detect_tools': lambda a: self.detect_tools(
                a.get('tools', []), a.get('timeout', 5)
            ),
            'system_get_env': lambda a: self.get_env(
                a.get('keys', []), a.get('anonymize_paths', False)
            ),
            'system_test_network': lambda a: self.test_network(
                a.get('targets', []), a.get('timeout', 3)
            ),
            'system_recommend_commands': lambda a: self.recommend_commands(
                a.get('task', ''), a.get('context', {})
            ),
        }

        fn = dispatch.get(tool_name)
        if not fn:
            return json.dumps({
                'status': 'error',
                'code': 'UNKNOWN_TOOL',
                'detail': f'未知工具: {tool_name}'
            })

        try:
            result = fn(args)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({
                'status': 'error',
                'code': 'EXECUTION_FAILED',
                'detail': str(e)
            }, ensure_ascii=False)
