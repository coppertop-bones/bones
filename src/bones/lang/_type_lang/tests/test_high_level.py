import antlr4

from bones.core.utils import assertRaises

from bones.lang._type_lang.py_type_lang_interpreter import PyTypeManager, PyTypeLangInterpreter


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

    with assertRaises(Exception) as ex:
        # this is a bit more complex since we haven't thought through intersections of maps and seq only fns
        # e.g. (a ** b & mem) & (c ** d & mem)
        # e.g. (N ** b & mem) & (N ** d & mem)
        # in functions the return type is a union of all the return types
        pytli.parse('(index ** txt & pydict) & (index ** txt & pylist)')
        raise Exception()

def test_frame():
    tm = PyTypeManager()
    pytli = PyTypeLangInterpreter(tm)

    src = '''
        f64: txt: mem: atom
        peopleframe: (N ** {name:txt, age:f64}) & {name:N**txt, age:N**f64}
    '''
    pytli.parse(src)




def test_files():
    tm = PyTypeManager()
    pytli = PyTypeLangInterpreter(tm)
    pytli.parse(antlr4.FileStream('type_lang_test.tl'))



def main():
    test_doc2_othogonal_spaces()
    test_frame()
    # test_files()


if __name__ == '__main__':
    main()
    print('passed')

