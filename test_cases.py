from parser import Parser
import pytest

def test_empty_string_matching():
    """Empty patterns and empty strings"""
    p = Parser("")
    p.compile()
    assert p.matcher("").match() == True
    assert p.matcher("a").match() == False

def test_zero_width_assertions():
    """Anchors should not consume characters"""
    p = Parser("^abc$")
    p.compile()
    assert p.matcher("abc").match() == True
    assert p.matcher("xabc").match() == False

def test_catastrophic_backtracking():
    """Evil regex patterns that cause exponential time"""
    # This should complete but may be slow
    p = Parser("(a+)+b")
    p.compile()
    matcher = p.matcher("aaaaaaaaac")  # No 'b' at end
    result = matcher.match()  # Should eventually return False
    assert result == False

def test_nested_quantifiers():
    """Quantifiers on quantified expressions"""
    p = Parser("(a*)*")
    p.compile()
    assert p.matcher("aaa").match() == True
    
def test_character_class_edge_cases():
    """Tricky character class patterns"""
    # Empty class
    with pytest.raises(SyntaxError):
        Parser("[]").parse()
    
    # ] as first character
    p = Parser("[]abc]")
    p.compile()
    assert p.matcher("]").match() == True

def test_greedy_vs_lazy():
    """Verify greedy/lazy behavior"""
    greedy = Parser("a*a")
    greedy.compile()

    lazy = Parser("a*?a")
    lazy.compile()

    # Both should match, but with different strategies
    assert greedy.matcher("aaa").match() == True
    assert lazy.matcher("aaa").match() == True