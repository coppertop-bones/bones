import antlr4

from bones.core.utils import assertRaises

from bones.lang._type_lang.py_interpreter import PyTypeManager as TM, PyTypeLangInterpreter as TLI, Atom, TLError



def test_atom():
    tli = TLI(tm := TM())
    t1 = tli.parse('''
        txt: atom
        txt
    ''')
    t2 = tm['txt']
    assert isinstance(t1, Atom), f'{t1} is not a Atom'
    assert t1 is t2 , f'{t1} is not {t2}'


def test_intersection():
    tli = TLI(tm := TM())
    tli.parse('''
        txt: isin: atom
        t1: isin & txt & isin
        t2: txt & isin & txt
    ''')
    t1 = tm['t1']
    t2 = tm['t2']
    assert t1 is t2, f'{t1} != {t2}'


def test_union():
    tli = TLI(tm := TM())
    tli.parse('''
        txt: err: atom
        t1: txt + err + err
        t2: err + txt + txt
    ''')
    t1 = tm['t1']
    t2 = tm['t2']
    assert t1 is t2, f'{t1} != {t2}'


def test_intersection_union_precedence():
    tli = TLI(tm := TM())
    tli.parse('''
        txt: isin: err: atom
        t1: txt & isin + err
        t2: err + isin & txt
    ''')
    t1 = tm['t1']
    t2 = tm['t2']
    assert t1 is t2, f'{t1} != {t2}'


def test_parse_expr():
    tli = TLI(tm := TM())
    tli.parse('''
        txt: isin: err: atom
        t1: txt & isin + err
    ''')
    t1 = tm['t1']
    t2 = tli.parse('err + isin & txt')
    assert t1 is t2, f'{t1} != {t2}'


def test_tuple():
    tli = TLI(tm := TM())
    tli.parse('''
        txt: isin: err: f64: atom
        t1: f64 * txt & isin + err
        t2: f64 * txt & isin + err * f64
        t3: f64 * txt & isin + err * f64
    ''')
    f64 = tm['f64']
    t1, t2, t3 = tm['t1'], tm['t2'], tm['t3']
    err, isin, txt = tm['err'], tm['isin'], tm['txt']
    u1 = tli.parse('err + isin & txt')
    assert t1.types == (f64, u1), f'{t1.types} != {(f64, u1)}'
    assert t2.types == (f64, u1, f64), f'{t2.types} != {(f64, u1, f64)}'
    assert t2 is t3, f'{t2} != {t3}'


def test_paren():
    tli = TLI(tm := TM())
    tli.parse('''
        txt: isin: err: f64: atom
        t1: f64 * txt & isin + err * f64 * txt & isin + err 
        t2: (f64 * txt & isin + err) * (f64 * txt & isin + err) 
        t3: f64 * txt & isin + err
        t4: t3 * t3
    ''')
    t1, t2, t4 = tm['t1'], tm['t2'], tm['t4']
    assert t1 is not t2, f'{t1} == {t2}'
    assert t2 is t4, f'{t2} == {t4}'


def test_doc2_othogonal_spaces():
    tli = TLI(tm := TM())

    src = '''
        index: txt: mem: atom
        pydict: pylist: atom in mem
    '''
    tli.parse(src)

    with assertRaises(TLError) as ex:
        tli.parse('pydict & pylist')

    with assertRaises(TLError) as ex:
        tli.parse('''
            (index ** txt) & pydict & 
            (index ** txt) & pylist
        ''')

    with assertRaises(Exception) as ex:
        # this is a bit more complex since we haven't thought through intersections of maps and seq only fns
        # e.g. (a ** b & mem) & (c ** d & mem)
        # e.g. (N ** b & mem) & (N ** d & mem)
        # in functions the return type is a union of all the return types
        tli.parse('(index ** txt & pydict) & (index ** txt & pylist)')
        raise Exception()


def test_arrow_intersections():
    tli = TLI(tm := TM())

    src = '''
        f64: txt: mem: index: atom
        peopleframe: (N ** {name:txt, age:f64}) & {name:N**txt, age:N**f64}
    '''
    tli.parse(src)

    src = '''
        listOfTxt: (N ** txt) & (index ** txt)
    '''
    tli.parse(src)


def test_runtime_fx():
    tli = TLI(tm := TM())

    src = '''
        ccyfx: ccysym: f64: atom
        ccy: ccy && {v:f64, ccy:ccysym} in ccyfx
        fx: fx && {v:f64, dom:ccysym, for:ccysym} in ccyfx

        convert_ccy_fn: ccy * fx ^ ccy
    '''

    # what about `fred: ccy && {v:f64, ccy:ccysym} in ccyfx`? or nested - can't tell until the assignment if it is
    # recursive - i.e. do we allocate a new inter or do we use the TBC and set the inter to be the recursive's main type

    t = tli.parse(src)


def test_static_fx1():
    tli = TLI(tm := TM())

    # NOTES:
    # - each ccy, GBP, JPY, etc is an intersection of ccy and orthognal to ccy
    # - each fx, GBPUSD, etc is an intersection of fx and domfor and orthognal to fx
    # - domfor types are not orthognal relying on the fx set to provide that
    # - parentheses are necessary around anonymous domfor creation to match with the predeclared ones
    # - fx and ccy are explicitly matched

    src = '''
        ccyfx: atom
        ccy: atom explicit in ccyfx
        GBP: GBP & ccy in ccy
        USD: USD & ccy in ccy
        JPY: JPY & ccy in ccy

        domfor: {dom: ccy & T1, for: ccy & T2}

        fx: atom explicit in ccyfx

        GBPUSD: fx & GBPUSD & {dom:GBP, for:USD} in fx
        USDJPY: fx & USDJPY & {dom:USD, for:JPY} in fx
    '''

    tli.parse(src)

    # NOTES:
    # - since domfor is not orthognal, domfor(GBP, USD) & domfor(USD, JPY) is valid
    src = '''
        # ccyfx: atom
        # ccy: atom explicit in ccyfx
        # GBP: GBP & ccy in ccy
        # USD: USD & ccy in ccy
        # JPY: JPY & ccy in ccy
        # 
        # domfor(T1, T2): {dom: ccy & T1, for: ccy & T2}
        # 
        # fx: atom explicit in ccyfx
        GBPUSD: fx & GBPUSD & domfor(GBP, USD) in fx
        USDJPY: fx & USDJPY & domfor(USD, JPY) in fx
        
        
        *: (ccy & T1) * (fx & {dom: ccy & T1, for: ccy & T2}) ^ (ccy & T2)
    '''


def test_static_fx2():
    tli = TLI(tm := TM())

    # NOTES:
    # - each ccy, GBP, JPY, etc is an intersection of ccy and orthognal to ccy
    # - each fx, GBPUSD, etc is an intersection of fx and domfor and orthognal to fx
    # - each domfor, GBP2USD, etc is an intersection of domfor and orthognal to domfor
    # - parentheses are necessary around anonymous domfor creation to match with the predeclared ones
    # - fx and ccy are explicitly matched

    src = '''
        ccyfx: atom
        ccy: atom explicit in ccyfx
        GBP: GBP & ccy in ccy
        USD: USD & ccy in ccy
        JPY: JPY & ccy in ccy
        
        domfor: {dom: ccy & T1, for: ccy & T2} & domfor in domfor
        GBP2USD: {dom:GBP, for:USD} & domfor in domfor
        USD2JPY: {dom:USD, for:JPY} & domfor in domfor
        
        fx: fx & domfor in ccyfx
        GBPUSD: fx & GBPUSD & ({dom:GBP, for:USD} & domfor) in fx
        USDJPY: fx & USDJPY & ({dom:USD, for:T1} & domfor) in fx
    '''

    tli.parse(src)

    src = '''
        ccyfx: atom
        ccy: ccy & T1 in ccyfx
        ccy(T1): ccy & T1 in ccy            // a type macro
        GBP: ccy(GBP)
        USD: ccy(USD)
        JPY: ccy(JPY)

        domforspc: atom
        domfor: {dom: ccy & T1, for: ccy & T2} & domfor in domforspc
        domfor(T1, T2): {dom: ccy & T1, for: ccy & T2} & domfor(T1,T2) in domforspc

        fx: fx & domfor in ccyfx
        fx(T1, T2): fx & {dom: ccy & T1, for: ccy & T2} & domfor in ccyfx
        
        GBPUSD: fx & GBPUSD & f(GBP, USD) in fx
        USDJPY: fx & USDJPY & domfor(USD, JPY) in fx
        
        
        *: (ccy & T1) * (fx(T1, T2)) ^ (ccy & T2)
        
        
        problem is we have {dom: ccy & T1, for: ccy & T2} & {dom: ccy & GBP, for: ccy & USD} in GBPUSD
    '''


    # NOTES:
    # three orthogonal spaces: ccy, fx, domfor
    # use && for intersections "in"
    # do not need type macros, but they would be useful for readability

    src = '''
        ccyfx: atom
        ccy: atom explicit in ccyfx             // disallow GBP & USD => GBP && ccy & USD && ccy
        fx: atom explicit in ccyfx              // disallow ccy & fx
        domfor: atom explicit in domfor         // allow fx & domfor
        
        ccy(T1): ccy(T1) && ccy in ccy          // a type macro
        GBP: ccy(GBP)
        GBP: GBP && ccy in ccy                  // where ccy(T1) is "GBP" and T1 is "GBP"
        USD: ccy(USD)
        USD: USD && ccy in ccy
        JPY: ccy(JPY)
        JPY: JPY && ccy in ccy

        domfor(T1, T2): domfor && {dom: ccy && T1, for: ccy && T2} in domfor
        GBP2USD: domfor(GBP, USD)
        GBP2USD: domfor && {dom:GBP, for:USD} in domfor      // where domfor(T1, T2) is "GBP2USD" and T1 is "GBP" and T2 is "USD"
        USD2JPY: domfor(USD, JPY)
        USD2JPY: domfor && {dom:USD, for:JPY} in domfor


        GBPUSD: fx & domfor(GBP, USD) in fx
        GBPUSD: fx & domfor && {dom:GBP, for:USD} in fx
        GBPUSD: fx & (domfor && {dom:GBP, for:USD} in domfor) in fx
        
        USDJPY: fx & domfor(USD, JPY) in fx
        USDJPY: fx & domfor && {dom:USD, for:JPY} in fx

        *: (ccy && T1) * (fx & domfor(T1, T2)) ^ (ccy && T2)
        *: (ccy && T1) * (fx & domfor && {dom: ccy && T1, for: ccy && T2})) ^ (ccy && T2)

    '''


def test_fitsWithin():
    tli = TLI(tm := TM())
    
    src = '''
        isin: err: mem: ccyfx: atom
        f64: txt: pylist: pydict: atom in mem
        ccy: fx: atom in ccyfx
    '''
    tli.parse(src)

    with assertRaises(TLError):
        tli.parse('f64 & txt')

    assert not tm.fitsWithin(tli.parse('isin'), tli.parse('txt'))

    assert tm.fitsWithin(tli.parse('isin & txt'), tli.parse('txt'))
    assert tm.fitsWithin(tli.parse('isin & txt'), tli.parse('isin'))
    assert tm.fitsWithin(tli.parse('isin & txt'), tli.parse('isin & txt'))

    assert tm.fitsWithin(tli.parse('isin'), tli.parse('isin + txt'))
    assert tm.fitsWithin(tli.parse('txt'), tli.parse('isin + txt'))
    assert tm.fitsWithin(tli.parse('isin + txt'), tli.parse('isin + txt'))



def test_files():
    tli = TLI(tm := TM())
    tli.parse(antlr4.FileStream('example.tl'))



def main():
    test_fitsWithin()
    test_atom()
    test_intersection()
    test_union()
    test_intersection_union_precedence()
    test_parse_expr()
    test_tuple()
    test_paren()
    test_doc2_othogonal_spaces()
    # test_doc2_othogonal_spaces()
    # test_arrow_intersections()
    # test_runtime_fx()
    # test_static_fx1()
    # test_static_fx2()
    # test_files()


if __name__ == '__main__':
    main()
    print('passed')

