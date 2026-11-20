# pseudocode pretty print

Converts Cambridge-style pseudocode to RTF with syntax highlighting. The
pseudocode format follows the Cambridge International syllabus; see the
[full guide](https://www.cambridgeinternational.org/Images/697401-2026-pseudocode-guide-for-teachers.pdf).

The colour scheme is based on Xcode's pretty-print style in light mode. Apple's
design guidelines are available
[here](https://developer.apple.com/design/human-interface-guidelines/color).

## requirements

Python 3.10 or newer. There are no runtime dependencies.

## usage

### interactive

```bash
python3 main.py
```

Paste your pseudocode, then type `END` (or `:end`) on its own line to finish
the block. Type `QUIT` to exit. `Ctrl-D` also exits.

### pipe or file

```bash
python3 main.py < input.txt
python3 main.py input.txt
```

### installed command

```bash
pip install -e .
pseudocode-prettyprint input.txt
pseudocode-prettyprint input.txt --stdout
pseudocode-prettyprint input.txt -o report.rtf
```

Run `pseudocode-prettyprint --help` for all options.

## output

By default, documents are written to `./outputs`. Existing files are never
overwritten: the next free numbered name is used
(`pretty_pseudocode.rtf`, `pretty_pseudocode_2.rtf`, ...). Use `--force` to
overwrite deliberately, or `--stdout` to write the RTF to standard output.

## customising colours

Colours are defined in `pseudocode_prettyprint/constants.py` in the
`COLOURS` dictionary. Each entry is a `(red, green, blue)` tuple of integers
in the range 0-255. The RTF colour table and `\cfN` mapping are generated from
this dictionary, so editing a value there is sufficient.

## supported syntax

### keywords and built-ins

```text
AND, APPEND, ARRAY, ASC, BOOLEAN, BYREF, BYVAL, CALL, CASE, CHAR, CHR,
CLASS, CLOSEFILE, CONSTANT, DATE, DECLARE, DIV, ELSE, ENDCASE, ENDCLASS,
ENDFUNCTION, ENDIF, ENDPROCEDURE, ENDTYPE, ENDWHILE, EOF, FALSE, FOR,
FUNCTION, GETRECORD, IF, INHERITS, IMPORT, INPUT, INT, INTEGER, IS_NUM,
LCASE, LEFT, LENGTH, MID, MOD, NEW, NEXT, NOT, NUM_TO_STR, OPENFILE, OF,
OR, OTHERWISE, OUTPUT, PRINT, PROCEDURE, PRIVATE, PUBLIC, PUTRECORD,
RAND, READ, READFILE, REAL, REPEAT, RETURN, RETURNS, RIGHT, SEEK, STEP,
STRING, STR_TO_NUM, SUPER, THEN, TO, TRUE, TYPE, UCASE, UNTIL, WHILE,
WRITE, WRITEFILE
```

`END` is reserved as the interactive end-of-block marker and is not a
language keyword.

### assignment

```pseudo
x ← 5
name ← "alice"
count ← count + 1
```

### comments

Single-line comments use `//`:

```pseudo
// this is a comment
```

### strings

Strings are delimited by double quotes. Straight and curly double quotes are
accepted:

```pseudo
PRINT "hello world"
message ← "enter your name: "
```

### types

```pseudo
DECLARE x : INTEGER
DECLARE name : STRING
DECLARE is_valid : BOOLEAN
DECLARE price : REAL
DECLARE ch : CHAR
DECLARE today : DATE
```

### operators

- arithmetic: `+`, `-`, `*`, `/`, `DIV`, `MOD`
- comparison: `=`, `<>`, `<`, `>`, `<=`, `>=`
- logical: `AND`, `OR`, `NOT`

### syntax highlighting

| element | colour |
|---------|--------|
| keywords | bold purple |
| strings | red |
| calls / procedures | bold purple |
| members (after `.`) | blue |
| indices (after `.`) | dark blue |
| comments | grey |

Procedure, function, class and type names are found from declarations and from
`CALL`, `NEW` and `INHERITS`, rather than from capitalisation. Tabs are
rendered as RTF tab stops; non-BMP Unicode is encoded as surrogate pairs.
Unrecognised characters and malformed input produce diagnostics instead of
silently corrupting the output.

## example

Input:

```pseudo
// calculate factorial
DECLARE n : INTEGER
DECLARE result : INTEGER

INPUT n
result ← 1
FOR i ← 1 TO n
    result ← result * i
NEXT i

OUTPUT result
```

## development

Run the regression suite with either:

```bash
python3 -m unittest discover -s tests -v
# or
pytest
```

Linting, type checking and CI configuration are in `pyproject.toml` and
`.github/workflows/ci.yml`.
