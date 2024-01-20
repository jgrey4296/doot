# doot

Author: John Grey
Date  : 2022-12-09

## Overview
This started out as an opinionated rewrite of the [doit](https://pydoit.org/contents.html) task runner.
For other, more mature alternatives, see [Luigi](https://github.com/spotify/luigi), and [SnakeMake](https://github.com/snakemake/snakemake)
and, of course, [GNU Make](https://www.gnu.org/software/make/).

Mainly, I found the process of authoring tasks and reusing them to be convoluted.
Doot is an attempt to simplify matters.
Settings and tasks are specified in toml files, which the doot program assists in writing.
More complicated logic is written in normal python, either as a library (eg: [Dootle](https://github.com/jgrey4296/dootle),
or as local task specific code.

To use doot, call `doot help`.

### doot.toml
The `doot.toml` file provides a place for marking where doot considers the current working directory,
and lets you control general settings.
It is created by just running `doot`, if no `doot.toml` file exists.

eg:
``` toml
# -*- mode:conf-toml; -*-
[settings.general]
loaders                  = { commands="default", task="default", parser="default"}
location_check           = { make_missing = true, print_levels={action="WARN", execute="WARN"}}

[settings.tasks]
sources = [".config/jg/templates/doot/home_tasks"] # Files or directories where task specs can be loaded from, expanded according to [[locations]] keys
code    = []                                       # Directories where task specific code can be imported from, expanded according to [[locations]] keys
sleep   = { tasks=0.2, subtask=1, batch=1 }

[plugins]
# Allows for defining aliases
command        = { other-run = "doot.cmds.run_cmd:RunCmd", tasks = "doot.cmds.list_cmd:ListCmd" }

[commands]
# Settings for commands, like telling the 'run' command what backends to use
run = { tracker = "default", runner = "default", reporter= "default", report-line = []}

[logging]
stream  = { level = "WARN", format  = "{levelname:<8} : {message}", filters = ["doot"] }
file    = { level = "DEBUG", format = "{levelname:<8} : {message:<20} :|: ({module}.{lineno}.{funcName})", filters =  ["doot"] }
printer = { colour = true }

[[locations]]
tasks        = ".tasks"
temp         = ".temp"
src          = "doot"

```


### Tasks
Tasks are specified in toml, by default in a `.tasks` directory, but that can be changed in `doot.toml:settings.tasks.sources`.
The easiest way to write one is to use `doot stub`.
The general form of a task is:

``` toml
[[tasks.examples]] # 'examples' is the group this task is part of
name                 = "basic" # combined together, this means this specific task is `examples::basic`
version              = "0.1"                # <str>
ctor                 = "task" # <type> the python class this task uses. See the plugins listed in 'doot plugins'
doc                  = ["Text to help understand what this task does"] # <list[str]>
actions              = []                   # <list[Any]> See below
required_for         = []                   # <list[DootTaskArtifact]> see below
depends_on           = []                   # <list[DootTaskArtifact]> see below
```

You can see what tasks are available by calling `doot list`.
You can get help on a specific task by calling `doot {task} --help` or `doot help {task}`.
You can run a task by calling `doot {task}` or `doot run {task}`.
eg: `doot examples::basic`

### Actions
Tasks run a sequence of actions, specified in the following form. the argument to `do` can be an import specifier, or an alias from `doot plugins`:

``` toml
{ do="write!",                      args=[], aKwd="val" },
{ do="doot.actions.io:WriteAction", args=[], aKwd="val" },
```

You can get help on writing an action using `doot stub --Actions {action}`. eg: `doot stub --A write!` will print:

```
- Action write! : doot.actions.io:WriteAction
-- Declared kwargs for action: ['from_', 'to']

-- Toml Form:
{ do="write!", args=[], inState=[], outState=[] } # plus any kwargs a specific action uses

- For Custom Python Actions, implement the following in the .tasks director
def custom_action(spec:DootActionSpec, task_state:dict) -> None|bool|dict:...
```

"{key}_"  : indirect keys that have a default internally. will be expanded according to state, and *that* value will be retrieved/expanded for use
eg: ```{do="read!", from_="{data_path}", update_="data"}``` with state ```{'data_path':"{temp}/file.json", "temp":".temp"}``` will read .temp/file.json into the task state's "data" key.

The defaults for indirect keys are for typical chaining, like initing a bibtex db and then loading into it.

Action standard kwargs:
from_   : the spec/state key to get primary data from
update_ : the state key to update with data from this action
from    : a path to read from  (as "from" is a reserved word in python)
to      : a path to write to

### Task Dependencies
Tasks can depend on other tasks, or artifacts like files.
these can be specified in the `required_for` and `depends_on` fields of a task spec.
To depend on a task, use its full name. eg: `eamples::basic`.
To depend on a file, specify it with the prefix `file://`. eg: `file://doot.toml`.

### String and Path expansion
To simplify using locations, both `doot.toml` and task toml files can have `[[locations]]` tables.
eg:
``` toml
[[locations]]
tasks   = ".tasks"
home    = "~"               # will be made into an absolute path when doot runs.
data    = "doot/data"       # A relative path, will be made absolute, according to cwd.
other   = "/somewhere/else" # Absolute paths can also be used.
subdata = "{data}/blah"     # {data} will expand to doot/data at runtime
```

Expansion of arguments is relatively straight forward, and is basically python string expansion.
Actions will expand parameters they support.
eg:
``` toml

actions = [
# This will write from the task state['data'] into the path "doot/data/example.txt":
{do="write!", from_="data", to="{data}/example.txt" },
# This will print to stdout the task state['data']:
{do="log",  msg="The data is: {data}" }
]
```

### Entry Points / Plugins
[Entry Points](https://packaging.python.org/en/latest/specifications/pyproject-toml/#entry-points) for doot to automatically recognise system installed packages are supported. Eg:

``` toml
# From dootle's pyproject.toml
[project.entry-points."doot.plugins.command"]
example = "dootle.cmds.example_cmd:ExampleCmd"
```

Plugins are specified in the pyproject.toml table `[project.entry-points."doot.plugins.TYPE"]`,
where TYPE is one of the forms defined in `doot.constants`:
1) Front End plugins: "command", "reporter", "report-line",
2) Back End plugins: "tracker", "runner", "command-loader", "task-loader", "parser", "action", "job", "database"

Currently available plugins are listed with the command `doot plugins`
