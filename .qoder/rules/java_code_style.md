---
trigger: always_on
---
# Java 代码规范

> 基于**阿里巴巴Java开发手册**和**Google Java Style Guide**  
> 最后更新: 2026-01-14  
> 版本: v1.0

---

## 1. 命名规范

### 1.1 基本原则

- **【强制】** 代码中的命名均不能以**下划线或美元符号**开始，也不能以下划线或美元符号结束
  - ❌ 反例: `_name`, `__name`, `$name`, `name_`, `name$`
  
- **【强制】** 代码中的命名**严禁使用拼音与英文混合**的方式，更不允许直接使用中文
  - ✅ 正例: `alibaba`, `taobao`, `youku`, `hangzhou`
  - ❌ 反例: `DaZhePromotion` (打折), `getPingfenByName()`, `String fw` (福娃)
  - 注意: 国际通用的名称（如 Beijing, Hangzhou）视为英文

- **【强制】** 类名使用 **UpperCamelCase** 风格
  - ✅ 正例: `ProjectController`, `UserService`, `AssetRepository`
  - ❌ 反例: `projectController`, `user_service`, `ASSETREPOSITORY`

- **【强制】** 方法名、参数名、成员变量、局部变量使用 **lowerCamelCase** 风格
  - ✅ 正例: `getUserById()`, `projectName`, `localValue`
  - ❌ 反例: `GetUserById()`, `project_name`, `LocalValue`

- **【强制】** 常量命名全部大写，单词间用下划线隔开
  - ✅ 正例: `MAX_STOCK_COUNT`, `DEFAULT_TIMEOUT`
  - ❌ 反例: `maxStockCount`, `default_timeout`

### 1.2 类命名规范

- **【强制】** 抽象类命名使用 `Abstract` 或 `Base` 开头
  - ✅ 正例: `AbstractService`, `BaseEntity`

- **【强制】** 异常类命名使用 `Exception` 结尾
  - ✅ 正例: `VideoRenderException`, `AssetNotFoundException`

- **【强制】** 测试类命名以它要测试的类名开始，以 `Test` 结尾
  - ✅ 正例: `ProjectServiceTest`, `StorageServiceTest`

- **【推荐】** 如果模块、接口、类、方法使用了设计模式，在命名时体现出具体模式
  - ✅ 正例: `ProjectFactory`, `VideoObserver`, `TaskQueueService`

### 1.3 包命名规范

- **【强制】** 包名统一使用**小写**，点分隔符之间有且仅有一个自然语义的英语单词
  - ✅ 正例: `com.aiscene.controller`, `com.aiscene.service`
  - ❌ 反例: `com.aiscene.Controller`, `com.aiscene.user_service`

### 1.4 方法命名规范

- **【推荐】** 获取单个对象的方法用 `get` 做前缀
  - ✅ 正例: `getProjectById()`, `getUserInfo()`

- **【推荐】** 获取多个对象的方法用 `list` 做前缀，复数结尾
  - ✅ 正例: `listProjects()`, `listAssets()`

- **【推荐】** 获取统计值的方法用 `count` 做前缀
  - ✅ 正例: `countProjects()`, `countActiveUsers()`

- **【推荐】** 插入的方法用 `save`/`insert` 做前缀
  - ✅ 正例: `saveProject()`, `insertAsset()`

- **【推荐】** 删除的方法用 `remove`/`delete` 做前缀
  - ✅ 正例: `removeProject()`, `deleteAsset()`

- **【推荐】** 修改的方法用 `update` 做前缀
  - ✅ 正例: `updateProjectStatus()`, `updateAssetUrl()`

---

## 2. 代码格式

### 2.1 缩进与空格

- **【强制】** 采用 **4 个空格缩进**，禁止使用 Tab 字符
  - 说明: 如果使用 Tab 缩进，必须设置 1 个 Tab 为 4 个空格

- **【强制】** 大括号使用约定（K&R 风格）
  ```java
  // ✅ 正确
  if (condition) {
      // code
  } else {
      // code
  }
  
  // ❌ 错误
  if (condition)
  {
      // code
  }
  ```

- **【强制】** 左小括号和右边相邻字符之间不出现空格；右小括号和左边相邻字符之间也不出现空格
  ```java
  // ✅ 正确
  if (condition) {
      method(arg1, arg2);
  }
  
  // ❌ 错误
  if ( condition ) {
      method( arg1, arg2 );
  }
  ```

- **【强制】** 左大括号前不换行；左大括号后换行
  ```java
  // ✅ 正确
  public void method() {
      // code
  }
  
  // ❌ 错误
  public void method()
  {
      // code
  }
  ```

### 2.2 行长度限制

- **【推荐】** 单行字符数限制不超过 **120** 个字符
  - 说明: Google Style 建议 100 个字符，阿里规范建议 120 个字符，本项目采用 120

- **【强制】** 换行时遵循如下原则：
  1. 第二行相对第一行缩进 4 个空格，从第三行开始，不再继续缩进
  2. 运算符与下文一起换行
  3. 方法调用的点符号与下文一起换行
  4. 方法调用中的多个参数需要换行时，在逗号后进行
  5. 在括号前不要换行
  
  ```java
  // ✅ 正确：运算符与下文一起换行
  String result = longVariableName1 + longVariableName2
      + longVariableName3;
  
  // ✅ 正确：方法链式调用换行
  project.setName("test")
      .setDescription("desc")
      .setStatus(ProjectStatus.CREATED);
  ```

### 2.3 空行规范

- **【强制】** 方法体内的执行语句组、变量的定义语句组、不同的业务逻辑之间或者不同的语义之间插入一个空行
  - 说明: 相同业务逻辑和语义之间不需要插入空行

- **【推荐】** 类内成员之间用一个空行分隔
  ```java
  public class Project {
      private Long id;
      
      private String name;
      
      public Long getId() {
          return id;
      }
      
      public void setId(Long id) {
          this.id = id;
      }
  }
  ```

### 2.4 导入顺序

- **【强制】** import 语句分组顺序如下：
  1. 所有静态导入（一个组）
  2. `java.*` 包
  3. `javax.*` 包
  4. 第三方库（如 `org.springframework.*`, `com.fasterxml.*`）
  5. 本项目内的包（如 `com.aiscene.*`）
  
- **【强制】** 禁止使用通配符导入 `import xxx.*`
  - ❌ 反例: `import java.util.*`
  - ✅ 正例: `import java.util.List`, `import java.util.ArrayList`

---

## 3. 面向对象规约

### 3.1 类设计

- **【强制】** 避免通过一个类的对象引用访问此类的静态变量或静态方法
  - 说明: 增加编译器解析成本，直接用类名来访问即可
  - ❌ 反例: `project.MAX_COUNT` (project 是 Project 类的实例)
  - ✅ 正例: `Project.MAX_COUNT`

- **【强制】** 所有的覆写方法，必须加 `@Override` 注解
  - 说明: 防止子类在 Override 父类方法时因拼写错误导致方法未覆写成功

- **【强制】** 外部正在调用或者二方库依赖的接口，不允许修改方法签名
  - 说明: 避免对接口调用方产生影响

- **【推荐】** 使用索引访问用 String 的 `split` 方法得到的数组时，需做最后一个分隔符后有无内容的检查

### 3.2 日志规约

- **【强制】** 应用中不可直接使用日志系统（Log4j、Logback）中的 API，而应依赖使用日志框架（SLF4J）中的 API
  ```java
  // ✅ 正确
  import org.slf4j.Logger;
  import org.slf4j.LoggerFactory;
  
  private static final Logger log = LoggerFactory.getLogger(ProjectService.class);
  ```

- **【强制】** 日志文件至少保存 15 天，因为有些异常具备以"周"为频次发生的特点

- **【强制】** 避免重复打印日志，浪费磁盘空间
  - 说明: 务必在日志配置文件中设置 `additivity=false`

- **【强制】** 异常信息应该包括两类信息：案发现场信息和异常堆栈信息
  ```java
  // ✅ 正确
  log.error("Failed to render video for project {}", projectId, exception);
  
  // ❌ 错误：未打印异常堆栈
  log.error("Failed to render video");
  ```

- **【推荐】** 谨慎地记录日志。生产环境禁止输出 debug 日志；有选择地输出 info 日志
  - 说明: 大量的无效日志会对系统性能产生影响，并且没有意义

---

## 4. 注释规范

### 4.1 类注释

- **【强制】** 类、类属性、类方法的注释必须使用 Javadoc 规范，使用 `/**内容*/` 格式
  ```java
  /**
   * 项目管理服务
   * 
   * @author zijun
   * @since 2026-01-14
   */
  public class ProjectService {
      // ...
  }
  ```

### 4.2 方法注释

- **【强制】** 所有的抽象方法（包括接口中的方法）必须要用 Javadoc 注释
  - 说明: 除了返回值、参数、异常说明外，还必须指出该方法做什么事情，实现什么功能

  ```java
  /**
   * 根据项目ID获取项目详情
   * 
   * @param projectId 项目ID，不能为null
   * @return 项目详情，如果不存在返回null
   * @throws IllegalArgumentException 如果projectId为null
   */
  public Project getProjectById(Long projectId) {
      // ...
  }
  ```

- **【推荐】** 方法内部单行注释，在被注释语句上方另起一行，使用 `//` 注释
  ```java
  // 检查项目状态是否允许删除
  if (project.getStatus() == ProjectStatus.RENDERING) {
      throw new IllegalStateException("Cannot delete project during rendering");
  }
  ```

### 4.3 其他注释

- **【强制】** 所有的枚举类型字段必须要有注释，说明每个数据项的用途
  ```java
  public enum ProjectStatus {
      /** 已创建 */
      CREATED,
      /** 分析中 */
      ANALYZING,
      /** 渲染中 */
      RENDERING,
      /** 已完成 */
      COMPLETED,
      /** 失败 */
      FAILED
  }
  ```

- **【推荐】** 特殊注释标记，请注明标记人与标记时间
  - `TODO`: 待办事项
  - `FIXME`: 需要修复的问题
  - `NOTE`: 重要说明
  
  ```java
  // TODO(zijun, 2026-01-14): 增加缓存机制提升性能
  // FIXME(zijun, 2026-01-14): 修复并发情况下的状态不一致问题
  ```

---

## 5. 异常处理

### 5.1 异常捕获

- **【强制】** 不要捕获 Java 类库中定义的继承自 `RuntimeException` 的运行时异常类
  - 说明: 如 `NullPointerException`, `IndexOutOfBoundsException` 等，应该通过预检查方式规避

- **【强制】** 异常不要用来做流程控制，条件控制
  - 说明: 异常设计的初衷是解决程序运行中的各种意外情况，且异常的处理效率比条件判断方式要低很多

- **【强制】** 对大段代码进行 `try-catch`，这是不负责任的表现
  - 说明: `catch` 时请分清稳定代码和非稳定代码，稳定代码指的是无论如何不会出错的代码
  
  ```java
  // ✅ 正确：仅对可能抛出异常的代码进行 try-catch
  try {
      String content = storageService.downloadFile(url);
  } catch (IOException e) {
      log.error("Failed to download file from {}", url, e);
      throw new RuntimeException("File download failed", e);
  }
  
  // ❌ 错误：try 块范围过大
  try {
      // 100 lines of code
  } catch (Exception e) {
      log.error("Error", e);
  }
  ```

- **【强制】** 捕获异常是为了处理它，不要捕获了却什么都不处理而抛弃之
  - ❌ 反例: `catch (Exception e) { /* empty */ }`

### 5.2 异常抛出

- **【强制】** 方法的返回值可以为 `null`，不强制返回空集合或空对象
  - 说明: 但必须添加注释充分说明什么情况下会返回 `null` 值

- **【推荐】** 防止 `NPE`（NullPointerException），是程序员的基本修养
  - 使用 `Optional` 或在方法调用前进行 `null` 检查

  ```java
  // ✅ 推荐使用 Optional
  public Optional<Project> findProjectById(Long id) {
      return projectRepository.findById(id);
  }
  
  // ✅ 使用前检查 null
  if (project != null && project.getName() != null) {
      log.info("Project name: {}", project.getName());
  }
  ```

---

## 6. 单元测试

### 6.1 测试原则

- **【强制】** 单元测试代码必须写在如下工程目录：`src/test/java`
  - 不允许写在业务代码目录下

- **【推荐】** 单元测试的基本目标：语句覆盖率达到 70%；核心模块的语句覆盖率和分支覆盖率都要达到 100%
  - 说明: 本项目 Backend 使用 JaCoCo，当前阈值: 指令覆盖率 ≥ 80%

- **【推荐】** 编写单元测试代码遵守 BCDE 原则，以保证被测试模块的交付质量
  - **B**order：边界值测试
  - **C**orrect：正确的输入，期望得到正确的结果
  - **D**esign：设计文档中的说明
  - **E**rror：强制错误信息输入，得到期望的错误结果

### 6.2 测试命名

- **【强制】** 测试方法命名使用 `should_ExpectedBehavior_When_StateUnderTest` 格式
  ```java
  @Test
  public void should_ReturnProject_When_ProjectExists() {
      // given
      Long projectId = 1L;
      Project project = new Project();
      project.setId(projectId);
      when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
      
      // when
      Project result = projectService.getProjectById(projectId);
      
      // then
      assertNotNull(result);
      assertEquals(projectId, result.getId());
  }
  ```

- **【推荐】** 测试方法使用 Given-When-Then 结构组织
  ```java
  @Test
  public void should_ThrowException_When_ProjectNotFound() {
      // given (准备测试数据)
      Long projectId = 999L;
      when(projectRepository.findById(projectId)).thenReturn(Optional.empty());
      
      // when & then (执行并验证)
      assertThrows(EntityNotFoundException.class, () -> {
          projectService.getProjectById(projectId);
      });
  }
  ```

---

## 7. 安全规约

### 7.1 输入验证

- **【强制】** 用户敏感数据禁止直接展示，必须对展示数据进行脱敏
  - 说明: 手机号显示为 `138****1234`，身份证号显示为 `330***********01`

- **【强制】** 用户输入的 SQL 参数严格使用参数绑定或者 METADATA 字段值限定
  - 说明: 防止 SQL 注入
  
  ```java
  // ✅ 正确：使用参数绑定
  @Query("SELECT p FROM Project p WHERE p.userId = :userId")
  List<Project> findByUserId(@Param("userId") String userId);
  
  // ❌ 错误：拼接 SQL
  String sql = "SELECT * FROM projects WHERE user_id = '" + userId + "'";
  ```

### 7.2 密钥管理

- **【强制】** 禁止在代码中硬编码密码、密钥、Token 等敏感信息
  - 说明: 必须通过环境变量注入
  
  ```java
  // ❌ 错误
  private static final String API_KEY = "sk-1234567890abcdef";
  
  // ✅ 正确
  @Value("${dashscope.api.key}")
  private String apiKey;
  ```

- **【强制】** 禁止在日志中打印密码、API Key、Token、Presigned URL 的敏感参数
  ```java
  // ❌ 错误
  log.info("API Key: {}", apiKey);
  log.info("Presigned URL: {}", presignedUrl);
  
  // ✅ 正确
  log.info("API Key configured: {}", apiKey != null && !apiKey.isEmpty());
  log.info("Generated presigned URL for file: {}", fileName);
  ```

---

## 8. 项目特定规范

### 8.1 Spring Boot 规范

- **【强制】** Controller 层只做参数校验和组装，不写业务逻辑
  - 业务逻辑必须放在 Service 层

- **【强制】** Service 层必须无状态，所有状态下沉到 DB/Redis/S3
  - 说明: 支持水平扩展

- **【推荐】** 使用 `@Slf4j` 注解自动注入日志
  ```java
  @Slf4j
  @Service
  public class ProjectService {
      public void doSomething() {
          log.info("Doing something");
      }
  }
  ```

### 8.2 数据库规范

- **【强制】** 禁止在业务代码中执行 DDL
  - 说明: 所有 Schema 变更必须通过 Flyway 迁移文件

- **【强制】** 不得使用外键与级联，一切外键概念必须在应用层解决
  - 说明: 外键影响数据库的插入速度

- **【推荐】** 表达是与否概念的字段，必须使用 `is_xxx` 的方式命名，数据类型是 `BOOLEAN`
  - ✅ 正例: `is_deleted`, `is_enabled`

---

## 9. 工具配置

### 9.1 IDE 配置

#### IntelliJ IDEA

1. **代码格式化**: Settings → Editor → Code Style → Java
   - Tab size: 4
   - Indent: 4
   - Continuation indent: 4

2. **导入顺序**: Settings → Editor → Code Style → Java → Imports
   - 按照 5.2.4 节的顺序配置

3. **阿里巴巴代码规约插件**: 
   - 安装插件: Alibaba Java Coding Guidelines
   - 启用实时检测

#### Eclipse

1. 导入 Google Java Style: 
   - 下载 [eclipse-java-google-style.xml](https://raw.githubusercontent.com/google/styleguide/gh-pages/eclipse-java-google-style.xml)
   - Preferences → Java → Code Style → Formatter → Import

### 9.2 Maven 配置

#### Checkstyle 集成

在 `pom.xml` 中添加（本项目暂未集成）：

```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-checkstyle-plugin</artifactId>
    <version>3.3.0</version>
    <configuration>
        <configLocation>google_checks.xml</configLocation>
    </configuration>
</plugin>
```

#### JaCoCo 覆盖率

本项目已集成 JaCoCo，当前阈值：

```xml
<rule>
    <element>BUNDLE</element>
    <limits>
        <limit>
            <counter>INSTRUCTION</counter>
            <value>COVEREDRATIO</value>
            <minimum>0.80</minimum>
        </limit>
    </limits>
</rule>
```

---

## 10. 参考资源

### 官方文档

- [阿里巴巴Java开发手册（嵩山版）](https://alibaba.github.io/p3c/)
- [Google Java Style Guide](https://google.github.io/styleguide/javaguide.html)
- [阿里巴巴代码规约插件](https://github.com/alibaba/p3c)

### 工具下载

- IntelliJ IDEA: Alibaba Java Coding Guidelines 插件
- Eclipse: Google Java Style XML
- Maven: Checkstyle Plugin

---

## 附录：快速检查清单

开发前检查：
- [ ] 类名、方法名、变量名符合命名规范
- [ ] 导入语句已排序，无通配符导入
- [ ] 缩进使用 4 个空格，无 Tab 字符
- [ ] 单行代码不超过 120 字符

提交代码前检查：
- [ ] 所有公共方法都有 Javadoc 注释
- [ ] 异常处理完整，日志记录充分
- [ ] 无硬编码的密钥、密码
- [ ] 单元测试覆盖率 ≥ 80%
- [ ] 通过 `mvn verify` 质量门禁

代码审查时关注：
- [ ] 是否有潜在的 NPE 风险
- [ ] 日志级别是否合理
- [ ] 是否有不必要的代码重复
- [ ] 性能是否有优化空间
