#!/usr/bin/env python3
"""
The doot cli runner
"""
# ruff: noqa: PLR0912, BLE001, PLR0915
# Imports:
from __future__ import annotations

import logging as logmod

##-- logging
logging         = logmod.root
##-- end logging

if __name__ == '__main__':
    import doot
    from doot.control.main import DootMain
    main = DootMain()
    main.run_cmd()
