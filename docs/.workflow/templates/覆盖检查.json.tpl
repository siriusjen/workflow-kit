{
  "_comment": "需求完整性校验报告 — 由 OpenSpec 填写，validators.py req_coverage 读取判定",
  "_usage": "OpenSpec 完成需求结构化后，按此格式填写 passed 和 dimensions 字段",
  "feature_id": "{{feature_id}}",
  "passed": null,
  "timestamp": null,
  "dimensions": {
    "main_flow": {
      "_desc": "主流程：核心业务路径是否完整覆盖",
      "covered": null,
      "r_numbers": [],
      "missing": null
    },
    "exception_flow": {
      "_desc": "异常流程：错误路径、超时、回滚、降级是否覆盖",
      "covered": null,
      "r_numbers": [],
      "missing": null
    },
    "boundary": {
      "_desc": "边界条件：空值、最大值、临界值、并发边界是否覆盖",
      "covered": null,
      "r_numbers": [],
      "missing": null
    },
    "permission": {
      "_desc": "权限控制：角色权限、数据权限、操作权限是否覆盖",
      "covered": null,
      "r_numbers": [],
      "missing": null
    },
    "acceptance": {
      "_desc": "验收口径：每条需求的验收方式是否明确",
      "covered": null,
      "r_numbers": [],
      "missing": null
    }
  },
  "uncovered_inputs": [],
  "block_reason": null
}
