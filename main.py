from parser import Parser

# # Email-like pattern
# parser = Parser(r"[a-zA-Z0-9]+@[a-zA-Z]+\.[a-z]+")
# matcher = parser.matcher("user@example.com")
# print(matcher.match())  # True

# # Phone number pattern
# parser = Parser(r"\d{3}-\d{3}-\d{4}")
# matcher = parser.matcher("123-456-7890")
# print(matcher.match())  # True

# # URL pattern with groups
parser = Parser(r"(https?)://([a-z.]+)")
parser.compile()
print(parser.compiled_pattern)
matcher = parser.matcher("https://example.com")
if matcher.match():
    print(f"Groups: {matcher.groups}")