# pseudocode pretty print

i built this to convert cambridge-style pseudocode into nicely formatted rtf files with syntax highlighting. it's based on the pseudocode convention from cambridge international's syllabus - you can find the full guide [here](https://www.cambridgeinternational.org/Images/697401-2026-pseudocode-guide-for-teachers.pdf).

## how to run it

two ways to use it:

1. **interactive** - run `python3 main.py`, paste your code, then type `END` on its own line when you're done
2. **piped** - `python3 main.py < yourfile.txt`

output goes to the `outputs/` folder.

## what it supports

### keywords
all the usual cambridge ones:
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
uses the ← symbol:
```
x ← 5
name ← "alice"
count ← count + 1
```

### comments
single line with //:
```
// this is a comment
```

### strings
anything in double quotes:
```
PRINT "hello world"
message ← "enter your name: "
```

### types
when declaring variables:
```
DECLARE x : INTEGER
DECLARE name : STRING
DECLARE is_valid : BOOLEAN
DECLARE price : REAL
DECLARE ch : CHAR
DECLARE today : DATE
```

### operators
- arithmetic: +, -, *, /, DIV, MOD
- comparison: =, <>, <, >, <=, >=
- logical: AND, OR, NOT

### special identifiers
certain things get highlighted differently:
- **keywords** - bold purple
- **strings** - red
- **calls/procedures** - bold purple (anything after CALL, or starting with a capital, or followed by `(`)
- **members** - blue (anything after a dot, like `object.property`)
- **comments** - grey
- **indices** - dark blue (numbers after a dot, like `arr.0`)

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

this gets turned into a formatted rtf file with syntax highlighting.

that's pretty much it. hope it's useful!
