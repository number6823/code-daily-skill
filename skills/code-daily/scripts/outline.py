"""
outline.py — code-daily 규칙으로 작성된 Python 코드의 뼈대를 추출한다

요약: 모듈 docstring·섹션 구분선·함수 시그니처(타입 힌트)·docstring 첫 줄을 읽어
      블로그 글의 "구조" 파트에 바로 쓸 수 있는 마크다운(또는 JSON)으로 출력한다.
      타입 힌트가 빠진 곳도 함께 알려주므로 code 모드의 점검 도구로도 쓴다.
사용: python outline.py <파일 또는 폴더> [...] [--json] [--check]
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Final, List, Optional, Pattern, Set

# ===== 설정 =====

# 제목에 = 이외의 글자가 있어야 섹션. 없으면 "# =====" 만 있는 배너 줄이다
SECTION_RE: Final[Pattern[str]] = re.compile(r"^\s*#\s*={3,}\s*([^=\s][^=]*?)\s*={3,}\s*$")
BANNER_RE: Final[Pattern[str]] = re.compile(r"^\s*#\s*[=\-─#*]{3,}\s*$")
TODO_RE: Final[Pattern[str]] = re.compile(r"#\s*(TODO|FIXME)(\([^)]*\))?:?\s*(.*)")
SKIP_DIRS: Final[Set[str]] = {".git", ".venv", "venv", "__pycache__", "node_modules", ".ipynb_checkpoints"}

# ===== 추출 =====


def _seg(source: str, node: Optional[ast.AST]) -> Optional[str]:
    """노드의 원본 소스 문자열. 3.8 에는 ast.unparse 가 없어서 원문을 잘라 쓴다."""
    if node is None:
        return None
    return ast.get_source_segment(source, node)


def _func_info(source: str, fn: ast.AST) -> Dict[str, Any]:
    """함수 하나의 시그니처·docstring·타입 누락 정보."""
    assert isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
    a = fn.args
    params: List[Dict[str, Optional[str]]] = []
    positional = a.posonlyargs + a.args
    defaults: List[Optional[ast.expr]] = [None] * (len(positional) - len(a.defaults)) + list(a.defaults)
    for arg, default in zip(positional, defaults):
        params.append({"name": arg.arg, "type": _seg(source, arg.annotation), "default": _seg(source, default)})
    if a.vararg:
        params.append({"name": "*" + a.vararg.arg, "type": _seg(source, a.vararg.annotation), "default": None})
    for arg, default in zip(a.kwonlyargs, a.kw_defaults):
        params.append({"name": arg.arg, "type": _seg(source, arg.annotation), "default": _seg(source, default)})
    if a.kwarg:
        params.append({"name": "**" + a.kwarg.arg, "type": _seg(source, a.kwarg.annotation), "default": None})

    # self/cls 는 관례상 타입을 적지 않으므로 누락으로 치지 않는다
    missing = [p["name"] for p in params if p["type"] is None and p["name"] not in ("self", "cls")]
    returns = _seg(source, fn.returns)
    if returns is None and fn.name != "__init__":
        missing.append("return")

    doc = ast.get_docstring(fn)
    return {
        "name": fn.name,
        "line": fn.lineno,
        "async": isinstance(fn, ast.AsyncFunctionDef),
        "private": fn.name.startswith("_") and not fn.name.startswith("__"),
        "params": params,
        "returns": returns,
        "summary": doc.strip().splitlines()[0] if doc else None,
        "missing_types": missing,
    }


def find_sections(lines: List[str]) -> List[Dict[str, Any]]:
    """`# ===== 이름 =====` 한 줄형과, 구분선 사이에 `# 이름` 이 낀 3줄 배너형을 모두 섹션으로 읽는다."""
    found: List[Dict[str, Any]] = []
    i = 0
    while i < len(lines):
        m = SECTION_RE.match(lines[i])
        if m:
            found.append({"title": m.group(1), "line": i + 1})
        elif (
            BANNER_RE.match(lines[i])
            and i + 2 < len(lines)
            and BANNER_RE.match(lines[i + 2])
            and re.match(r"^\s*#\s*\S", lines[i + 1])
        ):
            found.append({"title": lines[i + 1].strip().lstrip("#").strip(), "line": i + 2})
            i += 2
        i += 1
    return found


def analyze_file(path: Path) -> Dict[str, Any]:
    """파일 하나를 분석해 dict 로 반환. 문법 오류면 error 키만 채운다."""
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"path": str(path), "error": f"SyntaxError: {e}"}

    doc = ast.get_docstring(tree)
    lines = source.splitlines()
    sections = find_sections(lines)
    todos = [{"line": i, "text": l.strip()} for i, l in enumerate(lines, 1) if TODO_RE.search(l)]

    functions: List[Dict[str, Any]] = []
    classes: List[Dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(_func_info(source, node))
        elif isinstance(node, ast.ClassDef):
            cdoc = ast.get_docstring(node)
            fields = [
                {"name": _seg(source, s.target), "type": _seg(source, s.annotation)}
                for s in node.body
                if isinstance(s, ast.AnnAssign)
            ]
            methods = [_func_info(source, s) for s in node.body if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))]
            classes.append({
                "name": node.name,
                "line": node.lineno,
                "bases": [_seg(source, b) for b in node.bases],
                "summary": cdoc.strip().splitlines()[0] if cdoc else None,
                "fields": fields,
                "methods": methods,
            })

    constants = [
        {"name": _seg(source, n.target), "type": _seg(source, n.annotation), "line": n.lineno}
        for n in tree.body
        if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id.isupper()
    ]
    constants += [
        {"name": t.id, "type": None, "line": n.lineno}
        for n in tree.body
        if isinstance(n, ast.Assign)
        for t in n.targets
        if isinstance(t, ast.Name) and t.id.isupper()
    ]

    return {
        "path": str(path),
        "title": doc.strip().splitlines()[0] if doc else None,
        "docstring": doc,
        "has_future_annotations": "from __future__ import annotations" in source,
        "has_main_guard": "if __name__ == \"__main__\"" in source or "if __name__ == '__main__'" in source,
        "sections": sections,
        "constants": sorted(constants, key=lambda c: c["line"]),
        "classes": classes,
        "functions": functions,
        "todos": todos,
    }


def collect(paths: List[str]) -> List[Path]:
    """인자로 받은 파일·폴더에서 .py 파일 목록을 모은다."""
    files: List[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            files += sorted(f for f in p.rglob("*.py") if not SKIP_DIRS & set(f.parts))
        elif p.suffix == ".py":
            files.append(p)
        else:
            print(f"[skip] {p} (파이썬 파일/폴더 아님)", file=sys.stderr)
    return files


# ===== 출력 =====


def _sig(f: Dict[str, Any]) -> str:
    """함수 정보 dict 를 `name(a: int = 1) -> str` 형태 문자열로."""
    parts = []
    for p in f["params"]:
        s = p["name"] + (f": {p['type']}" if p["type"] else "")
        if p["default"] is not None:
            s += f" = {p['default']}"
        parts.append(s)
    ret = f" -> {f['returns']}" if f["returns"] else ""
    return f"{'async ' if f['async'] else ''}{f['name']}({', '.join(parts)}){ret}"


def _cell(text: Optional[str]) -> str:
    """마크다운 표 셀 안에서 깨지는 | 를 이스케이프."""
    return (text or "—").replace("|", "\\|")


def to_markdown(results: List[Dict[str, Any]]) -> str:
    """post 모드용: 파일별 제목·섹션·상수·클래스·함수표를 마크다운으로."""
    out: List[str] = []
    for r in results:
        out.append(f"## {r['path']}")
        if "error" in r:
            out += [f"⚠️ {r['error']}", ""]
            continue
        out.append(f"**제목(모듈 docstring 첫 줄)**: {r['title'] or '없음'}")
        if r["sections"]:
            out.append("**섹션**: " + " → ".join(s["title"] for s in r["sections"]))
        if r["constants"]:
            out.append("**상수**: " + ", ".join(f"`{c['name']}`" + (f": `{c['type']}`" if c["type"] else "") for c in r["constants"]))
        out.append("")
        for c in r["classes"]:
            out.append(f"### class `{c['name']}`" + (f"({', '.join(c['bases'])})" if c["bases"] else "") + f" — L{c['line']}")
            out.append(c["summary"] or "(docstring 없음)")
            if c["fields"]:
                out += ["", "| 필드 | 타입 |", "|---|---|"] + [f"| `{fl['name']}` | `{_cell(fl['type'])}` |" for fl in c["fields"]]
            if c["methods"]:
                out += ["", "| 메서드 | 시그니처 | 설명 |", "|---|---|---|"]
                out += [f"| `{m['name']}` | `{_cell(_sig(m))}` | {_cell(m['summary'])} |" for m in c["methods"]]
            out.append("")
        if r["functions"]:
            out += ["| 함수 | 입력 | 출력 | 설명 |", "|---|---|---|---|"]
            for f in r["functions"]:
                ins = ", ".join(f"{p['name']}: {p['type'] or '?'}" for p in f["params"]) or "—"
                out.append(f"| `{f['name']}` | `{_cell(ins)}` | `{_cell(f['returns'] or '?')}` | {_cell(f['summary'])} |")
            out.append("")
        if r["todos"]:
            out.append("**TODO**: " + "; ".join(f"L{t['line']} {t['text']}" for t in r["todos"]))
            out.append("")
    return "\n".join(out)


def to_check(results: List[Dict[str, Any]]) -> str:
    """code 모드 점검용: 규칙 위반 목록만 출력."""
    out: List[str] = []
    for r in results:
        if "error" in r:
            out.append(f"{r['path']}: {r['error']}")
            continue
        issues: List[str] = []
        if not r["title"]:
            issues.append("모듈 docstring(파일 헤더) 없음")
        if not r["sections"] and len(r["functions"]) + len(r["classes"]) >= 3:
            issues.append("섹션 구분선(# ===== 이름 =====) 없음")
        fns = r["functions"] + [m for c in r["classes"] for m in c["methods"]]
        for f in fns:
            if f["missing_types"]:
                issues.append(f"L{f['line']} {f['name']}: 타입 누락 → {', '.join(f['missing_types'])}")
            if not f["summary"] and not f["private"] and not f["name"].startswith("__"):
                issues.append(f"L{f['line']} {f['name']}: docstring 없음")
        for c in r["constants"]:
            if c["type"] is None:
                issues.append(f"L{c['line']} 상수 {c['name']}: 타입 누락")
        status = "OK" if not issues else f"{len(issues)}건"
        out.append(f"[{status}] {r['path']}")
        out += [f"  - {i}" for i in issues]
    return "\n".join(out)


# ===== 실행 =====


def main() -> None:
    """CLI 진입점."""
    # Windows 콘솔 기본값(cp949)은 —·이모지 출력에서 UnicodeEncodeError 가 난다
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description="code-daily 코드 뼈대 추출기")
    ap.add_argument("paths", nargs="+", help="분석할 .py 파일 또는 폴더")
    ap.add_argument("--json", action="store_true", help="JSON 으로 출력")
    ap.add_argument("--check", action="store_true", help="규칙 위반(타입·docstring 누락)만 출력")
    args = ap.parse_args()

    results = [analyze_file(f) for f in collect(args.paths)]
    if not results:
        sys.exit("분석할 .py 파일이 없습니다.")
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.check:
        print(to_check(results))
    else:
        print(to_markdown(results))


if __name__ == "__main__":
    main()
