# System Detection - 系统检测技能

> 自动检测运行环境的操作系统、架构、Python 版本、可用工具等信息，为跨平台适配提供支持。

## 触发条件

以下情况自动激活：
- 用户询问系统信息（"我的系统是什么？"、"检测环境"）
- 需要执行平台相关命令前
- 安装依赖或配置环境时
- 遇到跨平台兼容性问题时

## 核心功能

### 1. 操作系统检测
- 识别 Windows / Linux / macOS
- 获取系统版本和架构（x64 / ARM / x86）
- 检测 WSL（Windows Subsystem for Linux）环境

### 2. Python 环境检测
- Python 版本和解释器路径
- 虚拟环境状态（venv / conda / poetry）
- 已安装的包管理器（pip / conda / poetry）

### 3. 常用工具检测
检测以下工具是否可用：
- **版本控制**：git, svn, hg
- **包管理器**：npm, yarn, pnpm, pip, conda, cargo, go
- **构建工具**：make, cmake, gcc, clang, rustc
- **容器工具**：docker, podman, kubectl
- **数据库客户端**：psql, mysql, redis-cli, mongo
- **编辑器/IDE**：code, vim, emacs, nano

### 4. 环境变量
- 读取常用环境变量（PATH, HOME, SHELL 等）
- 检测代理配置（HTTP_PROXY, HTTPS_PROXY）
- 检测语言和地区设置（LANG, LC_ALL）

### 5. 网络连接
- 检测网络连通性
- DNS 解析测试
- 常用服务可达性（GitHub, PyPI, npm registry）

## 工具列表

### `system_detect_os`
检测操作系统信息。

**返回：**
```json
{
  "os": "Windows",
  "version": "10.0.19045",
  "architecture": "AMD64",
  "is_wsl": false,
  "hostname": "DESKTOP-XXX",
  "username": "user"
}
```

### `system_detect_python`
检测 Python 环境。

**返回：**
```json
{
  "version": "3.11.5",
  "executable": "C:\\Python311\\python.exe",
  "venv_active": true,
  "venv_path": "C:\\projects\\myapp\\venv",
  "pip_version": "23.2.1",
  "site_packages": "C:\\Python311\\Lib\\site-packages"
}
```

### `system_detect_tools`
批量检测工具可用性。

**参数：**
- `tools`（可选）：工具名称列表，默认检测所有常用工具

**返回：**
```json
{
  "available": {
    "git": "2.41.0",
    "node": "18.17.0",
    "npm": "9.8.1",
    "docker": "24.0.5"
  },
  "unavailable": ["kubectl", "cargo"]
}
```

### `system_get_env`
读取环境变量。

**参数：**
- `keys`：环境变量名称列表

**返回：**
```json
{
  "PATH": "C:\\Windows\\system32;C:\\Python311;...",
  "HOME": "C:\\Users\\user",
  "TEMP": "C:\\Users\\user\\AppData\\Local\\Temp"
}
```

### `system_test_network`
测试网络连通性。

**参数：**
- `targets`（可选）：测试目标列表，默认 ["github.com", "pypi.org"]

**返回：**
```json
{
  "connected": true,
  "results": {
    "github.com": {"reachable": true, "latency_ms": 45},
    "pypi.org": {"reachable": true, "latency_ms": 78}
  },
  "dns_working": true,
  "proxy_detected": false
}
```

### `system_recommend_commands`
根据当前系统推荐命令。

**参数：**
- `task`：任务描述（如 "安装 Python 包"、"启动服务"）

**返回：**
```json
{
  "task": "安装 Python 包",
  "recommended": "pip install package_name",
  "alternatives": ["conda install package_name", "poetry add package_name"],
  "notes": "检测到虚拟环境已激活，建议使用 pip"
}
```

## 使用场景

### 1. 跨平台命令适配
在执行命令前，根据系统类型选择合适的命令：
```python
# 检测系统
os_info = system_detect_os()

# 根据系统选择命令
if os_info["os"] == "Windows":
    cmd = "dir"
else:
    cmd = "ls -la"
```

### 2. 依赖安装引导
检测可用的包管理器，推荐安装命令：
```python
tools = system_detect_tools(["pip", "conda", "poetry"])

if "pip" in tools["available"]:
    print("使用 pip 安装：pip install requests")
elif "conda" in tools["available"]:
    print("使用 conda 安装：conda install requests")
```

### 3. 环境问题诊断
当用户遇到环境问题时，收集完整信息：
```python
# 收集诊断信息
os_info = system_detect_os()
python_info = system_detect_python()
tools_info = system_detect_tools()
network_info = system_test_network()

# 生成诊断报告
print(f"系统: {os_info['os']} {os_info['version']}")
print(f"Python: {python_info['version']}")
print(f"网络: {'正常' if network_info['connected'] else '异常'}")
```

### 4. 智能命令建议
根据系统和可用工具，自动调整命令建议：
```python
# 用户: "如何查看进程？"
os_info = system_detect_os()

if os_info["os"] == "Windows":
    suggest("使用 tasklist 或任务管理器")
else:
    suggest("使用 ps aux 或 top")
```

## 配置参数

无需配置，开箱即用。

## 性能考虑

- 所有检测操作都有超时限制（默认 5 秒）
- 工具检测结果会缓存 5 分钟
- 网络测试采用并发执行，最快 1 秒完成

## 边界

- 不收集敏感信息（密码、密钥、个人文件）
- 不修改系统配置或环境变量
- 不执行需要管理员权限的操作
- 检测结果仅供参考，不保证 100% 准确

## 隐私保护

- 所有检测信息仅在本地使用，不上传
- 主机名和用户名可选脱敏（仅显示前 3 字符）
- 环境变量仅返回用户请求的键

## 错误处理

所有工具调用失败时返回友好的错误信息：
```json
{
  "status": "error",
  "code": "DETECTION_FAILED",
  "detail": "无法检测操作系统版本",
  "fallback": "假设为 Windows 10"
}
```
