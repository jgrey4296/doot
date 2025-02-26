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
logging.setLevel(logmod.WARNING)
##-- end logging

def main():
    import doot
    from doot.control.main import DootMain
    main_obj = DootMain()
    main_obj.main()

if __name__ == "__main__":
    main()
