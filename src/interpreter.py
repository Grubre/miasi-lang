import sys
import codecs
import traceback

from antlr4 import CommonTokenStream, FileStream
from antlr4.error.ErrorListener import ErrorListener

from GrammarLexer import GrammarLexer
from GrammarParser import GrammarParser
from GrammarVisitor import GrammarVisitor

from graphics import GraphicsController
from shape import *


class ReturnValue(Exception):
    def __init__(self, value=None): self.value = value
class BreakLoop(Exception): pass
class ContinueLoop(Exception): pass
class InterpreterRuntimeError(Exception):
    def __init__(self, message, ctx): # Store context
        super().__init__(message)
        self.line = ctx.start.line if ctx else '?'
        self.column = ctx.start.column if ctx else '?'
        self.message = message

    def __str__(self):
        return f"Error:{self.line}:{self.column} - {self.message}"


# --- Basic Error Listener ---
# (Optional but recommended to get better error messages than default console)
class BasicErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        print(f"Error:{line}:{column} - Syntax Error: {msg}", file=sys.stderr)
        raise SyntaxError(f"Line {line}:{column} {msg}")

def builtin_print(*args):
    print(*args)
    return None

def parse_hex_color(hex_str: str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) != 6:
        raise ValueError(f"Invalid hex color string: '{hex_str}'")

    try:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return r, g, b
    except Exception as e:
        raise ValueError(f"Invalid hex color string: '{hex_str}'") from e


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

    def print_scopes(self):
        for i, scope in enumerate(self.scopes):
            print(f"Scope {i}:")
            for name, value in scope.items():
                print(f"  {name}: {value}")
            print()

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
                raise InterpreterRuntimeError(f"Error setting property '{name}': {e}", ctx.expression()) from e
        else:
            raise InterpreterRuntimeError(f"Unknown property '{name}'. Cannot be set.", ctx.IDENTIFIER())

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

    def visitForStatement(self, ctx: GrammarParser.ForStatementContext):
        variable = ctx.IDENTIFIER().getText()
        iterable = self.visit(ctx.expression())

        if not isinstance(iterable, list):
            raise InterpreterRuntimeError(f"Type Error: Cannot iterate over non-array type {type(iterable).__name__}",
                                          ctx.expression())

        for value in iterable:
            self.enter_scope()
            try:
                self.declare_variable(variable, value)
                self.visit(ctx.statement())
            except BreakLoop:
                break
            except ContinueLoop:
                continue

            self.exit_scope()

    def visitListComprehension(self, ctx:GrammarParser.ListComprehensionContext):
        name = ctx.IDENTIFIER().getText()
        iterable = self.visit(ctx.iterExpr)

        output_arr = []

        for item in iterable:
            self.enter_scope()
            self.declare_variable(name, item)
            should_append = True

            if ctx.condExpr:
                should_append = bool(self.visit(ctx.condExpr))

            if should_append:
                value = self.visit(ctx.outputExpr)
                output_arr.append(value)

            self.exit_scope()

        return output_arr

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
        raise InterpreterRuntimeError(f"Unsupported comparison operator: {op}", ctx.compOp())

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
                 raise InterpreterRuntimeError(f"Unsupported additive operator: {op}", ctx.addOp(i-1))
        return result

    def visitMultiplicativeExpr(self, ctx: GrammarParser.MultiplicativeExprContext):
        result = self.visit(ctx.unaryExpr(0))

        try:
            for i in range(1, len(ctx.unaryExpr())):
                op = ctx.mulOp(i - 1).getText()
                right = self.visit(ctx.unaryExpr(i))
                if op == '*':
                    result *= right
                elif op == '/':
                    if right == 0:
                        raise InterpreterRuntimeError("Division by zero", ctx.unaryExpr(i))
                    result /= right
                elif op == '%':
                    if right == 0:
                        raise InterpreterRuntimeError("Modulo by zero", ctx.unaryExpr(i))
                    result %= right
                else:
                    raise InterpreterRuntimeError(f"Unsupported multiplicative operator: {op}", ctx.mulOp(i - 1))
            return result
        except TypeError as e:
            raise InterpreterRuntimeError(f"Type Error: {e}", ctx) from e

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
        if ctx.LBRACKET():
            arr_ctx = ctx.primaryExpr()
            index_ctx = ctx.expression()

            arr = self.visit(arr_ctx)
            index = self.visit(index_ctx)

            if not isinstance(arr, list):
                raise InterpreterRuntimeError(f"Type Error: Cannot index non-array type {type(arr).__name__}",
                                              index_ctx)
            if not isinstance(index, int):
                raise InterpreterRuntimeError(f"Type Error: Array index must be an integer, not {type(index).__name__}",
                                              index_ctx)
            try:
                return arr[index]
            except IndexError:
                raise InterpreterRuntimeError(f"Index Error: Array index {index} out of bounds (length {len(arr)})",
                                              index_ctx)
        if ctx.listComprehension():
            return self.visit(ctx.listComprehension())
        if ctx.IDENTIFIER():
            return self.get_variable(ctx.IDENTIFIER().getText())
        if ctx.literal():
            return self.visit(ctx.literal())
        if ctx.functionCall():
            return self.visit(ctx.functionCall())
        if ctx.expression():
            return self.visit(ctx.expression())
        if ctx.shapeLiteral():
            return self.visit(ctx.shapeLiteral())
        if ctx.arrayLiteral():
            return self.visit(ctx.arrayLiteral())

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
        elif ctx.colorLiteral():
            return self.visitColorLiteral(ctx.colorLiteral())
        elif ctx.STRING():
            string_literal = ctx.STRING().getText()
            value_inside_quotes = string_literal[1:-1]
            processed_value, _ = codecs.unicode_escape_decode(value_inside_quotes)
            return processed_value
        else:
            raise TypeError("Unsupported literal type")

    def visitColorLiteral(self, ctx: GrammarParser.ColorLiteralContext):
        if ctx.HEX_COLOR():
            hex_str = ctx.HEX_COLOR().getText()[1:]
            if len(hex_str) != 6:
                raise ValueError(f"Invalid hex color string: '{hex_str}'")
            color = parse_hex_color(hex_str)
            return color
        elif ctx.rgbColor():
            r = self.visit(ctx.rgbColor().r)
            g = self.visit(ctx.rgbColor().g)
            b = self.visit(ctx.rgbColor().b)
            return r, g, b
        else:
            raise TypeError("Unsupported color literal type")

    def visitShapeLiteral(self, ctx: GrammarParser.ShapeLiteralContext):
        if ctx.rectangleLiteral():
            return self.visit(ctx.rectangleLiteral())
        elif ctx.circleLiteral():
            return self.visit(ctx.circleLiteral())
        elif ctx.triangleLiteral():
            return self.visit(ctx.triangleLiteral())
        elif ctx.lineLiteral():
            return self.visit(ctx.lineLiteral())
        else:
            raise TypeError("Unknown shape literal type")

    def visitRectangleLiteral(self, ctx: GrammarParser.RectangleLiteralContext):
        args_dict = {}
        if ctx.namedArgumentList():
            args_dict = self.visit(ctx.namedArgumentList()) # Get dict of name:value
        try:
            return Rectangle(**args_dict)
        except Exception as e: # Catch potential errors during object creation
             raise RuntimeError(f"Error creating rectangle: {e}") from e

    def visitCircleLiteral(self, ctx: GrammarParser.CircleLiteralContext):
        args_dict = {}
        if ctx.namedArgumentList():
            args_dict = self.visit(ctx.namedArgumentList())
        try:
            return Circle(**args_dict)
        except Exception as e:
             raise RuntimeError(f"Error creating circle: {e}") from e

    def visitTriangleLiteral(self, ctx: GrammarParser.TriangleLiteralContext):
        args_dict = {}
        if ctx.namedArgumentList():
            args_dict = self.visit(ctx.namedArgumentList())
        try:
            return Triangle(**args_dict)
        except Exception as e:
             raise RuntimeError(f"Error creating triangle: {e}") from e

    def visitLineLiteral(self, ctx: GrammarParser.LineLiteralContext):
        args_dict = {}
        if ctx.namedArgumentList():
            args_dict = self.visit(ctx.namedArgumentList())
        try:
            return Line(**args_dict)
        except Exception as e:
             raise RuntimeError(f"Error creating line: {e}") from e

    def visitNamedArgumentList(self, ctx: GrammarParser.NamedArgumentListContext):
        args_dict = {}
        for arg_ctx in ctx.namedArgument():
            name, value = self.visit(arg_ctx)
            if name in args_dict:
                print(f"Warning: Duplicate argument name '{name}' provided.")
            args_dict[name] = value
        return args_dict

    def visitNamedArgument(self, ctx: GrammarParser.NamedArgumentContext):
        name = ctx.IDENTIFIER().getText()
        value = self.visit(ctx.expression())
        return name, value

    def visitArrayLiteral(self, ctx: GrammarParser.ArrayLiteralContext):
        arr = []
        if ctx.argumentList():
            arr = self.visit(ctx.argumentList())

        return arr

def setup_builtin_functions(interpreter: CustomInterpreterVisitor, graphics_controller: GraphicsController):
    interpreter.add_builtin_function('print', builtin_print)
    interpreter.add_builtin_function('draw', lambda x, y, shape: graphics_controller.draw_shape(x, y, shape))

    interpreter.add_property('width', lambda width: graphics_controller.set_window_width(width))
    interpreter.add_property('height', lambda height: graphics_controller.set_window_height(height))
    interpreter.add_property('bg_color', lambda color: graphics_controller.set_background_color(color))

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
    except InterpreterRuntimeError as e:
        print(e, file=sys.stderr)
    except NameError as e:
        print(e, file=sys.stderr)
    except SyntaxError as e:
        print(f"Halting due to Syntax Error.", file=sys.stderr)
    except Exception as e:
        print(f"\n--- An Unexpected Internal Interpreter Error Occurred ---", file=sys.stderr)
        print(f"Error Type: {type(e).__name__}", file=sys.stderr)
        print(f"Error Details: {e}", file=sys.stderr)
        print("-" * 50, file=sys.stderr)
        traceback.print_exc()