#!/usr/bin/env python3
from dataclasses import dataclass, field, InitVar
import abc
import logging as root_logger
from bkmkorg.utils.dfs.files import get_data_files

logging = root_logger.getLogger(__name__)

file = str

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
            with open(t, 'r') as f:
                main += cls.read(f)

        return main

    @staticmethod
    def read(f:file) -> 'BaseFileFormat':
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
