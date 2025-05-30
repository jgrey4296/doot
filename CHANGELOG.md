# Changelog

All notable changes to this project will be documented in this file.

(Generated using [git-cliff](https://git-cliff.org/)

## [1.1.1] - 2025-04-23

### Dependencies

- Bumpver targets
- Version 1.1.0 -> 1.1.1

## [1.1.0] - 2025-04-23

### Features

- Log msg guard
- Atexit handler and reporter controls
- Merge branch 'in.tree.docs'

### Bug Fixes

- Write action
- Tracking of abstract artifacts
- Split tracker
- Codereference usage
- Tests
- Caplog test targets
- Bumpver target for docs conf.py

### Dependencies

- Submodules
- Version 1.0.4 -> 1.1.0

### Refactoring

- Statemachine tracker to dootle
- New reporter interface
- Printers -> reporter
- Logging/reporting
- Run cmd interrupt control
- Docs to be in-tree
- Docs to in-tree

### Testing

- Path dkeys

## [1.0.4] - 2025-03-02

### Bug Fixes

- Injection of cli args

### Dependencies

- Py version in github actions
- Version 1.0.3 -> 1.0.4

## [1.0.3] - 2025-03-02

### Bug Fixes

- Dependency

### Dependencies

- Version 1.0.2 -> 1.0.3

## [1.0.2] - 2025-03-01

### Bug Fixes

- Version string test

### Dependencies

- Version 1.0.1 -> 1.0.2

## [1.0.1] - 2025-03-01

### Features

- Bumpver targets aliases/constants data files

### Bug Fixes

- Alias and constants version strs

### Dependencies

- Version 1.0.0 -> 1.0.1

## [1.0.0] - 2025-03-01

### Features

- Move action 'force' option
- Component tracker
- Required_for job head
- Branch 'statemachine.tracker'
- Global state aware dkey decorator
- Improved python error reporting
- Is_write_protected stub
- Cmd alias registration
- Constant INJECT_KEYS value
- Inject suffix option
- Taskspec recognition of jobs by name
- Branch 'refactor.injector'
- DKeyed extension tests
- Dkey extra kwargs
- Firefox refresher action
- Merge branch 'docs'
- Todo test markers

### Bug Fixes

- Config-less startup
- Logger typo
- Branch 'docs'
- Job expansion on emptylist/none source
- Cwd expansion
- Cleanup task halting
- Injection matching
- Tests
- Enums
- Tests
- Startup bugs
- Branch 'refactor.errors'
- Param spec sorting and use
- Help md and error printing
- Cmd selection
- Task loading and verification
- Commands and arg parsing
- Injection building
- Injection
- Location check
- Dkey import
- Path dkey final hooks
- Injection spec key checking
- Dkey global state access
- Injections not building required keys
- Tests
- Path modification
- Copy action key expansion
- Missing var
- Artifact exists check

### Dependencies

- Dependencies
- Jgdv version
- Submodule
- Version 0.13.0 -> 1.0.0

### Refactoring

- Auto dkey mark assignment
- Abstract loader specs
- Importer_m is obsolete
- Overlord to use loader_p for instance checks
- Build_injection and match_with_constraints to mixin
- Relationmeta to [needs, blocks]
- Relation injection/constraint format and use
- Shell action printing
- Traker build_network
- Matching out of injection_m to TaskMatcher_m
- Location/artifact
- Flagsbuilder_m
- Relationspec instantiation
- Enum declaration locations
- Artifact status out from task status
- Location dict keywords
- Old injection kwargs
- Enumbuilder_m and flagsbuilder_m to jgdv
- Key expansion to understand fallback=Self
- Redirection keys can return None
- Separate taskstatus and artifact  status
- Assertions to explicit errors
- Postbox to dootle
- Obsolete code
- Check_protocol, use jgdv instead
- Dkey and locations out to jgdv
- Tomlguard -> chainguard
- Tomlguard -> chainguard
- Update to pass tests
- Param spec to jgdv
- To use jgdv parser
- Base tracker transformer functionality
- Generate priority plan functionality
- Branch 'refactor.dkey.and.locations'
- Transformer tracking
- Transformer functionality
- Branch 'fix.trackers'
- Types
- Compress/json/speak time actions to dootle
- Errors
- Config loading, adding global task state
- Listcmd into separate mixins
- Logger use to use custom levels
- Stub cmd logging levels to 'user'
- Obsolete 'locs' command
- Imports and action decorators
- Cmd printing
- Cmd logging
- Trackers
- Overlord logging/printing
- Submodules
- Job actions to dootle
- Doot.mixins.injection -> injector
- Taskspec methods
- Action spec 'verify' calls
- Shell actions -> dootle
- Injection -> InjectSpec
- Build to be classmethod
- Trackers to have mixins
- Commands
- Runner and tests
- Locations -> locator
- Obsolete aliases
- Autodoc rst's
- Move static templates
- Protocols
- Typing imports
- Protocol and mixin use
- Base_cmd -> cmds.base
- Decorator definition
- Param spec names
- Main/init into classes
- Imports and test setup
- Doottracker -> naivetracker
- Unnecessary subprinter retrieval guard

### Testing

- Injection building

### [Merge]

- Branch 'docs'
- Branch 'fix.trackers'

### [submodule]

- Doot-examples

### [update]

- Sphinx config

## [0.13.0] - 2024-09-06

### Features

- Printer subchildren init
- Option to hardlink
- Log/print target control
- 'soft' kw for touch action
- State propagation to cleanup task
- Branch 'linux-main'

### Bug Fixes

- _printer_ retrieval
- Guard path touching
- Dkey checking to account for numpy extension in dootle
- Dkey handling of paths
- Typo
- Explicit multikey mark conflicts

### Dependencies

- Jgdv
- Version 0.12.0 -> 0.13.0

### Refactoring

- Requirements.txt
- Dkey meta to abstract
- Test organisation
- Shell interact

## [0.12.0] - 2024-08-25

### Bug Fixes

- Sh.command broke key expansion

### Dependencies

- Jgdv version
- Wiki
- Version 0.11.0 -> 0.12.0

### Refactoring

- Coderef and structuredname to jgdv
- Log config and spec
- Logging/printing use
- Coderef and structuredname to jgdv
- Factor log config and specs to jgdv

### [Merge]

- Branch 'factor.out.struct.name' into linux-main
- Branch 'refactor.logging' into linux-main
- Branch 'factor.out.log.config' into linux-main
- Branch 'linux-main'

### [data]

- Update templates

## [0.11.0] - 2024-08-19

### Features

- Globbing for copy action
- Docstring printing for stubbing actions
- Dkey expansion tests
- Track_l logging for tracker
- .related
- Empty cmd control
- Hide names in list cmd
- Branch 'linux-main'
- Branch 'feature.tracker.edge.annotations'
- Multikey expansion handling of subkey conflicts
- Branch 'feature.multikey.subkey.conflicts'

### Bug Fixes

- Postbox
- Task spec specialization
- Dkey expansion
- Job expansion
- Spec injection building
- Task spec flag init
- Parser
- Cleanup task tracking
- Mutikey expansion

### Dependencies

- Pre-commit
- Doot setup
- .related
- Version 0.10.0 -> 0.11.0

### Refactoring

- Agendas
- Dkey expansion
- Config commands -> config.settings.commands

### [agenda]

- Tag entries

### [internal]

- Add taskname query for relation spec
- Improve taskname
- Update tracker to use new task spec methods

## [0.10.0] - 2024-08-06

### Features

- Guard around key parsing
- Rotating logfile handler
- Branch 'cli_arg_fix' into linux-main

### Bug Fixes

- Shell action with no env
- Walking paths
- Sh decorators
- Error logging
- Job head generation and injection

### Dependencies

- Wiki
- Version 0.9.1 -> 0.10.0

## [0.9.1] - 2024-07-12

### Bug Fixes

- Mixed str/path key expansions
- Shell command chaining

### Dependencies

- Version 0.9.0 -> 0.9.1

## [0.9.0] - 2024-07-11

### Features

- Loop_yes_set and loop_no_set
- Tolerance for backup task time test
- Cleanup as a dependant group of a task
- Branch 'linux-main'
- Env to installed check
- Cwd for shell action
- Pydantic compatible protocol
- Dkey formatting and tests
- Dkey functionality
- Dkey implementation
- Redirect dkey re_marking
- Branch 'refactor-key' into linux-main
- Branch 'linux-main'
- Key type conversion
- Branch 'linux-main'
- Improved path expansion for keys
- Branch 'linux-main'

### Revert

- Original key formatting implementation

### Bug Fixes

- Alias typo of zip.new
- Action decorator bug
- Recursive location expansion
- Dkey paths
- Missing import
- Explicit key expansion

### Dependencies

- Wiki commit
- Version 0.8.3 -> 0.8.4
- Tests
- Tests
- Wiki
- Version 0.8.4 -> 0.9.0

### Refactoring

- Remove lambda assignments
- Relation spec to have constraints and injections
- Task spec
- File exists check
- Enum and flag names
- Job.queue.head
- Key decorator out to separate class
- Task name methods to mixin
- Key decorator -> Keyed
- Add dkey stubs
- Dkey
- Key
- Code to use dkey instead of key
- Protocols
- Dkey tests
- Dkey new logic
- Dkey ctor logic and expansion amounts

### Testing

- Postbox
- Dkey

## [0.8.3] - 2024-06-05

### Dependencies

- Version 0.8.2 -> 0.8.3

## [0.8.2] - 2024-06-05

### Bug Fixes

- Missing set_level for logging
- Job head queueing
- Job expansion subtask count

### Dependencies

- Version 0.8.1 -> 0.8.2

### [Merge]

- Branch 'linux-main'

## [0.8.1] - 2024-05-31

### Bug Fixes

- Readme header

### Dependencies

- Version 0.8.0 -> 0.8.1

## [0.8.0] - 2024-05-31

### Features

- Modelines, linting config
- TaskSpec.match_with_constraints
- Tracker constraint matching
- Tracker artifact dependency expansion
- Base transformer
- Protocols
- Plan generation, plus tests
- Tracker cleanup of dead tasks
- Todo org file
- Branch 'dependency-refactor' into linux-main
- Branch 'linux-main'

### Bug Fixes

- Cli arg expansion
- Typos
- Cli override of params
- Job injection
- Aliases after plugin load
- Limit logging of tracker active set
- Log action expansion
- Job expansion sources
- Typo
- Cli param handling
- Exit announcement
- Job_head name removes JOB
- Equality test
- Postbox
- Job head tracking
- Next_for api

### Dependencies

- Agenda
- Wiki
- Changelog
- Version 0.7.2 -> 0.8.0

### Refactoring

- TaskStateEnum -> TaskStatus_e
- Structs from dataclasses -> pydantic
- Reporter to have a base implementation
- Minor abstract and struct changes
- Separate into tracker, network, queue
- TomlLocation -> Location
- Artifact to be a subclass of Locationj
- DependencySpec -> RelationSpec
- TaskName roots implementation
- Task name access
- Action spec construction
- Remove use of mock_gen in test_flexible
- Taskname creation without a group
- Task spec to have a sources list
- Base protocols
- Task status progression
- Relation enum names
- Common names
- Common names
- Logging

### Testing

- Update
- Update
- Tracking of job heads

### [lint]

- Imports

## [0.7.2] - 2024-04-20

### Bug Fixes

- Wrong variable

### Dependencies

- Version 0.7.1 -> 0.7.2

### Refactoring

- Stubbing, removing mixins

### [Merge]

- Branch 'linux-main'

## [0.7.1] - 2024-04-17

### Bug Fixes

- Typos and bugs

### Dependencies

- Version 0.7.0 -> 0.7.1

### Refactoring

- Decorators
- Control flow actions
- Tracker
- Runner
- Job expansion and queuing

### Testing

- Update to passing

## [0.7.0] - 2024-04-15

### Features

- Job actions can build subtasks
- Json actions
- Tracker handling of str ctor
- Job actions implementations and tests
- Job actions
- Human numbers as util class
- Extension check action
- _test_setup
- Key .basic, .direct
- Location checks don't build file locations
- Coercion to str for io.write
- Log dir and log naming
- Decorators
- Taskspec entry conditions
- Jgdv as dependency

### Bug Fixes

- Missing import
- Edge case
- Locs access
- Task name str production
- Release task state after use
- Typos
- Typo
- Typos
- Doot.toml stubbing
- Job expansion name conflicts
- Tracker doesn't overwrite spec.extra now if args already exist
- Outdated import
- Is_write_protected
- Failure handling in base_runner

### Dependencies

- Wiki
- Version 0.6.1 -> 0.7.0

### Refactoring

- Constants and aliases to toml
- Postbox to use tasknames
- Job build in preference of job actions
- Key get logic to separate class
- Job actions to separate files
- Build as static method, make as instance method
- Path parts generation
- Mixins
- Import ordering to avoid cycles
- Artifact
- Locations
- Queue_behaviour
- Key getter.get -> chained_get
- Task_name building
- Tests
- Stubs to dootle
- Imports
- Runner/task action groups
- Locations to have normOnLoad
- Max_steps to config settings.tasks
- Enum usage

### Testing

- Update
- Key basic and get logic
- Job injection
- Job actions
- Skip tests awaiting refactor

## [0.6.1] - 2024-02-24

### Bug Fixes

- Bumpver
- Bumpver

### Dependencies

- Version 0.6.0 -> 0.6.1

## [0.6.0] - 2024-02-23

### Features

- Signal handler disabling for pre-commit
- Printer level stubbing
- Handle config failures
- Util retrievers for expanders
- Merge branch 'linux-main'

### Bug Fixes

- Postbox subkey expansion
- Walker unique name creation
- Task loading failure messaging
- Missing argument in summarizepost
- Source expansion
- Path expansion in io actions
- Signal handler construction

### Dependencies

- Version 0.5.2 -> 0.6.0

### Refactoring

- Mixin names
- Structured names
- Task state to taskbase
- Base tracker to separate private and public methods

### Testing

- Update

## [0.5.2] - 2024-02-14

### Features

- Basic distribution tasks

### Bug Fixes

- Typo
- Build_head missing keys handling
- Subtask dependency linking
- Shell tty out bool
- Typo and config bug

### Dependencies

- Version 0.5.1 -> 0.5.2

### Refactoring

- Job:limit to separate file

## [0.5.1] - 2024-02-06

### Bug Fixes

- Remove breakpoint left in

### Dependencies

- Version 0.5.0 -> 0.5.1

## [0.5.0] - 2024-02-06

### Features

- Symlink handling to key.to_path
- Shell action baked shell envs
- PathParts state mod action
- Setup actions mixin
- Cli param stubbing
- Key decorators
- Shell baking for pipelining

### Bug Fixes

- Key expansion order: cli->spec->state->locs

### Dependencies

- Version 0.4.0 -> 0.5.0

### Refactoring

- Locations.update
- Compression and json out of io.py
- Action args to use key decorators
- Doot.locs.expand -> normalize

## [0.4.0] - 2024-01-20

### Features

- Subtask sub_generator control
- Skipfile action, touch file action
- De/compression actions
- Dootkey.redirect_multi
- Move action
- Headonly mixin
- Job matcher/limiter
- Subkeys for postboxes
- Cli replacement of params in tracker
- Postbox -> task expander

### Bug Fixes

- None access
- Typo

### Dependencies

- Version 0.3.1 -> 0.4.0

### Refactoring

- Key and location expansion
- Tracker task adding
- Tasker -> job
- Runner
- Tracker
- Filter_fn -> accept_fn

## [0.3.1] - 2024-01-04

### Features

- Bumpver config
- Miniwalker to default plugins
- Fleixble parser to defaults
- Run time mixins

### Bug Fixes

- Typo
- Typo

### Refactoring

- Dootkey -> structs
- Specialisations -> mixins
- Mixin use + tests
- Code aliases
- Stubbing
- Test mocking
- Old arg parser

## [0.3.0] - 2023-12-21

### Features

- Plugins listing command
- Globber implementation
- Action spec, with state checking
- Default time announce action
- Step cmd implementation
- Bool handling in stub->toml
- Fstem for globber
- Io,postbox,state actions
- String expansion function
- Backupaction
- Clean command implementation
- Actions
- Actions
- New flexible arg parser
- Flexible cli parsing
- Lazy tree shadow
- Dependency
- Debug and typecheck actions
- Bumpver setup
- Auto and reactive queue behaviour

### Bug Fixes

- Task spec specialization
- Runner tests
- Specializing print levels
- String expansion
- Tree walking hitting directories
- Config var access
- Task prep bad logic
- Task prep
- Task building again
- Typo

### Refactoring

- Reporting
- Location checking
- Templates
- Mixins
- Remove obsolete
- Check dirs -> check locs
- Print and action level control
- Print control
- Globber -> walker
- Action file names
- State retreival
- Task source config
- Structs to separate submodule
- Expansions into a single file
- Default plugins to separate file
- Taskspec runs_before/after -> require-for/depends-on
- Tomler -> tomlguard
- Structuredname -> codereference & taskname
- Action argument expansion
- Arg expansion. Add DootKey
- Shell arg expansion

### Testing

- Reporters
- Fixing failures
- Fixing failures
- Update

<!-- generated by git-cliff -->
