{
  "_comment": "任务拆分（T编号体系）— 由子Agent 生成，validators.py rdt_mapping 读取校验",
  "_usage": "每个 task 的所有字段都必须填写，空字段会被校验器标红阻断",
  "feature_id": "{{feature_id}}",
  "last_updated": null,
  "tasks": [
    {
      "_example": "以下是一个示例 T 任务，实际由子Agent 填写后删除此示例",
      "t_number": "T01",
      "title": "任务标题（业务语义，不要用技术描述）",
      "r_mapping": "R01",
      "d_mapping": "D01",
      "done_definition": "明确的完成标准（代码层面：测试通过、无 lint 错误等）",
      "acceptance": "业务层面的验收口径（接口返回值、数据库状态、通知发送等）",
      "parallel_group": "可选；同组内 scope 必须互斥，仅表达理论并行性，当前 S6 默认串行派遣",
      "write_scope_exclusive": true,
      "scope": [
        "src/main/java/com/example/feature/application/usecase/XxxUseCase.java",
        "src/test/java/com/example/feature/XxxUseCaseTest.java"
      ],
      "estimated_hours": 2,
      "dependencies": [],
      "notes": "可选：特殊注意事项、历史兼容要求、已知风险"
    }
  ]
}
