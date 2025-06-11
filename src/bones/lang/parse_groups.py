# **********************************************************************************************************************
# Copyright 2025 David Briant, https://github.com/coppertop-bones. Licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License. You may obtain a copy of the  License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  KIND,
# either express or implied. See the License for the specific language governing permissions and limitations under the
# License. See the NOTICE file distributed with this work for additional information regarding copyright ownership.
# **********************************************************************************************************************

# lexing -> grouping -> phrase and typelang parsing -> assembling -> inferring

# grouping creates groups of phrases, including:
#   functions from {...}, {[...]...}, and {[...]<:...>...}
#   frames from ([...]...)
#   tuples from (...)
#   blocks from [...]
#   modules to load
#   names to import from modules
#   typelang tags from <:...>
#
# tokens are consumed in order (see parseStructure) and bespoke classes match specific groups. because groups
# can be terminated implicitly (by new-lines and indent patterns) and some groups have optional components the
# termination decision is not always local to the class that handles most of the decisions for a group.
#
# continuations, "." dots, return type tagging, keyword naming are examples.
#
# this makes bones code pithier but the group code harder to understand - ideally we would be able to make the
# stopping of a group as easy to follow as the start. suggestions will be seriously considered.
#
# parseStructure is the main loop of the parser
#   inputs a stream of tokens
#   outputs a SnippetGp
# it consumes the tokens one by one injecting the token into the group at the top of the stack
#   * new groups are created and pushed onto the stack as openers are encountered
#   * groups are _finalised (checked for errors) and popped off the stack as closers are encountered or implicit
#     rules are triggered
#
# a group class may group tokens in one of four styles
#   comma separated phrases - commas are explicit
#   dot separated phrases (dot-list) - dots are optional if replaced with new-lines without extra indentation
#   comma separated dot-list (comma-sep-dot-list) - commas are explicit
#   semi-colon separated comma-sep-dot-list - semi-colons are explicit
#
# as an example consider the tuples "(;,1+1. 2*2)" and "()". they both result in semi-colon separated
# comma-sep-dot-lists with any collapsable dimensionality processed later either when the literal is passed as an
# argument or when, in the case of something that looks like parenthesis, it is used as parenthesis.
#
# this means certain errors, e.g. `fred(1,2;3)`, cannot be detected in the group phase but will be handled in the
# more context sensitive phrase parsing phase.
#
# _Group
#   |--- _Phrase
#   |        |--- ParameterGp
#   |        \--- TypelangGp
#   \--- _Phrases
#            |--- _KeywordGp
#            |--- FromImportGp
#            |--- LoadGp
#            |--- ParametersGp
#            |--- SnippetGp
#            |--- FrameGp
#            |--- FrameKeysGp
#            |--- FuncOrStructGp
#            |--- _SemiColonSepCommasSepPhrase
#            |        \--- TupParenOrDestructureGp
#            \--- _XSepYSepPhrase   (Y can be dot_or_new_line)
#                     \--- _SemiColonSepCommasSepDotNLSepPhrase
#                              \--- BlockGp
#
# list
#   \--- _GuardedList
#            |--- _TokensGL
#            |--- _DotOrCommaSepGL
#            |--- _CommaSepDotSepGL
#            \--- _SemiColonSepCommaSepDotSepGL


# SYNTAX RULES - focussing on inner qualities and essential relationships
# It may not be possible to a) convert this into a formal grammar, or, b) convert this clearly into a formal grammar.
# So as the class hierarchy above helps navigate the code-base and should be maintained as rigorously as the code base,
# here are the syntactic rules expressed in an informal yet rigorous manner. The rule names are used to ensure the
# conceptual grouping syntax corresponds to the code and also corresponds to the error messages reported to the user.
#
#
# TESTING AND ERROR DESCRIPTIONS
# Every rule should be tested and the rule being tested should be explicitly mentioned. The source code should
# reference which rules it is implementing? At minimum every rule should be referred to at least once in code
# comments. Every rule should be covered in bone.kernel.explanations.
#
# basics
#       atom - atomic literal int, dec, txt, dates and times, symbol
#       name - sequence of a-z or A-Z or _
#       inner_name - name.name
#       parent_value - .name.name (just one level for the moment as this creates an auto-partial - unless the module)
#       module_value - ..name.name (just one level for the moment as this creates an auto-partial - unless the module)
#       contextual_name - _.name.name
#       global_name - _..name.name
#       uni_name - as name1 but with unicode
#       symbolic - sequence of non-alpha-numeric characters
#           excluding these characters . , ;
#           and these sequences: [ ] { } ( ) <: : ; , . " ^ ^^  _. _.. _... ...  {[ {{ {{[ }} ([, [[ //
#           allowed non-alpha-numerics are these ascii character ! @ # $ % & * - + = ' | \ < > ? / ` ~ :
#           allowed non-ascii? - £€±§ÛÅØøË¨ etc (from my mac keyboard)
#
# this means a library can add various symbolic functions such as ->, >>, <-, <-/ and so on. Core libraries will
# typically define the usual +, -, *, /, >, <, >=, <=. <> or !=, = or ==, etc.
#
# in bones names can refer to nouns or functions - noun scope is different (and more restricted) than function scope
# in typelang names refer to types and type parameters and have different scoping than nouns and functions
#
# in bones:
# () is used for parenthesis and tuples
# [] is used for function parameters, blocks, block parameters, frame keys and structural access
# {} is used for functions and structs
#
# these overloads work well from the human perspective but need carefully crafted rules for the parsers
#
# in typelang:
# () is used for parenthesis
# [] is used for intersection
# {} is used for structs
#
# structural access
#       access1 - noun noun
#       access2 - noun[]        ordinal (tuples and lists) and lookup (structs and maps)
#       access3 - name.name     structs only
#       access4 - name.ordinal
#
# consider:
# fred [] and fred[] are similar but what about fred[1].joe and fred[1] .joe (.joe might be a parent value name)
# fred[`tradeDate].1
#
#
# TUPLE OR PAREN AND PARTIAL CALLING
# it is a little involved but unambiguous - possible because we know the difference between noun names and function
# names and the piping is only possible because we know the style of all function names - a small price to pay for
# increased pith.
#
# 2d tuples can be parameter lists but they can't have empty slots - as it would be far too hard to read the code
# 1d tuples can create partials depending on the number of empty slots
#
# define:
#
# tuple_null - ()           - exactly 1 empty phrase
# tuple_or_paren - (...)    - exactly 1 non-empty phrase (with no dots)
# tuple_empty0 - (...,...) etc
# tuple_empty1 - (,...) etc
# tuple_empty2 - (,,...) etc
# tuple_empty3 - (,,,...) etc
# tuple_empty4plus - (,,,,...) etc
# tuple_2d - (;)
#
# all of these can be determined by watching for ";", checking for content and counting blank slots
#
# CASE 1 - where fn is first token in phrase, i.e. `fn (...`
# pipe style  | ()        | empty = 0 |     1     |     2     |     3     |     4+
# -------------------------------------------------------------------------------------
# nullary     | noun      | noun      | unpipable | unpipable | unpipable | unpipable
# unary       | noun (4.) | noun      | unary     | NYP       | NYP       | NYP
# binary      | illegal   | noun      | unpipable | binary    | NYP       | NYP
# ternary     | illegal   | noun      | unpipable | unpipable | ternary   | NYP
#
# Notes:
# 1. NYP is Not Yet Pipeable
# 2. once something becomes unpipable it remains that way
# 3. the empty = 0 column shows that (...) is never a parenthesis
# 4. we allow this case to make it quick to define functions that take no arguments without casting with <:nullary>
#    e.g. it is a pain to write {7 *.x}<:nullary>()
#
# CASE 2
# noun unary tuple_or_paren        -> tuple_or_paren is paren, i.e. will end up as (noun unary->noun) noun application
# noun binary tuple_or_paren       -> tuple_or_paren is paren
# noun ternary tuple_or_paren noun -> tuple_or_paren is paren
#
# function tuple is highest precedence
#
# partial_on_partial
# it is possible to do a "curry"ish style by creating a partial that can be partially called that can be...
#
# rule can only make a partial from a 1D tuple with 0 dots
#
# phrase parser is responsible for generating errors with wrong number of arguments
#
#
# phrase
#       noun
#
#
# FUNCTION OR STRUCT
# {[, {{ and {{[ are always functions
# semi-colon is an error
# if we encounter a comma and the phrase is left-assign then it's a struct else commas are errors
#
# fn - function
#       fn1 - {...}
#       fn2 - {[...]...}
#       fn3 - {[...] <:...> ...}
#
# fn_style - function style
#       fn_style_unary1 - {...}
#       fn_style_unary2 - {...} <:unary>
#       fn_style_binary1 - {...} <:binary>
#       fn_style_binary2 - {{...}}
#       fn_style_nullary - {...} <:nullary>
#       fn_style_ternary1 - {...} <:ternary>
#       fn_style_ternary2 - {{{...}}}
#
# fn_or_struct - function or struct - a nonsensical function so we make it a struct
#       fn_or_struct - {name: phrase}   -> struct1
#
# fn_or_binary - in the case of {{...}} if the inner one is a struct then we
#       fn_or_binary
#
# struct
#       struct1 - {name: phrase}
#       struct2 - {name: phrase, name: phrase, etc}
#
# il_brace - illegal brace
#       il_brace1 - {... ; ...}
#       il_brace2 - {name: phrase . phrase, ...}
#
# bones_prec - precedence in the bones language
#       name(...)
#       name[...]
#       bones_prec1 - * comes before other names
#




import sys, itertools
if hasattr(sys, '_TRACE_IMPORTS') and sys._TRACE_IMPORTS: print(__name__)


from coppertop.pipe import coppertop
from coppertop.dm.pp import PP, EE

from bones.core.errors import ProgrammerError, UnhappyWomble, PathNotTested, handlersByErrSiteId, NotYetImplemented
from bones.core.sentinels import Missing
from bones.core.errors import ErrSite
from bones.core.errors import GroupError
from bones.lang.tc import tcnode
from bones.lang.symbol_table import LOCAL_SCOPE, PARENT_SCOPE, MODULE_SCOPE, CONTEXT_SCOPE, GLOBAL_SCOPE, fnSymTab

from bones.lang.lex import prettyNameByTag, Token, \
    L_ANGLE_COLON, L_PAREN, L_BRACKET, L_BRACE, R_ANGLE, R_PAREN, R_BRACKET, \
    R_BRACE, COMMA, L_PAREN_BRACKET, L_BRACE_BRACKET, KEYWORD_OR_ASSIGN_LEFT, LINE_COMMENT, \
    INLINE_COMMENT, BREAKOUT, CONTINUATION, LINE_BREAK, SEMI_COLON, COLON, DOT, \
    NAME, ASSIGN_RIGHT, ASSIGN_LEFT, GLOBAL_ASSIGN_LEFT, GLOBAL_ASSIGN_RIGHT, CONTEXT_ASSIGN_RIGHT, \
    CONTEXT_ASSIGN_LEFT, L_BRACE_BRACE, R_BRACE_BRACE, L_BRACE_BRACE_BRACKET, L_BRACKET_BRACKET, \
    COLON_L_PAREN, R_PAREN_COLON, TEXT, NULL, \
    GLOBAL_NAME, CONTEXT_NAME, MODULE_VALUE_NAME, PARENT_VALUE_NAME


from bones.lang.types import nullary, unary, binary, ternary, TBI

# tuple / paren / destructure style
TUPLE_NULL = 1
TUPLE_2D = 2
TUPLE_OR_PAREN = 3
TUPLE_0_EMPTY = 4
TUPLE_1_EMPTY = 5
TUPLE_2_EMPTY = 6
TUPLE_3_EMPTY = 7
TUPLE_4_PLUS_EMPTY = 8
DESTRUCTURE = 9

# function / struct style
UNARY_OR_STRUCT = 1
STRUCT = 2
UNARY = 3
BINARY = 4

# separation style
COMMA_OR_DOT_SEP = 1
COMMA_SEP = 2
DOT_SEP = 3
NO_SEP = 4

# phrase ending reason
NOT_ENDING = 0
SUGGESTED_BY_LINE_BREAK = 1
SECTION_END = 2                 # a LINE_BREAK without enough indentation, a comma, a dot
GROUP_END = 3                   # a closer encountered

# indentation constants
MIN_INDENT = 2

# policy for handling empty phrases
NOTE_EMPTY = 1
IGNORE_EMPTY = 2
ERR_ON_EMPTY = 3
ERR_ON_EMPTY_NONE_OK = 4

CAUGHT = True
NOT_CAUGHT = False

def PPDebug(token):
    if token.tag == BREAKOUT: return "{BO}"
    if token.tag == LINE_BREAK: return r'\n'
    if token.tag == INLINE_COMMENT: return f"{token.src}"
    return token

    # pp: match [
    #     token.tag == BREAKOUT, "{BO}";
    #     token.tag == INLINE_COMMENT, "{//}";
    #     token
    # ]

def PPCloser(tokenTag):
    if tokenTag is Missing:
        return '...'
    else:
        return prettyNameByTag[tokenTag]

def parseStructure(tokens, st, src, TRACE=False):
    stack = _Stack()
    currentG = stack.push(SnippetGp(Missing, Missing, st))   # this one obviously doesn't need catching!!
    openers = {
        L_PAREN : catchLParen,
        L_BRACKET : catchLBracket,
        L_ANGLE_COLON : catchLAngleColon,
        L_BRACE : catchLBrace,
        L_BRACKET_BRACKET : catchLBracketBracket,
        L_BRACE_BRACKET : catchLBraceBracket,
        L_BRACE_BRACE : catchLBraceBrace,
        L_BRACE_BRACE_BRACKET : catchLBraceBraceBracket,
        COLON_L_PAREN : catchColonLParen,
        L_PAREN_BRACKET : catchLParenBracket,
    }
    closers = (R_PAREN, R_BRACKET, R_ANGLE, R_BRACE, R_BRACE_BRACE, R_PAREN_COLON)
    traceGroupCount = itertools.count()
    traceGroups = {}

    # for all of the tokens in the stream
    for token in tokens[1:]:
        opener = openers.get(token.tag, Missing)
        isCloser = token.tag in closers
        isNormal = (not opener and not isCloser) or (token.tag == R_ANGLE and not isinstance(currentG, TypelangGp))

        # find a consumer for the token
        consumer = Missing
        while consumer is Missing:
            if currentG._isInteruptable:
                consumer = catchLoad(token, currentG, stack)
                if consumer is Missing: consumer = catchFromImport(token, currentG, stack)
                if consumer is Missing: consumer = catchKeyword(token, currentG, stack)
                if consumer:
                    if TRACE:
                        f"{currentG.PPDebug} != {PPDebug(token)} .1" >> PP
                    currentG = consumer
                    if TRACE:
                        f"{currentG.PPDebug} << {PPDebug(token)} .1" >> PP
                    if TRACE:
                        if currentG not in traceGroups: traceGroups[next(traceGroupCount)] = currentG  # FOR DEBUG
            if consumer is Missing:
                currentGChanged = False
                if isNormal:      # OPEN: change TypeLang to group normally with a different parser
                    consumer = currentG._consumeToken(token, token.indent)
                    if consumer:
                        if TRACE:
                            f"{currentG.PPDebug} << {PPDebug(token)} .2" >> PP
                        break
                if isCloser:
                    wanted = currentG._processCloserOrAnswerError(token)  # will cause anything that doesn't care to self _finalise
                    if isinstance(wanted, str):
                        # TODO identify location of both opener and closer and maybe also print the relevant lines of source?
                        f'{currentG.l1}:{currentG.c1} to {token.l2}:{token.c2}' >> EE
                        got = prettyNameByTag[token.tag]
                        raise GroupError('Wanted %s got %s - %s' % (wanted, got, token), ErrSite("wanted got"), currentG, token)
                    consumer = currentG
                    if TRACE:
                        f"{currentG.PPDebug} << {PPDebug(token)} .3" >> PP
                    break
                # pop groups off the stack that have finished consuming tokens
                while currentG._tokens is Missing:
                    if TRACE:
                        f"{currentG.PPDebug} != {PPDebug(token)} .4" >> PP
                    stack.pop()
                    currentG = stack.current
                    currentGChanged = True

                if not currentGChanged: break

        # finally allow the grouping
        if consumer is Missing:
            if isCloser:
                raise PathNotTested()
                wanted = currentG._processCloserOrAnswerError(token)             # will cause anything that doesn't care to self _finalise
                if isinstance(wanted, str):
                    # TODO identify location of both opener and closer and maybe also print the relevant lines of source?
                    f'{currentG.l1}:{currentG.c1} to {token.l2}:{token.c2}' >> EE
                    got = prettyNameByTag[token.tag]
                    raise GroupError('Wanted %s got %s - %s' % (wanted, got, token), ErrSite("wanted got"), currentG, token)
                consumer = currentG
            if opener:
                consumer = opener(token, currentG, stack)
                if consumer:
                    currentG = consumer
                    if TRACE:
                        f"{currentG.PPDebug} << {PPDebug(token)} .5" >> PP

        if consumer is Missing:
            raise GroupError('Unhandled token %s' % str(token), ErrSite("Unhandled token"), currentG, token)

        # pop groups off the stack that have finished consuming tokens
        while currentG._tokens is Missing:
            if isinstance(currentG, TypelangGp):
                currentG.tl = src[currentG.s1+2:currentG.s2-1]
            if isinstance(currentG, ParametersGp):
                for p in currentG.phrases:
                    if len(p) != 1: 1/0
                    p = p[0]
                    if p.typePhrase:
                        p.tl = src[p.typePhrase[0].s1:p.typePhrase[-1].s2]
            stack.pop()
            currentG = stack.current
    while currentG._tokens is not Missing:
        currentG._finalise(Missing)
        if stack.len > 1:
            stack.pop()
            currentG = stack.current
    snippetGroup = stack.current
    return snippetGroup



# _Group serves a two fold propose -
#   1) provide the behaviour of the current sink of tokens,
#   2) abstract base class of all groups,

class _Group:

    __slots__ = [
        '_id',
        'parent',
        '_startTok',
        '_endTok',
        '_isComplete',
        '_tokens',
        '_phraseIndent',
        '_phraseState',
        '_endOfCommaSection',
        '_endOfSemicolonSection',
        '_hasDot',
        '_hasComma',
        '_hasSemicolon',
        '_numEmpty',
        'st',
    ]

    def _consumeToken(self, tokenOrGroup, indent):                       # works in tandem with parseStructure
        # answer self if we consume the token or Missing if we don't
        assert self._tokens is not Missing

        if self._phraseState or self._endOfCommaSection or self._endOfSemicolonSection:
            self._finishPhrase(indent, self._phraseState, tokenOrGroup)
            self._phraseState = NOT_ENDING

        if self._endOfCommaSection or self._endOfSemicolonSection:
            self._finishCommaSection(tokenOrGroup)
            self._endOfCommaSection = False

        if self._endOfSemicolonSection:
            self._finishRow()
            self._endOfSemicolonSection = False

        if not isinstance(tokenOrGroup, Token):
            self._appendToken(tokenOrGroup, indent)

        elif tokenOrGroup.tag in (LINE_COMMENT, INLINE_COMMENT, BREAKOUT):
            pass

        elif tokenOrGroup.tag is CONTINUATION:
            self._phraseIndent = Missing

        elif tokenOrGroup.tag is LINE_BREAK:
            if self._phraseIndent is Missing:
                self._phraseState = SUGGESTED_BY_LINE_BREAK   # current needed by tuples not sure why SECTION_END was wanted
            elif indent > self._phraseIndent:
                self._phraseState = SUGGESTED_BY_LINE_BREAK
            else:
                self._phraseState = SUGGESTED_BY_LINE_BREAK     # current needed by snippet not sure why SECTION_END was wanted

        elif tokenOrGroup.tag is DOT:
            self._phraseState = SECTION_END
            self._dotEncountered(tokenOrGroup)

        elif tokenOrGroup.tag is COMMA:
            self._phraseState = SECTION_END
            self._commaEncountered(tokenOrGroup)

        elif tokenOrGroup.tag is SEMI_COLON:
            self._phraseState = SECTION_END
            self._semicolonEncountered(tokenOrGroup)

        elif tokenOrGroup.tag is KEYWORD_OR_ASSIGN_LEFT:
            if len(self._tokens) == 0:
                tokenOrGroup = toAssignLeft(tokenOrGroup)
                self._appendToken(tokenOrGroup, indent)
            else:
                # from x.y.z import ifTrue:ifFalse: turns the interuption off so this is valid
                # raise ProgrammerError("Should be handled by the keyword catcher?")
                tokenOrGroup = toAssignLeft(tokenOrGroup)
                self._appendToken(tokenOrGroup, indent)

        elif tokenOrGroup.tag is ASSIGN_RIGHT:
            # check we are NOT at start of phrase
            if not self._tokens:
                msg = f'":{tokenOrGroup.src}" (AssignRight) is not allowed at start of phrase ({tokenOrGroup.l1}:{tokenOrGroup.l2})'
                raise GroupError(msg, ErrSite(self.__class__, "assign right"), self, tokenOrGroup)
            self.st.noteSets(tokenOrGroup.src, LOCAL_SCOPE)
            self._appendToken(tokenOrGroup, indent)

        elif tokenOrGroup.tag is CONTEXT_ASSIGN_RIGHT:
            # check we are NOT at start of phrase
            if not self._tokens:
                msg = f'":{tokenOrGroup.src}" (AssignRight) is not allowed at start of phrase ({tokenOrGroup.l1}:{tokenOrGroup.l2})'
                raise GroupError(msg, ErrSite(self.__class__, "assign right"), self, tokenOrGroup)
            self.st.noteSets(tokenOrGroup.src, CONTEXT_SCOPE)
            self._appendToken(tokenOrGroup, indent)

        elif tokenOrGroup.tag is GLOBAL_ASSIGN_RIGHT:
            # check we are NOT at start of phrase
            if not self._tokens:
                msg = f'":{tokenOrGroup.src}" (AssignRight) is not allowed at start of phrase ({tokenOrGroup.l1}:{tokenOrGroup.l2})'
                raise GroupError(msg, ErrSite(self.__class__, "assign right"), self, tokenOrGroup)
            self.st.noteSets(tokenOrGroup.src, GLOBAL_SCOPE)
            self._appendToken(tokenOrGroup, indent)

        elif tokenOrGroup.tag is NAME:
            self.st.noteGets(tokenOrGroup.src, LOCAL_SCOPE)
            self._appendToken(tokenOrGroup, indent)

        elif tokenOrGroup.tag is PARENT_VALUE_NAME:                 # .name
            self.st.noteGets(tokenOrGroup.src[1:], PARENT_SCOPE)
            self._appendToken(tokenOrGroup, indent)

        elif tokenOrGroup.tag is MODULE_VALUE_NAME:                 # ..name
            self.st.noteGets(tokenOrGroup.src[2:], MODULE_SCOPE)
            self._appendToken(tokenOrGroup, indent)

        elif tokenOrGroup.tag is CONTEXT_NAME:                      # _.name
            self.st.noteGets(tokenOrGroup.src[2:], CONTEXT_SCOPE)
            self._appendToken(tokenOrGroup, indent)

        elif tokenOrGroup.tag is GLOBAL_NAME:
            self.st.noteGets(tokenOrGroup.src[3:], GLOBAL_SCOPE)         # _..name
            self._appendToken(tokenOrGroup, indent)

        else:
            self._appendToken(tokenOrGroup, indent)

        return self


    def _appendToken(self, tokenOrGroup, indent):
        self._phraseIndent = self._phraseIndent or indent
        self._tokens.append(tokenOrGroup)
        if self._startTok is Missing: self._startTok = tokenOrGroup
        self._endTok = tokenOrGroup

    def __init__(self, parent, opener, st):
        self._id = _getId()
        self._isComplete = False
        self.parent = parent
        if isinstance(opener, (Token, _Group)):
            self._startTok = opener
        elif opener is Missing:
            self._startTok = Missing
        else:
            raise ProgrammerError()
        self._endTok = Missing

        # state machine variables - private to the grouping process
        self._tokens = _TokensGL()
        self._phraseIndent = Missing
        self._phraseState = NOT_ENDING
        self._endOfCommaSection = False
        self._endOfSemicolonSection = False
        
        # COMMAS and SEMI_COLON are definite separators whereas DOT and LINE_BREAK are optional terminators
        self._hasDot = False
        self._hasComma = False
        self._hasSemicolon = False
        self._numEmpty = 0

        self.st = st

    def _startNewPhrase(self):
        self._tokens = _TokensGL()
        self._phraseIndent = Missing

    def _finishPhrase(self, indent, cause, tokenOrGroup):
        raise NotImplementedError("???", ErrSite(self.__class__))

    def _startNewCommaSection(self):
        raise NotImplementedError("???", ErrSite(self.__class__))

    def _finishCommaSection(self, tokenOrGroup):
        raise NotImplementedError("???", ErrSite(self.__class__))

    def _startNewRow(self):
        raise NotImplementedError("???", ErrSite(self.__class__))

    def _finishRow(self):
        raise NotImplementedError("???", ErrSite(self.__class__))

    def _dotEncountered(self, tokenOrGroup):
        self._hasDot = True
        self._finishPhrase(Missing, self._phraseState, tokenOrGroup)
        self._phraseState = NOT_ENDING
    
    def _commaEncountered(self, tokenOrGroup):
        self._hasComma = True
        self._endOfCommaSection = True
        self._finishPhrase(Missing, self._phraseState, tokenOrGroup)
        self._phraseState = NOT_ENDING
        self._finishCommaSection(tokenOrGroup)
        self._endOfCommaSection = False

    def _semicolonEncountered(self, tokenOrGroup):
        self._hasSemicolon = True
        self._endOfCommaSection = True
        self._endOfSemicolonSection = True
        self._finishPhrase(Missing, self._phraseState, tokenOrGroup)
        self._phraseState = NOT_ENDING
        self._finishCommaSection(tokenOrGroup)
        self._endOfCommaSection = False
        self._finishRow()
        self._endOfSemicolonSection = False

    def _processCloserOrAnswerError(self, token):
        raise NotImplementedError("???", ErrSite(self.__class__))

    def _finalise(self, tokenOrGroup):
        assert self._tokens is not Missing
        if self._tokens:
            # self._dumpState()
            raise ProgrammerError(
                f'Still have tokens in flight {self.l1}:{self.c1} to {self.l2}:{self.c2}',
                ErrSite(self.__class__),
                {
                    "l1": self.l1,
                    "c1": self.c1,
                    "l2": self.l2,
                    "c2": self.c2,
                }
            )
        self._tokens = Missing

    @property
    def tok1(self):
        return self._startTok

    @property
    def tok2(self):
        return self._endTok

    @property
    def indent(self):
        return self.tok1.indent

    @property
    def srcId(self):
        return self.tok1.srcId

    @property
    def l1(self):
        return self.tok1.l1

    @property
    def l2(self):
        return self.tok2.l2

    @property
    def c1(self):
        return self.tok1.c1

    @property
    def c2(self):
        return self.tok2.c2

    @property
    def s1(self):
        return self.tok1.s1

    @property
    def s2(self):
        return self.tok2.s2

    @property
    def PPGroup(self):
        raise NotImplementedError("???", ErrSite(self.__class__))

    @property
    def PPDebug(self):
        raise NotImplementedError("???", ErrSite(self.__class__))



class _Phrase(_Group):
    # the abstract base class for single phrase groups, e.g. parameters and typelang

    def __init__(self, parent, opener, st):
        super().__init__(parent, opener, st)
        self._phrase = Missing

    # @property
    # def tok2(self):
    #     return self._tokens[-1] if self._tokens else self._phrase[-1]



class _Phrases(_Group):
    # N**phrase separated by COMMA - e.g. parameters, keyword style call, frame, frame keys
    # N**phrase separated by DOT / LINE_BREAK - e.g. snippet, function

    __slots__ = ['_phrases', '_sep', '_emptyPolicy']

    def __init__(self, parent, opener, sep, emptyPolicy, st):
        if sep == COMMA_SEP:
            self._phrases = _DotOrCommaSepGL(',')
        elif sep == DOT_SEP:
            self._phrases = _DotOrCommaSepGL('.')
        elif sep in (COMMA_OR_DOT_SEP, NO_SEP):
            self._phrases = _DotOrCommaSepGL('#')
        super().__init__(parent, opener, st)
        self._sep = sep
        self._emptyPolicy = emptyPolicy

    def _finishPhrase(self, indent, cause, tokenOrGroup):
        # tokenOrGroup >> PP
        if (phrase := self._tokens):
            # phrase has tokesns
            if cause == SUGGESTED_BY_LINE_BREAK:
                if indent > self._phraseIndent:
                    # if new indent is greater than the prior indent it means we are continuing the phrase
                    # TODO mark the indent at the start of the phrase not the last indent
                    pass
                else:
                    if not self._allowNLPhraseStart:
                        raise GroupError(
                            f'Illegal new line',
                            ErrSite(self.__class__, 'Illegal new line'),
                            self, tokenOrGroup
                        )
                    phrase = _processAssigmentsInPhrase(phrase, self._exactlyOneNameInPhrase, self, tokenOrGroup, self.st)
                    self._phrases << phrase
                    self._startNewPhrase()
            elif cause == SECTION_END:
                phrase = _processAssigmentsInPhrase(phrase, self._exactlyOneNameInPhrase, self, tokenOrGroup, self.st)
                self._phrases << phrase
                self._startNewPhrase()
            else:
                raise ProgrammerError()
        else:
            # phrase is empty
            if cause == SUGGESTED_BY_LINE_BREAK:
                pass
            elif cause == SECTION_END:
                if self._emptyPolicy == NOTE_EMPTY:
                    nextTok = tokenOrGroup
                    # OPEN: add a NULL token?
                    self._phrases << Missing # Token(nextTok.srcId, '', NULL, nextTok.indent, -1, nextTok.l1, nextTok.l1, nextTok.c1, nextTok.c1, nextTok.s1, nextTok.s1)
                    self._numEmpty += 1
                elif self._emptyPolicy == ERR_ON_EMPTY:
                    raise GroupError(
                        f'Illegal empty phrase',
                        ErrSite(self.__class__, 'Illegal empty phrase'),
                        self, tokenOrGroup
                    )
                self._startNewPhrase()
            else:
                raise ProgrammerError()

    def _finishCommaSection(self, tokenOrGroup):
        if self._sep == COMMA_SEP:
            # nothing to do as already finished in the _finishPhrase method
            pass
        elif self._sep == COMMA_OR_DOT_SEP:
            self._sep = COMMA_SEP
            self._phrases.sep(',')
        else:
            super()._finishCommaSection(tokenOrGroup)

    @property
    def phrases(self):
        if self._tokens: raise ProgrammerError()
        return self._phrases

    @property
    def PPGroup(self):
        return self._phrases.PPGroup

    def __repr__(self):
        return f'{str(self.__class__.__name__)}{self._id}( {self._phrases} )'



class _CommaSepDotSepPhrase(_Phrases):
    # list of dot separated phrases separated by COMMA - only as a row of Block

    __slots__ = ['_row']

    def __init__(self, parent, opener, st):
        self._row = _CommaSepDotSepGL()
        super().__init__(parent, opener, DOT_SEP, NOTE_EMPTY, st)  # ERR_ON_EMPTY

    def _startNewCommaSection(self):
        self._phrases = _DotOrCommaSepGL('.')

    def _finishCommaSection(self, tokenOrGroup):
        if self._phrases:
            self._row << self._phrases
            self._startNewCommaSection()
        elif self._hasComma:
            self._row << Missing
            self._numEmpty += 1
            self._startNewCommaSection()

    @property
    def row(self):
        if self._tokens: raise ProgrammerError()
        return self._row

    @property
    def PPGroup(self):
        return  self.row.PPGroup

    def __repr__(self):
        return '%s<%r>( %r )' % (self.__class__.__name__, self._id,  self.row)



class _SemiColonSepCommasSepDotNLSepPhrase(_CommaSepDotSepPhrase):
    # grid of phrases, i.e. a SEMI_COLON separated list of COMMA separated list of DOT separated list of phrase - e.g. Block

    __slots__ = ['_grid']

    def __init__(self, parent, opener, st):
        self._grid = _SemiColonSepCommaSepDotSepGL()
        super().__init__(parent, opener, st)

    def _startNewRow(self):
        self._row = _CommaSepDotSepGL()

    def _finishRow(self):
        if self._row:
            self._grid << self._row
            self._startNewRow()
        elif self._hasSemicolon:
            self._grid << Missing
            self._numEmpty += 1
            self._startNewRow()

    @property
    def grid(self):
        # if self._tokens: raise ProgrammerError()
        return self._grid

    @property
    def PPGroup(self):
        return self.grid.PPGroup

    def __repr__(self):
        return '%s<%r>( %r )' % (self.__class__.__name__, self._id,  self.grid)



class _SemiColonSepCommasSepPhrase(_Phrases):
    # grid of phrases, i.e. a SEMI_COLON separated list of COMMA separated list of phrase - e.g. Tup

    __slots__ = ['_grid']

    def __init__(self, parent, opener, st):
        self._grid = SemiColonSepCommaSep()
        super().__init__(parent, opener, COMMA_SEP, NOTE_EMPTY, st)

    def _startNewRow(self):
        self._phrases = _DotOrCommaSepGL(',')

    def _finishRow(self):
        if self._phrases:
            self._grid << self._phrases
            self._startNewRow()
        elif self._hasSemicolon:
            self._grid << Missing
            self._numEmpty += 1
            self._startNewRow()

    @property
    def grid(self):
        # if self._tokens: raise ProgrammerError()
        return self._grid

    @property
    def PPGroup(self):
        return self.grid.PPGroup

    def __repr__(self):
        return '%s<%r>( %r )' % (self.__class__.__name__, self._id,  self.grid)


def _checkStyle(fnToken, name, st):
    if (style := fnToken._unaryBinaryOrStruct) in (nullary, unary, binary, ternary):
        style = fnToken._unaryBinaryOrStruct
        currentStyle = st.kernel.styleByName.setdefault(name, style)
        if currentStyle != style:
            raise Exception("Style changed")

def _processAssigmentsInPhrase(phrase, exactlyOneNameInPhrase, group, tokenOrGroup, st):
    # check for assignments, converting ASSIGN_LEFT into ASSIGN_RIGHT

    # convert left assignments into terminal right assignments
    if len(phrase) == 1:
        if isinstance(phrase[0], Token):
            if phrase[0].tag == ASSIGN_LEFT:
                raise GroupError("Syntax error", ErrSite("_processAssigmentsInPhrase #1"), group, tokenOrGroup)
            elif phrase[0].tag == CONTEXT_ASSIGN_LEFT:
                raise GroupError("Syntax error", ErrSite("_processAssigmentsInPhrase #2"), group, tokenOrGroup)
            elif phrase[0].tag == GLOBAL_ASSIGN_LEFT:
                raise GroupError("Syntax error", ErrSite("_processAssigmentsInPhrase #3"), group, tokenOrGroup)
            elif isinstance(phrase[0], TupParenOrDestructureGp) and phrase[0]._isDestructure:
                raise GroupError("Syntax error", ErrSite("_processAssigmentsInPhrase #4"), group, tokenOrGroup)

    elif len(phrase) >= 2:
        if isinstance(phrase[0], Token):
            if phrase[0].tag == ASSIGN_LEFT:
                # move first token to end
                st.noteSets(phrase[0].src, LOCAL_SCOPE)
                phrase = phrase[1:] + [toAssignRight(phrase[0])]
            elif phrase[0].tag == CONTEXT_ASSIGN_LEFT:
                # move first token to end
                st.noteSets(phrase[0].src, CONTEXT_SCOPE)
                phrase = phrase[1:] + [toContextAssignRight(phrase[0])]
            elif phrase[0].tag == GLOBAL_ASSIGN_LEFT:
                # move first token to end
                st.noteSets(phrase[0].src, GLOBAL_SCOPE)
                phrase = phrase[1:] + [toGlobalAssignRight(phrase[0])]

        elif isinstance(phrase[0], TupParenOrDestructureGp) and phrase[0]._isDestructure:
            # move first token to end
            for row in phrase[0].grid:
                for tok in row:
                    if tok[0].tag == NAME:
                        st.noteSets(tok[0].src, LOCAL_SCOPE)
                    else:
                        raise NotYetImplemented()
            phrase = phrase[1:] + [phrase[0]]

        # if isinstance(phrase[0], TypelangGp) and isinstance(phrase[1], Token):
        #     if phrase[1].tag == ASSIGN_LEFT:
        #         # move first two tokens to end
        #         phrase = phrase[2:] + phrase[0:1] + [toAssignRight(phrase[1])]
        #     elif phrase[1].tag == CONTEXT_ASSIGN_LEFT:
        #         # move first two tokens to end
        #         phrase = phrase[2:] + phrase[0:1] + [toContextAssignRight(phrase[1])]
        #     elif phrase[1].tag == GLOBAL_ASSIGN_LEFT:
        #         # move first two tokens to end
        #         phrase = phrase[2:] + phrase[0:1] + [toGlobalAssignRight(phrase[1])]

    # catch all right assignments and any unprocessed left assignments
    numNames = 0
    prior = phrase[0]
    for each in phrase[1:]:
        if isinstance(each, Token):
            try:
                if each.tag == ASSIGN_LEFT:
                    varName = each.src
                    numNames += 1
                    if isinstance(group, FuncOrStructGp):
                        raise NotYetImplemented()
                elif each.tag == ASSIGN_RIGHT:
                    varName = each.src
                    numNames += 1
                    if isinstance(prior, FuncOrStructGp):
                        _checkStyle(prior, varName, st)
                        st.defFnMeta(varName, TBI, LOCAL_SCOPE)
                    elif isinstance(group, FrameGp):
                        print()
                        raise NotYetImplemented(f'_processAssigmentsInPhrase<FrameGp>: {group}')
                    elif isinstance(prior, type):
                        raise NotYetImplemented(f'_processAssigmentsInPhrase<type>: {group}')
                    else:
                        # b: {{x + y}}
                        # a: b <:unary>     <<<< here a is being bound to as a unary function but we have no idea
                        #                        what a's type is until we analyse the phrase
                        if not st.fMetaForGet(varName, LOCAL_SCOPE) and not st.vMetaForGet(varName, LOCAL_SCOPE):
                            st.defVMeta(varName, TBI, LOCAL_SCOPE)
                        
                elif each.tag == CONTEXT_ASSIGN_RIGHT:
                    varName = each.src[5:]
                    numNames += 1
                    if isinstance(prior, FuncOrStructGp):
                        _checkStyle(prior, varName, st)
                        st.defFnMeta(varName, TBI, CONTEXT_SCOPE)
                    elif isinstance(group, FuncOrStructGp):
                        raise GroupError("Can't context assign with frame group", ErrSite("_processAssigmentsInPhrase #5"), group, tokenOrGroup)
                    else:
                        st.defVMeta(varName, TBI, CONTEXT_SCOPE)
                elif each.tag == GLOBAL_ASSIGN_RIGHT:
                    varName = each.src[5:]
                    numNames += 1
                    if isinstance(prior, FuncOrStructGp):
                        _checkStyle(prior, varName, st)
                        st.defFnMeta(varName, TBI, GLOBAL_SCOPE)
                    elif isinstance(group, FuncOrStructGp):
                        raise GroupError("Can't global assign with frame group", ErrSite("_processAssigmentsInPhrase #6"), group, tokenOrGroup)
                    else:
                        st.defVMeta(varName, TBI, GLOBAL_SCOPE)
                    st.defVMeta(varName, TBI, GLOBAL_SCOPE)
            except NotYetImplemented as ex:
                raise
            except Exception as ex:
                raise GroupError(f"l1: {repr(group)} l2: {group.l2}", ErrSite("_processAssigmentsInPhrase #7"), group, tokenOrGroup) from ex
        elif isinstance(each, TupParenOrDestructureGp) and each._isDestructure:
            numNames += len(each.grid[0])
        if isinstance(each, TypelangGp):
            pass
        else:
            prior = each

    if exactlyOneNameInPhrase and numNames != 1:
        raise GroupError(
            f"Exactly one name must be provided, but {numNames} were found",
            ErrSite('exactlyOneNameInPhrase and numNames != 1'),
            group, tokenOrGroup
        )
    return _TokensGL() + phrase



# **********************************************************************************************************************
# snippet
# **********************************************************************************************************************

class SnippetGp(_Phrases):
    _exactlyOneNameInPhrase = False
    _allowNLPhraseStart = True
    _isInteruptable = True
    def __init__(self, parent, opener, st):
        super().__init__(parent, opener, DOT_SEP, IGNORE_EMPTY, st)
    def _finalise(self, tokenOrGroup):
        if self._tokens is Missing: raise ProgrammerError()
        # since a Snippet has no closing token we have to close when the main parsing loop calls _finalise
        self._finishPhrase(Missing, SECTION_END, tokenOrGroup)
        super()._finalise(tokenOrGroup)
    def _commaEncountered(self, tokenOrGroup):
        raise GroupError(
            f'COMMA not valid in snippet - {tokenOrGroup.l1}:{tokenOrGroup.l2}',
            ErrSite(self.__class__, 'COMMA not valid in snippet'),
            self, tokenOrGroup
        )
    def _semicolonEncountered(self, tokenOrGroup):
        raise GroupError(
            f'SEMI_COLON not valid in snippet - {tokenOrGroup.l1}:{tokenOrGroup.l2}',
            ErrSite(self.__class__, 'SEMI_COLON not valid in snippet'),
            self, tokenOrGroup
        )
    @property
    def PPDebug(self):
        return f'{{SNIPPET}} - {PPCloser(self._requiredCloser)}'



# **********************************************************************************************************************
# [...
# **********************************************************************************************************************

def catchLBracket(token, currentG, stack):
    if not (token.tag == L_BRACKET): return Missing
    block = BlockGp(currentG, token, currentG.st)
    currentG._consumeToken(block, token.indent)
    return stack.push(block)

def catchLBracketBracket(token, currentG, stack):
    if not (token.tag == L_BRACKET_BRACKET): return Missing
    block = BlockGp(currentG, token, currentG.st)
    currentG._consumeToken(block, token.indent)
    stack.push(block)
    dp = ParametersGp(block, token, block.st)
    block._params = dp
    return stack.push(dp)

class BlockGp(_SemiColonSepCommasSepDotNLSepPhrase):
    _isInteruptable = True
    _exactlyOneNameInPhrase = False
    _allowNLPhraseStart = True
    __slots__ = ['_params', '_tRet']
    def __init__(self, parent, opener, st):
        super().__init__(parent, opener, st)
        self._params = Missing
        self._tRet = Missing
    def _processCloserOrAnswerError(self, token):
        if token.tag != R_BRACKET: return prettyNameByTag[R_BRACKET]
        self._endTok = token
        self._finishPhrase(Missing, SECTION_END, token)
        self._finishCommaSection(token)
        self._finishRow()
        self._finalise(token)
        if self._phrases and self._phrases[0] and self._phrases[0] and isinstance(self._phrases[0][0][0], TypelangGp):
            self._tRet = self._phrases[0][0]
            self._phrases[0].pop(0)
    @property
    def PPGroup(self):
        pps = self.grid.PPGroup
        return f"[{''.join(pps)}]"
    @property
    def PPDebug(self):
        return f'{self.PPGroup} - {PPCloser(self._requiredCloser)}'



# **********************************************************************************************************************
# (...
# **********************************************************************************************************************

def catchLParen(token, currentG, stack):
    if not (token.tag == L_PAREN): return Missing
    il = TupParenOrDestructureGp(currentG, token, False, currentG.st)
    currentG._consumeToken(il, token.indent)
    return stack.push(il)

def catchColonLParen(token, currentG, stack):
    if not (token.tag == COLON_L_PAREN): return Missing
    il = TupParenOrDestructureGp(currentG, token, True, currentG.st)
    currentG._consumeToken(il, token.indent)
    return stack.push(il)

class TupParenOrDestructureGp(_SemiColonSepCommasSepPhrase):
    _exactlyOneNameInPhrase = False
    _allowNLPhraseStart = False
    _isInteruptable = True
    __slots__ = ['_isDestructure']
    def __init__(self, parent, opener, isDestructure, st):
        self._isDestructure = isDestructure
        super().__init__(parent, opener, st)
    @property
    def tupleType(self):
        if self._isDestructure:
            return DESTRUCTURE
        elif len(self.grid[0]) == 1 and self.grid[0][0] is Missing:
            return TUPLE_NULL
        elif self._hasSemicolon:
            return TUPLE_2D
        elif not self._hasComma:
            return TUPLE_OR_PAREN
        elif self._numEmpty == 0:
            return TUPLE_0_EMPTY
        elif self._numEmpty == 1:
            return TUPLE_1_EMPTY
        elif self._numEmpty == 2:
            return TUPLE_2_EMPTY
        elif self._numEmpty == 3:
            return TUPLE_3_EMPTY
        else:
            return TUPLE_4_PLUS_EMPTY
    def _processCloserOrAnswerError(self, token):
        if token.tag == R_PAREN_COLON:
            self._isDestructure = True
            # OPEN: check only names raise grouping error if not
        elif token.tag != R_PAREN:
            return prettyNameByTag[R_PAREN]
        self._endTok = token
        self._finishPhrase(Missing, SECTION_END, token)
        self._finishCommaSection(token)
        self._finishRow()
        self._finalise(token)
    @property
    def PPGroup(self):
        if self._isDestructure:
            pps = self.grid.PPNames
            return f"{{:({''.join(pps)})}}"
        else:
            pps = self.grid.PPGroup
            return f"({''.join(pps)})"
    @property
    def PPDebug(self):
        return f'{self.PPGroup} - {PPCloser(self._requiredCloser)}'



# **********************************************************************************************************************
# {... , {[..., {{..., {{[...
# **********************************************************************************************************************

def catchLBrace(token, currentG, stack):
    if not (token.tag == L_BRACE): return Missing
    f = FuncOrStructGp(currentG, token, UNARY_OR_STRUCT, R_BRACE, COMMA_OR_DOT_SEP, fnSymTab(currentG.st))
    currentG._consumeToken(f, token.indent)
    return stack.push(f)

def catchLBraceBracket(token, currentG, stack):
    if not (token.tag == L_BRACE_BRACKET): return Missing
    f = FuncOrStructGp(currentG, token, UNARY, R_BRACE, DOT_SEP, fnSymTab(currentG.st))
    currentG._consumeToken(f, token.indent)
    stack.push(f)
    dp = ParametersGp(f, token, f.st)
    f._params = dp
    return stack.push(dp)

def catchLBraceBrace(token, currentG, stack):
    if not (token.tag == L_BRACE_BRACE): return Missing
    f = FuncOrStructGp(currentG, token, BINARY, R_BRACE_BRACE, DOT_SEP, fnSymTab(currentG.st))
    currentG._consumeToken(f, token.indent)
    return stack.push(f)

def catchLBraceBraceBracket(token, currentG, stack):
    if not (token.tag == L_BRACE_BRACE_BRACKET): return Missing
    f = FuncOrStructGp(currentG, token, BINARY, R_BRACE_BRACE, DOT_SEP, fnSymTab(currentG.st))
    currentG._consumeToken(f, token.indent)
    stack.push(f)
    dp = ParametersGp(f, token, f.st)
    f._params = dp
    return stack.push(dp)

class FuncOrStructGp(_Phrases):
    _isInteruptable = True
    _exactlyOneNameInPhrase = False
    _allowNLPhraseStart = True
    __slots__ = ['_params', '_tRet', '_unaryBinaryOrStruct', '_requiredCloser']

    def __init__(self, parent, opener, unaryBinaryOrStruct, closer, sep, st):
        super().__init__(parent, opener, sep, ERR_ON_EMPTY, st)
        self._params = Missing
        self._tRet = Missing
        self._unaryBinaryOrStruct = unaryBinaryOrStruct
        self._requiredCloser = closer

    def _commaEncountered(self, tokenOrGroup):
        if (
            self._unaryBinaryOrStruct in [UNARY, BINARY] or     # it's a function (and commas are illegal)
            self._params or                                     # has parameters so it's a function
            self._tRet or                                       # has return type so it's a function
            self._hasDot                                        # has a dot so it's a function
        ):
            f"{tokenOrGroup.l1}:{tokenOrGroup.c1} to {tokenOrGroup.l2}:{tokenOrGroup.c2}" >> EE
            raise GroupError(
                "Illegal comma encountered in function body",
                ErrSite(self.__class__, "illegal COMMA in function body"),
                self, tokenOrGroup
            )
        if (
                not self._tokens or                          # having a comma with a blank phrase is illegal
                self._tokens[0].tag != ASSIGN_LEFT           # having a comma without an assign left is illegal
        ):
            f"{tokenOrGroup.l1}:{tokenOrGroup.c1} to {tokenOrGroup.l2}:{tokenOrGroup.c2}" >> EE
            raise GroupError(
                "Illegal comma encountered in function body",
                ErrSite(self.__class__, "illegal COMMA in {}"),
                self, tokenOrGroup
            )
        # if self._unaryBinaryOrStruct not in [STRUCT, UNARY_OR_STRUCT]: raise ProgrammerError()  filtered above
        self._unaryBinaryOrStruct = STRUCT
        self._phrases.sep(',')
        super()._commaEncountered(tokenOrGroup)

    def _semicolonEncountered(self, tokenOrGroup):
        f"{tokenOrGroup.l1}:{tokenOrGroup.c1} to {tokenOrGroup.l2}:{tokenOrGroup.c2}" >> EE
        raise GroupError(
            "Semi-colon encountered in function body",
            ErrSite(self.__class__, "illegal SEMI_COLON in function body"),
            self, tokenOrGroup
        )

    def _processCloserOrAnswerError(self, token):
        if token.tag != self._requiredCloser: return prettyNameByTag[self._requiredCloser]
        self._endTok = token
        currentPhrase = self._tokens
        isAssignLeft = currentPhrase and isinstance(currentPhrase[0], Token) and currentPhrase[0].tag == ASSIGN_LEFT
        numPhrases = (1 if currentPhrase else 0) + len(self._phrases)
        if numPhrases == 0:
            raise GroupError(
                "empty struct/function not allowed",
                ErrSite(self.__class__, "null struct"),
                self, token
            )
        elif numPhrases == 1:
            if self._unaryBinaryOrStruct == UNARY_OR_STRUCT:
                if isAssignLeft:
                    self._unaryBinaryOrStruct = STRUCT
                    self._phrases.sep(',')
                    # OPEN error if the assign is a tuple or struct assign
                else:
                    self._unaryBinaryOrStruct = UNARY
                    self._phrases.sep('.')
            elif self._unaryBinaryOrStruct == BINARY:
                if isAssignLeft:
                    raise GroupError(
                        "empty struct/function not allowed",
                        ErrSite(self.__class__, "assign left in single phrase binary"),
                        self, token
                    )
            elif self._unaryBinaryOrStruct == UNARY:
                pass
            else:
                raise ProgrammerError()
        else:
            if self._unaryBinaryOrStruct == UNARY_OR_STRUCT:
                if self._hasComma:
                    raise ProgrammerError()
                else:
                    self._unaryBinaryOrStruct = UNARY
                    self._phrases.sep('.')
        self._finishPhrase(Missing, SECTION_END, token)  # converts LEFT_ASSIGN into RIGHT_ASSIGN
        self._finalise(token)

    def _finalise(self, tokenOrGroup):
        if self._tokens is Missing: raise ProgrammerError()
        if self._unaryBinaryOrStruct == UNARY_OR_STRUCT:
            raise ProgrammerError()
        super()._finalise(tokenOrGroup)
        if self._phrases and self._phrases[0] and isinstance(self._phrases[0][0], TypelangGp):
            self._tRet = self._phrases[0][0]
            self._phrases.pop(0)

    @property
    def PPGroup(self):
        if self._unaryBinaryOrStruct == STRUCT:
            kvs = []
            for phrase in self._phrases:
                rhs = _TokensGL() + phrase[0:-1]
                name = phrase[-1].src
                kvs.append(f'{name}: {rhs.PPGroup}')
            return f"{{{', '.join(kvs)}}}"
        else:
            pp = self._params.PPGroup + ' ' if self._params else ''
            if self._unaryBinaryOrStruct == UNARY:
                return '{' + pp + self._phrases.PPGroup + '}'
            else:
                return '{{' + pp + self._phrases.PPGroup + '}}'

    @property
    def PPDebug(self):
        if self._unaryBinaryOrStruct == STRUCT:
            return f'{{STRUCT}}'
        else:
            if self._tokens is Missing:
                return f'{{[x] y}} - {PPCloser(self._requiredCloser)}'
            else:
                return f'{{[x] ...}} - {PPCloser(self._requiredCloser)}'



class ParametersGp(_Phrases):

    _isInteruptable = False

    __slots__ = ['_actualParams']

    def __init__(self, parent, opener, st):
        super().__init__(parent, opener, COMMA_SEP, NOTE_EMPTY, st)
        assert parent._params is Missing
        parent._params = self
        self._actualParams = Missing
        
    def _finishPhrase(self, indent, cause, tokenOrGroup):
        # five cases "fred: num", "fred:num", "fred :num",  "fred : num", "fred" - we could add some context to the
        # lexer to simplify our job here but for the moment let's not make it more complex
        phrase = self._tokens
        for token in phrase:
            if isinstance(token, TypelangGp):
                raise GroupError(
                    f'The type for a parameter must be specified after a `:` not with `<:...>`, i.e. not "{token}" - {token.l1}:{token.l2}',
                    ErrSite(self.__class__, "Param type must not be <:...>"),
                    self, token
                )
        if len(phrase) == 0:
            raise GroupError(
                f'{{[] has no arguments @{self.l1}:{self.c1}',
                ErrSite(self.__class__, "no args"),
                self, Missing
            )
        elif len(phrase) == 1:
            tok1 = phrase[0]
            if tok1.tag == ASSIGN_LEFT:
                raise GroupError(
                    f'{{[... {tok1.src} is missing type @{self.l1}:{self.c1}',
                    ErrSite(self.__class__, "missing type"),
                    self, tok1
                )
            elif tok1.tag != NAME:
                raise GroupError(
                    f'{{[... contains {tok1.src} which is not a name @{self.l1}:{self.c1}',
                    ErrSite(self.__class__, "not a name"),
                    self, tok1
                )
            phrase2 = [ParameterGp(self, tok1, [], self.st)]
        else:
            tok1 = phrase[0]
            if tok1.tag == ASSIGN_LEFT:
                # fred:num or fred: num
                newNameToken = Token(tok1.srcId, tok1.src, NAME, tok1.indent, tok1.t, tok1.l1, tok1.l2, tok1.c1, tok1.c2, tok1.s1, tok1.s2)
                phrase2 = [ParameterGp(self, newNameToken, phrase[1:], self.st)]
            elif tok1.tag == NAME and (secondToken := phrase[1]).tag == ASSIGN_RIGHT:
                # fred :num
                firstTypeName = Token(tok1.srcId, secondToken.src, NAME, secondToken.indent, secondToken.t, secondToken.l1, secondToken.l2, secondToken.c1, secondToken.c2, secondToken.s1, secondToken.s2)
                phrase2 = [ParameterGp(self, tok1, [firstTypeName] + phrase[2:], self.st)]
            elif len(phrase) >= 3 and tok1.tag == NAME and phrase[1].tag == COLON and phrase[2].tag == NAME:
                # fred : name
                phrase2 = [ParameterGp(self, tok1, phrase[2:], self.st)]
            else:
                raise GroupError(
                    f'{{[... contains {tok1.src} which is not a name @{self.l1}:{self.c1}',
                    ErrSite(self.__class__, "not a name"),
                    self, tok1
                )
        self._phrases << (_TokensGL() + phrase2)
        self._startNewPhrase()

    def _processCloserOrAnswerError(self, token):
        if token.tag != R_BRACKET: return prettyNameByTag[R_BRACKET]
        self._endTok = token
        self._finishPhrase(Missing, SECTION_END, token)
        self._finalise(token)
        
    def _finalise(self, tokenOrGroup):
        if self._tokens is Missing: raise ProgrammerError()
        if len(self._phrases) == 0:
            raise GroupError(
                'No parameters in list',
                ErrSite(self.__class__, 'No parameters in list'),
                self, Missing
            )
        for phrase in self._phrases:
            # [a :int, b] is max allowed (i.e. 2 tokens - a name and a type)
            if phrase is not Missing and (len(phrase) < 1 or len(phrase) > 3):
                raise GroupError(
                    'Parameters can only be one assigment expression each or a name',
                    ErrSite(self.__class__, 'only one assigment'),
                    self, phrase
                )
        super()._finalise(tokenOrGroup)
        
    # @property
    # def tok2(self):
    #     return self._phrases[-1][-1]

    @property
    def PPGroup(self):
        pps = self._phrases.PPGroup
        return f'[{"".join(pps)}]'

    @property
    def PPDebug(self):
        return f'{self.PPGroup} - {PPCloser(self._requiredCloser)}'


class ParameterGp(_Phrase):
    _isInteruptable = False
    __slots__ = ['nameToken', 'typePhrase', 'tl']
    def __init__(self, parent, nameToken, typePhrase, st):
        super().__init__(parent, nameToken, st)
        self.nameToken = nameToken
        self.typePhrase = typePhrase
        tl = Missing
    @property
    def PPGroup(self):
        return self.nameToken.PPGroup + ":t"
    def __repr__(self):
        return self.nameToken.src + ':' + (self.tl or 'TBI')
    @property
    def PPDebug(self):
        return f'{self.PPGroup} - {PPCloser(self._requiredCloser)}'



# **********************************************************************************************************************
# ([...
# **********************************************************************************************************************

def catchLParenBracket(token, currentG, stack):
    if not (token.tag == L_PAREN_BRACKET): return Missing
    t = FrameGp(currentG, token, currentG.st)
    currentG._consumeToken(t, token.indent)
    stack.push(t)
    k = FrameKeysGp(t, token, t.st)
    t._keys = k
    return stack.push(k)

class FrameGp(_Phrases):
    _exactlyOneNameInPhrase = True
    _allowNLPhraseStart = False
    _isInteruptable = False
    __slots__ = ['_keys']
    def __init__(self, parent, opener, st):
        super().__init__(parent, opener, COMMA_SEP, ERR_ON_EMPTY, st)
        self._keys = Missing
    def _processCloserOrAnswerError(self, token):
        if token.tag != R_PAREN: return prettyNameByTag[R_PAREN]
        self._endTok = token
        self._finishPhrase(Missing, SECTION_END, token)
        self._finalise(token)
    @property
    def PPGroup(self):
        ppKeys = self._keys.PPGroup + ' '
        return '(' + ppKeys + self._phrases.PPGroup + ')'

    @property
    def PPDebug(self):
        return f'{self.PPGroup} - {PPCloser(self._requiredCloser)}'

class FrameKeysGp(_Phrases):
    _exactlyOneNameInPhrase = True
    _allowNLPhraseStart = False
    _isInteruptable = False
    def __init__(self, parent, opener, st):
        super().__init__(parent, opener, COMMA_SEP, IGNORE_EMPTY, st)
    def _processCloserOrAnswerError(self, token):
        if token.tag != R_BRACKET: return prettyNameByTag[R_BRACKET]
        self._endTok = token
        self._finishPhrase(Missing, SECTION_END, token)
        self._finalise(token)
    @property
    def PPGroup(self):
        return '[' + self._phrases.PPGroup + ']'
    @property
    def PPDebug(self):
        return f'{self.PPGroup} - {PPCloser(self._requiredCloser)}'



# **********************************************************************************************************************
# <:...
# **********************************************************************************************************************

def catchLAngleColon(token, currentG, stack):
    if not (token.tag == L_ANGLE_COLON): return Missing
    tlg = TypelangGp(currentG, token, currentG.st)
    currentG._consumeToken(tlg, token.indent)
    return stack.push(tlg)

class TypelangGp(_Phrase):
    _isInteruptable = False
    __slots__ = ['tl']
    def __init__(self, parent, opener, st):
        super().__init__(parent, opener, st)
        self._isComplete = False
        self.tl = Missing
    def _processCloserOrAnswerError(self, token):
        if token.tag != R_ANGLE: return prettyNameByTag[R_ANGLE]
        if self._tokens is Missing: raise ProgrammerError()
        self._endTok = token
        self._phrase = self._tokens
        self._startNewPhrase()
        self._isComplete = True
        self._finalise(token)
    def _finishPhrase(self, indent, cause, tokenOrGroup):
        f"{tokenOrGroup.l1}:{tokenOrGroup.c1} to {tokenOrGroup.l2}:{tokenOrGroup.c2}" >> EE
        raise GroupError(
            "??? in _finishPhrase",
            ErrSite(self.__class__, "_finishPhrase"),
            self, tokenOrGroup
        )
    def _consumeToken(self, tokenOrGroup, indent):
        return self
    def _finalise(self, tokenOrGroup):
        try:
            if not self._isComplete:
                raise GroupError(
                    "missing closer (\">\") for typelang group",
                    ErrSite(self.__class__, "_finalise"),
                    group=self,
                    token=tokenOrGroup
                )
        except AttributeError as ex:
            raise
        return super()._finalise(tokenOrGroup)

    @property
    def PPGroup(self):
        return 't'
    @property
    def PPDebug(self):
        return f'{self.PPGroup} - {PPCloser(self._requiredCloser)}'



# **********************************************************************************************************************
# keyword style calls
# **********************************************************************************************************************

def catchKeyword(token, currentG, stack):
    if token.tag != KEYWORD_OR_ASSIGN_LEFT:
        return Missing
    if len(currentG._tokens) == 0 or isinstance(currentG, ParameterGp):
        # either there's nothing to the left so it can't be a keyword call, or we're parsing parameters for a function
        return Missing
    # if the potential keyword is on the same line then ok, or if it adds at least MIN_INDENT to
    # the indent of the first token in the expression
    indentOverFirstToken = token.indent - currentG._tokens[0].indent
    if (currentG._tokens[0].l2 != token.l2) and not (indentOverFirstToken >= MIN_INDENT):
        return Missing
    ketg = _KeywordGp(currentG, token, currentG.st)
    return stack.push(ketg)


# a: fred joe ifTrue: sally ugh ifFalse: []  => if encounter DOT, COMMA, SEMI_COLON then self._phraseState = SECTION_END
# answers ifTrue:ifFalse (fred joe, sally ugh, []) :a

def lastKv(d):
    k, v = d.popitem()
    d[k] = v
    return k, v

def atIfNonePut(d, k, v):
    return d.setdefault(k, v)

class _KeywordGp(_Phrases):
    # catches a sequence of {[ASSIGN_LEFT,] ARG_PHRASE, {KEYWORD_OR_ASSIGN_LEFT, ARG_PHRASE}}
    # _keywordTokens catches each KEYWORD_OR_ASSIGN_LEFT and _phrases catches each ARG_PHRASE
    # replaces the _tokens in the parent with {NAME, TUPLE (of args)}

    _exactlyOneNameInPhrase = False
    _allowNLPhraseStart = False
    _isInteruptable = False
    __slots__ = ['_latestToken', '_firstTokenInPhrase', '_keywordTokens', '_assignLeftOrMissing']

    def _consumeToken(self, tokenOrGroup, indent):                       # works in tandem with parseStructure
        # answer self if we consume the token or Missing if we don't
        if self._tokens is Missing: raise ProgrammerError()
        if self._phraseState == SUGGESTED_BY_LINE_BREAK:
            if indent > self._phraseIndent:
                self._phraseState = NOT_ENDING
                self.parent._phraseState = NOT_ENDING
            else:
                phrase = self._tokens
                if phrase:
                    phrase = _processAssigmentsInPhrase(phrase, self._exactlyOneNameInPhrase, self, tokenOrGroup, self.st)
                    self._phrases << phrase
                    self._latestToken = phrase[-1]
                    self._startNewPhrase()
                else:
                    self._phrases << Missing          # creating a partial
                    self._startNewPhrase()
                self._replaceSelfInParent()
                super()._finalise(tokenOrGroup)
                self.parent._consumeToken(tokenOrGroup, indent)
                return self
        elif self._phraseState == SECTION_END:
            phrase = self._tokens
            if phrase:
                phrase = _processAssigmentsInPhrase(phrase, self._exactlyOneNameInPhrase, self, tokenOrGroup, self.st)
                self._phrases << phrase
                self._startNewPhrase()
            else:
                self._phrases << Missing          # creating a partial
                self._startNewPhrase()
            self._phraseState = NOT_ENDING
            self.parent._phraseState = NOT_ENDING
        if isinstance(tokenOrGroup, Token):
            if tokenOrGroup.tag in (LINE_COMMENT, INLINE_COMMENT, BREAKOUT):
                pass
            elif tokenOrGroup.tag is CONTINUATION:
                self._phraseIndent = Missing
            elif tokenOrGroup.tag is LINE_BREAK:
                self._phraseState = SUGGESTED_BY_LINE_BREAK
                self.parent._phraseState = SUGGESTED_BY_LINE_BREAK
            elif tokenOrGroup.tag in (DOT, COMMA, SEMI_COLON):
                self._replaceSelfInParent()
                super()._finalise(tokenOrGroup)
                self.parent._consumeToken(tokenOrGroup, indent)
            elif tokenOrGroup.tag == KEYWORD_OR_ASSIGN_LEFT:
                if self._tokens:
                    self._keywordTokens << tokenOrGroup
                    self._phrases << self._tokens
                    self._startNewPhrase()
                else:
                    self._keywordTokens << tokenOrGroup
                    self._phrases << Missing          # creating a partial
                    self._startNewPhrase()
                self._latestToken = tokenOrGroup
            elif tokenOrGroup.tag == ASSIGN_RIGHT:
                if not self._tokens:
                    raise GroupError(
                        'AssignRight not only allowed at start of expression - %s',
                        ErrSite(self.__class__, 'AssignRight'),
                        self, tokenOrGroup
                    )
                self._tokens << tokenOrGroup
            else:
                if self._phraseIndent is Missing: self._phraseIndent = indent
                self._tokens << tokenOrGroup
        else:
            if self._phraseIndent is Missing: self._phraseIndent = indent
            self._tokens << tokenOrGroup
        return self

    def __init__(self, parent, opener, st):
        super().__init__(parent, opener, NO_SEP, NOTE_EMPTY, st)
        # temporarily steal the _tokens from the parent group and set theirs to missing
        # this will cause an error if we don't code _KeywordGp correctly acting as a bug detector :)
        parentTokens = parent._tokens
        parent._tokens = Missing
        self._phraseIndent = parentTokens[0].indent
        self._firstTokenInPhrase = parentTokens[0]
        self._latestToken = opener
        self._keywordTokens = _TokensGL() << opener
        if isinstance(parentTokens[0], Token) and parentTokens[0].tag == ASSIGN_LEFT:
            # separate out ASSIGN_LEFT from the keyword phrase
            self._assignLeftOrMissing = parentTokens[0]
            firstArg = _TokensGL() + parentTokens[1:]
            if not firstArg:
                raise GroupError(
                    'Double assign left',
                    ErrSite(self.__class__, 'Double assign left'),
                    self, opener
                )
        else:
            self._assignLeftOrMissing = Missing
            firstArg = parentTokens
        self._phrases << firstArg          # << store args in this

    def _processCloserOrAnswerError(self, token):
        phrase = self._tokens
        if phrase:
            phrase = _processAssigmentsInPhrase(phrase, self._exactlyOneNameInPhrase, self, token, self.st)
            self._phrases << phrase
            self._startNewPhrase()
        else:
            self._phrases << Missing
            self._startNewPhrase()
        self._replaceSelfInParent()
        super()._finalise(token)
        desiredTokenStringOrNone = self.parent._processCloserOrAnswerError(token)
        if desiredTokenStringOrNone: return desiredTokenStringOrNone

    def _finalise(self, tokenOrGroup):
        if self._tokens is Missing: raise ProgrammerError()
        phrase = self._tokens
        if phrase:
            phrase = _processAssigmentsInPhrase(phrase, self._exactlyOneNameInPhrase, self, tokenOrGroup, self.st)
            self._phrases << phrase
            self._startNewPhrase()
        else:
            self._phrases << Missing
            self._startNewPhrase()
        self._replaceSelfInParent()
        super()._finalise(tokenOrGroup)

    def _replaceSelfInParent(self):
        phraseForParent = (_TokensGL() << self._assignLeftOrMissing) if self._assignLeftOrMissing else _TokensGL()

        # add NAME
        newNameToken = Token(
            self.tok1.srcId,
            "".join([t.src + ":" for t in self._keywordTokens]),
            NAME,
            self.tok1.indent,
            Missing,
            self.tok1.l1,
            -1,#self.tok2.l2,
            self.tok1.c1,
            -1,#sself.tok2.c2,
            self.tok1.s1,
            -1,#sself.tok2.s2
        )
        phraseForParent << newNameToken

        # add (<args>)
        args = TupParenOrDestructureGp(self.parent, self._startTok, False, self.st)
        row = _CommaSepDotSepGL()
        for phrase in self._phrases:
            for tokenOrGroup in phrase:
                if isinstance(tokenOrGroup, _Group):
                    tokenOrGroup.parent = args
            _phrases = _DotOrCommaSepGL('.')
            _phrases << phrase
            row << _phrases
        if len(row) > 1:
            args._hasComma = True
        grid = _SemiColonSepCommaSepDotSepGL()
        grid << row
        # args._grid = _SemiColonSepCommaSepDotSepGL(grid)
        args._grid = grid
        args._finalise(Missing)
        phraseForParent << args

        if self.parent._tokens is not Missing: raise ProgrammerError()
        self.parent._tokens = phraseForParent

    @property
    def tok1(self):
        return self._firstTokenInPhrase
    @property
    def tok2(self):
        return self._latestToken
    @property
    def PPDebug(self):
        return f'{self.PPGroup} - {PPCloser(self._requiredCloser)}'



# **********************************************************************************************************************
# load ...
# **********************************************************************************************************************

def catchLoad(token, currentG, stack):
    if not (token.tag == NAME and token.src == 'load'): return Missing
    lg = LoadGp(currentG, token, currentG.st)
    currentG._consumeToken(lg, token.indent)
    return stack.push(lg)

class LoadGp(_Phrases):
    # load sdf.sdf.sdf, sdf.sdf   -> list of modules to load into the kernel

    _exactlyOneNameInPhrase = False
    _isInteruptable = False

    __slots__ = ['_awaitingTokens', '_lastLineBreakAndIndent']

    def __init__(self, parent, opener, st):
        super().__init__(parent, opener, COMMA_SEP, ERR_ON_EMPTY, st)
        self._awaitingTokens = True
        self._phraseIndent = opener.indent
        self._lastLineBreakAndIndent = Missing

    def _processCloserOrAnswerError(self, token):
        self._finalise(token)
        return self.parent._processCloserOrAnswerError(token)

    def _finalise(self, tokenOrGroup):
        if self._tokens:
            self._phrases << self._tokens
            self._tokens = _TokensGL()
        if len(self._phrases) == 0:
            raise GroupError(
                f'requires - no items specified - needs better error msg',
                ErrSite(self.__class__, 'requires - no items specified'),
                self, Missing
            )
        if self._awaitingTokens:
            raise GroupError(
                f'Encountered GROUP_END without a NAME - better error msg needed',
                ErrSite(self.__class__, 'Encountered GROUP_END without a NAME'),
                self, tokenOrGroup
            )
        super()._finalise(tokenOrGroup)

    @property
    def PPGroup(self):
        return '{L}'

    @property
    def PPDebug(self):
        return f'{self.PPGroup} - {PPCloser(self._requiredCloser)}'

    def _consumeToken(self, tokenOrGroup, indent):                       # works in tandem with parseStructure
        # answer self if we consume the token or Missing if we don't
        if self._tokens is Missing: raise ProgrammerError()

        if self._phraseState == GROUP_END:
            self._finalise(tokenOrGroup)
            return Missing

        stateToStore = Missing

        if not isinstance(tokenOrGroup, Token):
            raise GroupError(
                'No groups allowed in load - better error msg needed',
                ErrSite(self.__class__, 'No groups allowed in load'),
                self, tokenOrGroup
            )

        elif tokenOrGroup.tag is BREAKOUT:
            raise GroupError(
                'No breakouts allowed in load - better error msg needed',
                ErrSite(self.__class__, 'No breakouts allowed in load'),
                self, tokenOrGroup
            )

        elif tokenOrGroup.tag in (SEMI_COLON, KEYWORD_OR_ASSIGN_LEFT, ASSIGN_RIGHT):
            raise GroupError(
                f'{prettyNameByTag(tokenOrGroup.tag)} not allowed in load - better error msg needed',
                ErrSite(self.__class__, f'{prettyNameByTag(tokenOrGroup.tag)} not allowed in load)'),
                self, tokenOrGroup
            )

        elif tokenOrGroup.tag in (LINE_COMMENT, INLINE_COMMENT, CONTINUATION):
            pass

        elif tokenOrGroup.tag is LINE_BREAK:
            if self._lastLineBreakAndIndent is not Missing:
                self._phraseState = GROUP_END
                self._finalise(tokenOrGroup)
                self.parent._consumeToken(*self._lastLineBreakAndIndent)
                return Missing
            # need to store some state to send to the parent if it turns out I shouldn't have consumed this
            stateToStore = tokenOrGroup, indent

        elif (indent < self._phraseIndent + MIN_INDENT) or tokenOrGroup.tag is DOT:
            # any token to the left of the load statement + MIN_INDENT means we are ending the load section
            self._phraseState = GROUP_END
            self._finalise(tokenOrGroup)
            if self._lastLineBreakAndIndent is not Missing:
                self.parent._consumeToken(*self._lastLineBreakAndIndent)
            return Missing

        elif tokenOrGroup.tag is COMMA:
            if self._awaitingTokens:
                raise GroupError(
                    f'Encountered COMMA without a NAME - better error msg needed',
                    ErrSite(self.__class__, 'Encountered COMMA without a NAME'),
                    self, tokenOrGroup
                )
            else:
                self._phrases << self._tokens
                self._tokens = _TokensGL()
                self._awaitingTokens = True

        elif tokenOrGroup.tag in (NAME, TEXT):
            if self._awaitingTokens:
                self._appendToken(tokenOrGroup, indent)
                self._awaitingTokens = False
            else:
                raise GroupError(
                    f'Encountered a NAME or TEXT without a COMMA - better error msg needed',
                    ErrSite(self.__class__, 'Encountered NAME without a COMMA'),
                    self, tokenOrGroup
                )

        else:
            raise ProgrammerError(f'{prettyNameByTag(tokenOrGroup.tag)} hasn\'t been handled')

        self._lastLineBreakAndIndent = stateToStore
        return self



# **********************************************************************************************************************
# from ... import ...
# **********************************************************************************************************************

def catchFromImport(token, currentG, stack):
    if not (token.tag == NAME and token.src == 'from'): return Missing
    fig = FromImportGp(currentG, token, currentG.st)
    currentG._consumeToken(fig, token.indent)
    return stack.push(fig)

class FromImportGp(_Phrases):

    _exactlyOneNameInPhrase = False
    _isInteruptable = False

    __slots__ = ['path', '_seenImport', '_awaitingTokensPostComma']

    def __init__(self, parent, opener, st):
        super().__init__(parent, opener, COMMA_SEP, ERR_ON_EMPTY, st)
        self.path = Missing
        self._seenImport = False
        self._awaitingTokensPostComma = False

    def _processCloserOrAnswerError(self, token):
        return "FromImportGp doesn't take a closer"
        # self._finalise(token)
        # return self.parent._processCloserOrAnswerError(token)

    def _finalise(self, tokenOrGroup):
        if self._tokens: self._finishPhrase(Missing, SECTION_END, tokenOrGroup)
        if len(self._phrases) == 0:
            raise GroupError(
                f'requires - no items specified - needs better error msg',
                ErrSite(self.__class__, 'from import - no items specified'),
                self, Missing
            )
        if self._awaitingTokensPostComma:
            raise GroupError(
                f'requires - missing items after last comma - needs better error msg',
                ErrSite(self.__class__, 'from import - missing items after last comma'),
                self, Missing
            )
        super()._finalise(tokenOrGroup)

    @property
    def PPGroup(self):
        return '{FI}'

    @property
    def PPDebug(self):
        if self.path is Missing:
            return f'{{from ...}} - {PPCloser(self._requiredCloser)}'
        elif self._tokens is not Missing:
            if not self._seenImport:
                return f'{{from x}} - {PPCloser(self._requiredCloser)}'
            else:
                return f'{{from x import ...}} - {PPCloser(self._requiredCloser)}'
        else:
            return f'{{from x import y}} - {PPCloser(self._requiredCloser)}'

    def _consumeToken(self, tokenOrGroup, indent):                       # works in tandem with parseStructure
        # answer self if we consume the token or Missing if we don't
        if self._tokens is Missing: raise ProgrammerError()
        if self.path is Missing:
            if isinstance(tokenOrGroup, Token) and tokenOrGroup.tag == NAME:
                self.path = tokenOrGroup.src
                return self
            else:
                raise UnhappyWomble("needs some love")
        elif not self._seenImport:
            if isinstance(tokenOrGroup, Token):
                if tokenOrGroup.tag in (LINE_COMMENT, INLINE_COMMENT):
                    return self
                if tokenOrGroup.tag == NAME and tokenOrGroup.src == "import":
                    self._seenImport = True
                    return self
                raise GroupError(
                    f'requires "import" after the path',
                    ErrSite(self.__class__, 'requires import after path'),
                    self, Missing
                )
            else:
                raise UnhappyWomble("needs some love")
        else:
            return self._consumeToken2(tokenOrGroup, indent)

    # _consumeToken: {[o, tokenOrGroup, indent]
    #     case [
    #         o._tokens is Missing, ^^ err <:&ProgrammerError>;
    #         o.path is Missing, case [
    #             isinstance(tokenOrGroup, Token) and tokenOrGroup.tag == NAME, o.path: tokenOrGroup.src. CAUGHT;
    #             ^^ "needs some love" <:&UnhappyWomble>
    #         ];
    #         o._seenImport not, case [
    #             isinstance(tokenOrGroup, Token), case [
    #                 tokenOrGroup.tag in (LINE_COMMENT, INLINE_COMMENT), CAUGHT;
    #                 tokenOrGroup.tag == NAME and tokenOrGroup.src == "import", o._seenImport: True. CAUGHT;
    #                 ^^ err <:ProgrammerError>
    #             ];
    #             ^^ "needs some love" <:&UnhappyWomble>
    #         ];
    #         o._consumeToken2(tokenOrGroup, indent)
    #     ]
    # }


    def _consumeToken2(self, tokenOrGroup, indent):
        if self._tokens is Missing: raise ProgrammerError()

        if self._phraseIndent and indent <= self._phraseIndent:
            # any token to the left of the load statement means we are ending the group
            self._phraseState = GROUP_END

        if self._phraseState or self._endOfCommaSection:
            self._finishPhrase(indent, self._phraseState, tokenOrGroup)
            if self._phraseState == GROUP_END:
                self._finalise(tokenOrGroup)
                return Missing
            self._phraseState = NOT_ENDING

        if not isinstance(tokenOrGroup, Token):
            raise GroupError(
                'No groups allowed in from import - better error msg needed',
                ErrSite(self.__class__, 'No groups allowed in from import'),
                self, tokenOrGroup
            )

        elif tokenOrGroup.tag is BREAKOUT:
            raise GroupError(
                'No breakouts allowed in from import - better error msg needed',
                ErrSite(self.__class__, 'No breakouts allowed in from import'),
                self, tokenOrGroup
            )

        elif tokenOrGroup.tag in (LINE_COMMENT, INLINE_COMMENT, CONTINUATION, LINE_BREAK):
            pass

        elif tokenOrGroup.tag is DOT:
            self._phraseState = GROUP_END

        elif tokenOrGroup.tag is COMMA:
            if self._tokens:
                self._phrases << self._tokens
                self._startNewPhrase()
                self._awaitingTokensPostComma = True
            else:
                raise GroupError(
                    f'Encountered COMMA without a NAME - better error msg needed',
                    ErrSite(self.__class__, 'Encountered COMMA without a NAME'),
                    self, tokenOrGroup
                )

        elif tokenOrGroup.tag == SEMI_COLON:
            raise GroupError(
                f'{prettyNameByTag(tokenOrGroup.tag)} not allowed in from import - better error msg needed',
                ErrSite(self.__class__, f'{prettyNameByTag(tokenOrGroup.tag)} not allowed in from import'),
                self, tokenOrGroup
            )

        else:
            self._appendToken(tokenOrGroup, indent)
            self._awaitingTokensPostComma = False

        return self

    def _finishPhrase(self, indent, cause, tokenOrGroup):
        phrase = self._tokens
        if phrase:
            if cause == SUGGESTED_BY_LINE_BREAK:
                if indent > self._phraseIndent:
                    pass
                else:
                    phrase = _processAssigmentsInPhrase(phrase, self._exactlyOneNameInPhrase, self, tokenOrGroup, self.st)
                    self._phrases << phrase
                    self._startNewPhrase()
                    self._phraseState = GROUP_END
            elif cause == GROUP_END:
                phrase = _processAssigmentsInPhrase(phrase, self._exactlyOneNameInPhrase, self, tokenOrGroup, self.st)
                self._phrases << phrase
                self._startNewPhrase()
            else:
                # happens when there is no new line and this is the last statement
                phrase = _processAssigmentsInPhrase(phrase, self._exactlyOneNameInPhrase, self, tokenOrGroup, self.st)
                self._phrases << phrase
                self._startNewPhrase()
        else:
            if cause == SUGGESTED_BY_LINE_BREAK:
                if indent >= self._phraseIndent + MIN_INDENT:
                    # e.g. new line after load, new line after COMMA
                    pass
                else:
                    # end the load phrase
                    self._finalise(tokenOrGroup)
            elif cause == GROUP_END:
                self._finalise(tokenOrGroup)
            else:
                raise ProgrammerError()



# **********************************************************************************************************************
# Utilities
# **********************************************************************************************************************

@coppertop
def PPGroup(x):
    return x.PPGroup


_idSeed = 0
def _getId():
    global _idSeed
    _idSeed += 1
    return _idSeed


# these are typed collections that guard against the wrong thing being added
class _GuardedList(list):
    def __init__(self, sep, isTypeErrorFn):
        self._sep = sep
        self._isTypeError = isTypeErrorFn
        super().__init__()
    def sep(self, sep):
        self._sep = sep + ' '
        return self
    def __lshift__(self, other):   # self << other
        if self._isTypeError(other):
            raise TypeError()
        self.append(other)
        return self
    def __add__(self, other):
        for e in other:
            if self._isTypeError(e): raise TypeError()
            self.append(e)
        return self
    @property
    def first(self):
        return self[0]
    @property
    def last(self):
        return self[-1]
    @property
    def PPGroup(self):
        pps = [('' if e is Missing else e.PPGroup) for e in self]
        return self._sep.join(pps)
    @property
    def PPNames(self):
        pps = [('' if e is Missing else e.PPNames) for e in self]
        return self._sep.join(pps)
    def PPTC(self, depth):
        pps = [('' if e is Missing else e.PPTC(depth+1)) for e in self]
        return self._sep.join(pps)
    def append(self, other):
        if self._isTypeError(other): raise TypeError()
        return super().append(other)

class _TokensGL(_GuardedList):
    def __init__(self):
        super().__init__(
            ' ',
            lambda x: not isinstance(x, (Token, _Group))
        )

class _DotOrCommaSepGL(_GuardedList):
    def __init__(self, sep):
        super().__init__(
            sep + ' ',
            lambda x: not (
                isinstance(x, (_TokensGL, tcnode)) or
                x is Missing or
                (isinstance(x, Token) and x.tag is NULL)
            )
        )

class SemiColonSepCommaSep(_GuardedList):
    def __init__(self):
        super().__init__(
            '; ',
            lambda x: not (
                isinstance(x, _DotOrCommaSepGL) or
                x is Missing or
                (isinstance(x, Token) and x.tag is NULL)
            )
        )

class _CommaSepDotSepGL(_GuardedList):
    def __init__(self):
        super().__init__(
            ', ',
            lambda x: not (
                isinstance(x, _DotOrCommaSepGL) or
                x is Missing or
                (isinstance(x, Token) and x.tag is NULL)
            )
        )

class _SemiColonSepCommaSepDotSepGL(_GuardedList):
    def __init__(self):
        super().__init__(
            '; ',
            lambda x: not (
                isinstance(x, _CommaSepDotSepGL) or
                x is Missing or
                (isinstance(x, Token) and x.tag is NULL)
            )
        )



def toAssignLeft(t):
    assert t.tag == KEYWORD_OR_ASSIGN_LEFT
    return Token(
        t.srcId, t.src, ASSIGN_LEFT, t.indent,
        t.t, t.l1, t.l2, t.c1, t.c2, t.s1, t.s2
    )

def toAssignRight(t):
    assert t.tag == ASSIGN_LEFT
    return Token(
        t.srcId, t.src, ASSIGN_RIGHT, t.indent,
        t.t, t.l1, t.l2, t.c1, t.c2, t.s1, t.s2
    )

def toContextAssignRight(t):
    assert t.tag == CONTEXT_ASSIGN_LEFT
    return Token(
        t.srcId, t.src, CONTEXT_ASSIGN_RIGHT, t.indent,
        t.t, t.l1, t.l2, t.c1, t.c2, t.s1, t.s2
    )

def toGlobalAssignRight(t):
    assert t.tag == GLOBAL_ASSIGN_LEFT
    return Token(
        t.srcId, ':'+t.src[:-1], GLOBAL_ASSIGN_RIGHT, t.indent,
        t.t, t.l1, t.l2, t.c1, t.c2, t.s1, t.s2
    )


class _Stack:
    def __init__(self):
        self._list = []
    def push(self, x):
        self._list.append(x)
        return x
    def pop(self):
        self._list = self._list[0:-1]
    @property
    def current(self):
        return self._list[-1]
    @property
    def len(self):
        return len(self._list)


# from more_itertools import pairwise

from itertools import tee
def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


handlersByErrSiteId.update({
    ('bones.lang.parse_groups', Missing, 'parseStructure', 'Unhandled token') : '...',
    ('bones.lang.parse_groups', Missing, 'parseStructure', 'wanted got') : '...',

    ('bones.lang.parse_groups', Missing, '_processAssigmentsInPhrase', '_processAssigmentsInPhrase #1'): '...',
    ('bones.lang.parse_groups', Missing, '_processAssigmentsInPhrase', '_processAssigmentsInPhrase #2') : '...',
    ('bones.lang.parse_groups', Missing, '_processAssigmentsInPhrase', '_processAssigmentsInPhrase #3') : '...',
    ('bones.lang.parse_groups', Missing, '_processAssigmentsInPhrase', '_processAssigmentsInPhrase #4') : '...',
    ('bones.lang.parse_groups', Missing, '_processAssigmentsInPhrase', '_processAssigmentsInPhrase #5') : '...',
    ('bones.lang.parse_groups', Missing, '_processAssigmentsInPhrase', '_processAssigmentsInPhrase #6') : '...',
    ('bones.lang.parse_groups', Missing, '_processAssigmentsInPhrase', '_processAssigmentsInPhrase #7') : '...',
    ('bones.lang.parse_groups', Missing, '_processAssigmentsInPhrase', 'exactlyOneNameInPhrase and numNames != 1') : '...',

    ('bones.lang.parse_groups', 'FromImportGp', '_consumeToken', 'requires import after path') : '...',

    ('bones.lang.parse_groups', 'LoadGp', '_finalise', 'requires - no items specified') : '...',
    ('bones.lang.parse_groups', 'LoadGp', '_finalise', 'Encountered GROUP_END without a NAME') : '...',
    ('bones.lang.parse_groups', 'LoadGp', '_consumeToken', 'Encountered GROUP_END without a NAME') : '...',

    ('bones.lang.parse_groups', 'ParametersGp', '_finishPhrase', 'no args') : '...',
    ('bones.lang.parse_groups', 'ParametersGp', '_finishPhrase', 'Param type must not be <:...>') : '...',
    ('bones.lang.parse_groups', 'ParametersGp', '_consumeToken', 'assign right') : '...',

    ('bones.lang.parse_groups', 'SnippetGp', '_semicolonEncountered', 'SEMI_COLON not valid in snippet') : '...',
    ('bones.lang.parse_groups', 'SnippetGp', '_commaEncountered', 'COMMA not valid in snippet') : '...',
    ('bones.lang.parse_groups', 'SnippetGp', '_finishPhrase', 'Illegal empty phrase') : '...',

    ('bones.lang.parse_groups', 'FrameGp', '_dotEncountered', 'DOT not valid in group') : '...',
    ('bones.lang.parse_groups', 'FrameGp', '_finishPhrase', 'Illegal empty phrase') : '...',
    ('bones.lang.parse_groups', 'FrameGp', '_finishPhrase', 'Illegal new line') : '...',

    ('bones.lang.parse_groups', 'FrameKeysGp', '_finishPhrase', 'Illegal empty phrase') : '...',

    ('bones.lang.parse_groups', 'TupParenOrDestructureGp', '_commaEncountered', 'COMMA not valid in _DotSepPhrases') : '...',
    ('bones.lang.parse_groups', 'TypelangGp', '_finalise', '_finalise') : '',

    ('bones.lang.parse_groups', 'FuncOrStructGp', '_finishPhrase', 'Illegal empty phrase') : '...',
    ('bones.lang.parse_groups', 'FuncOrStructGp', '_semicolonEncountered', 'illegal SEMI_COLON in function body'): '...',
    ('bones.lang.parse_groups', 'FuncOrStructGp', '_commaEncountered', 'illegal COMMA in function body') : '...',
    ('bones.lang.parse_groups', 'FuncOrStructGp', '_processCloserOrAnswerError', 'null struct') : '...',
    ('bones.lang.parse_groups', 'FuncOrStructGp', '_processCloserOrAnswerError', 'assign left in single phrase binary') : '...',
})
