grammar Grammar;

// --- Parser Rules ---

program: statement* EOF;

statement: functionDefinition
         | ifStatement
         | whileStatement
         | blockStatement
         | expressionStatement
         | variableDeclaration
         | assignmentStatement
         | returnStatement
         | breakStatement
         | continueStatement
         | setStatement
         | forStatement
         ;

forStatement : FOR IDENTIFIER IN expression statement;

functionDefinition: PROC IDENTIFIER LPAREN parameterList? RPAREN blockStatement;
parameterList: IDENTIFIER (COMMA IDENTIFIER)*;

variableDeclaration: LET IDENTIFIER ASSIGN expression SEMI;

assignmentStatement: assignmentTarget ASSIGN expression SEMI;
assignmentTarget
    : IDENTIFIER
    | postfixExpr
    ;

returnStatement: RETURN expression? SEMI;

breakStatement: BREAK SEMI;

continueStatement: CONTINUE SEMI;

setStatement: SET IDENTIFIER expression SEMI;

ifStatement: IF LPAREN expression RPAREN statement (ELSE statement)?;

whileStatement: WHILE LPAREN expression RPAREN statement;

blockStatement: LBRACE statement* RBRACE;

expressionStatement: expression SEMI;

expression: logicalOrExpr;

logicalOrExpr
    : left=logicalAndExpr (OR right=logicalAndExpr)*;

logicalAndExpr
    : left=comparisonExpr (AND right=comparisonExpr)*;

comparisonExpr
    : left=additiveExpr (compOp right=additiveExpr)?;

additiveExpr
    : multiplicativeExpr (addOp multiplicativeExpr)*;

multiplicativeExpr
    : unaryExpr (mulOp unaryExpr)*;

unaryExpr
    : (NOT | MINUS) unaryExpr
    | postfixExpr;

atom
    : literal
    | IDENTIFIER
    | LPAREN expression RPAREN
    | shapeLiteral
    | arrayLiteral
    | listComprehension
    ;

postfixExpr
    : postfixExpr LBRACKET expression RBRACKET // array indexing a[10], a[i], etc.
    | postfixExpr LPAREN argumentList? RPAREN  // function call get_value(), f(x), etc.
    | atom
    ;

argumentList: expression (COMMA expression)*;

listComprehension
    : LBRACKET outputExpr=expression FOR IDENTIFIER IN iterExpr=expression (IF condExpr=expression)? RBRACKET
    ;

arrayLiteral
    : LBRACKET argumentList? RBRACKET
    ;

shapeLiteral
    : rectangleLiteral
    | circleLiteral
    | triangleLiteral
    | lineLiteral
    ;

namedArgumentList
    : namedArgument (COMMA namedArgument)*
    ;

namedArgument
    : IDENTIFIER COLON expression
    ;

rectangleLiteral : RECTANGLE LBRACE namedArgumentList? RBRACE;
circleLiteral : CIRCLE LBRACE namedArgumentList? RBRACE;
triangleLiteral : TRIANGLE LBRACE namedArgumentList? RBRACE;

lineLiteral : LINE LBRACE namedArgumentList? RBRACE;


compOp: EQ | NEQ | LT | GT | LTE | GTE;
addOp: PLUS | MINUS;
mulOp: MUL | DIV | MOD;

// Literal values
literal
    : NUMBER
    | BOOLEAN
    | colorLiteral
    | STRING;

colorLiteral: rgbColor | HEX_COLOR;

rgbColor: RGB LPAREN r=expression COMMA g=expression COMMA b=expression RPAREN;

// --- Lexer Rules ---

// Keywords
PROC: 'proc';
LET: 'let';
IF: 'if';
ELSE: 'else';
WHILE: 'while';
RETURN: 'return';
BREAK: 'break';
CONTINUE: 'continue';
TRUE: 'true';
FALSE: 'false';
AND: 'and';
OR: 'or';
NOT: 'not';
SET: 'set';
RGB: 'rgb';
FOR: 'for';
IN: 'in';

RECTANGLE: 'Rectangle';
CIRCLE: 'Circle';
TRIANGLE: 'Triangle';
LINE: 'Line';

// Operators and Punctuation
ASSIGN: '=';
PLUS: '+';
MINUS: '-';
MUL: '*';
DIV: '/';
MOD: '%';
EQ: '==';
NEQ: '!=';
LT: '<';
GT: '>';
LTE: '<=';
GTE: '>=';
LPAREN: '(';
RPAREN: ')';
LBRACE: '{';
RBRACE: '}';
LBRACKET: '[';
RBRACKET: ']';
COMMA: ',';
SEMI: ';';
COLON: ':';

STRING
    : '"'  (~'"' | '\\"')*? '"'
    ;

fragment HEX_DIGIT : [0-9a-fA-F];
HEX_COLOR : '#' HEX_DIGIT+ ;

IDENTIFIER: [a-zA-Z_] [a-zA-Z0-9_]*;

BOOLEAN: TRUE | FALSE;
NUMBER: INT | FLOAT;

fragment FLOAT: [0-9]+ '.' [0-9]* | '.' [0-9]+ ;
fragment INT: [0-9]+ ;

// Whitespace (skipped)
WS: [ \t\r\n]+ -> skip;

// Comments (skipped)
LINE_COMMENT: '//' ~[\r\n]* -> skip;
BLOCK_COMMENT: '/*' .*? '*/' -> skip; // Non-greedy match