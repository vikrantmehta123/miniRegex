pattern: (a*a)|c

Let's trace the execution:

Alternation(alternatives=[
    Group(regex=Concatenation(
        items=[
            Quantifier(atom=Character(value='a'), min_count=0, max_count=None, greedy=True), 
            Character(value='b')]
        ), name=None, capturing=True), 
    Character(value='c')])

This is the AST for the pattern. 

Input String: aaa

How would the pattern match this string?

- In `matcher.match()` method, we will ask the generate `match_node` to yield its values by iterating over the loop.
- In `match_node` method, we will first call `match_alternation`  and yield to `match` method: `yield from self.match_alternation(node, pos)`   
    - By saying `yield from`, we are saying that for each value yielded from the match_alternation method, return that value to `match()`.

- In `match_alternation` method, we iterate over each alternatives and then call `match_node` on that alternative & yield it. Here, the first alternative is the Group. In the Group, we again yield a value.