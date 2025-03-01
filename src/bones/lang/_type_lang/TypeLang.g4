grammar TypeLang;


tl_body     : assignments end EOF                           # ignored_1c
            | assignments EOF                               # return_last
            | end EOF                                       # ignored_1c
            | assignments end unhandled EOF                 # ignored_1c
            | assignments unhandled EOF                     # return_last
            | end unhandled EOF                             # ignored_1d
            ;

assignments : assignments assign                            # ignored_2a
            | assign                                        # ignored_2b
            ;

end         : expr_=expr                                    # return_expr
            | name_or_atom_=get                             # return_named_or_atom
            ;

unhandled   : ~EOF*                                         # check_all_consumed
            ;

assign      : atom_=assign_atom                             # ignored_3a
            | expr_=assign_expr                             # ignored_3b
            ;

assign_atom : name_=NAME ':' assign_atom                    # atom_multi
            | name_=NAME ':' 'atom'                         # atom
            | name_=NAME ':' 'atom' 'in' atom_=get          # atom_in
            | name_=NAME ':' 'atom' 'explicit'              # atom_explicit
            | name_=NAME ':' 'atom' 'explicit' 'in' atom_=get    # atom_explicit_in
            | name_=NAME ':' 'atom' 'implicitly' atom_=get  # atom_implicitly
            ;

get         : name_=NAME                                    # name
            | '(' atom_=assign_atom ')'                     # atom_in_parens
            ;

assign_expr : name_=NAME ':' expr_=expr                     # assign_expr_to
            | name_=NAME ':' 'tbc'                          # prealloc
            ;

expr        : lhs_=expr '&&' rhs_=expr                      # inter_in
            | lhs_=expr '&' rhs_=expr                       # inter
            | lhs_=expr '+' rhs_=expr                       # union
            | lhs_=expr '*' rhs_=expr                       # tuple
            | '{' fields_=fields '}'                        # struct
            | '{{' fields_=fields '}}'                      # rec
            | lhs_=SEQ_VAR '**' rhs_=expr                   # seq
            | lhs_=expr '**' rhs_=expr                      # map
            | lhs_=expr '^' rhs_=expr                       # fn
            | lhs_=expr '[' rhs_=expr ']'                   # inter_low
            | name_or_atom_=get                             # name_or_atom
            | '(' expr_=expr ')'                            # expr_parens
            | name_=SCHEMA_VAR                              # schema_var
            | '*(' expr_=expr ')'                           # mutable
            | expr_=expr 'in' name_or_atom_=get             # expr_in
            ;

comment     : comment_=LINE_COMMENT
            ;

fields      : name_=NAME ':' type_=expr                     # ignored_4a
            | name_=NAME ':' type_=expr ',' rhs_=fields     # ignored_4b
            ;


SCHEMA_VAR      : 'T' DIGIT | 'T' DIGIT DIGIT;
SEQ_VAR         : 'N' | 'N' DIGIT | 'N' DIGIT DIGIT | 'N' [a-z];
NAME            : ALPHA ( ALPHA | DIGIT )*;

ALPHA           : ([a-z] | [A-Z] | '_')+;
DIGIT           : [0-9];
WHITESPACE      : (' ' | '\t') -> channel(HIDDEN);
NEWLINE         : ('\r'? '\n' | '\r')+ -> channel(HIDDEN);
LINE_COMMENT    : '//' ~( '\n'|'\r' )* '\r'? '\n' -> channel(HIDDEN);

