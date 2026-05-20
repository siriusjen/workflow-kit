#!/usr/bin/env python3
"""
validators.py — 自动完整性校验器 v2.0

6个校验器：
  req_coverage     需求完整性（S2结束）
  req_cross_validate 需求交叉验证（S2结束）
  fact_inheritance 技术方案事实继承一致性（S3结束）
  rdt_mapping      映射闭环（S5结束）
  impl_drift       实现偏离（每次实现记录后）
  rdtv_closure     RDTV闭环（S9全链路验证后）

用法：
  python3 validators.py <validator> <FID> [args]
  python3 validators.py all <FID>             # 运行当前阶段适用的校验
"""

import json
import sys
import re
import subprocess
from datetime import datetime
from pathlib import Path


# ── 路径自适应 ────────────────────────────────────────────────────────────────

SCRIPT_FILE   = Path(__file__).resolve()
SCRIPTS_DIR   = SCRIPT_FILE.parent
WORKFLOW_DIR  = SCRIPTS_DIR.parent
DOCS_DIR      = WORKFLOW_DIR.parent
PROJECT_ROOT  = DOCS_DIR.parent
PRIMARY_FEATURES_ROOT = DOCS_DIR / "01-features"
LEGACY_FEATURES_ROOT = DOCS_DIR / "features"
BUGFIX_ROOT = DOCS_DIR / "02-bug-fix"

REQUIRED_DIMENSIONS = ["main_flow", "exception_flow", "boundary", "permission", "acceptance"]
DIMENSION_LABELS = {
    "main_flow": "主流程", "exception_flow": "异常流程",
    "boundary": "边界条件", "permission": "权限控制", "acceptance": "验收口径"
}
PASSING_FACT_STATUSES = {"preserved", "changed_with_approval"}
CODE_EVIDENCE_FACT_TYPES = {
    "data_source",
    "current_logic",
    "dependency_logic",
    "forbidden_legacy_path",
    "api_contract",
    "integration_contract",
    "external_dependency"
}


def resolve_features_root() -> Path:
    if PRIMARY_FEATURES_ROOT.exists():
        return PRIMARY_FEATURES_ROOT
    if LEGACY_FEATURES_ROOT.exists():
        return LEGACY_FEATURES_ROOT
    return PRIMARY_FEATURES_ROOT


FEATURES_ROOT = resolve_features_root()


def now_iso(): return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
def color(t, c): return f"\033[{c}m{t}\033[0m" if sys.stdout.isatty() else t
def green(t): return color(t, "32")
def yellow(t): return color(t, "33")
def red(t): return color(t, "31")
def cyan(t): return color(t, "36")
def bold(t): return color(t, "1")

def find_feature_dir(fid: str) -> Path:
    matches = [d for d in FEATURES_ROOT.iterdir()
               if d.is_dir() and d.name.startswith(fid)]
    if not matches:
        print(red(f"找不到 feature: {fid}")); sys.exit(1)
    return matches[0]


def find_bugfix_dir(bug_id: str) -> Path:
    if not BUGFIX_ROOT.exists():
        print(red(f"找不到 bugfix 根目录: {BUGFIX_ROOT}"))
        sys.exit(1)
    requested_date = None
    requested_id = bug_id
    if "/" in bug_id:
        requested_date, requested_id = bug_id.split("/", 1)
    elif "@" in bug_id:
        requested_id, requested_date = bug_id.split("@", 1)
    matches = []
    for date_dir in sorted([d for d in BUGFIX_ROOT.iterdir() if d.is_dir()], key=lambda p: p.name, reverse=True):
        if requested_date and date_dir.name != requested_date:
            continue
        matches.extend([d for d in date_dir.iterdir() if d.is_dir() and d.name.startswith(requested_id)])
    if not matches:
        print(red(f"找不到 bugfix: {bug_id}"))
        sys.exit(1)
    if len(matches) > 1 and not requested_date:
        print(red(f"bug 编号跨日期歧义: {bug_id}"))
        print(yellow("请使用 YYYY-MM-DD/BFxx 或 BFxx@YYYY-MM-DD 指定日期"))
        for match in matches:
            print(f"  - {match.parent.name}/{match.name}")
        sys.exit(1)
    return matches[0]

def load_json(p: Path) -> dict:
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except: return {}

def save_json(p: Path, d: dict):
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def save_bug_state(bdir: Path, state: dict):
    state["last_updated"] = now_iso()
    save_json(bdir / "state.json", state)


def normalize_mapping_values(value):
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if value:
        return [str(value)]
    return []


def non_empty_list(value):
    return isinstance(value, list) and any(str(v).strip() for v in value)


def extract_requirement_numbers(fdir: Path):
    state = load_json(fdir / "state.json")
    baseline = state.get("baseline", {}).get("requirement")
    requirement_path = fdir / baseline if baseline else None
    if not requirement_path or not requirement_path.exists():
        files = sorted((fdir / "01-需求确认").glob("需求说明书-v*.md"))
        requirement_path = files[-1] if files else None
    if not requirement_path or not requirement_path.exists():
        return set()
    return set(re.findall(r"\bR\d+\b", requirement_path.read_text(encoding="utf-8")))


def print_result(name: str, passed: bool, details: list = None, block: str = None):
    icon = green("✅") if passed else red("❌")
    print(f"\n{icon} [{name}] {'通过' if passed else '未通过'}")
    if details:
        for d in details:
            p = green("  ✓") if d.get("ok") else red("  ✗")
            print(f"{p} {d['msg']}")
    if not passed and block:
        print(red(f"\n  阻断: {block}"))
    print()


def _trigger_auto(fid: str, key: str):
    """通过 stage_gates auto 触发状态转移"""
    result = subprocess.run(
        ["python3", str(SCRIPTS_DIR / "stage_gates.py"), "auto", fid, key],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(cyan(f"  自动转移: {key}"))
    else:
        print(yellow(f"  手动执行: python3 docs/.workflow/scripts/stage_gates.py auto {fid} {key}"))


# ── 校验器 1: 需求完整性 ─────────────────────────────────────────────────────

def v_req_coverage(fdir: Path) -> bool:
    print(bold("\n── 校验器 1: 需求完整性 ──"))

    f = fdir / "01-需求确认" / "覆盖检查.json"
    data = load_json(f)
    if not data:
        print(red("  覆盖检查.json 不存在或为空"))
        return False

    if data.get("passed") in {True, False}:
        dims = data.get("dimensions", {})
        details = []
        for k in REQUIRED_DIMENSIONS:
            dim = dims.get(k, {})
            covered = dim.get("covered")
            if covered is True:
                details.append({"ok": True,
                                "msg": f"{DIMENSION_LABELS[k]}: ✓ {dim.get('r_numbers', [])}"})
            else:
                details.append({"ok": False,
                                "msg": f"{DIMENSION_LABELS[k]}: 未覆盖 — {dim.get('missing','原因未说明')}"})

        for u in data.get("uncovered_inputs", []):
            details.append({"ok": False,
                            "msg": f"未映射输入: '{u.get('original','')}' [{u.get('status','')}]" })

        passed = data.get("passed") is True and all(d["ok"] for d in details)
        if data.get("passed") is True and not passed:
            print(yellow("  报告声明 passed=true，但覆盖维度或未映射输入仍未闭合；按严格规则判定为未通过"))
        print_result("req_coverage", passed, details, data.get("block_reason"))
        if passed:
            _trigger_auto(fdir.name.split("-")[0], "req-coverage-passed")
        return passed

    print(yellow("  覆盖检查.json 的 passed 字段为 null"))
    print(yellow("  请先让 OpenSpec 完成需求结构化并填写"))
    return False


# ── 校验器 2: 需求交叉验证 ───────────────────────────────────────────────────

def v_req_cross_validate(fdir: Path) -> bool:
    print(bold("\n── 校验器 2: 需求交叉验证 ──"))

    # 查找差异报告
    cv_dir = fdir / "01-需求确认"
    reports = sorted(cv_dir.glob("差异报告*.json"))
    if not reports:
        print(red("  差异报告.json 不存在"))
        print(yellow("  请先让\"需求交叉验证\"子Agent 生成报告"))
        return False

    data = load_json(reports[-1])
    discrepancies = data.get("discrepancies", [])
    severities = [str(d.get("severity", "")).lower() for d in discrepancies]
    low_only_accepted = (
        bool(discrepancies)
        and all(sev == "low" for sev in severities)
        and data.get("main_agent_accepted_low_severity") is True
    )
    passed = len(discrepancies) == 0 or low_only_accepted

    if data.get("passed") is True and not passed:
        print(yellow(
            "  报告声明 passed=true，但存在未获主Agent确认的差异；按严格规则判定为未通过"
        ))

    discrepancy_ok = low_only_accepted
    details = [{"ok": discrepancy_ok, "msg": f"差异项: {d}"} for d in discrepancies[:10]]
    if passed:
        msg = (
            "仅剩低优先级差异，且主Agent已确认可接受"
            if low_only_accepted
            else "需求输入 vs 需求确认 完全对齐"
        )
        details.append({"ok": True, "msg": msg})

    anchor_missing = False
    if passed:
        anchors = sorted(cv_dir.glob("需求事实锚点*.json"))
        if not anchors:
            passed = False
            anchor_missing = True
            details.append({
                "ok": False,
                "msg": "需求事实锚点: 缺少 01-需求确认/需求事实锚点.json"
            })

    block_reason = None
    if not passed:
        block_reason = "缺少需求事实锚点" if anchor_missing else f"发现 {len(discrepancies)} 处差异"

    print_result("req_cross_validate", passed, details, block_reason)
    if anchor_missing:
        print(yellow("  请确认需求交叉验证子Agent已按要求产出此文件"))

    if passed:
        _trigger_auto(fdir.name.split("-")[0], "req-cross-validated")
    return passed


def v_fact_inheritance(fdir: Path) -> bool:
    print(bold("\n── 校验器 3: 技术方案事实继承一致性 ──"))

    anchors = sorted((fdir / "01-需求确认").glob("需求事实锚点*.json"))
    if not anchors:
        print(red("  缺少需求事实锚点: 01-需求确认/需求事实锚点.json"))
        print(yellow("  请先从需求输入/确认中抽取不可漂移事实。"))
        return False

    influences = sorted((fdir / "02-技术方案").glob("代码影响点与依赖逻辑清单*.md"))
    if not influences:
        print(red("  缺少代码影响点与依赖逻辑清单: 02-技术方案/代码影响点与依赖逻辑清单.md"))
        print(yellow("  请先梳理当前代码影响点与依赖逻辑。"))
        return False

    checks = sorted((fdir / "02-技术方案").glob("技术方案一致性检查*.json"))
    if not checks:
        print(red("  缺少技术方案一致性检查: 02-技术方案/技术方案一致性检查.json"))
        return False

    anchor_data = load_json(anchors[-1])
    check_data = load_json(checks[-1])

    facts = check_data.get("facts") or check_data.get("checks") or []
    if not facts:
        print(red("  一致性检查中未找到 facts/checks 列表"))
        return False

    details = []
    passed = True
    for fact in facts:
        fact_id = str(fact.get("fact_id") or fact.get("id") or "?")
        status = str(fact.get("status", "")).strip().lower()
        fact_type = str(fact.get("fact_type", fact.get("type", ""))).strip().lower()
        tech_ref = str(fact.get("tech_plan_reference", fact.get("tech_ref", ""))).strip()
        summary = str(fact.get("summary", fact.get("description", fact_id))).strip()
        approval_ref = str(fact.get("approval_reference", fact.get("approval_ref", ""))).strip()
        code_evidence = fact.get("code_evidence", [])
        requires_code = bool(fact.get("requires_code_evidence")) or fact_type in CODE_EVIDENCE_FACT_TYPES

        issue = []
        if not summary:
            issue.append("缺少摘要")
        if not tech_ref:
            issue.append("缺少技术方案引用")
        if status not in PASSING_FACT_STATUSES:
            issue.append(f"状态={status or '空'}")
        if status == "changed_with_approval" and not approval_ref:
            issue.append("变更缺少审批引用")
        if requires_code and not non_empty_list(code_evidence):
            issue.append("缺少代码证据")

        if issue:
            passed = False
            details.append({"ok": False, "msg": f"{fact_id}: {summary} — {', '.join(issue)}"})
        else:
            details.append({"ok": True, "msg": f"{fact_id}: {summary} ✓"})

    if anchor_data.get("facts") and len(anchor_data.get("facts", [])) > len(facts):
        passed = False
        details.append({
            "ok": False,
            "msg": "技术方案一致性检查中的 facts 数量少于需求事实锚点数量"
        })

    print_result(
        "fact_inheritance",
        passed,
        details,
        "需求事实未被技术方案完整继承" if not passed else None
    )

    if passed:
        _trigger_auto(fdir.name.split("-")[0], "fact-inheritance-passed")
    return passed


# ── 校验器 4: 映射闭环 (R→D→T) ───────────────────────────────────────────────

def v_rdt_mapping(fdir: Path) -> bool:
    print(bold("\n── 校验器 3: 映射闭环 R→D→T ──"))

    f = fdir / "03-落地计划" / "任务清单.json"
    data = load_json(f)
    tasks = data.get("tasks", [])
    if not tasks:
        print(red("  任务清单.json 为空"))
        return False

    details = []; passed = True
    mapped_requirements = set()
    for t in tasks:
        tid = t.get("t_number", t.get("id", "?"))
        issues = []
        if not t.get("r_mapping"):   issues.append("无R映射")
        if not t.get("d_mapping"):   issues.append("无D映射")
        if not t.get("done_definition"): issues.append("无完成定义")
        if not t.get("acceptance"):  issues.append("无验收方式")

        if issues:
            passed = False
            details.append({"ok": False, "msg": f"{tid}: {', '.join(issues)}"})
        else:
            mapped_requirements.update(normalize_mapping_values(t.get("r_mapping")))
            details.append({"ok": True,
                            "msg": f"{tid}: R={t['r_mapping']} D={t['d_mapping']} ✓"})

    requirement_numbers = extract_requirement_numbers(fdir)
    missing_requirements = sorted(requirement_numbers - mapped_requirements)
    for r_number in missing_requirements:
        passed = False
        details.append({"ok": False, "msg": f"{r_number}: 没有被任何 T 覆盖"})

    block = f"{sum(1 for d in details if not d['ok'])} 任务有问题" if not passed else None
    print_result("rdt_mapping", passed, details, block)

    if passed:
        rdtv = fdir / "03-落地计划" / "RDTV映射表.json"
        rdtv_data = load_json(rdtv)
        rdtv_data["last_updated"] = now_iso()
        rows = []
        for t in tasks:
            r_values = normalize_mapping_values(t.get("r_mapping"))
            d_values = normalize_mapping_values(t.get("d_mapping"))
            t_number = t.get("t_number", t.get("id", ""))
            for r_value in r_values:
                rows.append({
                    "r": r_value,
                    "d": d_values,
                    "t": t_number,
                    "v": None,
                    "v_result": None
                })
        rdtv_data["mapping"] = rows
        save_json(rdtv, rdtv_data)
        print(cyan(f"  RDTV映射表 已更新（V列待填）"))
        _trigger_auto(fdir.name.split("-")[0], "rdt-mapping-passed")

    return passed


# ── 校验器 4: 实现偏离 ───────────────────────────────────────────────────────

def v_impl_drift(fdir: Path, t_number: str) -> bool:
    print(bold(f"\n── 校验器 4: 实现偏离检测 ({t_number}) ──"))

    tasks_f = fdir / "03-落地计划" / "任务清单.json"
    tasks = load_json(tasks_f).get("tasks", [])
    target = next((t for t in tasks
                   if t.get("t_number") == t_number or t.get("id") == t_number), None)
    if not target:
        print(yellow(f"  任务清单中找不到 {t_number}"))
        return True

    scope = target.get("scope", [])
    if not scope:
        print(yellow(f"  {t_number} 未定义 scope，跳过"))
        return True

    impl_dir = fdir / "04-实现记录"
    impl_files = sorted(impl_dir.glob(f"实现记录-*-{t_number}.md"), reverse=True)
    if not impl_files:
        impl_files = [
            path for path in sorted(impl_dir.glob("实现记录-*.md"), reverse=True)
            if t_number in path.read_text(encoding="utf-8")
        ]
    if not impl_files:
        print(red(f"  找不到 {t_number} 对应的实现记录"))
        return False

    content = impl_files[0].read_text(encoding="utf-8")
    details = []
    out_of_scope = []

    for s in scope:
        if s.lower() in content.lower():
            details.append({"ok": True, "msg": f"范围内: {s}"})
        else:
            details.append({"ok": False, "msg": f"范围内但未提及: {s}"})

    mentioned = re.findall(
        r'[A-Za-z][A-Za-z0-9_/]+\.(?:py|ts|tsx|js|jsx|java|go|kt|swift|rs)',
        content
    )
    all_scopes = []
    for task in tasks:
        all_scopes.extend(task.get("scope", []))
    scope_l = [s.lower() for s in all_scopes]
    for m in set(mentioned):
        if not any(s in m.lower() or m.lower() in s for s in scope_l):
            out_of_scope.append(m)

    for f in out_of_scope[:5]:
        details.append({"ok": False, "msg": f"疑似超出范围: {f}"})

    has_issues = any(not d["ok"] for d in details)
    if has_issues:
        print_result("impl_drift", False, details,
                      f"{t_number} 存在偏离，已记录")

        # 写入 exception_log
        state_f = fdir / "state.json"
        s = json.loads(state_f.read_text(encoding="utf-8"))
        s.setdefault("exception_log", []).append({
            "type": "impl_drift", "t_number": t_number,
            "detail": f"超范围: {out_of_scope[:3]}",
            "recorded_at": now_iso(), "risk_level": "medium"
        })
        save_json(state_f, s)
        return False
    else:
        print_result("impl_drift", True, details)
        return True


# ── 校验器 5: RDTV 闭环 ──────────────────────────────────────────────────────

def v_rdtv_closure(fdir: Path) -> bool:
    print(bold("\n── 校验器 5: RDTV 闭环 ──"))

    state = load_json(fdir / "state.json")
    allowed_stages = {"交叉验证", "验收发布", "done"}
    if state.get("current_stage") not in allowed_stages:
        print(red(
            f"  当前阶段不允许执行 RDTV 闭环: {state.get('current_stage')} "
            f"(允许: {', '.join(sorted(allowed_stages))})"
        ))
        return False
    if not state.get("checklist", {}).get("artifact_package_done"):
        print(red("  Jar 构建尚未完成，禁止执行 RDTV 闭环"))
        return False
    if not state.get("checklist", {}).get("http_acceptance_done"):
        print(red("  HTTP 验收尚未完成，禁止执行 RDTV 闭环"))
        return False
    if not state.get("checklist", {}).get("cross_validate_done"):
        print(red("  全链路验证尚未完成，禁止执行 RDTV 闭环"))
        print(yellow("  请先完成全链路验证并执行 stage_gates.py auto <FID> cross-validate-done"))
        return False

    f = fdir / "03-落地计划" / "RDTV映射表.json"
    data = load_json(f)
    mapping = data.get("mapping", [])
    if not mapping:
        print(red("  RDTV映射表为空"))
        return False

    report_f = fdir / "05-测试验证" / "RDTV报告.json"
    report = load_json(report_f) or {}
    report_rows = {}
    for row in report.get("rdtv_table", []):
        if not isinstance(row, dict):
            continue
        key = (str(row.get("r", "")), str(row.get("t", "")))
        report_rows[key] = row

    details = []; passed = True
    rows = []
    for m in mapping:
        r, d, t = m.get("r","?"), m.get("d","?"), m.get("t","?")
        v, vr = m.get("v"), m.get("v_result")
        report_row = report_rows.get((str(r), str(t)))
        if (not v or not vr) and report_row:
            v = v or report_row.get("v")
            vr = vr or report_row.get("result")
        issues = []
        if not v: issues.append("缺V编号")
        if not vr: issues.append("V结果空")
        elif str(vr).lower() not in {"pass", "passed", "true", "通过"}:
            issues.append(f"V结果未通过({vr})")
        if issues:
            passed = False
            details.append({"ok": False, "msg": f"R={r} D={d} T={t}: {', '.join(issues)}"})
        else:
            details.append({"ok": True,
                            "msg": f"R={r}→D={d}→T={t}→V={v} [{vr}]"})
        rows.append({"r":r, "d":d, "t":t, "v": v or "—", "result": vr or "—"})
        m["v"] = v
        m["v_result"] = vr

    mapped_requirements = set()
    for row in mapping:
        mapped_requirements.update(normalize_mapping_values(row.get("r")))
    missing_requirements = sorted(extract_requirement_numbers(fdir) - mapped_requirements)
    for r_number in missing_requirements:
        passed = False
        details.append({"ok": False, "msg": f"{r_number}: 没有 RDTV 闭环记录"})

    data["last_updated"] = now_iso()
    save_json(f, data)

    report = {
        "passed": passed, "timestamp": now_iso(),
        "rdtv_table": rows,
        "total": len(mapping),
        "passed_count": sum(1 for d in details if d["ok"]),
        "failed_count": sum(1 for d in details if not d["ok"])
    }
    rf = fdir / "05-测试验证" / "RDTV报告.json"
    rf.parent.mkdir(exist_ok=True)
    save_json(rf, report)

    block = f"{report['failed_count']} 条链路未闭合" if not passed else None
    print_result("rdtv_closure", passed, details, block)

    if passed:
        print(cyan(f"  追溯表: 05-测试验证/RDTV报告.json"))
        print(cyan(f"  {report['total']} 条链路全部闭合"))
        if state.get("current_stage") == "交叉验证":
            _trigger_auto(fdir.name.split("-")[0], "rdtv-mapping-complete")

    return passed


# ── Bug 校验器: 根因→方案→任务闭环 ───────────────────────────────────────────

def _check_array_of_objects(data: dict, array_name: str, required_fields: list) -> list:
    """校验 JSON 数组的元素是否为对象且含必填字段。
    返回错误信息列表，空列表表示无错误。
    """
    items = data.get(array_name, [])
    errors = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{array_name}[{i}] 不是 JSON 对象，当前类型: {type(item).__name__}")
            continue
        for f in required_fields:
            if not item.get(f):
                errors.append(f"{array_name}[{i}] 缺少必填字段: {f}")
    return errors


def v_bug_chain(bdir: Path) -> bool:
    print(bold("\n── Bug 校验器: 根因→方案→任务闭环 ──"))

    required_docs = [
        "00-总览.md",
        "01-问题描述.md",
        "02-环境与影响范围.md",
        "03-根因分析.md",
        "04-解决方案.md",
        "05-任务拆解.md",
        "06-执行记录.md",
        "07-测试验证.md",
        "08-验收发布.md",
        "09-复盘与沉淀.md",
        "10-AI协作记录.md",
        "state.json",
    ]
    details = []
    passed = True
    for rel in required_docs:
        path = bdir / rel
        ok = path.exists() and path.stat().st_size > 0
        details.append({"ok": ok, "msg": f"{rel}: {'存在' if ok else '缺失或为空'}"})
        if not ok:
            passed = False

    anchor_path = bdir / "事实锚点.json"
    anchors = load_json(anchor_path)
    if not anchors:
        details.append({"ok": False, "msg": "事实锚点.json: 缺失或 JSON 无效"})
        passed = False
    else:
        schema_errors = []
        schema_errors += _check_array_of_objects(anchors, "rootcause_anchors", ["id", "summary", "source"])
        schema_errors += _check_array_of_objects(anchors, "solution_mappings", ["rootcause_id", "solution_ref", "status"])
        schema_errors += _check_array_of_objects(anchors, "task_mappings", ["solution_ref", "task_id", "status"])
        if schema_errors:
            passed = False
            for err in schema_errors:
                details.append({"ok": False, "msg": err})

        # status 值域校验
        for item in anchors.get("solution_mappings", []):
            if isinstance(item, dict):
                status = item.get("status", "")
                if status not in {"covered", "partial", "uncovered"}:
                    passed = False
                    details.append({"ok": False, "msg": f"solution_mappings 中 status 值 '{status}' 不在允许范围 (covered/partial/uncovered)"})
        for item in anchors.get("task_mappings", []):
            if isinstance(item, dict):
                status = item.get("status", "")
                if status not in {"covered", "partial", "uncovered"}:
                    passed = False
                    details.append({"ok": False, "msg": f"task_mappings 中 status 值 '{status}' 不在允许范围 (covered/partial/uncovered)"})

        rootcause_ids = {
            str(item.get("id"))
            for item in anchors.get("rootcause_anchors", [])
            if isinstance(item, dict) and item.get("id")
        }
        solution_ids = {
            str(item.get("rootcause_id"))
            for item in anchors.get("solution_mappings", [])
            if isinstance(item, dict) and item.get("rootcause_id") and item.get("status") == "covered"
        }
        missing_solution = sorted(rootcause_ids - solution_ids)
        if missing_solution:
            passed = False
            details.append({"ok": False, "msg": f"根因未被方案覆盖: {missing_solution}"})
        else:
            details.append({"ok": True, "msg": "所有根因均被方案覆盖"})

        # HTML 物理注释锚点扫描校验
        rc_file = bdir / "03-根因分析.md"
        if rc_file.exists():
            rc_content = rc_file.read_text(encoding="utf-8")
            physical_anchors = set(re.findall(r"<!--\s*anchor\s*:\s*(RC\d+)\s*-->", rc_content))
            declared_anchors = {
                str(item.get("id"))
                for item in anchors.get("rootcause_anchors", [])
                if isinstance(item, dict) and item.get("id")
            }
            missing_physical = sorted(declared_anchors - physical_anchors)
            if missing_physical:
                passed = False
                details.append({"ok": False, "msg": f"事实锚点.json 中声明的根因在 03-根因分析.md 中缺少对应的物理 HTML 注释锚点: {missing_physical}"})
            else:
                details.append({"ok": True, "msg": "所有声明的根因均在 03-根因分析.md 中有对应的物理 HTML 注释锚点"})
            
            undeclared_physical = sorted(physical_anchors - declared_anchors)
            if undeclared_physical:
                passed = False
                details.append({"ok": False, "msg": f"03-根因分析.md 中存在未在 事实锚点.json 中声明的物理 HTML 注释锚点: {undeclared_physical}"})

        solution_refs = {
            str(item.get("solution_ref"))
            for item in anchors.get("solution_mappings", [])
            if isinstance(item, dict) and item.get("solution_ref")
        }
        task_refs = {
            str(item.get("solution_ref"))
            for item in anchors.get("task_mappings", [])
            if isinstance(item, dict) and item.get("solution_ref") and item.get("status") == "covered"
        }
        missing_tasks = sorted(solution_refs - task_refs)
        if missing_tasks:
            passed = False
            details.append({"ok": False, "msg": f"方案未被任务覆盖: {missing_tasks}"})
        else:
            details.append({"ok": True, "msg": "所有方案均被任务覆盖"})

    state = load_json(bdir / "state.json")
    current_packet = state.get("context_manifest", {}).get("current_packet")
    if not state.get("checklist", {}).get("context_packet_done"):
        passed = False
        details.append({"ok": False, "msg": "state.json: context_packet_done 未完成"})
    elif not current_packet:
        passed = False
        details.append({"ok": False, "msg": "state.json: current_packet 为空"})
    elif not (bdir / current_packet).exists():
        passed = False
        details.append({"ok": False, "msg": f"上下文包不存在: {current_packet}"})
    else:
        details.append({"ok": True, "msg": f"上下文包已就绪: {current_packet}"})

    print_result("bug_chain", passed, details, "Bug 根因、方案或任务链路未闭合" if not passed else None)

    if passed:
        state.setdefault("checklist", {})
        state["checklist"]["fact_chain_done"] = True
        save_bug_state(bdir, state)

    return passed


# ── 入口 ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(0)

    v = sys.argv[1]
    fid = sys.argv[2]
    if fid.upper().startswith("BF"):
        bdir = find_bugfix_dir(fid)
        if v == "bug_chain":
            sys.exit(0 if v_bug_chain(bdir) else 1)
        elif v == "all":
            sys.exit(0 if v_bug_chain(bdir) else 1)
        else:
            print(red(f"Bug 流程不支持校验器: {v}"))
            print(yellow("可用: bug_chain, all"))
            sys.exit(1)

    fdir = find_feature_dir(fid)

    if v == "req_coverage":
        sys.exit(0 if v_req_coverage(fdir) else 1)
    elif v == "req_cross_validate":
        sys.exit(0 if v_req_cross_validate(fdir) else 1)
    elif v == "fact_inheritance":
        sys.exit(0 if v_fact_inheritance(fdir) else 1)
    elif v == "rdt_mapping":
        sys.exit(0 if v_rdt_mapping(fdir) else 1)
    elif v == "impl_drift":
        if len(sys.argv) < 4:
            print(red("用法: impl_drift <FID> <T_NUMBER>")); sys.exit(1)
        sys.exit(0 if v_impl_drift(fdir, sys.argv[3]) else 1)
    elif v == "rdtv_closure":
        sys.exit(0 if v_rdtv_closure(fdir) else 1)
    elif v == "all":
        s = load_json(fdir / "state.json")
        stage = s.get("current_stage", "")
        cl = s.get("checklist", {})
        ran = 0
        if not cl.get("req_coverage_check") and stage == "需求确认":
            v_req_coverage(fdir); ran += 1
        if not cl.get("req_cross_validate") and stage == "需求确认":
            v_req_cross_validate(fdir); ran += 1
        if not cl.get("fact_inheritance_check") and stage == "技术方案":
            v_fact_inheritance(fdir); ran += 1
        if not cl.get("rdt_mapping_complete") and stage in ("任务拆分","实现"):
            v_rdt_mapping(fdir); ran += 1
        if stage == "交叉验证":
            v_rdtv_closure(fdir); ran += 1
        if ran == 0:
            print(yellow(f"\n阶段 '{stage}' 无适用校验"))
    else:
        print(red(f"未知校验器: {v}"))
        sys.exit(1)


if __name__ == "__main__":
    main()
