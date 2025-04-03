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

    def visitProgram(self, ctx: GrammarParser.ProgramContext):
        return self.visitChildren(ctx)

    def visitStatement(self, ctx: GrammarParser.StatementContext):
        return self.visitChildren(ctx)

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

    def visitParameterList(self, ctx: GrammarParser.ParameterListContext):
        return self.visitChildren(ctx)

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
        return self.visitChildren(ctx)

    def visitBreakStatement(self, ctx: GrammarParser.BreakStatementContext):
        return self.visitChildren(ctx)

    def visitContinueStatement(self, ctx: GrammarParser.ContinueStatementContext):
        return self.visitChildren(ctx)

    def visitIfStatement(self, ctx: GrammarParser.IfStatementContext):
        return self.visitChildren(ctx)

    def visitWhileStatement(self, ctx: GrammarParser.WhileStatementContext):
        return self.visitChildren(ctx)

    def visitBlockStatement(self, ctx: GrammarParser.BlockStatementContext):
        self.enter_scope()
        result = self.visitChildren(ctx)
        self.exit_scope()
        return result

    def visitExpressionStatement(self, ctx: GrammarParser.ExpressionStatementContext):
        return self.visitChildren(ctx)

    def visitExpression(self, ctx: GrammarParser.ExpressionContext):
        return self.visitChildren(ctx)

    def visitLogicalOrExpr(self, ctx: GrammarParser.LogicalOrExprContext):
        return self.visitChildren(ctx)

    def visitLogicalAndExpr(self, ctx: GrammarParser.LogicalAndExprContext):
        return self.visitChildren(ctx)

    def visitComparisonExpr(self, ctx: GrammarParser.ComparisonExprContext):
        return self.visitChildren(ctx)

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
        return self.visitChildren(ctx)

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
        self.enter_scope()

        if params:
            for i in range(len(params.IDENTIFIER())):
                name = params.IDENTIFIER(i).getText()
                value = call_args[i]
                self.set_variable(name, value)

        self.visit(body)

        self.exit_scope()

        return None

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
    """
    Parses and interprets the given file using the ExprCore grammar and MyInterpreterVisitor.
    """
    print(f"Attempting to interpret file: {filename}")
    try:
        input_stream = FileStream(filename)
        lexer = GrammarLexer(input_stream)
        lexer.removeErrorListeners() # Remove default console listener
        lexer.addErrorListener(BasicErrorListener())

        stream = CommonTokenStream(lexer)
        parser = GrammarParser(stream)
        parser.removeErrorListeners() # Remove default console listener
        parser.addErrorListener(BasicErrorListener())

        tree = parser.program() # Start parsing from the 'program' rule

        if parser.getNumberOfSyntaxErrors() == 0:
            print("Parsing successful. Starting interpretation...")
            visitor = CustomInterpreterVisitor()
            visitor.visit(tree) # Start interpretation by visiting the tree root
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
        # Catch other potential errors during interpretation
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()