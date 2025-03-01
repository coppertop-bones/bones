import antlr4

from bones.core.utils import assertRaises

from bones.lang._type_lang.py_type_lang_interpreter import PyTypeManager, PyTypeLangInterpreter


# OPEN: can explicit, implicitly and in just be for atoms?

def test_doc2_othogonal_spaces():
    tm = PyTypeManager()
    pytli = PyTypeLangInterpreter(tm)

    src = '''
        index: txt: mem: atom
        pydict: atom in mem
        pylist: atom in mem
    '''
    pytli.parse(src)

    with assertRaises(Exception) as ex:
        pytli.parse('pydict & pylist')
        raise Exception()

    with assertRaises(Exception) as ex:
        pytli.parse('''
            (index ** txt) & pydict & 
            (index ** txt) & pylist
        ''')
        raise Exception()

    src = '''
        
    '''


    with assertRaises(Exception) as ex:
        # this is a bit more complex since we haven't thought through intersections of maps and seq only fns
        # e.g. (a ** b & mem) & (c ** d & mem)
        # e.g. (N ** b & mem) & (N ** d & mem)
        # in functions the return type is a union of all the return types
        pytli.parse('(index ** txt & pydict) & (index ** txt & pylist)')
        raise Exception()


def test_arrow_intersections():
    tm = PyTypeManager()
    pytli = PyTypeLangInterpreter(tm)

    src = '''
        f64: txt: mem: index: atom
        peopleframe: (N ** {name:txt, age:f64}) & {name:N**txt, age:N**f64}
    '''
    pytli.parse(src)

    src = '''
        listOfTxt: (N ** txt) & (index ** txt)
    '''
    pytli.parse(src)


def test_runtime_fx():
    tm = PyTypeManager()
    pytli = PyTypeLangInterpreter(tm)

    src = '''
        ccyfx: ccysym: f64: atom
        ccy: ccy && {v:f64, ccy:ccysym} in ccyfx
        fx: fx && {v:f64, dom:ccysym, for:ccysym} in ccyfx

        convert_ccy_fn: ccy * fx ^ ccy
    '''
    pytli.parse(src)


def test_static_fx1():
    tm = PyTypeManager()
    pytli = PyTypeLangInterpreter(tm)

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
        USDJPY: fx & USDJPY & (dom:USD, for:JPY} in fx
    '''

    pytli.parse(src)

    # NOTES:
    # - since domfor is not orthognal, domfor(GBP, USD) & domfor(USD, JPY) is valid
    src = '''
        ccyfx: atom
        ccy: atom explicit in ccyfx
        GBP: GBP & ccy in ccy
        USD: USD & ccy in ccy
        JPY: JPY & ccy in ccy

        domfor(T1, T2): {dom: ccy & T1, for: ccy & T2}

        fx: atom explicit in ccyfx
        GBPUSD: fx & GBPUSD & domfor(GBP, USD) in fx
        USDJPY: fx & USDJPY & domfor(USD, JPY) in fx
        
        
        *: (ccy & T1) * (fx & {dom: ccy & T1, for: ccy & T2}) ^ (ccy & T2)
    '''


def test_static_fx2():
    tm = PyTypeManager()
    pytli = PyTypeLangInterpreter(tm)

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
        
        fx: fx & domfor explicit in ccyfx
        GBPUSD: fx & GBPUSD & ({dom:GBP, for:USD} & domfor) in fx
        USDJPY: fx & USDJPY & ({dom:USD, for:JPY} & domfor) in fx
    '''

    pytli.parse(src)

    src = '''
        ccyfx: atom
        ccy: ccy & T1 explicit in ccyfx
        ccy(T1): ccy & T1 in ccy            // a type macro
        GBP: ccy(GBP)
        USD: ccy(USD)
        JPY: ccy(JPY)

        domforspc: atom
        domfor: {dom: ccy & T1, for: ccy & T2} & domfor in domforspc
        domfor(T1, T2): {dom: ccy & T1, for: ccy & T2} & domfor(T1,T2) in domforspc

        fx: fx & domfor explicit in ccyfx
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
        
        USDJPY: fx & domfor(USD, JPY) in fx
        USDJPY: fx & domfor && {dom:USD, for:JPY} in fx

        *: (ccy && T1) * (fx & domfor(T1, T2)) ^ (ccy && T2)
        *: (ccy && T1) * (fx & domfor && {dom: ccy && T1, for: ccy && T2})) ^ (ccy && T2)

    '''





def test_files():
    tm = PyTypeManager()
    pytli = PyTypeLangInterpreter(tm)
    pytli.parse(antlr4.FileStream('type_lang_test.tl'))



def main():
    test_doc2_othogonal_spaces()
    test_arrow_intersections()
    test_runtime_fx()
    test_static_fx1()
    test_static_fx2()
    test_files()


if __name__ == '__main__':
    main()
    print('passed')

