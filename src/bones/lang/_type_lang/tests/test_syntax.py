import antlr4
from bones.lang._type_lang.tests.syntax_parser import parse

parse(antlr4.FileStream('tests/type_lang_test.tl'))
