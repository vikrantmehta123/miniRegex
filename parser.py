from matcher import *

"""
The parser will use recursive descent parsing algorithm to parse a regex pattern.

We allow a simplified regex grammar, which is slightly restrictive than the original grammar. 
"""
class Parser:
    
    def __init__(self, pattern:str):
        """
        Initialise the parser with the pattern string.
        
        Args:
            pattern: The regex pattern string to parse
        """

        self.pattern = pattern
        self.pos = 0 # Current parsing position in the pattern i.e. next char to consume
        self.length = len(pattern)

    def peek(self, offset=0):
        """
        "peek" a character without consuming it.

        Args:
            offset: How many characters ahead to look (default 0 = current char)
            
        Returns:
            The character at pos + offset, or None if past the pattern end.
        """

        index = self.pos + offset

        if index < self.length:
            return self.pattern[index]
        return None

    def consume(self):
        """
        Consume and return the current character, and advance the "pos" pointer.

        Returns:
            The current character, or None if at end
        """

        if self.pos < self.length:
            char = self.pattern[self.pos]
            self.pos += 1
            return char
        
        return None

    def expect(self, expected):
        """
        Consume a character and verify it matches what we expected.

        Args:
            expected: the character we expect to see

        Raises:
            SyntaxError if the character doesn't match
        """

        char = self.consume()

        if char != expected:
            raise SyntaxError(f"Expected '{expected}' at position {self.pos-1}, got '{char}'")

    def parse(self):
        """
        Entry point: parse the entire regex pattern

        Returns:
            an AST node representing parsed regex
        """

        # Grammar Rule: regex → alternation
        ast = self.parse_alternation()
        
        # Verify that we have consumed the entire pattern
        if self.pos < self.length:
            raise SyntaxError(f"Unexpected character at position {self.pos}: '{self.peek()}'")

        return ast
        
    def parse_alternation(self):
        """
        Parse an alternation expression.
        Grammar Rule: alternation → concatenation ('|' concatenation)*
        
        An alternation represents choice between alternatives like 'cat|dog|bird'. Each alternative is a concatenation.

        We parse the first concatenation, then check for '|' symbol and parse the additional alternatives if present.

        Returns:
            An AST node (either a single concatenation or an Alternation node)
        """

        # Parse the first alternative
        alternatives = [self.parse_concatenation()]

        # Look for additional alternatives separated by '|'
        while self.peek() == '|':
            self.consume() # consume the '|' character
            alternatives.append(self.parse_concatenation())

        # If there is only one alternative, return it directly
        if len(alternatives) == 1:
            return alternatives[0]

        # More than one alternatives, return the Alternation node
        return Alternation(alternatives)

    def parse_concatenation(self):
        """
        Parse a concatenation expression.
        Grammar Rule: concatenation → quantified*
        
        A concatenation is a sequence of quantified atoms that must match in order,
        such as 'abc' or 'a+b*c'. We keep parsing quantified expressions until we hit
        something that isn't one (like '|', ')', or end of input).

        Returns:
            An ASTNode (either a single quantified or a Concatenation node)
        """
        items = [ ]
        
        # Keep parsing quantified items until we can't anymore
        while self.pos < self.length:
            # Check if we're at a character that 'ends' a concatenation like '|' or ')'.
            char = self.peek()
            if char in ('|', ')'): 
                break

            items.append(self.parse_quantified())

        # If we have no items, then the concatenation is Empty (matches empty string)
        if len(items) == 0:
            return Empty()

        # If we have exactly one item, return it directly as ASTNode
        if len(items) == 1:
            return items[0]

        # Multiple items: return as a Concatenation node
        return Concatenation(items)


    def parse_quantified(self):
        """
        Parse a quantified expression (atom with optional quantifier).
        Grammer Rule: quantified → atom quantifier?
        
        First parse an atom, then check if it is followed by a quantifier. 
        If there is a quantifier, we wrap the atom in a Quantifier node that specifies
        how many times the atom should repeat. If there's no quantifier, we just return
        the atom as is.

        Returns:
            ASTNode (either the atom itself or a Quantified node wrapping the atom)
        """
        
        # Parse the atom first
        atom = self.parse_atom()
        
        # Check if there is a quantifier following the atom
        char = self.peek()
        if char == '*':
            # Zero or more repetitions
            self.consume() # consume the '*'
            
            # Check if is lazy or greedy
            greedy = not (self.peek() == '?')
            
            if not greedy:
                self.consume() # consume the '?'
            
            return Quantifier(atom, min_count=0, max_count=None, greedy=greedy)
        
        elif char == '+':
            # One or more repetitions
            self.consume() # consume the '+'
           
            greedy = not (self.peek() == '?')
            if not greedy:
                self.consume()

            return Quantifier(atom, min_count=1, max_count=None, greedy=greedy)

        elif char == '?':
            # Zero or One repetitions
            self.consume() # consume the '?'

            greedy = not (self.peek() == '?')
            if not greedy:
                self.consume()

            return Quantifier(atom, min_count=0, max_count=1, greedy=greedy)

        elif char == '{':
            # Explicit count quantifier like {n}, {n, } or {n, m}
            return self.parse_counted_quantifier(atom)

        # No quantifier found. Just return the atom
        return atom
    
    def parse_counted_quantifier(self, atom):
        """
        Parse a counted quantifier like {3}, {2,5}, or {1,}.
        
        This is called when we've already parsed an atom and found a '{' character.
        We need to parse the numbers inside the braces and figure out the min/max counts.
        
        Args:
            atom: The ASTNode that this quantifier applies to
        
        Returns:
            A Quantifier node with the appropriate min/max counts
        """

        self.expect('{') # consume the opening brace
        
        # Parse the first number. This is always required
        min_count = self.parse_number()

        # Check what comes next
        if self.peek() == '}':
            # Exact count like {n}
            self.consume() # consume the closing brace
            max_count = min_count

        elif self.peek() == ',':
            # Range: either {n, } or {n, m}
            self.consume() # consume the comma

            if self.peek() == '}':
                # open-ended range like {n, }
                self.consume()
                max_count = None
            else:
                # Closed range like {n, m}
                max_count = self.parse_number()
                self.expect('}') # Consume the closing brace

        else:
            raise SyntaxError(f"Expected '}}' or ',' at position {self.pos}")

        # Check for lazy modifier like {n, m}?
        greedy = not (self.peek() == '?')
        if not greedy:
            self.consume()

        return Quantifier(atom, min_count=min_count, max_count=max_count, greedy=greedy)

    def parse_atom(self):
        """
        Parse an atomic expression.
        Grammar Rule: atom → character | '.' | character-class | group | anchor | escape-sequence
        
        An atom is the fundamental building block of a regex. We look at the current
        character to determine which type of atom we're parsing, as each of the above
        substitutions have a unique starting character. Then we dispatch to the 
        appropriate handler function.

        Returns:
            An ASTNode representing the atom.
        """

        char = self.peek()
        
        if char is None:
            raise SyntaxError(f"Unexpected end of pattern at position {self.pos}")

        if char == '.':
            # The dot metacharacter
            self.consume()
            return Dot()

        elif char == '[':
            # Character class like [abc] or [^0-9]
            return self.parse_character_class()

        elif char == '(':
            # Group (capturing, non-capturing, or named)
            return self.parse_group()

        elif char == '^':
            # Start of the line anchor
            self.consume()
            return Anchor('start')

        elif char == '$':
            # end of the line anchor
            self.consume()
            return Anchor('end')

        elif char == '\\':
            # escape sequence 
            return self.parse_escape_sequence()

        elif char in ('*', '+', '?', '{', '|', ')'):
            # metacharacters. Shouldn't have occurred without escape character
            raise SyntaxError(f"Unexpected metacharacter '{char}' at position {self.pos}")

        else:
            # regular literal character
            self.consume()
            return Character(char)


    def parse_number(self):
        """
        Parse a sequence of digits as an integer.
        
        This function reads consecutive digit characters and converts them into
        an integer. It is used primarily for parsing quantifier counts like {3}
        or {2,5}.
        
        Returns:
            An integer value
        
        Raises:
            SyntaxError if no digits are found
        """
        
        start_pos = self.pos
        digits = []
        
        # Keep consuming digits until we hit a non-digit character
        while self.peek() and self.peek().isdigit():
            digits.append(self.consume())
        
        # Make sure we actually found at least one digit
        if len(digits) == 0:
            raise SyntaxError(f"Expected a number at position {start_pos}")
        
        # Convert the digit characters into an integer and return it
        return int(''.join(digits))

    def parse_character_class(self):
        """
        Parse a character class like [abc] or [^0-9] or [a-zA-Z0-9]
        Grammar Rule: character-class → '[' '^'? class-item+ ']'

        Character classes match any single character from a set. The set can be
        specified as individual characters like [abc], ranges like [a-z], or a mix of both.

        A leading caret negates the class, matching anything NOT in the set.

        Returns:
            A CharacterClass node containing the items and negation flag
        """ 

        self.expect('[') # consume the opening bracket

        # Check for negation i.e. the leading caret symbol
        negated = False
        if self.peek() == '^':
            negated = True
            self.consume()

        # Parse the items inside the character class
        items = [ ]

        # Special case: if the first character is a closing bracket, it's treated as
        # a literal closing bracket character, not the end of the class. This allows
        # patterns like []abc] where the first ] is part of the class content.
        if self.peek() == ']':
            items.append(self.consume())


        # Keep parsing items until we hit the closing bracket
        while self.peek() and self.peek() != ']':
            items.append(self.parse_class_item())

        if len(items) == 0:
            raise SyntaxError(f"Empty character class at position {self.pos}")

        self.expect(']') # Consume the closing bracket

        return CharacterClass(items, negated=negated)

    def parse_class_item(self):
        """
        Parse a single item within a character class.
        Grammar Rule: class-item → class-character | class-character '-' class-character | escape-sequence

        An item inside a character class can be one of three things. It can be a single
        character like 'a'. It can be a range like 'a-z' which represents all characters
        from 'a' to 'z' inclusive. Or it can be an escape sequence like '\n' or '\d'.

        Returns:
            Either a single character string, a tuple ('range', start, end) for a range, 
            or a tuple ('escape', char) for escape sequences.
        """

        # Check if this is an escape sequence
        if self.peek() == '\\':
            return self.parse_escape_sequence_in_class()

        first_char = self.consume()
        if first_char is None:
            raise SyntaxError(f"Unexpected end of character class at position {self.pos}")

        # Check if this is a range by looking for a hyphen followed by another character.
        # We need to make sure the hyphen isn't at the end of the class i.e. before ']'
        if self.peek() == '-' and self.peek(1) and self.peek(1) != ']':
            self.consume() # consume the hyphen
            
            # Parse the end character of the range
            if self.peek() == '\\':
                end_char = self.parse_escape_sequence_in_class()

            else:
                end_char = self.consume()

            return ('range', first_char, end_char)

        # Just a single char, not a range
        return first_char

    def parse_escape_sequence_in_class(self):
        """
        Pare an escape sequence inside a character class.

        Inside character classes, escape sequences work slightly differently than they
        do in regular regex context. Most character class escape sequences like \d or \w
        represent sets of characters rather than single characters. Some escapes like \n
        represent single special characters.

        Returns:
            A tuple ('escape', char) representing the escape sequence type and value
        """

        self.expect('\\')
        char = self.consume()
        
        if char is None:
            raise SyntaxError(f"Unexpected end after backslash at position {self.pos}")
        
        # Return a tuple that marks this as an escape sequence. The actual interpretation
        # of what characters this represents will happen later during the matching phase.
        return ('escape', char)

    def parse_group(self):
        """
        Parse a group: capturing (), non-capturing (?:), or named (?<name>).
        Grammar Rule: group → '(' regex ')' | '(?:' regex ')' | '(?<' group-name '>' regex ')'

        Capturing groups with plain parentheses remember what they matched for later use or backreferences. Non-capturing groups provide grouping for alternation or quantification without the overhead of capturing. Named groups allow referencing captures by name instead of a number.

        Returns:
            A Group node with appropriate capturing and naming information.
        """

        self.expect('(')

        # check if this is a non-capturing or named group
        if self.peek() == '?':
            self.consume() # consume the question mark

            if self.peek() == ':':
                # Non-capturing group: (?:....)
                self.consume()

                inner = self.parse_alternation()
                self.expect(')')
                return Group(inner, name=None, capturing=False)
            elif self.peek() == '<':
                # Named group: (?<name>....)
                self.consume() # consume the less than symbol.

                name = self.parse_group_name()
                self.expect('>') # Expect and consume the end of name symbol i.e. '>'

                inner = self.parse_alternation()
                self.expect(')')

                return Group(inner, name=name, capturing=True)
            else:
                raise SyntaxError(f"Invalid group syntax at position {self.pos}")
        

        # Regular capturing group: (...)
        inner = self.parse_alternation()
        self.expect(')')
        return Group(inner, name=None, capturing=True)

    def parse_group_name(self):
        """
        Parse a group name for named capture groups.
        Grammar Rule: group-name → identifier-start identifier-continue*
        
        Group names follow typical identifier rules. They must start with a letter or
        underscore, and can contain letters, digits, and underscores in the rest of
        the name.
        
        Returns:
            The group name as a string
        """

        name_chars = [ ]

        # first character must be a letter or an underscore
        first = self.peek()
        if not first or not (first.isalpha() or first == '_'):
            raise SyntaxError(f"Group name must start with a letter or an underscore at position {self.pos}")

        name_chars.append(self.consume())

        # remaining characters can be digits, letters, or underscores
        while self.peek() and (self.peek().isalnum() or self.peek() == '_'):
            name_chars.append(self.consume())

        return "".join(name_chars)

    def parse_escape_sequence(self):
        """
        Parse an escape sequence like \n, \d, \w, \b, etc.
        Grammar Rule: escape-sequence → '\' metacharacter | '\n' | '\r' | '\t' | '\\' | 
                                       '\d' | '\D' | '\w' | '\W' | '\s' | '\S'

        Sometimes a backslash makes
        a special character literal, like \* for an actual asterisk. Other times it creates
        special meaning for regular characters, like \d for any digit or \n for newline.
        Word boundary anchors like \b also use the backslash syntax but match positions
        rather than characters.
        
        Returns:
            An appropriate ASTNode based on the escape sequence type
        """

        self.expect('\\') # Consume the backslash
        char = self.consume()
        
        if char is None:
            raise SyntaxError(f"Unexpected end of pattern after backslash at position {self.pos}")

        # Handle special character escapes that represent single characters
        if char == 'n':
            return Character('\n') # newline
        elif char == 'r':
            return Character('\r') # carriage return
        elif char == 't':
            return Character('\t') # tab
        elif char == '\\':
            return Character('\\') # literal backslash
        
        # Handle character class shortcuts which represent sets of characters
        elif char in ('d', 'D', 'w', 'W', 's', 'S'):
            # \d matches digits [0-9], \D matches non-digits
            # \w matches word characters [a-zA-Z0-9_], \W matches non-word characters
            # \s matches whitespace, \S matches non-whitespace
            return CharacterClass([('escape', char)], negated=False)

        elif char == 'b':
            return Anchor('word') # word boundary

        elif char == 'B':
            return Anchor('non-word') # Non-word boundary

        # Handle escaped metacharacters to make them literal
        elif char in ('.', '*', '+', '?', '|', '(', ')', '[', ']', '{', '}', '^', '$'):
            return Character(char) # treat as literal character
        
        else:
            # For any other character after backslash, treat it as literal.
            # This is a permissive approach. Some regex engines would throw an error here.
            return Character(char)
    
    def matcher(self, input_string):
        """
        Create a Matcher for the pattern.

        Args:
            input_string: the text to match against

        Returns:
            A Matcher object ready to perform matching
        """
        
        ast = self.parse()
        return Matcher(ast, input_string)

def test_parser():
    """Test our parser with a comprehensive set of examples."""
    
    print("=== Basic Tests ===")
    
    p1 = Parser("a")
    ast1 = p1.parse()
    print("Test 1 - 'a':", ast1)
    
    p2 = Parser("abc")
    ast2 = p2.parse()
    print("\nTest 2 - 'abc':", ast2)
    
    p3 = Parser("a|b")
    ast3 = p3.parse()
    print("\nTest 3 - 'a|b':", ast3)
    
    print("\n=== Quantifier Tests ===")
    
    p4 = Parser("a*")
    ast4 = p4.parse()
    print("Test 4 - 'a*':", ast4)
    
    p5 = Parser("a*?")
    ast5 = p5.parse()
    print("\nTest 5 - 'a*?':", ast5)
    
    p6 = Parser("a{3}")
    ast6 = p6.parse()
    print("\nTest 6 - 'a{3}':", ast6)
    
    p7 = Parser("a{2,5}")
    ast7 = p7.parse()
    print("\nTest 7 - 'a{2,5}':", ast7)
    
    print("\n=== Character Class Tests ===")
    
    p8 = Parser("[abc]")
    ast8 = p8.parse()
    print("Test 8 - '[abc]':", ast8)
    
    p9 = Parser("[a-z]")
    ast9 = p9.parse()
    print("\nTest 9 - '[a-z]':", ast9)
    
    p10 = Parser("[^0-9]")
    ast10 = p10.parse()
    print("\nTest 10 - '[^0-9]':", ast10)
    
    print("\n=== Group Tests ===")
    
    p11 = Parser("(abc)")
    ast11 = p11.parse()
    print("Test 11 - '(abc)':", ast11)
    
    p12 = Parser("(?:abc)")
    ast12 = p12.parse()
    print("\nTest 12 - '(?:abc)':", ast12)
    
    p13 = Parser("(?<name>abc)")
    ast13 = p13.parse()
    print("\nTest 13 - '(?<name>abc)':", ast13)
    
    print("\n=== Escape Sequence Tests ===")
    
    p14 = Parser("\\d+")
    ast14 = p14.parse()
    print("Test 14 - '\\d+':", ast14)
    
    p15 = Parser("\\bword\\b")
    ast15 = p15.parse()
    print("\nTest 15 - '\\bword\\b':", ast15)
    
    p16 = Parser("\\*\\+\\?")
    ast16 = p16.parse()
    print("\nTest 16 - '\\*\\+\\?':", ast16)
    
    print("\n=== Complex Pattern Tests ===")
    
    p17 = Parser("[a-z]+@[a-z]+\\.[a-z]+")
    ast17 = p17.parse()
    print("Test 17 - '[a-z]+@[a-z]+\\.[a-z]+':", ast17)
    
    p18 = Parser("(cat|dog)s?")
    ast18 = p18.parse()
    print("\nTest 18 - '(cat|dog)s?':", ast18)
    
    p19 = Parser("((a|b)+c)")
    ast19 = p19.parse()
    print("\nTest 19 - '((a|b)+c)':", ast19)


if __name__ == "__main__":
    test_parser()
