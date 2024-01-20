---
title: ChangeLog
---


# 0.2.3 : 2023-12-10
Initial ... release.

# 0.3.0 : 2023-12-21
- Add reactive and auto queue behaviour for tasks.
- Rewrite action argument expansion, using DootKey
- bugfixes
# 0.3.1 : 2024-01-04
- refactor task specs to use mixins
- improve arg parser
- change file name prefix to "file:>"
# 0.4.1 : 2024-01-20
- refactor tasker -> job
- refactor walker 'filter_fn' -> 'accept_fn'
- add skipfile action
- add touch file action
- add de/compress actions
- add DootKey.redirect_multi
- add DootKey and Locations chaining/on_fail
- add postbox subboxs
- add postbox -> task expander mixin for job
- add headonly mixin
- add basic injection of cli params
