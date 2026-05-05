import ast
import operator

# Supported operators
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}

def safe_eval(expr, variables):
    """
    Safely evaluate a math expression using AST
    """
    def _eval(node):
        if isinstance(node, ast.Num):  # number
            return node.n

        elif isinstance(node, ast.Name):  # variable
            return variables.get(node.id, 0)

        elif isinstance(node, ast.BinOp):  # x + y
            left = _eval(node.left)
            right = _eval(node.right)
            return OPERATORS[type(node.op)](left, right)

        elif isinstance(node, ast.UnaryOp):  # -x
            return -_eval(node.operand)

        else:
            raise ValueError("Unsupported expression")

    tree = ast.parse(expr, mode='eval')
    return _eval(tree.body)
