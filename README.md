# pseudocode pretty print

converts cambridge-style pseudocode to rtf with syntax highlighting. the pseudocode format follows the cambridge international syllabus - see the [full guide](https://www.cambridgeinternational.org/Images/697401-2026-pseudocode-guide-for-teachers.pdf) for reference.

the colour scheme is based on xcode's prettyprint style in light mode. apple's design guidelines are available [here](https://developer.apple.com/design/human-interface-guidelines/color).

## usage

run interactively:
```bash
python3 main.py
```
paste your pseudocode, then type `END` on its own line to finish.

or pipe input from a file:
```bash
python3 main.py < input.txt
```

output files are written to the `outputs/` folder.

rtf was chosen because it preserves syntax highlighting when pasted into microsoft word or apple pages.

## customising colours

colours are defined in `core/constants.py` in the `COLOURS` dictionary. each entry is (red, green, blue) in hex format, with inline comments indicating what each colour is used for.

## supported syntax

### keywords
```
IF, THEN, ELSE, ENDIF
FOR ... TO ... STEP ... NEXT
WHILE ... ENDWHILE
REPEAT ... UNTIL
CASE ... OF ... OTHERWISE ... ENDCASE
CALL
FUNCTION ... ENDFUNCTION
PROCEDURE ... ENDPROCEDURE
CLASS ... ENDCLASS
TYPE ... ENDTYPE
DECLARE
INPUT, OUTPUT, PRINT
OPENFILE, READFILE, WRITEFILE, CLOSEFILE
GETRECORD, PUTRECORD
RAND, RANDOM
RETURN
AND, OR, NOT
TRUE, FALSE
```

### assignment
```
x ← 5
name ← "alice"
count ← count + 1
```

### comments
single-line comments using `//`:
```
// this is a comment
```

### strings
delimited by double quotes:
```
PRINT "hello world"
message ← "enter your name: "
```

### types
```
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
| comments | grey |
| indices (after `.`) | dark blue |

## example

input:
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
