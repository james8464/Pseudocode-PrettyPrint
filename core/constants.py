# colour palette - RTF uses 1-indexed \cfN (0 is auto)
COLOURS = {
    "black": (0x26, 0x26, 0x26),
    "string": (0xD2, 0x27, 0x23),
    "keyword": (0xA8, 0x35, 0x96),
    "member": (0x00, 0x72, 0xA3),
    "index": (0x18, 0x27, 0xCC),
    "callable": (0x76, 0x46, 0xAB),
    "comment": (0x6B, 0x6B, 0x6B),
}

KEYWORDS = frozenset({
    "AND", "APPEND", "ARRAY", "BOOLEAN", "BYREF", "BYVAL", "CALL",
    "CASE", "OF", "CHAR", "CLASS", "CLOSEFILE", "CONSTANT", "DATE",
    "DECLARE", "DIV", "ELSE", "ENDCASE", "ENDCLASS", "ENDFUNCTION",
    "ENDIF", "ENDPROCEDURE", "ENDTYPE", "ENDWHILE", "EOF", "FALSE",
    "FOR", "TO", "STEP", "FUNCTION", "GETRECORD", "IF", "INHERITS",
    "IMPORT", "INPUT", "INT", "INTEGER", "LCASE", "LENGTH", "MID", "MOD", "NEXT",
    "NEW", "NOT", "OPENFILE", "OR", "OTHERWISE", "OUTPUT", "PROCEDURE",
    "PRIVATE", "PUBLIC", "PUTRECORD", "RAND", "RANDOM", "READ", "READFILE",
    "REAL", "REPEAT", "RETURN", "RETURNS", "RIGHT", "SEEK", "STRING",
    "SUPER", "THEN", "TRUE", "TYPE", "UCASE", "UNTIL", "WHILE", "WRITE",
    "WRITEFILE", "END", "END FOR", "END IF",
})
