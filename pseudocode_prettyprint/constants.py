# Colour palette and language constants.

from enum import Enum


class Colour(str, Enum):
    """Named RTF colours, in the order they appear in the colour table."""

    BLACK = "black"
    STRING = "string"
    KEYWORD = "keyword"
    MEMBER = "member"
    INDEX = "index"
    CALLABLE = "callable"
    COMMENT = "comment"


# Each colour is an (red, green, blue) tuple of integers in the range 0-255.
# The RTF colour table and the \cfN mapping are both generated from this mapping,
# so editing a value here is sufficient to change the rendered output.
COLOURS: dict[Colour, tuple[int, int, int]] = {
    Colour.BLACK: (0x26, 0x26, 0x26),      # default text
    Colour.STRING: (0xD2, 0x27, 0x23),     # "strings in quotes"
    Colour.KEYWORD: (0xA8, 0x35, 0x96),    # IF, THEN, ELSE, etc.
    Colour.MEMBER: (0x00, 0x72, 0xA3),     # object.property
    Colour.INDEX: (0x18, 0x27, 0xCC),      # arr.0, arr.1
    Colour.CALLABLE: (0x76, 0x46, 0xAB),   # function names, procedures
    Colour.COMMENT: (0x6B, 0x6B, 0x6B),    # // comments
}

# Cambridge International pseudocode keywords and built-in functions.
KEYWORDS: frozenset[str] = frozenset({
    "AND", "APPEND", "ARRAY", "ASC", "BOOLEAN", "BYREF", "BYVAL", "CALL",
    "CASE", "OF", "CHAR", "CHR", "CLASS", "CLOSEFILE", "CONSTANT", "DATE",
    "DECLARE", "DIV", "ELSE", "ENDCASE", "ENDCLASS", "ENDFUNCTION",
    "ENDIF", "ENDPROCEDURE", "ENDTYPE", "ENDWHILE", "EOF", "FALSE",
    "FOR", "TO", "STEP", "FUNCTION", "GETRECORD", "IF", "INHERITS",
    "IMPORT", "INPUT", "INT", "INTEGER", "IS_NUM", "LCASE", "LEFT",
    "LENGTH", "MID", "MOD", "NEXT", "NEW", "NOT", "NUM_TO_STR",
    "OPENFILE", "OR", "OTHERWISE", "OUTPUT", "PRINT", "PROCEDURE",
    "PRIVATE", "PUBLIC", "PUTRECORD", "RAND", "READ", "READFILE", "REAL", "REPEAT",
    "RETURN", "RETURNS", "RIGHT", "SEEK", "STRING", "STR_TO_NUM", "SUPER",
    "THEN", "TRUE", "TYPE", "UCASE", "UNTIL", "WHILE", "WRITE",
    "WRITEFILE",
})
