import sys

from antlr4 import CommonTokenStream, FileStream
from antlr4.error.ErrorListener import ErrorListener

from GrammarLexer import GrammarLexer
from GrammarParser import GrammarParser
from GrammarVisitor import GrammarVisitor

from graphics import GraphicsController

class ReturnValue(Exception):
    def __init__(self, value=None): self.value = value
class BreakLoop(Exception): pass
class ContinueLoop(Exception): pass

# --- Basic Error Listener ---
# (Optional but recommended to get better error messages than default console)
class BasicErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        print(f"Syntax Error at Line {line}:{column} - {msg}", file=sys.stderr)
        raise SyntaxError(f"Line {line}:{column} {msg}")

def builtin_print(*args):
    print(*args)
    return None

class CustomInterpreterVisitor(GrammarVisitor):
    def __init__(self, graphics_controller: GraphicsController):
        self.functions: dict[str, {}] = {}
        self.builtin_functions = {}
        self.scopes = [{}]
        self.properties = {}

        self.graphics_controller = graphics_controller

    def add_builtin_function(self, name, func):
        if name in self.functions or name in self.builtin_functions:
            raise NameError(f"Cannot add built-in function: Name '{name}' is already defined.")

        self.builtin_functions[name] = func

    def add_property(self, name, func):
        if name in self.properties:
            print(f"Warning: Property '{name}' is being redefined.")

        self.properties[name] = func

    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        # we don't want to pop the global scope
        if len(self.scopes) > 1:
            self.scopes.pop()

    def declare_variable(self, name, value):
        if name in self.scopes[-1]:
            print(f"Warning: Variable '{name}' already declared in this scope (shadowing).")

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

    def visitProgram(self, ctx:GrammarParser.ProgramContext):
        self.graphics_controller.start_display()
        self.graphics_controller.set_window_size(800, 800)
        self.graphics_controller.set_background_color((125, 125, 255))
        try:
            for statement in ctx.statement():
                self.visit(statement)
        except ReturnValue:
            print(f"Warning: 'return' encountered outside of a function call at top level.")
        except BreakLoop:
            print(f"Error: 'break' encountered outside of a loop at top level.")
        except ContinueLoop:
            print(f"Error: 'continue' encountered outside of a loop at top level.")

        return None

    def visitSetStatement(self, ctx:GrammarParser.SetStatementContext):
        name = ctx.IDENTIFIER().getText()

        if name in self.properties:
            setter_func = self.properties[name]
            try:
                value = self.visit(ctx.expression())
                setter_func(value)
            except Exception as e:
                raise RuntimeError(f"Error setting property '{name}': {e}") from e
        else:
            raise NameError(f"Unknown property '{name}'. Cannot be set.")

        return None

    def visitFunctionDefinition(self, ctx: GrammarParser.FunctionDefinitionContext):
        name = ctx.IDENTIFIER().getText()
        if name in self.builtin_functions:
            raise NameError(f"Function '{name}' is a reserved built-in function name.")
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

        self.declare_variable(name, value)

        return None

    def visitAssignmentStatement(self, ctx: GrammarParser.AssignmentStatementContext):
        name = ctx.IDENTIFIER().getText()
        value = self.visit(ctx.expression())
        self.assign_variable(name, value)
        return None

    def visitReturnStatement(self, ctx: GrammarParser.ReturnStatementContext):
        value = None
        if ctx.expression():
            value = self.visit(ctx.expression())
        raise ReturnValue(value)

    def visitBreakStatement(self, ctx: GrammarParser.BreakStatementContext):
        raise BreakLoop()

    def visitContinueStatement(self, ctx: GrammarParser.ContinueStatementContext):
        raise ContinueLoop()

    def visitIfStatement(self, ctx: GrammarParser.IfStatementContext):
        condition = self.visit(ctx.expression())

        is_true = bool(condition)

        if is_true:
            self.visit(ctx.statement(0))
        elif ctx.ELSE():
            self.visit(ctx.statement(1))
        return None

    def visitWhileStatement(self, ctx: GrammarParser.WhileStatementContext):
        while True:
            try:
                condition = self.visit(ctx.expression())
                is_true = bool(condition)

                if not is_true:
                    break

                self.visit(ctx.statement())

            except BreakLoop:
                break
            except ContinueLoop:
                continue

        return None

    def visitBlockStatement(self, ctx: GrammarParser.BlockStatementContext):
        self.enter_scope()
        try:
            for statement in ctx.statement():
                self.visit(statement)
        finally:
            self.exit_scope()
        return None

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

        param_names = []
        arity = 0
        if params:
            param_names = [p.getText() for p in params.IDENTIFIER()]
            arity = len(param_names)

        if arity != len(call_args):
            raise TypeError(f"Incorrect number of arguments for function '{function_name}'. Expected {arity}, got {len(call_args)}")

        # execute the function
        self.enter_scope()
        return_value = None

        try:
            if params:
                for name, value in zip(param_names, call_args):
                    print(f"Assigning parameter '{name}' to value {value}" )
                    self.declare_variable(name, value)

            self.visit(body)

        except ReturnValue as rv:
            return_value = rv.value
        finally:
            self.exit_scope()

        return return_value

    def visitArgumentList(self, ctx: GrammarParser.ArgumentListContext):
        return [self.visit(expr) for expr in ctx.expression()]

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

def setup_builtin_functions(interpreter: CustomInterpreterVisitor, graphics_controller: GraphicsController):
    interpreter.add_builtin_function('print', builtin_print)
    interpreter.add_builtin_function('rect', lambda x,y,w,h: graphics_controller.draw_rectangle(x,y,w,h,(0,0,0)))

    interpreter.add_property('width', lambda width: graphics_controller.set_window_width(width))
    interpreter.add_property('height', lambda height: graphics_controller.set_window_height(height))

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
            graphics_controller = GraphicsController([800, 800])
            visitor = CustomInterpreterVisitor(graphics_controller)
            setup_builtin_functions(visitor, graphics_controller)

            visitor.visit(tree)

            print("Interpretation complete. Waiting for graphics window to close...")
            graphics_controller.wait_for_display_close()
            print("Graphics window closed.")
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