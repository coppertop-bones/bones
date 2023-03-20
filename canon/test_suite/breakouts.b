/-
breakout ideas
-/

'{[type:python, mod:fred.joe.sally, compileWith:cython]
    @coppertop
    def addOne(x:int) -> int:
        return x + 1
}'


'{[category:panels, protocol:accessors]}'
colNames:{[x:table] ^ x `colNames}


'{[test]}'
{
    t: ([] a:`a)
    a colName check == `a
}
