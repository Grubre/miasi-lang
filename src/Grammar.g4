// ExprCore.g4
grammar Grammar;

// --- Parser Rules ---

program: statement* EOF;

statement: functionDefinition
         | ifStatement
         | whileStatement
         | blockStatement       // Explicit block as a statement type
         | expressionStatement  // For things like function calls `myFunc();`
         | variableDeclaration  // Added let for completeness within blocks
         | assignmentStatement  // Added assignment
         | returnStatement      // Added return
         | breakStatement       // Added break for loops
         | continueStatement    // Added continue for loops
         ;

functionDefinition: PROC IDENTIFIER LPAREN parameterList? RPAREN blockStatement;
parameterList: IDENTIFIER (COMMA IDENTIFIER)*; // Simple list of names, no types yet

variableDeclaration: LET IDENTIFIER ASSIGN expression SEMI;

assignmentStatement: IDENTIFIER ASSIGN expression SEMI; // Simple assignment to existing var

returnStatement: RETURN expression? SEMI; // Optional expression

breakStatement: BREAK SEMI;

continueStatement: CONTINUE SEMI;

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
    | primaryExpr;

primaryExpr
    : literal
    | IDENTIFIER
    | functionCall
    | LPAREN expression RPAREN
    ;

functionCall: IDENTIFIER LPAREN argumentList? RPAREN;
argumentList: expression (COMMA expression)*;

compOp: EQ | NEQ | LT | GT | LTE | GTE;
addOp: PLUS | MINUS;
mulOp: MUL | DIV | MOD;

// Literal values
literal: NUMBER | BOOLEAN;


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
COMMA: ',';
SEMI: ';';

// Identifiers (start with letter or underscore, followed by letters, numbers, or underscores)
IDENTIFIER: [a-zA-Z_] [a-zA-Z0-9_]*;

// Literals
BOOLEAN: TRUE | FALSE; // Defined via keywords
NUMBER: INT | FLOAT; // Define INT and FLOAT below

// Define FLOAT before INT to avoid ambiguity ('123' could be INT or start of FLOAT)
fragment FLOAT: [0-9]+ '.' [0-9]* | '.' [0-9]+ ;
fragment INT: [0-9]+ ;

// Whitespace (skipped)
WS: [ \t\r\n]+ -> skip;

// Comments (skipped)
LINE_COMMENT: '//' ~[\r\n]* -> skip;
BLOCK_COMMENT: '/*' .*? '*/' -> skip; // Non-greedy match