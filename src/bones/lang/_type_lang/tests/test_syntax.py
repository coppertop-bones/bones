import sys

import antlr4
from type_lang.TypeLangLexer import TypeLangLexer
from type_lang.TypeLangParser import TypeLangParser
from type_lang.tests.syntax_parser import Listener


f = antlr4.FileStream('tests/type_lang_test.tl')
l = TypeLangLexer(f)
stream = antlr4.CommonTokenStream(l)
p = TypeLangParser(stream)
tree = p.tl_body()

w = antlr4.ParseTreeWalker()
listener = Listener()
w.walk(listener, tree)

print(tree)
print(tree.toStringTree(recog=p))
