# **********************************************************************************************************************
# Copyright (c) 2025 David Briant. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance
# with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
# the specific language governing permissions and limitations under the License.
# **********************************************************************************************************************

import antlr4

from bones.core.utils import assertRaises

from bones.lang.core import TLError, bmtatm
from bones.lang.type_lang import TypeLangInterpreter
from bones.lang._type_lang.py_type_manager import PyTypeManager as TM
from bones.lang._type_lang.jones_type_manager import JonesTypeManager as TM



def test_atom():
    tli = TypeLangInterpreter(tm := TM())
    t1 = tli.parse('''
        txt: atom
        txt
    ''')
    t2 = tm['txt']
    assert t1.bmtid == bmtatm, f'{t1} is not a Atom'
    assert t1 is t2 , f'{t1} is not {t2}'


def test_intersection():
    tli = TypeLangInterpreter(tm := TM())
    tli.parse('''
        txt: isin: atom
        t1: isin & txt & isin
        t2: txt & isin & txt
    ''')
    t1 = tm['t1']
    t2 = tm['t2']
    assert t1 is t2, f'{t1} != {t2}'


def test_union():
    tli = TypeLangInterpreter(tm := TM())
    tli.parse('''
        txt: err: atom
        t1: txt + err + err
        t2: err + txt + txt
    ''')
    t1 = tm['t1']
    t2 = tm['t2']
    assert t1 is t2, f'{t1} != {t2}'


def test_intersection_union_precedence():
    tli = TypeLangInterpreter(tm := TM())
    tli.parse('''
        txt: isin: err: atom
        t1: txt & isin + err
    ''')
    t1 = tm['t1']
    t2 = tli.parse('err + isin & txt')
    assert t1 is t2, f'{t1} != {t2}'


def test_tuple():
    tli = TypeLangInterpreter(tm := TM())
    tli.parse('''
        txt: isin: err: f64: atom
        t1: f64 * txt & isin + err
        t2: f64 * txt & isin + err * f64
        t3: f64 * txt & isin + err * f64
    ''')
    f64 = tm['f64']
    t1, t2, t3 = tm['t1'], tm['t2'], tm['t3']
    u1 = tli.parse('err + isin & txt')
    assert t1.types == (f64, u1), f'{t1.types} != {(f64, u1)}'
    assert t2.types == (f64, u1, f64), f'{t2.types} != {(f64, u1, f64)}'
    assert t2 is t3, f'{t2} != {t3}'


def test_paren():
    tli = TypeLangInterpreter(tm := TM())
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
    tli = TypeLangInterpreter(tm := TM())

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

        # a function overload requires a langauge mechanism to select the actual function being used ideally statically
        # and dynamically if necessary. It is hard to imagine a memory backed data arrow serving the same role.
        # Therefore we will disallow more than one arrow per intersection. Structs and tuples can be converted in an
        # isomorphic manner so we probably don't need to be able to intersect them.from

        # what about fx?

        # GBPUSD: domfor & f64
        # GBPUSD: domfor & (f64 * ccy * ccy)

        # here the struct domfor is only a label, e.g.

        # (N ** txt & isin) & (index ** txt) & pylist   - a pylist of isin that is serializable
        # (N1 ** N2 ** f64) & (index ** f64) & array    - a serializable matrix

        # given that an overload is special is it really a intersection type?

        # i32 ^ txt
        # i32 ** txt
        # N ** txt

        # from the memory manager's perspective memory an object has extant and pointers (pointer location could be
        # data dependent which is more complex)


def test_arrow_intersections():
    tli = TypeLangInterpreter(tm := TM())

    src = '''
        f64: txt: mem: index: atom
        peopleframe: (N ** {name:txt, age:f64}) & {name:N**txt, age:N**f64}
    '''
    tli.parse(src)

    src = '''
        listOfTxt: (N ** txt) & (index ** txt)
    '''
    tli.parse(src)


def test_runtime_ccy():
    tli = TypeLangInterpreter(tm := TM())
    src = '''
        ccysym: atom
        GBP_: GBP_ & ccysym
        USD_: USD_ & ccysym
        GBP: GBP & ccysym in ccysym
        USD: USD & ccysym in ccysym
    '''
    tli.parse(src)
    # the following shows that "intersection" is not enough but "intersection in" is required
    tli.parse('GBP_ & USD_')
    with assertRaises(TLError):
        tli.parse('GBP & USD')
    assert tm.fitsWithin(tm['GBP'], tm['ccysym'])
    assert not tm.fitsWithin(tm['GBP'], tm['USD'])


def test_runtime_fx():
    tli = TypeLangInterpreter(tm := TM())
    src = '''
        ccyfx: ccysym: f64: atom
        ccy: ccy && {v:f64, ccy:ccysym} in ccyfx
        fx: fx && {v:f64, dom:ccysym, for:ccysym} in ccyfx
        convert_ccy_fn: ccy * fx ^ ccy
        GBP: GBP & ccysym in ccysym
        USD: USD & ccysym in ccysym
    '''
    tli.parse(src)



def test_runtime_fx_err():
    # ccy is correctly to be an implicit recursive type but is not used immediately in the assignment
    tli = TypeLangInterpreter(tm := TM())
    src = '''
        ccyfx: ccysym: f64: atom
        fred: ccy && {v:f64, ccy:ccysym} in ccyfx
    '''
    with assertRaises(TLError):
        tli.parse(src)


def test_static_fx1():
    tli = TypeLangInterpreter(tm := TM())

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
    tli = TypeLangInterpreter(tm := TM())

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
    tli = TypeLangInterpreter(tm := TM())
    
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

    assert tm.fitsWithin(tm['f64'], tm['T1'])



def test_recursive_space():
    tli = TypeLangInterpreter(tm := TM())
    tli.parse('domfor: atom explicit in domfor')



def test_files():
    tli = TypeLangInterpreter(tm := TM())
    tli.parse(antlr4.FileStream('example.tl'))



def main():
    test_recursive_space()
    test_runtime_ccy()
    test_fitsWithin()
    test_atom()
    test_intersection()
    test_union()
    test_intersection_union_precedence()
    test_tuple()
    test_paren()
    test_doc2_othogonal_spaces()
    # test_arrow_intersections()
    test_runtime_ccy()
    test_runtime_fx()
    test_runtime_fx_err()
    # test_static_fx1()
    # test_static_fx2()
    test_files()


if __name__ == '__main__':
    main()
    print('passed')

