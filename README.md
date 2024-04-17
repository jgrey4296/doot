![doot](https://github.com/jgrey4296/doot/assets/5943270/170a5631-6175-4d92-8d66-e26aa2c2e472)
# doot
Version : 0.7.1  
Author  : John Grey  
Date    : 2022-12-09  

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
Examples and details can be found in the [Wiki](https://github.com/jgrey4296/doot/wiki)

### doot.toml
The `doot.toml` file provides a place for marking where doot considers the current working directory,
and lets you control general settings.
It is created from a default template by just running `doot`, if no `doot.toml` file exists.
If you don't want a separate file, everything can be added to `pyproject.toml` by prepending `tool.doot` to sections.

eg:
``` toml
# -*- mode:conf-toml; -*-
[settings.general]
notify                   = { say-on-exit = false }
loaders                  = { commands="default", task="default", parser="default"}
location_check           = { make_missing = true, print_levels={action="WARN", execute="WARN" } }

[settings.tasks]
sources = [".tasks"] # Files or directories where task specs can be loaded from, expanded according to [[locations]] keys
code    = []         # Directories where task specific code can be imported from, expanded according to [[locations]] keys
sleep   = { task=0.2, subtask=1, batch=1 }

[logging]
stream  = { level="WARN",  allow=["doot"], format="{levelname:<8} : {message}", colour=true }
file    = { level="DEBUG", allow=["doot"], format="{levelname:<8} : {message:<20} :|: (module:{module} line:{lineno} fn:{funcName})" }
printer = { level="INFO", colour=true}

[plugins]
# Allows for defining shorthands
command        = { other-run = "doot.cmds.run_cmd:RunCmd", tasks = "doot.cmds.list_cmd:ListCmd" }
report-line    = {}
reporter       = {}
action         = {}
task           = {}

[commands]
run = { tracker = "default", runner = "default", reporter= "default", report-line = []}

[[locations]]
temp          = ".temp"
desktop       = "~/Desktop"
```


### Tasks
Tasks are specified in toml, by default in the `doot.toml` file, or toml files in a `.tasks` directory, but that can be changed in `doot.toml:settings.tasks.sources`.
The easiest way to write one is to use `doot stub`.
eg: `doot stub mygroup::mytask` produces:

``` toml
[[tasks.mygroup]] # mygroup is the group this task is part of
name                 = "mytask" # combined together, this means this specific task is `mygroup::mytask`
version              = "0.1"    # <str>
ctor                 = "task"   # <type> the python class this task uses. See the plugins listed in 'doot plugins'
doc                  = ["Text to help understand what this task does"] # <list[str]>
required_for         = []                   # <list[DootTaskArtifact]> see below
depends_on           = []                   # <list[DootTaskArtifact]> see below
actions              = []                   # <list[Any]> See below
```

You can see what tasks are available by calling `doot list`.
You can get help on a specific task by calling `doot {task} --help` or `doot help {task}`.
You can run a task by calling `doot {task}` or `doot run {task}`.
eg: `doot mygroup::mytask`

### Actions
Tasks run a sequence of actions, specified in the following form. the argument to `do` can be an import specifier,
or an alias from the actions section of `doot plugins`:

``` toml
{ do="write!",                      args=[], aKwd="val" },
{ do="doot.actions.io:WriteAction", args=[], aKwd="val" },
```

You can get help on writing an action using `doot stub --Actions {action}`. eg: `doot stub --A write!` will print:

```
- Action write! : doot.actions.io:WriteAction
-- Declared kwargs for action: ['from_', 'to']

-- Toml Form:
{ do="write!", args=[] }

- For Custom Python Actions, implement the following in the .tasks director
def custom_action(spec:DootActionSpec, task_state:dict) -> None|bool|dict:...
```

When specifying values in toml you can use direct keys, or indirect keys.
For example, the action:
``` toml
{ do="log", msg="This is a test", level="INFO" }
```
will log that exact message, at that exact logging level.
Meanwhile the action:

``` toml
{ do="log", msg_="gen_msg", level="INFO" }
```
Will use the string stored in the task state's 'gen_msg' variable, assuming that variable has been set by a prior action, or the toml spec of the task.
This also allows you to specify the key to put information into:

``` toml
{ do="read!", from="{data}/names.txt", update_="names" }
```
This reads from the `names.txt` file, and adds it to the task state in the key `names`.

### Task Dependencies
Tasks can depend on other tasks, or artifacts like files.
These can be specified in the `required_for` and `depends_on` fields of a task spec.
To depend on a task, use its full name. eg: `examples::basic`.
To depend on a file, specify it with the prefix `file:>`. eg: `file:>./doot.toml`.

### String and Path expansion
To simplify using locations, both `doot.toml` and task toml files can have `[[locations]]` tables.
eg:
``` toml
[[locations]]
tasks   = ".tasks"
home    = "~"               # will be made into an absolute path when a task uses the {home} key in a path.
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

[project-entry-points."doot.plugins.action"]
an_action = "..."
```

Plugins are specified in the pyproject.toml table `[project.entry-points."doot.plugins.TYPE"]`,
where TYPE is one of the forms defined in variables found in `doot.constants`:
1) `FRONTEND_PLUGIN_TYPES` : "command", "reporter", "report-line",
2) `BACKEND_PLUGIN_TYPES`  : "tracker", "runner", "command-loader", "task-loader", "parser", "action", "job", "database"

Currently available plugins are listed with the command `doot plugins`.
They can be filtered with a simple pattern (`pattern:str in plugin.fullname:str` essentially).
