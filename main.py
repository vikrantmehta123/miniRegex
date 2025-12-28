from parser import Parser

p = Parser("(?<mygroup>a*a)|c")
matcher = p.matcher('aaaa')

matcher.match()