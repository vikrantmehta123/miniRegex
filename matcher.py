# region ASTNode classes

class ASTNode:
    """Base class for all AST nodes"""

    def __repr__(self):
        """Provide a readable string representation for debugging."""
        
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"

class Character(ASTNode):
    """Represents a single literal character"""

    def __init__(self, val):
        self.value = val

class Empty(ASTNode):
    """Represents an empty match (matches the empty string)"""
    pass

class Concatenation(ASTNode):
    """Represents a sequence of regex items that must match in order."""
    
    def __init__(self, items):
        self.items = items # List of ASTNode objects

class Alternation(ASTNode):
    """Represents a choice between multiple alternatives i.e. '|' operator in regex."""
    
    def __init__(self, alternatives):
        self.alternatives = alternatives

class Quantifier(ASTNode):
    """Represents a quantified expression (atom with repetition)."""

    def __init__(self, atom, min_count, max_count, greedy=True):
        self.atom = atom
        self.min_count = min_count # minimum repetitions. Eg. 0 for *, 1 for +.
        self.max_count = max_count # None if unlimited
        self.greedy = greedy # Set to False for lazy quantifiers like *?

class Dot(ASTNode):
    """Represents the dot metacharacter (matches any character except newline)."""
    pass

class CharacterClass(ASTNode):
    """Represents a character class like [abc] or [^0-9]."""

    def __init__(self, items, negated=False):
        self.items = items
        self.negated = negated

class Group(ASTNode):
    """Represents a capturing or non-capturing group."""

    def __init__(self, regex, name=None, capturing=None):
        self.regex = regex # The grammar has recursive structure. The ASTNode inside the group.
        self.name = name # Group name for named captures, else None
        self.capturing = capturing # False for non-capturing groups


class Anchor(ASTNode):
    """Reprsents an anchor (^, $, \\b, \B)"""

    def __init__(self, anchor_type):
        self.anchor_type = anchor_type  # One of: 'start', 'end', 'word', 'non-word'


# endregion -------------------------------------------------------------------------------------------------


class Matcher:
    """
    Matches a compiled regex pattern (AST) against an input string.
    """

    def __init__(self, ast, input_string):
        """
        Initialize the matcher with a compiled pattern and input string
        
        Args:
            ast: the parsed AST from MiniRegex.parse()
            input_string: the text to match against.
        """

        self.ast = ast
        self.input = input_string
        self.length = len(input_string)
        
        self.match_start = None
        self.match_end = None
        self.matched = False

        self.groups = [ ]

    def match(self):
        """
        Try to match the pattern against the entire input string.
        """

        # try to match the AST starting from position 0
        # match_node returns the ending position if successful, or None if it fails
        end_pos = self.match_node(self.ast, 0)

        # We return True only if the pattern entirely matches the input_string
        # Later if required, we can look at partial matching, etc.
        if end_pos is not None and end_pos == self.length:
            return True
        else:
            return False

    def match_node(self, node, pos):
        """
        Match an AST node at a given position in the input

        This function mostly acts as a dispatcher, which routes to the 'match'
        functions of the appropriate AST Node type.

        Args:
            node: an ASTNode instance to match against the input
            pos: The position in the input string to start matching from

        Returns:
            The position after successfully matching the input_string, or None if no match
        """

        # Basic sanity check
        if pos > self.length:
            # we are past the end- only Empty node can match here
            if isinstance(node, Empty):
                return pos
            return None

        # Dispatch to appropriate matching functions
        if isinstance(node, Character):
            # A literal character like 'a'
            return self.match_character(node, pos)
        
        elif isinstance(node, Empty):
            # An empty match - always succeeds without consuming input
            return self.match_empty(node, pos)

        elif isinstance(node, Concatenation):
            # a sequence like "abc" that must match in order
            return self.match_concatenation(node, pos)

        elif isinstance(node, Alternation):
            # An alternation like "a|b|c"
            return self.match_alternation(node, pos)

        elif isinstance(node, Quantifier):
            # an atom like a+, a*, a{2,5} etc.
            return self.match_quantifier(node, pos)

        elif isinstance(node, Dot):
            # the dot metacharacter that matches everything except newline
            return self.match_dot(node, pos)

        elif isinstance(node, CharacterClass):
            # A character class like [abc] or [^0-9]
            return self.match_character_class(node, pos)

        elif isinstance(node, Group):
            # A capturing, named, or non-capturing group
            return self.match_group(node, pos)

        elif isinstance(node, Anchor):
            # An anchor like ^ or $ or \b
            return self.match_anchor(node, pos)

        else:
            # There is a new AST type for which we haven't written the match function
            raise ValueError(f"Unknown AST node type: {type(node).__name__}")


    def match_character(self, node: Character, pos):
        """
        Match a literal character

        Args:
            node: the ASTNode of type Character
            pos: the idx in the string
        
        Returns:
            pos + 1 if the character matches, or None if it doesn't / we're past the input
        """

        if pos >= self.length:
            return None

        # Check if the character is matching or not
        if self.input[pos] == node.value:
            # pos + 1 because we have consumed one character and we need to move forward
            return pos + 1

        return None

    def match_empty(self, node: Empty, pos):
        """
        Match an Empty node

        Empty nodes are special - they represent matching the empty string,
        which means they always succeed without consuming any input. This is
        like an epsilon transition in finite automata.
        
        Args:
            node: an Empty node
            pos: the current position in the input

        Returns:
            the same position (Empty match always succeeds)
        """

        return pos

    def match_concatenation(self, node: Concatenation, pos):
        """
        Match a sequence of items in order

        We start with the current position and try to match the first item. If that
        succeeds, it gives us a new position. We then try to match the second item 
        starting from the new position. This continues till either we've successfully
        matched all items ( success ) or one of the items fails to match.

        Args:
            node: A Concatenation node
            pos: the current position in the input string

        Returns:
            the final position after matching all the items, or None if failure
        """

        current_pos = pos

        # Iterate over the items and try to match each one of them
        for item in node.items:
            new_pos = self.match_node(item, current_pos)

            # Check if the item matched successfully
            if new_pos is None:
                # The match failed. One item's failed match means entire Concatenation
                # fails the match. So return None
                return None

            current_pos = new_pos
        
        # the match succeeded, so return the final position after matching all items
        return current_pos

    def match_alternation(self, node: Alternation, pos):
        """
        Matches the Alternation node

        Alternation node represents pattern like "a|b|c". In our algorithm, we first
        try to match the first alternative. If that succeeds, we return the pos. Else
        we try to match the next alternative, till either we succeed or we run out of
        alternatives.

        Args:
            node: An Alternation node
            pos: the current position in the input string

        Returns:
            the position after matching the first successful alternative, or None
            if all the alternatives fail
        """

        for alternative in node.alternatives:
            result_pos = self.match_node(alternative, pos)

            # Check if the match succeeded.
            if result_pos is not None:
                return result_pos

        return None

    def match_dot(self, node: Dot, pos):
        """
        Matches a Dot node.

        Dot node matches any character except newline. Very similar implementation
        as match_character.
        
        Args:
            node: A Dot node (we don't actually need to examine it)
            pos: Current position in the input string
    
        Returns:
            pos + 1 if there's a non-newline character to match, None otherwise
        """

        # Sanity check: Is there input string still to be consumed?
        if pos >= self.length:
            return None

        char = self.input[pos]

        # If char is a newline, match fails.
        if char == '\n':
            return None
        
        # if the char is not a newline, we match one character successfully. Advance pos 
        return pos + 1

    def match_character_class(self, node:CharacterClass, pos):
        """
        Matches a CharacterClass like [a-z] or [^0-9]

        To match a character class, we need to check if the char at input[pos] is 
        in the set defined by the character class or not. The set is defined by
        multiple "items". Note that a character class
        matches one single character. Hence, if match is successful, we return pos + 1.
        If match fails, we return None.

        Args:
            node: the CharacterClass node
            pos: the current position in the input
        
        Returns:
            pos + 1 if successful match, None otherwise.
        """
        # Sanity check
        if pos >= self.length:
            return None
        
        char = self.input[pos]

        # Iterate over the items of the character class and check if the char
        # belongs to the set defined by any of the items
        char_in_class = False
        
        for item in node.items:
            # Each item can be either a plain char, escape sequence, or a range


            if isinstance(item, str):
                # Plain character: just check for equality 
                if char == item:
                    char_in_class = True
                    break

            elif isinstance(item, tuple):
                if item[0] == 'range':
                    # range like a-z: check if the char falls in the unicode range
                    start_char = item[1]
                    end_char = item[2]

                    if ord(start_char) <= ord(char) <= ord(end_char):
                        char_in_class = True
                        break

                elif item[0] == 'escape':
                    # escape sequence like \w, \s, etc.
                    escape_type = item[1] # e.g. 'w' in '\w'

                    matched = False
                    if escape_type == 'd':
                        matched = char.isdigit()
                    elif escape_type == 'D':
                        matched = not char.isdigit()
                    elif escape_type == 'w':
                        matched = char.isalnum() or char == '_'
                    elif escape_type == 'W':
                        matched = not( char.isalnum() or char == '_' )
                    elif escape_type == 's':
                        matched = char.isspace()
                    elif escape_type == 'S':
                        matched = not char.isspace()
                    else:
                        # For any other escape, treat as literal character
                        matched = char == escape_type

                    if matched:
                        char_in_class = True
                        break
        
        if node.negated:
            matches = not char_in_class
        else:
            matches = char_in_class

        if matches:
            return pos + 1
        else:
            return None

    def match_group(self, node:Group, pos):
        """
        Matches a group (capturing or non-capturing)

        Args:
            node: a Group node
            pos: current position in the input string

        Returns:
            the position after matching the inner pattern, or None if it fails
        """

        # The group is itself has a "regex" attribute, which is ASTNode.
        # Recursively match_node
        return self.match_node(node.regex, pos)

    def match_anchor(self, node:Anchor, pos):
        """
        Matches an Anchor node.

        Anchor nodes do NOT move the pos in the input string. They consume zero chars.
        They either validate that we are at the right position or fail.

        Args:
            node: the Anchor node
            pos: the current position in the input
        
        Returns:
            pos if the anchor validation is successful, otherwise None
        """

        if node.anchor_type == 'start':
            if pos == 0:
                return pos
            return None

        elif node.anchor_type == 'end':
            if pos == self.length:
                return pos
            return None

        elif node.anchor_type == 'word':
            # \b matches at a word boundary
            # a word boundary exists between a word character (\w) and a non-word char
            # or at the start / end of the string if next to a word.

            # Check what's before the current position
            before_is_word = False
            if pos > 0:
                before_char = self.input[pos - 1]
                before_is_word = before_char.isalnum() or before_char == '_'

            # Check what's after the current position
            after_is_word = False
            if pos < self.length:
                after_char = self.input[pos]
                after_is_word = after_char.isalnum() or after_char == '_'

            # Word boundary exists when one side is word char and the other isn't
            # That is, before_is_word and after_is_word shouldn't be same
            if before_is_word != after_is_word:
                return pos
            return None
        
        elif node.anchor_type == 'non-word':
            # \B matches where there is NOT a word boundary. i.e. opposite of \b

            # Check what's before the current position
            before_is_word = False
            if pos > 0:
                before_char = self.input[pos - 1]
                before_is_word = before_char.isalnum() or before_char == '_'

            # Check what's after the current position
            after_is_word = False
            if pos < self.length:
                after_char = self.input[pos]
                after_is_word = after_char.isalnum() or after_char == '_'

            # Word boundary doesn't exist when both sides are word char or
            # both sides aren't word chars
            # That is, before_is_word and after_is_word should be same
            if before_is_word == after_is_word:
                return pos
            return None
        else:
            raise ValueError(f"Unknown anchor type: {node.anchor_type}")


    def match_quantifier(self, node:Quantifier, pos):
        """
        Matches a quantified pattern like a*, a+, a*?, a{2, 5}, etc.

        
        """

        pass
