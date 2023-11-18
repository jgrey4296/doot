# doot

Author: John Grey
Date  : 2022-12-09

## Overview
This is an opinionated rewrite of the doit task runner.


### Actions

``` toml
{ do="write!",                      args=[], aKwd="val" }
{ do="doot.actions.io:WriteAction", args=[], aKwd="val" }
```

{key}_  : indirect keys that have a default internally. will be expanded according to state, and *that* value will be retrieved/expanded for use
eg: ```{do="read!", from_="{data_path}"}``` with state ```{'data_path':"{temp}/file.json", "temp":".temp"}``` will read .temp/file.json

the defaults for indirect keys are for typical chaining, like initing a bibtex db and then loading into it

Action standard kwargs:
from_   : the spec/state key to get primary data from
update_ : the state key to update with data from this action
_from    : a path to read from  (as "from" is a reserved word in python)
to      : a path to write to

## Examples
