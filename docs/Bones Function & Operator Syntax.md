# 🦴 Bones Function & Operator Syntax

Bones offers a compact, expressive syntax for calling functions. Inspired by **Fortran**, **Smalltalk**, and **KDB**, 
it supports multiple calling styles with consistent, powerful semantics.

---


## 🔹 Function Call Styles

Bones supports three primary call syntaxes:

| Style         | Description                                     | Example                           |
|---------------|-------------------------------------------------|-----------------------------------|
| **Fortran**   | Function calls with parentheses and commas      | `(a, b)`                          |
| **Smalltalk** | Message-style unary, binary, and keyword calls  | `x plus y`, `cond ifTrue: block1` |
| **KDB**       | Ternary calls with three space-separated terms  | `a between b c`                   |

---


## 🔸 Fortran-style Calls

Use **parentheses and commas** to call or partially apply functions.

### 📌 Rules

- Commas define the function’s **arity**.
- Empty slots mean partial application.

### ✅ Examples

```bones
(x, y)         # call with 2 args
(x, )          # partial with first arg only
(, y)          # partial with second arg only
()             # no args (nullary function)
```

---


## 🔸 Smalltalk-style Calls

Inspired by **Smalltalk** (and adopted in **Swift**), Bones supports **unary**, **binary**, and **keyword message-style** calls.

### ✅ Unary:
```bones
x negate        # same as negate(x)
```
### ✅ Binary:
```bones
a plus b        # same as plus(a, b)
```

### ✅ Keyword-style (multi-arg):
```bones
cond ifTrue: block1 ifFalse: block2
```

This reads naturally:

> "If cond is true, do block1; otherwise, do block2."

Bones treats this as a message with **named parameters**, like in Smalltalk or Swift.

---

## 🔁 Equivalent Fortran-style
The above keyword call can also be expressed in **Fortran-style** syntax:

```bones
ifTrue:ifFalse: (cond, block1, block2)
```

This is the exact same logic, written using a traditional function name and comma-separated arguments.

| Smalltalk-style                       | Fortran-style                            |
| ------------------------------------- | ---------------------------------------- |
| `cond ifTrue: block1 ifFalse: block2` | `ifTrue:ifFalse: (cond, block1, block2)` |


Both forms are fully supported and equivalent. Choose whichever is more readable for your context.

---

## 🔸 KDB-style Ternary Calls
Ternary application uses three space-separated parts:

```bones
x between y z     # means between(x, y, z)
```
Used for simple range tests, like:

```bones
n between 1 100   # is n between 1 and 100?
```

---
## 🔸 Summary of Calling Syntax
| Form                  | Example                     | Interpreted As                |
| --------------------- | --------------------------- | ----------------------------- |
| **Fortran-style**     | `(x, y)`                    | `f(x, y)`                     |
| **Unary Smalltalk**   | `x f`                       | `f(x)`                        |
| **Binary Smalltalk**  | `x plus y`                  | `plus(x, y)`                  |
| **Keyword Smalltalk** | `cond ifTrue: a ifFalse: b` | `ifTrue:ifFalse:(cond, a, b)` |
| **KDB Ternary**       | `x f y z`                   | `f(x, y, z)`                  |
| **Partial (first)**   | `(x, )`                     | `λy. f(x, y)`                 |
| **Partial (second)**  | `(, y)`                     | `λx. f(x, y)`                 |
| **Empty**             | `()`                        | `λ. f()`                      |

---

✅ Notes
- You can freely mix styles — Bones resolves them unambiguously.
- Function names are **first-class** citizens.
- Keyword-style messages increase clarity for branching and expressive DSL-like patterns.

