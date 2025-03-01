grammar TypeLang;

tl_body     : assign tl_body                        # ignore1
//            OPEN: check for unassigned recursives
            | expr_=expr EOF                        # return_expr
            ;

assign      : atom_=assign_atom                     # define_atom
            | expr_=assign_expr                     # define_expr
            ;

assign_atom : name_=NAME ':' assign_atom                    # atom_multi
            | name_=NAME ':' 'atom'                         # atom
            | name_=NAME ':' 'atom' 'in' atom_=get          # atom_in
            | name_=NAME ':' 'atom' 'exp'                   # atom_explicit
            | name_=NAME ':' 'atom' 'exp' 'in' atom_=get    # atom_explicit_in
            | name_=NAME ':' 'atom' 'implicitly' atom_=get  # atom_implicitly
            ;

get         : name_=NAME                            # name
            | '(' atom_=assign_atom ')'             # assign_atom2
            ;

assign_expr : name_=NAME ':' expr_=expr 'exp'       # explicit_expr
            | name_=NAME ':' expr_=expr             # assign_expr_to
            | name_=NAME ':' 'tbc'                  # prealloc
            ;

expr        : lhs_=expr '&' rhs_=expr               # inter
            | lhs_=expr '+' rhs_=expr               # union
            | lhs_=expr '*' rhs_=expr               # tuple
            | '{' fields_=fields '}'                # struct
            | '{{' fields_=fields '}}'              # rec
            | lhs_=SEQ_VAR '**' rhs_=expr           # seq
            | lhs_=expr '**' rhs_=expr              # map
            | lhs_=expr '^' rhs_=expr               # fn
            | lhs_=expr '[' rhs_=expr ']'           # inter_low
            | name_or_atom_=get                     # name_or_atom
            | '(' expr_=expr ')'                    # expr_parens
            | name_=SCHEMA_VAR                      # schema_var
            | '*(' expr_=expr ')'                   # mutable
            ;

comment     : comment_=LINE_COMMENT
            ;

fields      : name_=NAME ':' type_=expr
            | name_=NAME ':' type_=expr ',' rhs_=fields
            ;


SCHEMA_VAR      : 'T' DIGIT | 'T' DIGIT DIGIT;
SEQ_VAR         : 'N' | 'N' DIGIT | 'N' DIGIT DIGIT | 'N' [a-z];
NAME            : ALPHA ( ALPHA | DIGIT )*;

ALPHA           : ([a-z] | [A-Z] | '_')+;
DIGIT           : [0-9];
WHITESPACE      : (' ' | '\t') -> channel(HIDDEN);
NEWLINE         : ('\r'? '\n' | '\r')+ -> channel(HIDDEN);
LINE_COMMENT    : '//' ~( '\n'|'\r' )* '\r'? '\n' -> channel(HIDDEN);
