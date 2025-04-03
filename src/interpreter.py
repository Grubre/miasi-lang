import sys
from antlr4 import CommonTokenStream, FileStream
from antlr4.error.ErrorListener import ErrorListener

from GrammarLexer import GrammarLexer
from GrammarParser import GrammarParser
from GrammarVisitor import GrammarVisitor

# --- Basic Error Listener ---
# (Optional but recommended to get better error messages than default console)
class BasicErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        print(f"Syntax Error at Line {line}:{column} - {msg}", file=sys.stderr)
        raise SyntaxError(f"Line {line}:{column} {msg}")

def builtin_print(*x):
    print(*x)

class CustomInterpreterVisitor(GrammarVisitor):
    def __init__(self):
        self.functions: dict[str, {}] = {}
        self.builtin_functions = {}
        self.scopes = [{}]
        self.break_loop = False
        self.continue_loop = False
        self.return_stmt_called = False
        self.is_inside_loop = False
        self.is_inside_func = False

        self.builtin_functions["print"] = builtin_print

    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        # we don't want to pop the global scope
        if len(self.scopes) > 1:
            self.scopes.pop()

    def set_variable(self, name, value):
        self.scopes[-1][name] = value

    def assign_variable(self, name, value):
        for scope in reversed(self.scopes):
            if name in scope:
                scope[name] = value
                return
        raise NameError(f"Variable '{name}' is not defined before assignment")

    def get_variable(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise NameError(f"Variable '{name}' is not defined")

    def visitFunctionDefinition(self, ctx: GrammarParser.FunctionDefinitionContext):
        name = ctx.IDENTIFIER().getText()
        if name in self.builtin_functions:
            raise NameError(f"Function '{name}' is a reserved keyword and cannot be used as a function name.")
        if name in self.functions:
            raise NameError(f"Function '{name}' has already been defined.")
        self.functions[name] = {
            'params': ctx.parameterList(),
            'body': ctx.blockStatement()
        }
        return None

    def visitVariableDeclaration(self, ctx: GrammarParser.VariableDeclarationContext):
        name = ctx.IDENTIFIER().getText()
        value = self.visit(ctx.expression())

        self.set_variable(name, value)

        return None

    def visitAssignmentStatement(self, ctx: GrammarParser.AssignmentStatementContext):
        name = ctx.IDENTIFIER().getText()
        value = self.visit(ctx.expression())
        self.assign_variable(name, value)
        return None

    def visitReturnStatement(self, ctx: GrammarParser.ReturnStatementContext):
        if not self.is_inside_func:
            raise SyntaxError("Return statement outside function")
        value = None
        if ctx.expression():
            value = self.visit(ctx.expression())

        self.return_stmt_called = True
        return value

    def visitBreakStatement(self, ctx: GrammarParser.BreakStatementContext):
        if not self.is_inside_loop:
            raise SyntaxError("Break statement outside loop")
        self.break_loop = True
        return None

    def visitContinueStatement(self, ctx: GrammarParser.ContinueStatementContext):
        if not self.is_inside_loop:
            raise SyntaxError("Continue statement outside loop")
        self.continue_loop = True
        return None

    def visitIfStatement(self, ctx: GrammarParser.IfStatementContext):
        condition = self.visit(ctx.expression())

        is_true = bool(condition)

        if is_true:
            self.visit(ctx.statement(0))
        elif ctx.ELSE():
            self.visit(ctx.statement(1))
        return None

    def visitWhileStatement(self, ctx: GrammarParser.WhileStatementContext):
        self.is_inside_loop = True
        while True:
            condition = self.visit(ctx.expression())
            is_true = bool(condition)

            if not is_true:
                break

            self.visit(ctx.statement())

            if self.break_loop:
                self.break_loop = False
                break
            if self.continue_loop:
                self.continue_loop = False
                continue

        self.is_inside_loop = False

        return None

    def visitBlockStatement(self, ctx: GrammarParser.BlockStatementContext):
        self.enter_scope()
        result = None
        try:
            for statement in ctx.statement():
                result = self.visit(statement)
                if self.break_loop or self.continue_loop or self.return_stmt_called:
                    return result
        finally:
            self.exit_scope()
        return result

    def visitLogicalOrExpr(self, ctx: GrammarParser.LogicalOrExprContext):
        left = self.visit(ctx.left)

        if not ctx.OR():
            return left

        if bool(left):
            return left

        return self.visit(ctx.right)

    def visitLogicalAndExpr(self, ctx: GrammarParser.LogicalAndExprContext):
        left = self.visit(ctx.left)

        if not ctx.AND():
            return left

        if not bool(left):
            return left

        return self.visit(ctx.right)

    def visitComparisonExpr(self, ctx: GrammarParser.ComparisonExprContext):
        left = self.visit(ctx.left)

        if ctx.compOp() is None:
            return left

        right = self.visit(ctx.right)
        op = ctx.compOp().getText()

        if op == '==': return left == right
        if op == '!=': return left != right
        if op == '<':  return left < right
        if op == '>':  return left > right
        if op == '<=': return left <= right
        if op == '>=': return left >= right
        raise TypeError(f"Unsupported comparison operator: {op}")

    def visitAdditiveExpr(self, ctx: GrammarParser.AdditiveExprContext):
        result = self.visit(ctx.multiplicativeExpr(0))

        for i in range(1, len(ctx.multiplicativeExpr())):
            op = ctx.addOp(i-1).getText()
            right = self.visit(ctx.multiplicativeExpr(i))

            if op == '+':
                result += right
            elif op == '-':
                result -= right
            else:
                 raise TypeError(f"Unsupported additive operator: {op}")
        return result

    def visitMultiplicativeExpr(self, ctx: GrammarParser.MultiplicativeExprContext):
        result = self.visit(ctx.unaryExpr(0))

        for i in range(1, len(ctx.unaryExpr())):
            op = ctx.mulOp(i - 1).getText()
            right = self.visit(ctx.unaryExpr(i))
            if op == '*':
                result *= right
            elif op == '/':
                if right == 0:
                    raise ZeroDivisionError("Division by zero")
                result /= right
            elif op == '%':
                if right == 0:
                    raise ZeroDivisionError("Modulo by zero")
                result %= right
            else:
                raise TypeError(f"Unsupported multiplicative operator: {op}")
        return result

    def visitUnaryExpr(self, ctx: GrammarParser.UnaryExprContext):
        if ctx.primaryExpr():
            return self.visit(ctx.primaryExpr())

        operand = self.visit(ctx.unaryExpr())

        if ctx.NOT():
            return not bool(operand)
        elif ctx.MINUS():
            return -operand
        else:
            raise TypeError("Unsupported unary operator")

    def visitPrimaryExpr(self, ctx: GrammarParser.PrimaryExprContext):
        if ctx.IDENTIFIER():
            return self.get_variable(ctx.IDENTIFIER().getText())
        if ctx.literal():
            return self.visit(ctx.literal())
        if ctx.functionCall():
            return self.visit(ctx.functionCall())
        if ctx.expression():
            return self.visit(ctx.expression())

        raise RuntimeError("Unhandled primary expression type")

    def visitFunctionCall(self, ctx: GrammarParser.FunctionCallContext):
        function_name = ctx.IDENTIFIER().getText()

        if (function_name not in self.functions) and (function_name not in self.builtin_functions):
            raise NameError(f"Function '{function_name}' is not defined.")

        call_args = []
        if ctx.argumentList() is not None:
            call_args = self.visit(ctx.argumentList())

        if function_name in self.builtin_functions:
            return self.builtin_functions[function_name](*call_args)

        func_data = self.functions[function_name]
        params = func_data['params']
        body = func_data['body']

        arity = 0
        if params:
             arity = len(params.IDENTIFIER())

        if arity != len(call_args):
            raise TypeError(f"Incorrect number of arguments for function '{function_name}'. Expected {arity}, got {len(call_args)}")

        # execute the function
        self.is_inside_func = True
        self.enter_scope()

        if params:
            for i in range(len(params.IDENTIFIER())):
                name = params.IDENTIFIER(i).getText()
                value = call_args[i]
                self.set_variable(name, value)

        return_value = self.visit(body)

        self.exit_scope()
        self.is_inside_func = False
        self.return_stmt_called = False

        return return_value

    def visitArgumentList(self, ctx: GrammarParser.ArgumentListContext):
        args = []
        for arg in ctx.expression():
            args.append(self.visit(arg))
        return args

    def visitLiteral(self, ctx: GrammarParser.LiteralContext):
        if ctx.NUMBER():
            num_str = ctx.NUMBER().getText()
            if '.' in num_str:
                return float(num_str)
            else:
                return int(num_str)
        elif ctx.BOOLEAN():
            bool_str = ctx.BOOLEAN().getText()
            return True if bool_str == 'true' else False
        else:
            raise TypeError("Unsupported literal type")

def run_file(filename: str):
    print(f"Attempting to interpret file: {filename}")
    try:
        input_stream = FileStream(filename)
        lexer = GrammarLexer(input_stream)
        lexer.removeErrorListeners()
        lexer.addErrorListener(BasicErrorListener())

        stream = CommonTokenStream(lexer)
        parser = GrammarParser(stream)
        parser.removeErrorListeners()
        parser.addErrorListener(BasicErrorListener())

        tree = parser.program()

        if parser.getNumberOfSyntaxErrors() == 0:
            print("Parsing successful. Starting interpretation...")
            visitor = CustomInterpreterVisitor()
            visitor.visit(tree)
        else:
            print("Parsing failed. Halting execution.")

    except FileNotFoundError:
        print(f"Error: File not found: {filename}", file=sys.stderr)
    except NameError as e:
        print(f"Runtime Error: {e}", file=sys.stderr)
    except TypeError as e:
        print(f"Runtime Error: {e}", file=sys.stderr)
    except ZeroDivisionError as e:
        print(f"Runtime Error: {e}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()