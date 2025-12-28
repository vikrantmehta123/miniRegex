"""
In backtracking, you usually stand at a crossroads with several paths to take (e.g., in Sudoku, you could try numbers 1 through 9 in an empty cell).

- The Loop represents the different choices available at your current position.
- The Recursion (yield from) represents moving forward into one of those choices.
- The Generator State handles the "undo" (backtracking) automatically.


def permutations(string):
    if len(string) == 0:
        yield ""
    else:
        for i in range(len(string)): # <--- THE CHOICE MAKER
            char = string[i]
            remaining = string[:i] + string[i+1:]
            
            for p in permutations(remaining): # <--- GOING DEEPER
                yield char + p

Imagine you are a supervisor.
- yield is like you personally picking up an item and handing it to the customer.
- yield from is like you telling an assistant, "You take over and give the customer everything in this box. I'll wait here until you're finished."



def flatten(data):
    for item in data:
        if isinstance(item, list):
            # We found a sub-list! 
            # "Go into this list and yield everything you find."
            yield from flatten(item)
        else:
            # It's just a regular item.
            yield item

example = [1, [2, 3], 4]

The Trace of flatten([1, [2, 3], 4]):
- Item 1: It's the number 1. It yields 1.
- Item 2: It's a list [2, 3]. The code hits yield from flatten([2, 3]). This starts a new instance of flatten. That instance yields 2, then yields 3. Because of yield from, these values go straight to the main caller.
- Item 3: The sub-generator finishes. We move to the next item in the main list, which is 4. It yields 4.

Without yield from, if you just did yield flatten(item), the caller would receive: 1, <generator object>, 4. Not very helpful!
"""