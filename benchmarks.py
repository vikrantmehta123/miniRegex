import time
import re
from parser import Parser

def benchmark(pattern_str, test_string, iterations=1000):
    """Compare our engine vs Python's re module"""
    
    # Our engine
    start = time.time()
    for _ in range(iterations):
        p = Parser(pattern_str)
        matcher = p.matcher(test_string)
        result = matcher.match()
    our_time = time.time() - start
    
    # Python's re
    start = time.time()
    pattern = re.compile(pattern_str)
    for _ in range(iterations):
        result = pattern.fullmatch(test_string)
    re_time = time.time() - start
    
    print(f"Pattern: {pattern_str}")
    print(f"String: {test_string}")
    print(f"Our engine: {our_time:.4f}s")
    print(f"Python re:  {re_time:.4f}s")
    print(f"Ratio: {our_time/re_time:.2f}x slower\n")

# Run benchmarks
print("=== Regex Engine Benchmarks ===\n")
benchmark("abc", "abc")
benchmark("a*b", "aaaaaab")
benchmark("[a-z]+", "hello")
benchmark("\\d{3}-\\d{4}", "123-4567")