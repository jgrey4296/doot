#!/usr/bin/env python3
from __future__ import annotations
from typing import Tuple, Any
from typing import Callable, Iterator, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic, TypeAlias
from typing import TYPE_CHECKING, Protocol, TypeGuard
from typing import Final, final, overload, runtime_checkable
import abc
from dataclasses import dataclass, field, InitVar
from string import Template
import logging as logmod
logging = logmod.getLogger(__name__)

if TYPE_CHECKING:
    # tc only imports
    pass

from bibtexparser import bwriter

head_line  = Template("@$entry{$id,")
field_line = Template("$indent$field$eq_buffer= $value,")
close_line = "}"

class JGBibTexWriter(bwriter.BibTexWriter):
    """
    A Modified writer to work nicely with org-ref-clean
    """

    def __init__(self, *args):
        super(JGBibTexWriter, self).__init__(*args)
        self.equals_column = 14
        self.entry_separator = "\n\n"

    def _entry_to_bibtex(self, entry):
        bibtex : list[str] = []
        # Write BibTeX key
        bibtex.append(head_line.substitute(entry=entry['ENTRYTYPE'], id=entry['ID']))

        # create display_order of fields for this entry
        # first those keys which are both in self.display_order and in entry.keys
        display_order = [i for i in self.display_order if i in entry]
        # then all the other fields sorted alphabetically
        display_order += [i for i in sorted(entry) if i not in self.display_order]

        # Write field = value lines
        for field in [i for i in display_order if i not in ['ENTRYTYPE', 'ID']]:
            try:
                buffer_val = " " * (self.equals_column - (len(self.indent) + len(field)))
                formatted  = field_line.substitute(indent=self.indent,
                                                   field=field,
                                                   eq_buffer=buffer_val,
                                                   value=bwriter._str_or_expr_to_bibtex(entry[field]))
                bibtex.append(formatted)
            except TypeError:
                raise TypeError(u"The field %s in entry %s must be a string" % (field, entry['ID']))
        bibtex.append(close_line)
        as_string = "\n".join(bibtex) + self.entry_separator
        return as_string
