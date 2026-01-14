---
trigger: always_on
---
# Python 代码规范

> 基于 **PEP 8 - Style Guide for Python Code**  
> 最后更新: 2026-01-14  
> 版本: v1.0

---

## 1. 命名规范

### 1.1 基本原则

- **【强制】** 命名应具有描述性，避免使用单字符名称（除了计数器和迭代器）
  - ❌ 反例: `l`, `O`, `I` (易与数字混淆)
  - ✅ 正例: `user_count`, `total_items`

- **【强制】** 永远不要使用字符 `l`（小写字母 el）、`O`（大写字母 oh）或 `I`（大写字母 eye）作为单字符变量名
  - 说明: 在某些字体中，这些字符与数字 1 和 0 无法区分

- **【推荐】** 命名应遵循项目特定的风格指南
  - 说明: 如果发生冲突，项目规范优先于 PEP 8

### 1.2 命名风格

#### 模块和包名称

- **【强制】** 模块名应短小，全部使用小写字母，可使用下划线提高可读性
  ```python
  # ✅ 正确
  my_module.py
  video_render.py
  
  # ❌ 错误
  MyModule.py
  videoRender.py
  ```

- **【推荐】** 包名应全部使用小写字母，不推荐使用下划线
  ```python
  # ✅ 正确
  mypackage/
  videoprocessing/
  
  # ❌ 不推荐
  my_package/
  video_processing/
  ```

#### 类名

- **【强制】** 类名使用 **CapWords**（大驼峰）命名约定
  ```python
  # ✅ 正确
  class VideoRenderer:
      pass
  
  class ProjectService:
      pass
  
  # ❌ 错误
  class video_renderer:
      pass
  
  class project_service:
      pass
  ```

- **【推荐】** 异常类应以 `Error` 结尾（如果异常确实是一个错误）
  ```python
  # ✅ 正确
  class VideoRenderError(Exception):
      pass
  
  class AssetNotFoundError(Exception):
      pass
  ```

#### 函数和变量名

- **【强制】** 函数名和变量名应使用小写字母，单词之间用下划线分隔（**snake_case**）
  ```python
  # ✅ 正确
  def get_project_by_id(project_id):
      pass
  
  user_count = 10
  project_name = "Test"
  
  # ❌ 错误
  def getProjectById(projectId):
      pass
  
  userCount = 10
  projectName = "Test"
  ```

#### 常量

- **【强制】** 常量使用全大写字母，单词之间用下划线分隔
  ```python
  # ✅ 正确
  MAX_OVERFLOW = 100
  DEFAULT_TIMEOUT = 30
  REDIS_URL = "redis://localhost:6379"
  
  # ❌ 错误
  maxOverflow = 100
  default_timeout = 30
  ```

#### 方法名和实例变量

- **【强制】** 使用函数命名规则：小写字母，必要时用下划线分隔单词
  ```python
  class ProjectService:
      def __init__(self):
          self.project_count = 0  # 实例变量
      
      def get_project_by_id(self, project_id):  # 方法名
          pass
  ```

- **【推荐】** 非公有方法和实例变量使用单下划线前缀
  ```python
  class ProjectService:
      def __init__(self):
          self._internal_state = {}  # 非公有实例变量
      
      def _internal_method(self):  # 非公有方法
          pass
  ```

- **【推荐】** 为避免与子类命名冲突，使用双下划线前缀（触发名称改写）
  ```python
  class Base:
      def __init__(self):
          self.__private_var = 42  # 会被改写为 _Base__private_var
  ```

---

## 2. 代码布局

### 2.1 缩进

- **【强制】** 每个缩进级别使用 **4 个空格**
  ```python
  # ✅ 正确
  def long_function_name(
          var_one, var_two, var_three,
          var_four):
      print(var_one)
  
  # ❌ 错误（使用了 2 个空格）
  def long_function_name(
    var_one, var_two):
      print(var_one)
  ```

- **【强制】** 续行应垂直对齐或使用悬挂缩进
  ```python
  # ✅ 正确：与左括号对齐
  foo = long_function_name(var_one, var_two,
                           var_three, var_four)
  
  # ✅ 正确：悬挂缩进
  foo = long_function_name(
      var_one, var_two,
      var_three, var_four)
  
  # ❌ 错误：第一行有参数时未对齐
  foo = long_function_name(var_one, var_two,
      var_three, var_four)
  ```

### 2.2 制表符还是空格

- **【强制】** 空格是首选的缩进方法
  - 说明: Python 禁止混合使用制表符和空格进行缩进

- **【推荐】** 制表符应仅用于与已用制表符缩进的代码保持一致

### 2.3 最大行长

- **【强制】** 将所有行限制为最多 **79 个字符**
  - 说明: 对于结构限制较少的长文本块（文档字符串或注释），行长应限制为 72 个字符

- **【推荐】** 团队可将行长限制增加到 99 个字符
  - 说明: 但注释和文档字符串仍应在 72 个字符处换行
  - 注: **本项目 Engine 采用 88 个字符**（Black 默认值）

- **【推荐】** 包装长行的首选方法是使用 Python 在括号、方括号和大括号内的隐式行连续
  ```python
  # ✅ 正确：使用括号隐式连续
  income = (gross_wages
            + taxable_interest
            + (dividends - qualified_dividends)
            - ira_deduction
            - student_loan_interest)
  
  # ✅ 正确：使用反斜杠（不推荐，但有时必要）
  with open('/path/to/some/file/you/want/to/read') as file_1, \
       open('/path/to/some/file/being/written', 'w') as file_2:
      file_2.write(file_1.read())
  ```

### 2.4 二元运算符换行

- **【推荐】** 在二元运算符之前换行
  ```python
  # ✅ 正确：运算符与操作数对齐，易于阅读
  income = (gross_wages
            + taxable_interest
            + (dividends - qualified_dividends)
            - ira_deduction
            - student_loan_interest)
  
  # ❌ 不推荐：运算符远离操作数
  income = (gross_wages +
            taxable_interest +
            (dividends - qualified_dividends) -
            ira_deduction -
            student_loan_interest)
  ```

### 2.5 空行

- **【强制】** 顶级函数和类定义前后各留 **2 个空行**
  ```python
  import os
  import sys
  
  
  class ProjectService:
      pass
  
  
  def standalone_function():
      pass
  
  
  class AnotherClass:
      pass
  ```

- **【强制】** 类内方法定义之间留 **1 个空行**
  ```python
  class ProjectService:
      def __init__(self):
          self.projects = []
      
      def get_project(self, project_id):
          pass
      
      def create_project(self, name):
          pass
  ```

- **【推荐】** 在函数内使用空行（谨慎）分隔逻辑段
  ```python
  def complex_function():
      # 第一步：准备数据
      data = load_data()
      data = clean_data(data)
      
      # 第二步：处理数据
      result = process_data(data)
      
      # 第三步：返回结果
      return result
  ```

### 2.6 源文件编码

- **【强制】** Python 源文件始终使用 **UTF-8** 编码

- **【推荐】** 标准库中的标识符必须使用 ASCII 标识符，并在可行的情况下使用英语单词

---

## 3. 导入

### 3.1 导入规范

- **【强制】** 导入通常应分行
  ```python
  # ✅ 正确
  import os
  import sys
  
  # ❌ 错误
  import os, sys
  
  # ✅ 正确：从同一模块导入多个成员
  from subprocess import Popen, PIPE
  ```

- **【强制】** 导入应位于文件顶部，在模块注释和文档字符串之后，在模块全局变量和常量之前

- **【强制】** 导入应按以下顺序分组，每组之间用空行分隔：
  1. 标准库导入
  2. 相关第三方库导入
  3. 本地应用/库特定导入
  
  ```python
  # ✅ 正确
  import os
  import sys
  
  import redis
  from celery import Celery
  
  from .config import Config
  from .video_render import VideoRenderer
  ```

- **【推荐】** 推荐使用绝对导入
  ```python
  # ✅ 推荐
  from engine import video_render
  from engine.config import Config
  
  # ❌ 不推荐（但在某些情况下可接受）
  from . import video_render
  from .config import Config
  ```

- **【强制】** 避免通配符导入 `from module import *`
  - 说明: 通配符导入会使命名空间变得不明确，难以确定某个名称的来源
  
  ```python
  # ❌ 错误
  from video_render import *
  
  # ✅ 正确
  from video_render import VideoRenderer, render_video
  ```

---

## 4. 表达式和语句中的空白符

### 4.1 避免的情况

- **【强制】** 紧贴在括号、方括号或大括号内侧
  ```python
  # ✅ 正确
  spam(ham[1], {eggs: 2})
  
  # ❌ 错误
  spam( ham[ 1 ], { eggs: 2 } )
  ```

- **【强制】** 在尾随逗号和后面的闭括号之间
  ```python
  # ✅ 正确
  foo = (0,)
  
  # ❌ 错误
  foo = (0, )
  ```

- **【强制】** 紧贴在逗号、分号或冒号之前
  ```python
  # ✅ 正确
  if x == 4: print(x, y); x, y = y, x
  
  # ❌ 错误
  if x == 4 : print(x , y) ; x , y = y , x
  ```

- **【强制】** 在函数调用的开括号之前
  ```python
  # ✅ 正确
  spam(1)
  
  # ❌ 错误
  spam (1)
  ```

- **【强制】** 在索引或切片的开括号之前
  ```python
  # ✅ 正确
  dct['key'] = lst[index]
  
  # ❌ 错误
  dct ['key'] = lst [index]
  ```

### 4.2 其他建议

- **【强制】** 二元运算符两侧各留一个空格
  ```python
  # ✅ 正确
  i = i + 1
  submitted += 1
  x = x * 2 - 1
  hypot2 = x * x + y * y
  c = (a + b) * (a - b)
  
  # ❌ 错误
  i=i+1
  submitted +=1
  x = x*2 - 1
  hypot2 = x*x + y*y
  c = (a+b) * (a-b)
  ```

- **【推荐】** 在具有不同优先级的运算符周围添加空白
  ```python
  # ✅ 正确
  x = x*2 - 1
  hypot2 = x*x + y*y
  c = (a+b) * (a-b)
  
  # ❌ 不推荐（但不是错误）
  x = x * 2 - 1
  hypot2 = x * x + y * y
  c = (a + b) * (a - b)
  ```

- **【强制】** 函数注解中的冒号遵循正常规则，`->` 两侧各留一个空格
  ```python
  # ✅ 正确
  def munge(input: str) -> str:
      pass
  
  def munge() -> str:
      pass
  
  # ❌ 错误
  def munge(input:str)->str:
      pass
  ```

- **【强制】** 关键字参数或默认参数值的 `=` 两侧不要空格
  ```python
  # ✅ 正确
  def complex(real, imag=0.0):
      return magic(r=real, i=imag)
  
  # ❌ 错误
  def complex(real, imag = 0.0):
      return magic(r = real, i = imag)
  ```

---

## 5. 注释

### 5.1 块注释

- **【强制】** 块注释通常应用于跟随其后的一些（或全部）代码，并缩进到与该代码相同的级别
  ```python
  # ✅ 正确
  def render_video(project_id):
      # 第一步：下载所有素材文件
      # 这是一个耗时操作，可能需要几分钟
      assets = download_assets(project_id)
      
      # 第二步：生成视频帧
      frames = generate_frames(assets)
      
      return frames
  ```

- **【强制】** 块注释的每一行都以 `#` 和一个空格开始
  ```python
  # ✅ 正确
  # This is a block comment.
  # It spans multiple lines.
  
  # ❌ 错误
  #This is a block comment.
  #No space after hash.
  ```

### 5.2 行内注释

- **【推荐】** 谨慎使用行内注释
  - 说明: 行内注释是与语句在同一行的注释
  
  ```python
  # ✅ 正确（必要时使用）
  x = x + 1  # Compensate for border
  
  # ❌ 错误（显而易见的注释）
  x = x + 1  # Increment x
  ```

- **【强制】** 行内注释应至少与语句相隔两个空格，并以 `#` 和一个空格开始
  ```python
  # ✅ 正确
  x = x + 1  # Compensate for border
  
  # ❌ 错误
  x = x + 1 # No space before hash
  x = x + 1  #No space after hash
  ```

### 5.3 文档字符串

- **【强制】** 为所有公共模块、函数、类和方法编写文档字符串
  - 说明: 非公共方法不需要文档字符串，但应有注释说明其功能

- **【强制】** 多行文档字符串的 `"""` 应单独成行
  ```python
  # ✅ 正确
  def complex_function(arg1, arg2):
      """
      执行复杂操作的函数。
      
      Args:
          arg1 (str): 第一个参数的描述
          arg2 (int): 第二个参数的描述
      
      Returns:
          dict: 包含处理结果的字典
      
      Raises:
          ValueError: 当 arg2 为负数时
      """
      if arg2 < 0:
          raise ValueError("arg2 must be non-negative")
      
      return {"result": f"{arg1}_{arg2}"}
  
  # ✅ 正确：单行文档字符串
  def simple_function():
      """执行简单操作。"""
      pass
  ```

- **【推荐】** 使用 Google 风格或 NumPy 风格的文档字符串
  ```python
  # ✅ 正确：Google 风格
  def render_video(project_id: int, output_path: str) -> bool:
      """
      渲染指定项目的视频。
      
      Args:
          project_id: 项目ID
          output_path: 输出视频的路径
      
      Returns:
          渲染是否成功
      
      Raises:
          ProjectNotFoundError: 项目不存在
          RenderError: 渲染过程中出现错误
      """
      pass
  ```

---

## 6. 编程建议

### 6.1 代码比较

- **【强制】** 与 `None` 的比较应使用 `is` 或 `is not`，而不是等号运算符
  ```python
  # ✅ 正确
  if foo is None:
      pass
  
  if foo is not None:
      pass
  
  # ❌ 错误
  if foo == None:
      pass
  ```

- **【推荐】** 使用 `is not` 而不是 `not ... is`
  ```python
  # ✅ 正确
  if foo is not None:
      pass
  
  # ❌ 不推荐
  if not foo is None:
      pass
  ```

### 6.2 返回语句

- **【强制】** 函数中的所有 return 语句应保持一致
  ```python
  # ✅ 正确
  def foo(x):
      if x >= 0:
          return math.sqrt(x)
      else:
          return None
  
  # ❌ 错误
  def foo(x):
      if x >= 0:
          return math.sqrt(x)
  ```

### 6.3 字符串处理

- **【推荐】** 使用 `.startswith()` 和 `.endswith()` 而不是字符串切片
  ```python
  # ✅ 正确
  if foo.startswith('bar'):
      pass
  
  # ❌ 不推荐
  if foo[:3] == 'bar':
      pass
  ```

- **【推荐】** 使用 f-string 或 `.format()` 进行字符串格式化
  ```python
  # ✅ 推荐：f-string（Python 3.6+）
  name = "Alice"
  age = 30
  message = f"Hello, {name}! You are {age} years old."
  
  # ✅ 正确：.format()
  message = "Hello, {}! You are {} years old.".format(name, age)
  
  # ❌ 不推荐：% 格式化（除非必须兼容旧版本）
  message = "Hello, %s! You are %d years old." % (name, age)
  ```

### 6.4 类型注解

- **【推荐】** 使用类型注解提高代码可读性
  ```python
  # ✅ 推荐
  from typing import List, Dict, Optional
  
  def get_projects(user_id: str) -> List[Dict[str, any]]:
      """获取用户的所有项目。"""
      pass
  
  def find_project(project_id: int) -> Optional[Dict[str, any]]:
      """查找项目，如果不存在返回 None。"""
      pass
  ```

### 6.5 异常处理

- **【强制】** 捕获异常时要尽可能指定具体的异常类型
  ```python
  # ✅ 正确
  try:
      value = int(user_input)
  except ValueError:
      log.error("Invalid input: not a number")
  
  # ❌ 错误
  try:
      value = int(user_input)
  except:
      pass
  ```

- **【推荐】** 将 `try` 块中的代码量限制到绝对最小
  ```python
  # ✅ 正确
  try:
      value = collection[key]
  except KeyError:
      return default_value
  else:
      return process(value)
  
  # ❌ 不推荐
  try:
      value = collection[key]
      result = process(value)
      return result
  except KeyError:
      return default_value
  ```

---

## 7. 项目特定规范

### 7.1 Engine 模块规范

- **【强制】** 所有 Celery 任务必须包含错误处理和日志记录
  ```python
  @celery_app.task(bind=True)
  def render_video_task(self, project_id: int) -> dict:
      """
      渲染视频任务。
      
      Args:
          project_id: 项目ID
      
      Returns:
          包含渲染结果的字典
      """
      try:
          log.info(f"Starting video render for project {project_id}")
          result = render_video(project_id)
          log.info(f"Video render completed for project {project_id}")
          return result
      except Exception as e:
          log.error(f"Video render failed for project {project_id}", exc_info=True)
          raise
  ```

- **【推荐】** 使用 `Config` 类集中管理配置
  ```python
  # ✅ 正确
  from config import Config
  
  if Config.SUBTITLE_ENABLED:
      add_subtitles(video)
  
  # ❌ 不推荐
  import os
  
  if os.getenv('SUBTITLE_ENABLED', 'true').lower() == 'true':
      add_subtitles(video)
  ```

### 7.2 日志规范

- **【强制】** 使用结构化日志记录关键事件
  ```python
  # ✅ 正确
  log.info("Video render started", extra={
      "event": "render.started",
      "project_id": project_id,
      "user_id": user_id
  })
  
  # ❌ 错误：缺少结构化字段
  log.info(f"Video render started for project {project_id}")
  ```

- **【强制】** 必须在日志中包含 `request_id`（如果可用）
  ```python
  # ✅ 正确
  log.info("Processing request", extra={
      "request_id": request_id,
      "project_id": project_id
  })
  ```

### 7.3 配置验证

- **【推荐】** 在启动时验证关键配置
  ```python
  # ✅ 正确（参考 engine/worker.py）
  @worker_ready.connect
  def on_worker_ready(**kwargs):
      """Worker 启动时验证配置。"""
      warnings = Config.validate()
      if warnings:
          for warning in warnings:
              log.warning(f"Config validation: {warning}")
  ```

---

## 8. 工具配置

### 8.1 代码格式化工具

#### Black

本项目推荐使用 **Black** 进行代码格式化：

```bash
# 安装
pip install black

# 格式化代码
black engine/

# 检查格式（不修改文件）
black --check engine/
```

配置文件 `pyproject.toml`:

```toml
[tool.black]
line-length = 88
target-version = ['py310']
include = '\.pyi?$'
extend-exclude = '''
/(
  # 排除特定目录
  \.git
  | \.venv
  | build
  | dist
)/
'''
```

#### isort

使用 **isort** 管理导入排序：

```bash
# 安装
pip install isort

# 排序导入
isort engine/

# 检查导入顺序
isort --check-only engine/
```

配置文件 `pyproject.toml`:

```toml
[tool.isort]
profile = "black"
line_length = 88
```

### 8.2 代码检查工具

#### Flake8

使用 **Flake8** 进行代码检查：

```bash
# 安装
pip install flake8

# 检查代码
flake8 engine/
```

配置文件 `.flake8`:

```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude =
    .git,
    __pycache__,
    .venv,
    build,
    dist
```

#### Pylint

使用 **Pylint** 进行更严格的代码检查：

```bash
# 安装
pip install pylint

# 检查代码
pylint engine/
```

### 8.3 类型检查工具

#### MyPy

使用 **MyPy** 进行静态类型检查：

```bash
# 安装
pip install mypy

# 类型检查
mypy engine/
```

配置文件 `mypy.ini`:

```ini
[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False
ignore_missing_imports = True
```

---

## 9. 质量门禁

### 9.1 提交前检查

在提交代码前，运行以下命令：

```bash
# 1. 代码格式化
black engine/

# 2. 导入排序
isort engine/

# 3. 代码检查
flake8 engine/

# 4. 类型检查（可选）
mypy engine/
```

### 9.2 CI/CD 集成

在 GitHub Actions 或 GitLab CI 中添加质量检查：

```yaml
# .github/workflows/python-quality.yml
name: Python Quality Check

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install black isort flake8 mypy
      
      - name: Check formatting with Black
        run: black --check engine/
      
      - name: Check import order with isort
        run: isort --check-only engine/
      
      - name: Lint with Flake8
        run: flake8 engine/
      
      - name: Type check with MyPy
        run: mypy engine/
```

---

## 10. 参考资源

### 官方文档

- [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [PEP 8 中文版](https://peps.pythonlang.cn/pep-0008/)
- [PEP 257 - Docstring Conventions](https://peps.python.org/pep-0257/)

### 工具文档

- [Black - The uncompromising code formatter](https://black.readthedocs.io/)
- [isort - Import sorting utility](https://pycqa.github.io/isort/)
- [Flake8 - Code linting tool](https://flake8.pycqa.org/)
- [MyPy - Static type checker](https://mypy.readthedocs.io/)

### 风格指南

- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [The Hitchhiker's Guide to Python - Code Style](https://docs.python-guide.org/writing/style/)

---

## 附录：快速检查清单

开发前检查：
- [ ] 函数名、变量名使用 snake_case
- [ ] 类名使用 CapWords
- [ ] 常量使用 UPPER_CASE
- [ ] 每个缩进级别使用 4 个空格
- [ ] 单行代码不超过 88 个字符（Black 默认）

提交代码前检查：
- [ ] 运行 `black` 格式化代码
- [ ] 运行 `isort` 排序导入
- [ ] 运行 `flake8` 检查代码
- [ ] 所有公共函数都有文档字符串
- [ ] 异常处理完整，日志记录充分
- [ ] 无硬编码的密钥、密码

代码审查时关注：
- [ ] 导入顺序是否正确
- [ ] 是否有不必要的空白符
- [ ] 注释是否清晰有用
- [ ] 是否使用了类型注解
- [ ] 日志记录是否包含必要的上下文信息
