"""仅恢复编辑模型响应的无歧义外包装，不修改 JSON 正文或业务值。"""

import re
from json import JSONDecodeError

from app.logger import json_for_log, logger
from services.single_step_edit import _load_json

# 正则只识别包装语法；说明区不接受其它 JSON 边界或围栏，不推断自然语言含义。
_PROSE = r"[^`{}\[\]]*?"
_OPEN = r"```(?:json|jsonl|genui)?[ \t]*\r?\n"
_BODY = r"(?P<body>\{[\s\S]*\})"
_CLOSE = r"\s*```"
_WRAPPERS = (
    ("complete_fence", _PROSE + _OPEN + r"\s*" + _BODY + _CLOSE + _PROSE),
    ("opening_fence", _PROSE + _OPEN + r"\s*" + _BODY),
    ("closing_fence", _BODY + _CLOSE + _PROSE),
)


def normalize_edit_output(output: str, phase: str) -> str:
    text = output.strip().removeprefix("\ufeff").strip()
    candidate = text
    method = "bom" if text != output.strip() else "unchanged"
    for wrapper_method, pattern in _WRAPPERS:
        match = re.fullmatch(pattern, text, re.I)
        if match is not None:
            candidate = match.group("body")
            method = wrapper_method
            break
    result = output
    if method == "unchanged":
        return result
    try:
        parsed = _load_json(candidate)
    except ValueError as exc:
        # 保留原响应，让既有意图/执行修复循环处理，不在模型调用边界抛出解析错误。
        reason = exc.msg if isinstance(exc, JSONDecodeError) else "JSON 对象包含重复键"
        logger.warning(
            "[Widget Edit] output_wrapper_rejected details="
            + json_for_log({"phase": phase, "method": method,
                            "exceptionType": type(exc).__name__, "reason": reason})
        )
    else:
        if isinstance(parsed, dict):
            result = candidate
            logger.info(
                "[Widget Edit] output_wrapper_recovered details="
                + json_for_log({"phase": phase, "method": method, "outputChars": len(result)})
            )
    return result
