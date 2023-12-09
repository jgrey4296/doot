# doot Architecture

## Top Level

doot.setup inits the config
overlord loads plugins, parses cli args, and loads tasks, then triggers a cmd
cmd is the entry point to doing a particular thing.

## Configuration
Doot uses a `doot.toml` file to specify settings,
and either a `.tasks.toml` file or a `.tasks/**.toml` directory for task specification.

Both can be stubbed with `doot stub`

## Run
Loads a tracker, populates it with tasks, and sets start tasks
Loads a reporter,
Loads a runner, which uses the tracker to perform tasks, then reports using the reporter

## Taskers, Tasks and Actions
Taskers takes pre-existing tasks and applies them to multiple targets
Tasks perform a collection of actions on a particular target
Actions apply a single step of that task to the target

Taskers and Tasks fit into DootTaskSpec's
Actions are defined in toml as a list of:
1) a list of arguments to the task's intrinsic actions, or
2) a dict of { ctor = <str>, args = <list> }, or
3) a dict of { fun  = <str>, args = <list> }

which are converted to a TomlGuard for use.

that TomlGuard is passed either to the ctor, or made a partial function with functools.partial
when called, they are given a dict of the current task state,
which can be modified, and when returned is used to update the task state.

## CLI

The CLI automatically calls doot.setup (loading any doot.toml and pyproject.toml found in the cwd),
then uses doot.utils.log_config to set up logging from the loaded config,
then creates an overlord, which parses cli args and continues to start a cmd.
After it completes, it may announce it has finished.

`doot help` and `doot --help` offer initial instruction, and lists the available commands.

For any command, or task, add '--help' to the end of the instruction to get help.
So you can write what you remember of the call,
eg: `doot run task1`
and then add '--help' to figure out what next.

## Plugins
Using the pyproject.toml entry-points, plugins can be added to doot.
eg:
```toml
[project.entry-points."doot.plugins.command"]
example = "dootle.cmds.example_cmd:ExampleCmd"
difex   = "dootle.cmds.example_cmd:ExampleCmd"
```

The above adds two commands to the Doot cli interface, callable using `doot example` and `doot difex`.
