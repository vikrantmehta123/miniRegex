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

        # Store group captures as a list of tuples: (start_pos, end_pos, name)
        # The index in the list corresponds to the group_number.
        # For non-capturing groups, we don't add anything
        self.groups = [ ]

        # Counter to keep track of which group number we're at as we traverse the AST.
        self.group_counter = 0

    def match(self):
        """
        Try to match the pattern against the entire input string.
        """

        # try to match the AST starting from position 0
        for end_pos in self.match_node(self.ast, 0):

            # We only consider it a full match if we consumed the entire string
            if end_pos == self.length:
                return True
        
        # If we tried all possibilities and none consumed the entire string, we fail
        return False

    def match_node(self, node, pos):
        """
        Match an AST node at a given position in the input

        This function mostly acts as a dispatcher, which routes to the 'match'
        functions of the appropriate AST Node type.

        Args:
            node: an ASTNode instance to match against the input
            pos: The position in the input string to start matching from

        Yields:
            The position after successfully matching the input_string, or None if no match

        Important: If a node cannot match at all, this generator simply returns
        without yielding anything. The caller will see an empty iteration.
        """

        # Basic sanity check
        if pos > self.length:
            # we are past the end- only Empty node can match here
            if isinstance(node, Empty):
                yield pos
            return

        # Dispatch to appropriate matching functions
        if isinstance(node, Character):
            # A literal character like 'a'
            yield from self.match_character(node, pos)
        
        elif isinstance(node, Empty):
            # An empty match - always succeeds without consuming input
            yield from self.match_empty(node, pos)

        elif isinstance(node, Concatenation):
            # a sequence like "abc" that must match in order
            yield from self.match_concatenation(node, pos)

        elif isinstance(node, Alternation):
            # An alternation like "a|b|c"
            yield from self.match_alternation(node, pos)

        elif isinstance(node, Quantifier):
            # an atom like a+, a*, a{2,5} etc.
            yield from self.match_quantifier(node, pos)

        elif isinstance(node, Dot):
            # the dot metacharacter that matches everything except newline
            yield from self.match_dot(node, pos)

        elif isinstance(node, CharacterClass):
            # A character class like [abc] or [^0-9]
            yield from self.match_character_class(node, pos)

        elif isinstance(node, Group):
            # A capturing, named, or non-capturing group
            yield from self.match_group(node, pos)

        elif isinstance(node, Anchor):
            # An anchor like ^ or $ or \b
            yield from self.match_anchor(node, pos)

        else:
            # There is a new AST type for which we haven't written the match function
            raise ValueError(f"Unknown AST node type: {type(node).__name__}")


    def match_character(self, node: Character, pos):
        """
        Match a literal character

        Args:
            node: the ASTNode of type Character
            pos: the idx in the string
        
        Yields:
            pos + 1 if the character matches, or None if it doesn't / we're past the input
        """
        if pos >= self.length:
            return # Don't yield anything

        # Check if the character is matching or not
        if self.input[pos] == node.value:
            # pos + 1 because we have consumed one character and we need to move forward
            yield pos + 1

        # If the character doesn't match, we simply return without yielding.
        # The caller will see an empty iteration, which represents "no match found"

    def match_empty(self, node: Empty, pos):
        """
        Match an Empty node

        Empty nodes are special - they represent matching the empty string,
        which means they always succeed without consuming any input. This is
        like an epsilon transition in finite automata.
        
        Args:
            node: an Empty node
            pos: the current position in the input

        Yields:
            the same position (Empty match always succeeds)
        """

        yield pos

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

        Yields:
            the final position after matching all the items, or None if failure
        """
        # Base case: if there are no items to match, we succeed immediately
        # without consuming any input. This is like matching an empty string.
        if not node.items:
            yield pos
            return
        
        # Recursive case: we need to match the first item, then the rest
        first_item = node.items[0]
        remaining_items = node.items[1:]

        # Remember, match_node is a generator, so this loop will iterate through
        # all the different ways the first item can successfully match
        for pos_after_first in self.match_node(first_item, pos):
            # We've successfully matched the first item, and we're now at
            # pos_after_first. Now we need to see if we can match the remaining items
            # starting from this new position.
            
            # Special case: if there are no remaining items, we're done!
            # The first item was the last item, so we've matched the entire concatenation
            if not remaining_items:
                yield pos_after_first
            else:
                # There are more items to match. We create a temporary Concatenation
                # node for the remaining items and try to match it recursively.
                rest_concatenation = Concatenation(remaining_items)
                
                # Try to match the rest starting from pos_after_first
                # This is another generator, so we iterate over all the ways
                # the rest can match
                for final_pos in self.match_node(rest_concatenation, pos_after_first):
                    # Success! We found a way to match both the first item AND
                    # all the remaining items. This is a complete solution, so yield it.
                    yield final_pos
                
                # If the inner loop didn't yield anything, it means the remaining items
                # couldn't match starting from pos_after_first. That's okay! The outer
                # loop will automatically try the next way the first item can match.
                # This is backtracking in action - we don't need to explicitly say
                # "that didn't work, try again." The loop structure handles it for us.

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

        Yields:
            the position after matching the first successful alternative, or None
            if all the alternatives fail
        """

        for alternative in node.alternatives:
            for result_pos in self.match_node(alternative, pos):
                yield result_pos

        # If no alternatives matched, we simply return without yielding
        # We yield results from ALL alternatives that match, not just the first.
        # This is important for backtracking. If the first matching alternative
        # doesn't lead to a complete pattern match later on, the calling code can
        # try the results from other alternatives.

    def match_dot(self, node: Dot, pos):
        """
        Matches a Dot node.

        Dot node matches any character except newline. Very similar implementation
        as match_character.
        
        Args:
            node: A Dot node (we don't actually need to examine it)
            pos: Current position in the input string
    
        Yields:
            pos + 1 if there's a non-newline character to match, None otherwise
        """

        # Sanity check: Is there input string still to be consumed?
        if pos >= self.length:
            return

        char = self.input[pos]

        # If char is a newline, match fails.
        if char == '\n':
            return
        
        # if the char is not a newline, we match one character successfully. Advance pos 
        yield pos + 1

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
        
        Yields:
            pos + 1 if successful match, None otherwise.
        """
        # Sanity check
        if pos >= self.length:
            return
        
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
            yield pos + 1

    def match_group(self, node:Group, pos):
        """
        Matches a group (capturing or non-capturing)

        Args:
            node: a Group node
            pos: current position in the input string

        Yields:
            the position after matching the inner pattern, or None if it fails
        """

        # The group is itself has a "regex" attribute, which is ASTNode.
        # Recursively match_node

        # Non-capturing group stores nothing
        if node.capturing == False:
            yield from self.match_node(node.regex, pos)
        
        group_num = self.group_counter
        self.group_counter += 1

        # Try to match the inner regex
        for end_pos in self.match_node(node.regex, pos):

            # If the inner pattern matched successfully then capture the group
            capture = (pos, end_pos, node.name)

            # Make sure that the groups list is big enough to store the group
            while len(self.groups) <= group_num:
                self.groups.append(None)

            self.groups[group_num] = capture

            yield end_pos

            # Note: If backtracking occurs and this match doesn't lead to overall success,
            # the calling code will request the next match from this generator.
            # When we try a different match, we'll overwrite this capture with new values.
            # This is actually the behavior we want - only the final successful path
            # through the pattern should have its captures recorded.            

    def match_anchor(self, node:Anchor, pos):
        """
        Matches an Anchor node.

        Anchor nodes do NOT move the pos in the input string. They consume zero chars.
        They either validate that we are at the right position or fail.

        Args:
            node: the Anchor node
            pos: the current position in the input
        
        Yields:
            pos if the anchor validation is successful, otherwise None
        """

        if node.anchor_type == 'start':
            if pos == 0:
                yield pos

        elif node.anchor_type == 'end':
            if pos == self.length:
                yield pos

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
                yield pos
        
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
                yield pos
        else:
            raise ValueError(f"Unknown anchor type: {node.anchor_type}")

    def match_quantifier(self, node:Quantifier, pos):
        """
        Match a quantified expression with full backtracking support.
        
        Quantifiers are what make regex patterns truly powerful and flexible. They
        allow you to specify that something should repeat: zero or more times (*),
        one or more times (+), zero or one time (?), or a specific range of times
        like {2,5}. But here's the challenge: when a quantifier can match in multiple
        ways (say, matching 2, 3, or 4 times), which way should we choose?
        
        Quantifiers come in two flavors: greedy and lazy.
        - Greedy quantifiers (like a*, a+, a{2,5}) try to match as much as possible
          first, then backtrack to fewer matches if needed. They yield maximum matches
          first, then progressively fewer matches.
        - Lazy quantifiers (like a*?, a+?, a{2,5}?) try to match as little as possible
          first, then expand to more matches if needed. They yield minimum matches
          first, then progressively more matches.
        
        The algorithm has two phases:
        1. Discovery: Match the atom repeatedly to discover all valid repetition counts
        2. Yielding: Yield the positions in the order determined by greediness
        
        Args:
            node: a Quantifier node with atom, min_count, max_count, and greedy attributes
            pos: current position in the input string
        
        Yields:
            Positions after different numbers of successful matches of the atom,
            in an order determined by the greedy flag. For greedy quantifiers, yields
            positions from maximum matches down to minimum. For lazy quantifiers,
            yields positions from minimum matches up to maximum.
        """
        
        # Phase 1: Discovery - figure out all the ways we can match this quantifier
        # We'll try to match the atom repeatedly and record the position after each match
        
        # match_positions[i] is the position after matching the atom i times
        # We start with position after zero matches, which is just the current position
        match_positions = [pos]
        
        current_pos = pos
        match_count = 0
        
        # Keep trying to match the atom one more time until we can't anymore
        # or until we hit the maximum allowed repetitions
        while True:
            # Check if we've reached the maximum count (if there is one)
            # max_count can be None for unbounded quantifiers like * and +
            if node.max_count is not None and match_count >= node.max_count:
                # We've reached the limit, stop trying to match more
                break
            
            # Try to match the atom one more time starting from current_pos
            # Remember, match_node returns a generator that yields possible positions
            # For the purpose of counting repetitions, we only want to know if the
            # atom CAN match, and if so, where it ends. We take the first successful
            # match (if any) and use that to determine if we can continue.
            
            matched_once = False
            for new_pos in self.match_node(node.atom, current_pos):
                # The atom successfully matched! Take this first match.
                # We don't explore other ways the atom could match here because
                # we're just trying to count how many times total it can match,
                # not exploring all the internal variations of each match.
                matched_once = True
                
                # Important edge case: zero-width matches
                # If the atom matched but didn't consume any characters (new_pos == current_pos),
                # we need to be careful. This can happen with patterns like (a*) matching
                # against "bbb" - the a* matches zero times, which is a zero-width match.
                # If we allow infinite zero-width matches, we'll loop forever.
                # So we allow ONE zero-width match and then stop.
                if new_pos == current_pos:
                    # Zero-width match. Record it and stop trying to match more.
                    match_count += 1
                    match_positions.append(new_pos)
                    # Set matched_once to True so we break out of the while loop
                    # But also break from this for loop immediately
                    break
                
                # Normal match that consumed characters
                match_count += 1
                current_pos = new_pos
                match_positions.append(new_pos)
                
                # We only take the first way the atom can match at this position
                # because we're building a count of sequential matches, not exploring
                # all possible ways to match
                break
            
            # If the atom didn't match at all, we can't match any more times
            if not matched_once:
                break

        # Phase 2: Validation - check if we met the minimum requirement
        # For example, a+ requires at least one match, a{2,5} requires at least two
        if match_count < node.min_count:
            # We couldn't match enough times to satisfy the minimum
            # This quantifier fails completely, so don't yield anything
            return
        
        # Phase 3: Yielding - now yield positions in the appropriate order
        # The order depends on whether the quantifier is greedy or lazy
        
        if node.greedy:
            # Greedy: try maximum matches first, then backtrack to fewer
            # We iterate from match_count down to min_count
            # For example, if we matched 5 times and minimum is 2, we try:
            # 5 matches, then 4, then 3, then 2
            for num_matches in range(match_count, node.min_count - 1, -1):
                yield match_positions[num_matches]
                # The calling code will try this number of matches. If it doesn't
                # work out (the rest of the pattern fails), it will ask us for the
                # next value, and we'll yield the position after one fewer match.
                # This is backtracking in action!
        
        else:
            # Lazy: try minimum matches first, then expand to more if needed
            # We iterate from min_count up to match_count
            # For example, if minimum is 2 and we matched 5 times, we try:
            # 2 matches, then 3, then 4, then 5
            for num_matches in range(node.min_count, match_count + 1):
                yield match_positions[num_matches]
                # The calling code will try this number of matches. If it doesn't
                # work out, it will ask us for more, and we'll yield the position
                # after one more match. This is how lazy quantifiers expand on demand.
        
        # When we've yielded all possibilities and the calling code asks for more,
        # this generator will be exhausted (raise StopIteration), and the calling
        # code will know there are no more ways to match this quantifier.
        # This signals that we need to backtrack even further, perhaps to an earlier
        # choice point in the pattern.