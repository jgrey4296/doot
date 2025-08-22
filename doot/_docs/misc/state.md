# Lets Talk About State
As actions are of the form `def action(spec, state):...`, you can spend a lot of time
trying to get a value from the spec, the state, cli args, and registered locations, and if its missing entirely using a default.
Enter `DKey`.  

`DKey` is a utility class which extends `str` to define a key value that *may* exist in a source dictionary. 
If it does exist, the key can be expanded to its value. Additionally, DKey's can cast a retrieved value to a type, and provide a fallback value to use otherwise.
`DKey` can also be used as a decorator, to add retrieved values to the action's arglist.

## Creation
All `DKey` forms (for their are a few) are created through a single constructor: `DKey`.
Depending on the string passed in, and a couple of extra arguments, an appropriate key type is created
and customised.

``` python
from doot.structs import DKey
simple         : DKey = DKey("simple")
another_simple : DKey = DKey("{second}")
multi          : DKey = DKey("{simple} :: {second}")
typed_key      : DKey = DKey("something", check=set|list)
```

There are specialised DKey types:
```python
# Will expand to a path:
path_key = DKey[pl.Path]("{temp}/{name}.log")
# Will expand to a task name:
name_key = DKey[TaskName]("{blah}::{bloo}")
# Will expand to a code reference:
code_key = DKey[CodeReference]("doot.structs:{cls}")
# Redirection:
redirect = DKey("{test_}")
redirect_alt = DKey("{test}", mark=DKey.Marks.REDIRECT)
```

This can be done in TOML using string formatting type conversion:
```toml
a_name = "{key!p}" # path key
b_name = "{key!c}" # code key
c_name = "{key!R}" # redirect key
d_name = "{key!t}" # taskname key

```


## Expansion Logic
When you want to use a `DKey`'s value from a source, you expand it by passing in all the sources you want to try, in order:

``` python
from doot.structs import DKey
simple = DKey("simple")
result = simple.expand({"simple" : "blah"})
assert(result == "blah")
assert(simple.expand({}) is None)
assert(simple.expand({}, fallback="bob") == "bob")
assert(isinstance(simple.expand({"simple": set([1,2,3,4])}, check=set|list), set))
assert(simple.expand({"blah": 2}, {"simple": 5}) == 5)
```

## Fallbacks

## Decorators
Of course, manually expanding keys is only a slight improvement.
We can decorate actions, instead.

``` python
from doot.structs import DKeyed

@DKeyed.formats("name")
def my_action(spec, state, name:str):
    # Use name as you would normally here.
    return {}

@DKeyed.paths("file")
def my_file_action(spec, state, _fpath:pl.Path):
    # An underscore prefix allows the variable to be named different
    # from the key
    return {}

@DKeyed.types("library", check=None|list, fallback=[1,2,3,4])
@DKeyed.paths("lib_file")
def my_lib_action(spec, state, library, lib_file):
    # Multiple keys are retrieved,
    # if `library` isn't found, the default is.
    # if `library` is not a list, the action errors.
    return {}

```

If there is a disconnect between the key and the argument of the function,
the decorator will raise an error:

``` python
from doot.structs import DKeyed

@DKey.formats("name")
def my_action(spec, state, address):
   """ This will error on importing the file """
    return
```


## Paths 
Paths and locations can easily get complex, especially when working with variables.

``` python
from doot.structs import DKey
# Make a key that expands as a path
key = DKey[pl.Path]("{myroot}/subdir/{name}", explicit=True)
# Expand it:
result : pl.Path = key.expand({"myroot": pl.Path.cwd()}, {"name": "bob"})
assert(result == (pl.Path.cwd() / "subdir" / "bob"))
```
## Toml
Because `DKey`s are customized strings, this allows them to be specified in the TOML spec of tasks 
and actions.

``` toml
[[tasks.example]]
name = "key"
my-custom-value = "blah"
actions = [
    { do="log", msg="My custom value is {my-custom-value}" },
]
```

## Using type! to check state
Check the state of an action to ensure consistency.

``` toml
{ do="type!", {statekey}="typestr" }
```

## Subtypes of Keys

### Redirections
Consider if two actions use the key `name`, but for different things.
You want to use two different actual variable places in your sources: `name_a`, and `name_b`.
This is where redirections come in. Instead of having a direct key -> value relationship,
you can use an indirect key, `name_` -> `DKey` -> value.

``` python
from doot.structs import DKey
key = DKey("name_", mark=DKey.Marks.REDIRECT)
result = key.expand({"name": "blah", "name_": "name_a"}, {"name_a": "bob"})
assert(result == "name_a")
assert(isinstance(result, DKey))
expanded = result.expand({"name": "blah", "name_": "name_a"}, {"name_a": "bob"})
assert(expanded == "bob")
```


### Args and KWargs
What if you use an actions `args` field, or want to get all key-value pairings of an action spec?
You decorate with `@DKeyed.args` or `@DKeyed.kwargs`. 
These return a list or dict, respectively, without any further expansion.

### Imports
When you are interfacing with non-doot code, it can be useful to import things.
The decorator `@DKeyed.references` builds a key which interprets the retrieved value string
as a `jgdv.structs.code_ref.CodeReference`. This allows functions and classes to be easily imported,
specified by a task spec.

### Passing State between tasks: PostBoxes
State is internal to tasks by default.
To allow passing of results between tasks, there are *PostBoxes* (in `doot.actions.postbox`).
They are aliased as the actions `post.put` and `post.get`.

Essentially Postboxes are persistent pigeonholes that can be indexed by task names.
To add finer granularity, the last value after a root marker (ie: a space),
can be a subbox.
Thus:

> simple::task..a                : Refers to the postbox of 'simple::task', subbox 'a'.
> format::lib.bibtexs..finished  : Refers to 'format::lib.bibtexs', subbox 'finished'

Each subbox is a `list`, values are appended to the list, and iterables are concatenated.
Thus:

> post.put  simple::task..a = [1,2,3]
> post.put  simple::task..a = [4,5,6]
> post.put  simple::task..a = 7
> Result: [1,2,3,4,5,6,7]

As toml, the actual syntax is:
```toml
[[tasks.demonstration]]
name     = "postboxes"
word     = "boo"
wordlist = ["hello", "world"]
numlist  = [1,2,3,4]
actions  = [
    # This adds the expansions of the 'statevalN's to the current task's default subbox: '-'
    # So: demonstration::postboxes..- = ["boo", 1,2,3,4]
    { do="post.put", args=["word", "numlist"] },
    
    # This adds to an *implicit* box corresponding to the current task, with an explicit subbox:
    # So: demonstration::postboxes..a = ["hello", "world", 1,2,3,4]
    { do="post.put", a=["{wordlist}", "{numlist}"] },
    
    # This adds an expansion value to an explicit box and subbox:
    # So: simple::task..a = ["boo"]
    { do="post.put", "simple::task..a"="{word}" },
    
    # This adds multiple expansions to the same explicit box and subbox:
    # So: simple::task..a = ["boo", "boo", "boo"]
    { do="post.put", "simple::task..a"=["{word}", "{word}", "{word}"] },
    
]
```

To *retrieve* data from a postbox:
```toml
[[tasks.demonstration]]
name = "retrieval"
actions = [
    # Updates state['val1'] = ["boo", 1,2,3,4]
    { do="post.get", val1="demonstration::postboxes..-" } ,
    
    # Updates state['val2'] = ["hello", "world", 1,2,3,4]
    # and state['val3'] = ["boo"]
    { do="post.get", val2="demonstration::postboxes..a", val3="simple::task..a" },
]

```
