"""


key formatting:

- key.format()
- '{}'.format(key)
- format(key, spec)

key -> str:
keep as a key if missing.
{x} -> {x}

_expand to string if not missing:
{x} -> blah
respect format specs if not missing:
{x: <5} -> 'blah  '
keep format specs if missing:
{x: <5} -> {x: <5}

-----

key expansion:
- key._expand(fmtspec, spec=actionspec, state=state)
- key(spec, state)

key -> str by default.

key -> path|type if conversion spec
{x!t} -> dict() etc..

----

format(DKey, fmt) -> DKey.__format__ -> str
DKey.__format__   -> str
Dkey.format       -> DKeyFormatter.fmt -> KF._expand -> KF.format -> str
DKey._expand       -> KF._expand -> KF.format -> KF._expand -> Any

----

Extends the format string syntax
https://docs.python.org/3/library/string.html#format-string-syntax
with additional DKey options:

Type Conversion:
!t : type formatting  eg: '{x!t}'+{x:dict(a=2,b=3)}    -> 'dict(a=2,b=3)'
!_ : key redirection. eg: '{x!_}'+{x_:blah, blah:bloo} -> {blah}
!k : as key,          eg: '{x!k}'+{x:blah, blah:bloo}  -> '{bloo}'
!CR : as coderef      eg: '{x!cr}'+{x:'doot.utils.key_formatter:DKeyFormatter} -> DKeyFormatter

and formating controls:

:.[0-9] : using precision for amount of recursive expansion
:#      : using alt form for 'direct' key: {key}
:#_     : indirect key form: {key_}
:...!   : bang at end of format spec means insist on expansion

Keys can have a number of forms:
{x}  : Direct Expansion form
{x_} : Indirect Expansion form
x    : Name form, no expansion




"""
