{
  "_comment": "R→D→T→V 完整映射表 — 由工作流自动维护，validators.py rdtv_closure 读取校验",
  "_lifecycle": "S5任务拆分校验通过后：R/D/T 列填充；S7测试验证完成后：V 列填充；S8完成Jar构建和HTTP验收；S9全链路验证完成后执行闭环校验",
  "feature_id": "{{feature_id}}",
  "last_updated": null,
  "mapping": [
    {
      "_example": "以下是示例，由 validators.py rdt_mapping 通过后自动生成，删除此示例",
      "r": "R01",
      "d": "D01",
      "t": "T01",
      "v": null,
      "v_result": null
    }
  ]
}
