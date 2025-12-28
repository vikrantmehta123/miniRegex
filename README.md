# miniRegex: A Regular Expression Engine from Scratch

A complete regex engine implementation in Python featuring a recursive descent parser, Abstract Syntax Tree (AST) representation, and a backtracking matcher with support for advanced regex features.

## Project Overview

This project implements a fully functional regular expression engine without relying on Python's built-in `re` module. It demonstrates:

- **Parsing & Backtracking**: Recursive descent parsing and backtracking search
- **Pattern Matching**: Support for quantifiers, character classes, groups, and anchors

## Features

### Supported Regex Syntax

| Feature | Syntax | Description | Example |
|---------|--------|-------------|---------|
| **Literals** | `abc` | Match exact characters | `hello` matches "hello" |
| **Alternation** | `a\|b` | Match either pattern | `cat\|dog` matches "cat" or "dog" |
| **Quantifiers** | `*`, `+`, `?`, `{n,m}` | Repetition control | `a+` matches "a", "aa", "aaa"... |
| **Lazy Quantifiers** | `*?`, `+?`, `??`, `{n,m}?` | Non-greedy matching | `a*?` matches as few 'a's as possible |
| **Character Classes** | `[abc]`, `[a-z]` | Match any character in set | `[0-9]` matches any digit |
| **Negated Classes** | `[^abc]` | Match any character NOT in set | `[^0-9]` matches non-digits |
| **Dot Metacharacter** | `.` | Match any character except newline | `a.c` matches "abc", "a1c" |
| **Character Escapes** | `\d`, `\w`, `\s` | Predefined character classes | `\d+` matches one or more digits |
| **Anchors** | `^`, `$`, `\b`, `\B` | Position assertions | `^\w+` matches word at start |
| **Groups** | `(...)` | Capturing groups | `(ab)+` captures repeated "ab" |
| **Non-capturing** | `(?:...)` | Group without capture | `(?:ab)+` groups but doesn't capture |
| **Named Groups** | `(?<name>...)` | Named capture groups | `(?<year>\d{4})` captures as "year" |

### Character Class Shortcuts

- `\d` - Digits `[0-9]`
- `\D` - Non-digits `[^0-9]`
- `\w` - Word characters `[a-zA-Z0-9_]`
- `\W` - Non-word characters
- `\s` - Whitespace characters
- `\S` - Non-whitespace characters

### Escape Sequences

- `\n` - Newline
- `\r` - Carriage return
- `\t` - Tab
- `\\` - Literal backslash
- `\.`, `\*`, `\+`, etc. - Escaped metacharacters

### Optimization:

- Boyer-Moore String matching algorithm to perform fast string matching on long, literal sequence

## Architecture

The architecture is similar to the `java.util.regex` regex engine.

### 1. Parser (`parser.py`)

The parser implements a **recursive descent parsing algorithm** that converts a regex pattern string into an Abstract Syntax Tree (AST).

**The Complete Grammar Structure:**
```
regex           → alternation
alternation     → concatenation ('|' concatenation)*
concatenation   → quantified*
quantified      → atom quantifier?
quantifier      → ('*' | '+' | '?') '?'? | '{' number '}' '?'? | '{' number ',' '}' '?'? | '{' number ',' number '}' '?'?
atom            → character | '.' | character-class | group | anchor | escape-sequence
```

### 2. AST Nodes (`matcher.py`)

The AST represents the parsed regex pattern in a tree structure:

```python
ASTNode (base class)
├── Character       # Literal character
├── Empty           # ε (epsilon) - matches empty string
├── Concatenation   # Sequence: abc
├── Alternation     # Choice: a|b|c
├── Quantifier      # Repetition: a*, a+, a{n,m}
├── Dot             # Wildcard: .
├── CharacterClass  # Set: [abc], [a-z], [^0-9]
├── Group           # Grouping: (...), (?:...), (?<name>...)
└── Anchor          # Positions: ^, $, \b, \B
```

### 3. Matcher (`matcher.py`)

The matcher uses a **backtracking algorithm** with generators to find matches.

**Key Algorithm Features:**
- **Generator-based backtracking**: Each matching function is a generator that yields all possible match positions
- **Greedy vs. Lazy quantifiers**: Controls the order of backtracking attempts
- **Capture group tracking**: Records matched text for groups


## Usage

### Basic Pattern Matching

```python
from parser import Parser

# Create parser and matcher
parser = Parser("hello|world")
matcher = parser.matcher("hello")

# Check for match
if matcher.match():
    print("Pattern matched!")
```

### Complex Patterns

```python
# Email-like pattern
parser = Parser(r"[a-zA-Z0-9]+@[a-zA-Z]+\.[a-z]+")
matcher = parser.matcher("user@example.com")
print(matcher.match())  # True

# Phone number pattern
parser = Parser(r"\d{3}-\d{3}-\d{4}")
matcher = parser.matcher("123-456-7890")
print(matcher.match())  # True

# URL pattern with groups
parser = Parser(r"(https?)://([a-z.]+)")
matcher = parser.matcher("https://example.com")
if matcher.match():
    print(f"Groups: {matcher.groups}")
```

### Quantifier Examples

```python
# Greedy matching
parser = Parser("a*a")
matcher = parser.matcher("aaaa")
print(matcher.match())  # True - matches all 'a's

# Lazy matching
parser = Parser("a*?a")
matcher = parser.matcher("aaaa")
print(matcher.match())  # True - matches minimally

# Counted repetitions
parser = Parser("a{2,4}")
matcher = parser.matcher("aaa")
print(matcher.match())  # True
```

## Limitations

- **Performance**: Not optimized for production use (no NFA/DFA compilation)
- **Features**: Limited compared to PCRE (no lookahead/lookbehind, backreferences)
- **Unicode**: Basic ASCII support (can be extended for full Unicode)

## Future Enhancements

1. **Optimization**:
   - NFA/DFA compilation for linear-time matching
   - Memoization to avoid redundant computations

2. **Advanced Features**:
   - Lookahead/lookbehind assertions
   - Backreferences (\1, \2, etc.)
   - Atomic groups and possessive quantifiers

3. **Tooling**:
   - Interactive regex debugger with step-by-step visualization
   - Performance benchmarking suite

## References

- **Compilers Course, By Suresh Purini**: [Link](https://www.youtube.com/playlist?list=PLde1J4XOn2z0i6fc39dI6OWjEoNuaFglI)
- **Java's Regex Engine**: [Link](https://github.com/openjdk/jdk/blob/master/src/java.base/share/classes/java/util/regex/Pattern.java)

## Author

Vikrant Mehta - vikrantmehta123@gmail.com

---

**Note**: This is an educational project demonstrating compiler construction and algorithm implementation. For production regex needs, use Python's built-in `re` module.
