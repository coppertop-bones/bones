# **********************************************************************************************************************
# Copyright 2025 David Briant, https://github.com/coppertop-bones. Licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License. You may obtain a copy of the  License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  KIND,
# either express or implied. See the License for the specific language governing permissions and limitations under the
# License. See the NOTICE file distributed with this work for additional information regarding copyright ownership.
# **********************************************************************************************************************

import sys
if hasattr(sys, '_TRACE_IMPORTS') and sys._TRACE_IMPORTS: print(__name__)


import re, collections, itertools
from bones.core.errors import ProgrammerError, SpellingError, ErrSite, handlersByErrSiteId, NotYetImplemented
from bones.core.sentinels import Missing


_tagIdSeed = itertools.count(start=0)

# META
START = next(_tagIdSeed)

# WHITE SPACE
WHITE_BREAK = next(_tagIdSeed)
LEADING_SPACES = next(_tagIdSeed)
NULL = next(_tagIdSeed)

# NON-CODE
LINE_COMMENT = next(_tagIdSeed)         # //
INLINE_COMMENT = next(_tagIdSeed)
BREAKOUT = next(_tagIdSeed)
CONTINUATION = next(_tagIdSeed)

# CONDITIONAL_COMMENT
CONDITIONAL_COMMENT = next(_tagIdSeed)

# SEPARATORS
COLON = next(_tagIdSeed)
COMMA = next(_tagIdSeed)
SEMI_COLON = next(_tagIdSeed)
DOT = next(_tagIdSeed)
LINE_BREAK = next(_tagIdSeed)

# IDENTIFIERS
NAME = next(_tagIdSeed)                 # fred.joe.sally - lookup attribute (`sally on (`joe on name fred))
SYMBOLIC_NAME = next(_tagIdSeed)
CONTEXT_NAME = next(_tagIdSeed)         # _.joe
GLOBAL_NAME = next(_tagIdSeed)          # _..joe
PARENT_VALUE_NAME = next(_tagIdSeed)    # .joe
MODULE_VALUE_NAME = next(_tagIdSeed)    # ..joe

# COMPOUND
KEYWORD_OR_BIND_LEFT = next(_tagIdSeed)       # for keyword messages and assignments
BIND_RIGHT = next(_tagIdSeed)                 # only for right assignments

# PROCESSED KEYWORD_OR_BIND_LEFT
BIND_LEFT = next(_tagIdSeed)
KEYWORD_FRAGMENT = next(_tagIdSeed)
GLOBAL_BIND_LEFT = next(_tagIdSeed)
GLOBAL_BIND_RIGHT = next(_tagIdSeed)
CONTEXT_BIND_LEFT = next(_tagIdSeed)
CONTEXT_BIND_RIGHT = next(_tagIdSeed)

# MISC
SIGNAL = next(_tagIdSeed)
RETURN = next(_tagIdSeed)

# LITERALS
DECIMAL = next(_tagIdSeed)
INTEGER = next(_tagIdSeed)
TEXT = next(_tagIdSeed)
SYMS = next(_tagIdSeed)
SYM = next(_tagIdSeed)
GLOBALTIMESTAMP_SS = next(_tagIdSeed)
GLOBALTIMESTAMP_S = next(_tagIdSeed)
GLOBALTIMESTAMP_M = next(_tagIdSeed)
LOCALTIMESTAMP_SS = next(_tagIdSeed)
LOCALTIMESTAMP_S = next(_tagIdSeed)
LOCALTIMESTAMP_M = next(_tagIdSeed)
DATE = next(_tagIdSeed)
GLOBALTIME_SS = next(_tagIdSeed)
GLOBALTIME_S = next(_tagIdSeed)
GLOBALTIME_M = next(_tagIdSeed)
LOCALTIME_SS = next(_tagIdSeed)
LOCALTIME_S = next(_tagIdSeed)
LOCALTIME_M = next(_tagIdSeed)
ELLIPSES = next(_tagIdSeed)

LITERAL1 = DECIMAL
LITERAL2 = ELLIPSES

# GROUPING
L_BRACE = next(_tagIdSeed)              # for functions and structs
R_BRACE = next(_tagIdSeed)
L_BRACE_BRACE = next(_tagIdSeed)        # for binary functions
R_BRACE_BRACE = next(_tagIdSeed)
R_PAREN_COLON = next(_tagIdSeed)
COLON_L_PAREN = next(_tagIdSeed)
L_PAREN = next(_tagIdSeed)
R_PAREN = next(_tagIdSeed)
L_BRACKET = next(_tagIdSeed)
R_BRACKET= next(_tagIdSeed)
L_ANGLE_COLON = next(_tagIdSeed)
R_ANGLE = next(_tagIdSeed)
L_BRACE_BRACKET = next(_tagIdSeed)      # for functions with parameters
L_PAREN_BRACKET = next(_tagIdSeed)      # for tables
L_BRACE_BRACE_BRACKET = next(_tagIdSeed)
L_BRACKET_BRACKET = next(_tagIdSeed)

ILLEGAL_MANY_DOTS = next(_tagIdSeed)
ILLEGAL_TWO_DOTS = next(_tagIdSeed)
ILLEGAL_NAME = next(_tagIdSeed)
ILLEGAL_GLOBAL_NAME = next(_tagIdSeed)
ILLEGAL_GLOBAL_BIND_LEFT = next(_tagIdSeed)
ILLEGAL_GLOBAL_BIND_RIGHT = next(_tagIdSeed)
ILLEGAL_CONTEXT_NAME = next(_tagIdSeed)
ILLEGAL_CONTEXT_BIND_LEFT = next(_tagIdSeed)
ILLEGAL_CONTEXT_BIND_RIGHT = next(_tagIdSeed)
ILLEGAL_PARENT_VALUE_NAME = next(_tagIdSeed)

ILLEGAL1 = ILLEGAL_MANY_DOTS
ILLEGAL2 = ILLEGAL_PARENT_VALUE_NAME

_NUM_TAGS = next(_tagIdSeed)

prettyNameByTag = [''] *_NUM_TAGS
prettyNameByTag[NULL] = 'NULL'
prettyNameByTag[LINE_COMMENT] = 'LINE_COMMENT'
prettyNameByTag[INLINE_COMMENT] = 'INLINE_COMMENT'
prettyNameByTag[BREAKOUT] = 'BREAKOUT'
prettyNameByTag[CONDITIONAL_COMMENT] = 'CONDITIONAL_COMMENT'
prettyNameByTag[COLON] = 'COLON'
prettyNameByTag[COMMA] = 'COMMA'
prettyNameByTag[SEMI_COLON] = 'SEMI_COLON'
prettyNameByTag[DOT] = 'DOT'
prettyNameByTag[LINE_BREAK] = 'LINE_BREAK'
prettyNameByTag[NAME] = 'NAME'
prettyNameByTag[SYMBOLIC_NAME] = 'SYMBOLIC_NAME'
prettyNameByTag[DECIMAL] = 'DECIMAL'
prettyNameByTag[INTEGER] = 'INTEGER'
prettyNameByTag[TEXT] = 'TEXT'
prettyNameByTag[SYMS] = 'SYMS'
prettyNameByTag[SYM] = 'SYM'
prettyNameByTag[GLOBALTIMESTAMP_SS] = 'GLOBALTIMESTAMP_SS'
prettyNameByTag[GLOBALTIMESTAMP_S] = 'GLOBALTIMESTAMP_S'
prettyNameByTag[GLOBALTIMESTAMP_M] = 'GLOBALTIMESTAMP_M'
prettyNameByTag[LOCALTIMESTAMP_SS] = 'LOCALTIMESTAMP_SS'
prettyNameByTag[LOCALTIMESTAMP_S] = 'LOCALTIMESTAMP_S'
prettyNameByTag[LOCALTIMESTAMP_M] = 'LOCALTIMESTAMP_M'
prettyNameByTag[DATE] = 'DATE'
prettyNameByTag[GLOBALTIME_SS] = 'GLOBALTIME_SS'
prettyNameByTag[GLOBALTIME_S] = 'GLOBALTIME_S'
prettyNameByTag[GLOBALTIME_M] = 'GLOBALTIME_M'
prettyNameByTag[LOCALTIME_SS] = 'LOCALTIME_SS'
prettyNameByTag[LOCALTIME_S] = 'LOCALTIME_S'
prettyNameByTag[LOCALTIME_M] = 'LOCALTIME_M'
prettyNameByTag[L_BRACE] = 'L_BRACE'
prettyNameByTag[R_BRACE] = 'R_BRACE'
prettyNameByTag[L_BRACE_BRACE] = 'L_BRACE_BRACE'
prettyNameByTag[L_BRACE_BRACE_BRACKET] = 'L_BRACE_BRACE_BRACKET'
prettyNameByTag[R_BRACE_BRACE] = 'R_BRACE_BRACE'
prettyNameByTag[R_PAREN_COLON] = 'R_PAREN_COLON'
prettyNameByTag[COLON_L_PAREN] = 'COLON_L_PAREN'
prettyNameByTag[L_PAREN] = 'L_PAREN'
prettyNameByTag[R_PAREN] = 'R_PAREN'
prettyNameByTag[L_BRACKET] = 'L_BRACKET'
prettyNameByTag[L_BRACKET_BRACKET] = 'L_BRACKET_BRACKET'
prettyNameByTag[R_BRACKET] = 'R_BRACKET'
prettyNameByTag[L_ANGLE_COLON] = 'L_ANGLE_COLON'
prettyNameByTag[R_ANGLE] = 'R_ANGLE'
prettyNameByTag[L_BRACE_BRACKET] = 'L_BRACE_BRACKET'
prettyNameByTag[L_PAREN_BRACKET] = 'L_PAREN_BRACKET'
prettyNameByTag[KEYWORD_OR_BIND_LEFT] = 'KEYWORD_OR_BIND_LEFT'
prettyNameByTag[BIND_LEFT] = 'BIND_LEFT'
prettyNameByTag[KEYWORD_FRAGMENT] = 'KEYWORD_FRAGMENT'
prettyNameByTag[BIND_RIGHT] = 'BIND_RIGHT'
prettyNameByTag[CONTINUATION] = 'CONTINUATION'
prettyNameByTag[ELLIPSES] = 'ELLIPSES'
prettyNameByTag[ILLEGAL_MANY_DOTS] = 'ILLEGAL_MANY_DOTS'
prettyNameByTag[ILLEGAL_TWO_DOTS] = 'ILLEGAL_TWO_DOTS'

prettyNameByTag[ILLEGAL_NAME] = 'ILLEGAL_NAME'
prettyNameByTag[ILLEGAL_GLOBAL_NAME] = 'ILLEGAL_GLOBAL_NAME'
prettyNameByTag[ILLEGAL_GLOBAL_BIND_RIGHT] = 'ILLEGAL_GLOBAL_BIND_RIGHT'
prettyNameByTag[ILLEGAL_CONTEXT_NAME] = 'ILLEGAL_CONTEXT_NAME'
prettyNameByTag[ILLEGAL_PARENT_VALUE_NAME] = 'ILLEGAL_PARENT_VALUE_NAME'
prettyNameByTag[ILLEGAL_GLOBAL_BIND_LEFT] = 'ILLEGAL_GLOBAL_BIND_LEFT'

prettyNameByTag[GLOBAL_BIND_LEFT] = 'GLOBAL_BIND_LEFT'
prettyNameByTag[GLOBAL_BIND_RIGHT] = 'GLOBAL_BIND_RIGHT'
prettyNameByTag[GLOBAL_NAME] = 'GLOBAL_NAME'
prettyNameByTag[CONTEXT_BIND_LEFT] = 'CONTEXT_BIND_LEFT'
prettyNameByTag[CONTEXT_BIND_RIGHT] = 'CONTEXT_BIND_RIGHT'
prettyNameByTag[CONTEXT_NAME] = 'CONTEXT_NAME'
prettyNameByTag[PARENT_VALUE_NAME] = 'PARENT_VALUE_NAME'
prettyNameByTag[MODULE_VALUE_NAME] = 'MODULE_VALUE_NAME'

prettyNameByTag[SIGNAL] = 'SIGNAL'
prettyNameByTag[RETURN] = 'RETURN'

prettyNameByTag= tuple(prettyNameByTag)


# see https://regex101.com/r/mtZL62/1


# [abc]  a single character matching a b or c
# [^abc]  any single character except a b or c
# [a-z] a single character in range a...z  [A-Z] [0-9]
# .   any single character
# \s - any whitespace character,   \S - any non-whitespace character
# \d - any digit,  \D - any non-digit
# \w - word character i.e. [a-zA-Z0-9_],  \W -
# \v - vertical whitespace (newline and vertical tab)
# (a|b)    either a or b
# a? - zero or one
# a* - zero or more - greedy quantifier - e.g. `a.*a` for "greedy can be dangerous at times" matches "an be dangerous a"
# a*? - Matches as few characters as possible. /r\w*?/  r re regex
# a+ - one or more
# a{3} - exactly three of a
# a{3,} - three or more of a
# a{4-6} - four to six of a
# \b - b is any metacharacter, i.e.  [ ] ^ - \ ( ) | { } ? , . as well as \n, \t, \r \0

# (?#This is a comment)
# (?P<name>...) - named capture group rather than a number, (?P<firstName>Sally)
# (?P=name) - Matches the text matched by a previously named capture group. This is the python specific notation.
# (?(1)yes|no) - If capturing group 1 was matched so far, matches the pattern before the vertical bar. Otherwise,
#      matches the pattern after the vertical bar. A group name, or a relative position (-1) in PCRE, can be used. Global
#      flag breaks conditionals.

# (...)\n - Usually referred to as a `backreference`, this will match a repeat of `...` in a previous set of parentheses. To
#      reduce ambiguity one may also use `\gn`, or `\g{n}` where m is a digit. e.g. (.)\1
# (...) - CAPTURE everything enclosed, parts of the regex enclosed in parentheses may be referred to later in the
#      expression or extracted from the results of a successful match. `(abc)` checks for `abc`
# (?:...) - MATCH everything enclosed,  e.g. `(?:abc)` checks for `abc` - this construct is similar
#      to (...), but won't create a capture group.


# ^ - start of string - Matches the start of a string without consuming any characters. If multiline mode is used, this will
#      also match immediately after a newline character. e.g. "start of string" >> RE >> "^\w+" answers "start"
# $ - end of string

# (?=...) - positive lookahead - without consuming characters does the expression match the FOLLOWING characters?
#      "foobaz" >> RE >> "foo(?=(bar|baz))" >> assertEquals >> (0, 3, 'foo')
# (?!...) - negative lookahead - without consuming characters does the expression NOT match the FOLLOWING characters?
#      "foobah" >> RE >> "foo(?!(bar|baz))" >> assertEquals >> (0, 3, 'foo')
# (?<=...) - positive lookbehind - without consuming characters does the expression match the PREVIOUS characters?
#      "afoobar" >> RE >> "\w{4}(?<=foo)bar" >> assertEquals >> (0, 7, 'afoobar')
# (?<!...) - negative lookbehind - without consuming characters does the expression NOT match the PREVIOUS characters?
#      "not bar" >> RE >> ".{4}(?<!(but ))bar" >> assertEquals >> (0, 7, 'not bar')


def compileBonesRE(rule):
    rule = "".join(re.split('\s', rule))    # strips out whitespace
    rule = " ".join(re.split('<sp>', rule))  # adds back in deliberate spaces
    try:
        return re.compile(rule)
    except Exception as ex:
        1/0

    # rules is pretty much constant but used in unit tests

    # (r'(?<![.a-zA-Z])([a-zA-Z][a-zA-Z_0-9]*)', NAME),



# do this https://prog21.dadgum.com/20.html?
#
# a collect {x*2} <:matrix>
#         vs
# person?: a typeOf <= <:Person>
# update!
# colour@
#
# I prefer the former


ALPHA_NUMERIC_NAME_RE = '([a-zA-Z_]\w*)'
OPERATOR_RE = '([_<>!=#_@$%^&*+/|~\'\?\-])'


_NAME_RE = f'''
    ({ALPHA_NUMERIC_NAME_RE}\.)*   (?#zero or more {{name,dot}})
    {ALPHA_NUMERIC_NAME_RE}      (?#name)
'''

_PARENT_VALUE_NAME_RE = fr'''
    (\.)                (?#one dot)
    ({ALPHA_NUMERIC_NAME_RE}\.)*   (?#zero or more {{name,dot}})
    {ALPHA_NUMERIC_NAME_RE}      (?#name)
'''

_MODULE_VALUE_NAME_RE = fr'''
    (\.\.)              (?#two dots)
    ({ALPHA_NUMERIC_NAME_RE}\.)*   (?#zero or more {{name,dot}})
    {ALPHA_NUMERIC_NAME_RE}      (?#name)
'''

_CONTEXT_NAME_RE = fr'''
    (_\.)               (?#underscore,dot)
    ({ALPHA_NUMERIC_NAME_RE}\.)*   (?#zero or more {{name,dot}})
    {ALPHA_NUMERIC_NAME_RE}      (?#name)
'''

_CONTEXT_BIND_LEFT_RE = fr'''
    (_\.)               (?#underscore,dot)
    ({ALPHA_NUMERIC_NAME_RE}\.)*   (?#zero or more {{name,dot}})
    {ALPHA_NUMERIC_NAME_RE}      (?#name)
    (:)                 (?#colon)
'''

_CONTEXT_BIND_RIGHT_RE = fr'''
    (:_\.)              (?#colon,underscore,dot)
    ({ALPHA_NUMERIC_NAME_RE}\.)*   (?#zero or more {{name,dot}})
    {ALPHA_NUMERIC_NAME_RE}      (?#name)
'''

_GLOBAL_NAME_RE = fr'''
    (_\.\.)             (?#underscore,underscore,dot)
    ({ALPHA_NUMERIC_NAME_RE}\.)*   (?#zero or more {{name,dot}})
    {ALPHA_NUMERIC_NAME_RE}      (?#name)
'''

_GLOBAL_BIND_LEFT_RE = fr'''
    (_\.\.)             (?#underscore,dot,dot)
    ({ALPHA_NUMERIC_NAME_RE}\.)*   (?#zero or more {{name,dot}})
    {ALPHA_NUMERIC_NAME_RE}      (?#name)
    (:)                 (?#colon)
'''

_GLOBAL_BIND_RIGHT_RE = fr'''
    (:_\.\.)            (?#colon,underscore,dot,dot)
    ({ALPHA_NUMERIC_NAME_RE}\.)*   (?#zero or more {{name,dot}})
    {ALPHA_NUMERIC_NAME_RE}      (?#name)
'''



_bonesLexRules = [
    (r'[<sp>]+', LEADING_SPACES),
    (r'[<sp>\t]+', WHITE_BREAK),

    # the lexer captures all the enclosed text of these next three
    (
        r"(\'\{\[)"                                         # '{[sectionType]...}'  https://regex101.com/r/4x595M/2
        r"([\S\s]*)" 
        r"(\])([\S\s]*?[^\\](\\\\)*)" 
        r"(\}\')", BREAKOUT
    ),
    (r"(/-)(([\S\s]*)-/)", INLINE_COMMENT),                 # /-...-/               https://regex101.com/r/5FUfMm/1
    (r"(/\!)(([\S\s]*)\!/)", CONDITIONAL_COMMENT),          # /!...!/               https://regex101.com/r/5WCGml/1
    (r'\/\/[^\n]*', LINE_COMMENT),                          # //...\n
    (r'[\n]+', LINE_BREAK),
    (r'(\")(([\S\s]*?[^\\](\\\\)*))\1', TEXT),
    (r'(`\w+){2,}', SYMS),
    (r'(`\w+)', SYM),

    # dates and numbers
    (r'[1-2][0-9][0-9][0-9]\.[0-1][0-9]\.[0-3][0-9]D[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\.[0-9]+[A-Z][A-Z][A-Z]', GLOBALTIMESTAMP_SS),          # must come before DATE
    (r'[1-2][0-9][0-9][0-9]\.[0-1][0-9]\.[0-3][0-9]D[0-9][0-9]:[0-9][0-9]:[0-9][0-9][A-Z][A-Z][A-Z]', GLOBALTIMESTAMP_S),
    (r'[1-2][0-9][0-9][0-9]\.[0-1][0-9]\.[0-3][0-9]D[0-9][0-9]:[0-9][0-9][A-Z][A-Z][A-Z]', GLOBALTIMESTAMP_M),
    (r'[1-2][0-9][0-9][0-9]\.[0-1][0-9]\.[0-3][0-9]D[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\.[0-9]+', LOCALTIMESTAMP_SS),  # must come before DATE
    (r'[1-2][0-9][0-9][0-9]\.[0-1][0-9]\.[0-3][0-9]D[0-9][0-9]:[0-9][0-9]:[0-9][0-9]', LOCALTIMESTAMP_S),
    (r'[1-2][0-9][0-9][0-9]\.[0-1][0-9]\.[0-3][0-9]D[0-9][0-9]:[0-9][0-9]', LOCALTIMESTAMP_M),
    (r'[1-2][0-9][0-9][0-9]\.[0-1][0-9]\.[0-3][0-9]', DATE),          # must come before DECIMAL
    (r'[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\.[0-9]+[A-Z][A-Z][A-Z]', GLOBALTIME_SS),
    (r'[0-9][0-9]:[0-9][0-9]:[0-9][0-9][A-Z][A-Z][A-Z]', GLOBALTIME_S),
    (r'[0-9][0-9]:[0-9][0-9][A-Z][A-Z][A-Z]', GLOBALTIME_M),
    (r'[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\.[0-9]+', LOCALTIME_SS),
    (r'[0-9][0-9]:[0-9][0-9]:[0-9][0-9]', LOCALTIME_S),
    (r'[0-9][0-9]:[0-9][0-9]', LOCALTIME_M),
    (r'[0-9]+\.[0-9]+(?!0-9)', DECIMAL),                           # must come before INTEGER and after DATE etc
    (r'[0-9]+(?!0-9)', INTEGER),

    # catch these before any NAMEs
    (r'>(?!>)', R_ANGLE),  # a lone '>'
    (r'\^\^(?!\^)', SIGNAL),
    (r'\^(?!\^)', RETURN),
    (r'<:', L_ANGLE_COLON),
    
    (_GLOBAL_BIND_LEFT_RE, GLOBAL_BIND_LEFT),
    (_GLOBAL_NAME_RE, GLOBAL_NAME),
    (_GLOBAL_BIND_RIGHT_RE, GLOBAL_BIND_RIGHT),
    (_CONTEXT_BIND_LEFT_RE, CONTEXT_BIND_LEFT),
    (_CONTEXT_NAME_RE, CONTEXT_NAME),
    (_CONTEXT_BIND_RIGHT_RE, CONTEXT_BIND_RIGHT),
    (_MODULE_VALUE_NAME_RE, MODULE_VALUE_NAME),
    (_PARENT_VALUE_NAME_RE, PARENT_VALUE_NAME),
    (_NAME_RE, NAME),
    
    # since '(', ')', '{', '}', '[', ']', ':' are exclusively used to indictate structure they can come here
    (r'\((\s)*\[', L_PAREN_BRACKET),
    # (r'\):', R_PAREN_COLON),      catch in lexer loop
    # (r':\(', COLON_L_PAREN),      catch in lexer loop
    (r'\(', L_PAREN),
    (r'\(', L_PAREN),
    (r'\)', R_PAREN),
    (r'\[\[', L_BRACKET_BRACKET),
    (r'\[', L_BRACKET),
    (r'\]', R_BRACKET),
    (r'{{(\s)*\[', L_BRACE_BRACE_BRACKET),
    (r'{(\s)*\[', L_BRACE_BRACKET),
    (r'{{', L_BRACE_BRACE),
    (r'}}', R_BRACE_BRACE),
    (r'{', L_BRACE),
    (r'}', R_BRACE),
    
    (r'\\(^\t| )*[\n]', CONTINUATION),                     # consumes just one \n

    (rf'{OPERATOR_RE}{{1,3}}', SYMBOLIC_NAME),    # comes after TEXT, and NAME
    (r'[\.]{4,}', ILLEGAL_MANY_DOTS),
    (r'(\.\.\.)', ELLIPSES),
    (r'(\.\.)', ILLEGAL_TWO_DOTS),
    (r'\.', DOT),
    (r',', COMMA),
    (r';', SEMI_COLON),
    (r':', COLON),

]


_atomicTags = {
    DOT, COMMA, SEMI_COLON, COLON, CONTINUATION, ELLIPSES, WHITE_BREAK, LEADING_SPACES, LINE_BREAK, L_PAREN,
    L_BRACKET, L_BRACE, L_ANGLE_COLON, L_PAREN_BRACKET, L_BRACE_BRACKET, L_BRACE_BRACE, R_PAREN, R_BRACKET,
    R_BRACE, R_ANGLE, R_BRACE_BRACE
}



Token = collections.namedtuple('Token', 'srcId, src, tag, indent, t, l1, l2, c1, c2, s1, s2')
# we might drop src for efficiency then this can be a regular array
# id - token number in output
# l1, l2 - line number
# t - unknown                   OPEN: remove
# c1, c2 - offset in line       OPEN: should be slice
# s1, s2 - offset in src        OPEN: should be slice
# indent - indent of line
# Token.__str__ = Token.__repr__
Token.__repr__ = lambda self:('{%s}' % (prettyNameByTag[self.tag])) if (self.tag in _atomicTags) else ('{%s:%s}' % (prettyNameByTag[self.tag], self.src))
@property
def _PPGroup(self):
    tag = self.tag
    if tag == BIND_LEFT:
        raise ProgrammerError('Unprocessed BIND_LEFT in tokens')
    if tag == BIND_RIGHT:
        return '{:%s}' % self.src
    if tag == CONTEXT_BIND_LEFT:
        raise ProgrammerError('Unprocessed CONTEXT_BIND_LEFT in tokens')
    if tag == CONTEXT_BIND_RIGHT:
        return '{:_.%s}' % self.src
    if tag == GLOBAL_BIND_LEFT:
        raise ProgrammerError('Unprocessed GLOBAL_BIND_LEFT in tokens')
    if tag == GLOBAL_BIND_RIGHT:
        return '{:_..%s}' % self.src
    if LITERAL1 <= tag and tag <= LITERAL2:
        return 'l'
    if tag == NAME:
        return 'n'
    if tag == PARENT_VALUE_NAME:
        return '.n'
    if tag == MODULE_VALUE_NAME:
        return '..n'
    if tag == CONTEXT_NAME:
        return '_.n'
    if tag == GLOBAL_NAME:
        return '_..n'
    if tag == SYMBOLIC_NAME:
        return 'n'
    if tag == RETURN:
        return '^'
    if tag == SIGNAL:
        return '^^'
    return self.__repr__()
Token.PPGroup = _PPGroup
@property
def _PPNames(self):
    tag = self.tag
    if tag == NAME:
        return self.src
    raise ProgrammerError()
Token.PPNames = _PPNames
@property
def tok1(self):
    return self
Token.tok1 = tok1
@property
def tok2(self):
    return self
Token.tok2 = tok2

SrcRef = collections.namedtuple('SrcRef', 't1, t2, l1, l2, c1, c2, s1, s2')   # t is token num
Line = collections.namedtuple('Line', 'l, s1, s2, src')


def lexBonesSrc(srcId, src):

    rules = _bonesLexRules

    # CAPTURE LINE NUMBERS
    lines = ['START']               # lines start at 1 so need something to take up slot 0
    NL = re.compile(r'[\n]')
    allUpToNL = re.compile(r'[^\n]*')
    pos = 0
    lineNum = 1
    # get the first ine
    match = allUpToNL.match(src, pos)
    line = match.group()
    s1 = match.start()
    s2 = match.end()
    lines.append(Line(lineNum, s1, s2, line) )
    # print('lexing.lexBonesSrc: %r %r %r %r \n' % (lineNum, c1, c2, line))
    pos = s2
    while match:
        # move to the next line
        match = NL.match(src, pos)
        if match:
            pos = match.end()
            lineNum += 1
            # get the line
            match = allUpToNL.match(src, pos)
            line = match.group() if match else ""
            s1 = match.start()
            s2 = match.end()
            lines.append(Line(lineNum, s1, s2, line))
            # print('%r %r %r %r' % (lineNum, s1, s2, line))
            pos = s2
    '       a: '
    '        a: '
    # TOKENISE SRC
    pos = 0
    tokens = [Token(srcId, '', START, 0, 0, 0, 0, 0, 0, 0, 0)]    # tokens start at 1 so need something to take up slot 0
    rules = [(compileBonesRE(pattern), tag) for (pattern, tag) in rules]
    l1 = 1
    indent = 0
    lastNewLineS2 = 0
    priorTag = None
    while pos < len(src):
        for regex, tag in rules:
            match = regex.match(src, pos)
            if match:
                name = prettyNameByTag[tag]
                if tag == LEADING_SPACES:
                    # if indent == 0:
                    #     indent = match.end() - match.start()
                    pass
                elif tag == WHITE_BREAK:
                    pass
                else:
                    # a bit fiddly but some of the regex match multiple lines
                    text = match.group()
                    s1 = match.start()
                    s2 = match.end()
                    while s1 > lines[l1].s2:
                        l1 += 1
                    l2 = l1
                    while s2 > lines[l2].s2:
                        l2 += 1
                    indent = s1 - (0 if l2 == 1 else lines[l2-1].s2 + 1)
                    if tag == LINE_BREAK:
                        c1 = 0
                        c2 = -1
                    else:
                        c1 = s1 - (-1 if l1 == 1 else lines[l1 - 1].s2)
                        c2 = s2 - (0 if l2 == 1 else (lines[l2 - 1].s2) + 1)
                        # testing
                        assert text == src[s1:s2]
                        if l1 < l2:
                            t1 = lines[l1].src[c1-1:]
                            if not text.startswith(t1):
                                1/0
                            t2 = lines[l2].src[:c2]
                            if not text.endswith(t2):
                                1/0
                        else:
                            t = lines[l1].src[c1-1:c2]
                            if text != t:
                                1/0

                    # the name regexes consume any extra dots - these are illegal so change the tag name accordingly
                    if text[-1] == '.':
                        if tag == NAME: tag = ILLEGAL_NAME
                        if tag == GLOBAL_NAME: tag = ILLEGAL_GLOBAL_NAME
                        if tag == GLOBAL_BIND_RIGHT: tag = ILLEGAL_GLOBAL_BIND_RIGHT
                        if tag == CONTEXT_NAME: tag = ILLEGAL_CONTEXT_NAME
                        if tag == PARENT_VALUE_NAME: tag = ILLEGAL_PARENT_VALUE_NAME
                    if tag == GLOBAL_BIND_LEFT:
                        if text[-2] == '.':
                            tag = ILLEGAL_GLOBAL_BIND_LEFT
                    # I'm not confident that it's quicker for me to implement the following in regex, and I'm not
                    # confident regex will execute it any faster. Adding state to the lex loop feels a little hacky but
                    # appropiate if lexing is taken as a whole however I suspect this little state machine could
                    # be generalised. The following implies that a:b is KEYWORD_OR_BIND_LEFT and
                    # that a space is needed for BIND_RIGHT, i.e. a :b
                    if priorTag == NAME and tag == COLON:
                        # merge NAME COLON sequence (with no WHITE_BREAK in between) into a KEYWORD_OR_BIND_LEFT
                        tag = KEYWORD_OR_BIND_LEFT
                        priorToken = tokens[-1]
                        tokens[-1] = Token(srcId, priorToken.src, tag, priorToken.indent, priorToken.t,    priorToken.l1, l2, priorToken.c1, c2, priorToken.s1, s2)
                    elif priorTag == COLON and (tag in (NAME, GLOBAL_NAME)):
                        # merge COLON NAME sequence (with no WHITE_BREAK in between) into a BIND_RIGHT
                        tag = BIND_RIGHT
                        tokens[-1] = Token(srcId, text, tag, indent, len(tokens),                          l1, l2, s1-lastNewLineS2, c2, s1, s2)
                    elif tag == SYM:
                        tokens.append(Token(srcId, text[1:], tag, indent, len(tokens),                     l1, l2, s1-lastNewLineS2, c2, s1, s2))
                    elif tag == SYMS:
                        tokens.append(Token(srcId, text.split('`')[1:], tag, indent, len(tokens),          l1, l2, s1-lastNewLineS2, c2, s1, s2))
                    elif tag in (L_BRACE_BRACKET, L_PAREN_BRACKET):
                        tokens.append(Token(srcId, ''.join(text.split()), tag, indent, len(tokens),        l1, l2, s1-lastNewLineS2, c2, s1, s2))
                    elif priorTag == R_PAREN and tag == COLON:
                        # merge R_PAREN COLON sequence (with no WHITE_BREAK in between) into R_PAREN_COLON
                        tag = R_PAREN_COLON
                        priorToken = tokens[-1]
                        tokens[-1] = Token(srcId, priorToken.src, tag, priorToken.indent, priorToken.t,    priorToken.l1, l2, priorToken.c1, c2, priorToken.s1, s2)
                    elif priorTag == COLON and tag == L_PAREN:
                        # merge COLON L_PAREN sequence (with no WHITE_BREAK in between) into COLON_L_PAREN
                        tag = COLON_L_PAREN
                        priorToken = tokens[-1]
                        tokens[-1] = Token(srcId, priorToken.src, tag, priorToken.indent, priorToken.t,    priorToken.l1, l2, priorToken.c1, c2, priorToken.s1, s2)
                    else:
                        if tag == LINE_BREAK and indent + 1 == (s2 - lines[l1].s1):
                            # set blank lines to have indent of 0 (thus forcing a new phrase)
                            tokens.append(Token(srcId, text, tag, 0, len(tokens),                          l1, l2, c1, c2, s1, s2))
                        else:
                            tokens.append(Token(srcId, text, tag, indent, len(tokens),                     l1, l2, c1, c2, s1, s2))
                if tag in (LINE_BREAK, CONTINUATION):
                    # indent = 0
                    pass
                break
        if (ILLEGAL1 <= tag and tag <= ILLEGAL2):
            token = tokens[-1]
            raise SpellingError(f'Illegal token: {token.src} @line {token.l1}:  {lines[token.l1].src}', ErrSite('illegal tag'))
        if tag == CONDITIONAL_COMMENT:
            raise NotYetImplemented('this will need handling at the lex stage')
        if not match:
            width = len(str(l2))
            print("Understood the source code upto this point - syntax error after shortly after:")
            print(f"{str(l2 - 2).rjust(width)} {lines[l2 - 2].src}")
            print(f"{str(l2 - 1).rjust(width)} {lines[l2 - 1].src}")
            print(f"{str(l2 - 0).rjust(width)} {lines[l2 - 0].src}")
            print(" "*width+"  "+ " " *(c2-1) + "^")
            raise SpellingError(f'Illegal character: {src[pos:pos+1]} @line {l2}:  {lines[l2].src}', ErrSite('no match'))
        pos = match.end()
        priorTag = tag

    return tokens, lines


handlersByErrSiteId.update({
    ('bones.parse.lex', Missing, 'lexBonesSrc', 'illegal tag') : '...',
    ('bones.parse.lex', Missing, 'lexBonesSrc', 'no match') : '...',
})
