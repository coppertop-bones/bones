import sys

import antlr4
from bones.lang._type_lang.TypeLangLexer import TypeLangLexer
from bones.lang._type_lang.TypeLangParser import TypeLangParser
from bones.lang._type_lang.tests.semantic_parser import Listener


f = antlr4.FileStream('type_lang_test.tl')
l = TypeLangLexer(f)
stream = antlr4.CommonTokenStream(l)
p = TypeLangParser(stream)
tree = p.tl_body()

w = antlr4.ParseTreeWalker()
listener = Listener()
w.walk(listener, tree)

# print(tree)
# print(tree.toStringTree(recog=p))
