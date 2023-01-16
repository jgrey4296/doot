#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import pathlib as pl
import abc
import logging as root_logger
from dataclasses import InitVar, dataclass, field

##-- end imports

logging = root_logger.getLogger(__name__)

class BaseFileFormat(metaclass=abc.ABCMeta):

    sep : str = field(default=" : ")
    ext : str

    @classmethod
    def builder(cls, target, ext=None) -> 'BaseFileFormat':
        """
        Build an tag file from a target directory or file
        """
        main = cls()
        ext = ext or main.ext
        for t in get_data_files(target, ext):
            main += cls.read(t)

        return main


    @staticmethod
    def read(p:pl.Path) -> 'BaseFileFormat':
        pass

    @abc.abstractmethod
    def __iter__(self):
        pass

    @abc.abstractmethod
    def __str__(self):
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__}: {len(self)}>"

    @abc.abstractmethod
    def __iadd__(self, values) -> 'BaseFileFormat':
        pass

    @abc.abstractmethod
    def __len__(self):
        pass

    @abc.abstractmethod
    def __contains__(self, value):
        pass
