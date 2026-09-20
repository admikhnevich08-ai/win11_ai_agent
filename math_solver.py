# -*- coding: utf-8 -*-
"""
Модуль математики: распознаёт примеры и считает их.
"""
import re
import ast
import operator


_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp):
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Недопустимая операция")


def is_math_question(text):
    text_norm = text.lower()
    text_norm = text_norm.replace("плюс", "+").replace("минус", "-")
    text_norm = text_norm.replace("умножить на", "*").replace("умножить", "*")
    text_norm = text_norm.replace("разделить на", "/").replace("делить на", "/")
    text_norm = text_norm.replace("в квадрате", "**2").replace("в кубе", "**3")
    text_norm = text_norm.replace("х", "*").replace("×", "*").replace("÷", "/")
    text_norm = text_norm.replace("=", "")
    cleaned = re.sub(r"[^0-9\+\-\*\/\(\)\.\s%]", "", text_norm)
    cleaned = cleaned.strip()
    pattern = r"\d\s*(?:\*\*|[\+\-\*\/%])\s*\d"
    return bool(re.search(pattern, cleaned)), cleaned


def solve(text):
    ok, expr = is_math_question(text)
    if not ok:
        return None, None
    try:
        if not re.fullmatch(r"[\d\+\-\*\/\(\)\.\s%]+", expr):
            return None, None
        tree = ast.parse(expr, mode="eval")
        result = _safe_eval(tree.body)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return result, expr
    except Exception:
        return None, None


if __name__ == "__main__":
    tests = [
        "2+2",
        "сколько будет 15 умножить на 7",
        "100 минус 42",
        "2 в квадрате",
        "2 в кубе",
        "(5+3)*2",
        "10 % 3",
        "2**10",
        "100 % 7",
        "расскажи про нейросети",
    ]
    for t in tests:
        r, e = solve(t)
        print(f"{t!r:40} -> {r}  (expr: {e})")