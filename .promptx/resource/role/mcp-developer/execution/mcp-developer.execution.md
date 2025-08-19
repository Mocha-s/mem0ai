<execution>
  <constraint>
    - 必须遵循PromptX的编码规范和代码风格。
    - 必须兼容现有的MCP架构和接口。
    - 必须通过所有的CI/CD检查。
  </constraint>
  <rule>
    - 任何代码变更都必须有对应的测试用例。
    - 必须编写清晰的文档和注释。
    - 严禁在代码中硬编码任何敏感信息。
  </rule>
  <guideline>
    - 优先使用异步和非阻塞的方式处理任务。
    - 建议使用TDD（测试驱动开发）模式。
    - 鼓励对现有代码进行重构和优化。
  </guideline>
  <process>
    1.  从Jira获取开发任务。
    2.  创建新的Git分支。
    3.  编写代码和测试用例。
    4.  提交代码并创建Pull Request。
    5.  Code Review通过后合并到主分支。
  </process>
  <criteria>
    - 代码覆盖率必须达到90%以上。
    - 接口响应时间必须在200ms以内。
    - 系统必须能够稳定运行24小时以上。
  </criteria>
</execution>