#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import abc
import logging as logmod
from dataclasses import InitVar, dataclass, field
from string import Template
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)

from bibtexparser import bwriter

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

import doot
logging    = logmod.getLogger(__name__)

head_line  : Final         = Template("@$entry{$id,")
field_line : Final         = Template("$indent$field$eq_buffer= $value,")
close_line : Final         = "}"
default_field_sort : Final = ["author", "editor", "title", "subtitle", "short_parties", "year", "journal", "booktitle", "institution", "country", "tags"]
field_sort : Final         = doot.config.on_fail(default_field_sort, list).bibtex.field_sort()
indent_column : Final      = doot.config.on_fail(14, int).bibtex.indent_column()

class TODO_BibtexWriter_i:
    """ TODO replace bibtexparser writer with custom interface """
    def write(self, db:list[dict]):
        raise NotImplementedError()




class JGBibTexWriter(bwriter.BibTexWriter):
    """
    A Modified writer to work nicely with org-ref-clean
    """

    def __init__(self, *args):
        super(JGBibTexWriter, self).__init__(*args)
        self.equals_column   = indent_column
        self.entry_separator = "\n"
        self.display_order   = field_sort

    def _entry_to_bibtex(self, entry) -> str:
        filtered_entry     = {x:y for x,y in entry.items() if x[:2] != "__"}
        bibtex : list[str] = []
        # Write BibTeX key
        bibtex.append(head_line.substitute(entry=filtered_entry['ENTRYTYPE'], id=filtered_entry['ID']))

        # create display_order of fields for this entry
        # first those keys which are both in self.display_order and in entry.keys
        display_order = [i for i in self.display_order if i in filtered_entry]
        # then all the other fields sorted alphabetically
        display_order += [i for i in sorted(filtered_entry) if i not in self.display_order]

        # Write field = value lines
        for field in [i for i in display_order if i not in ['ENTRYTYPE', 'ID']]:
            try:
                buffer_val = " " * (self.equals_column - (len(self.indent) + len(field)))
                field_val  = bwriter._str_or_expr_to_bibtex(filtered_entry[field])
                # Remove unnecessary double wrapping
                if field_val[:2] == "{{" and field_val[-2:] == "}}":
                    field_val = field_val[1:-1]

                formatted  = field_line.substitute(indent=self.indent,
                                                   field=field,
                                                   eq_buffer=buffer_val,
                                                   value=field_val)
                bibtex.append(formatted)
            except TypeError:
                raise TypeError(u"The field %s in entry %s must be a string" % (field, filtered_entry['ID']))
        bibtex.append(close_line)
        as_string = "\n".join(bibtex) + self.entry_separator
        return as_string


class JGMarkdownWriter:
    """
    For converting bibtex files to markdown
    """

    def write(self, db) -> str:
        results = []
        for entry in db.entries:
            results.append(self._write_entry(entry))

        return "\n".join(results)

    def _write_entry(self, entry:dict) -> str:
        # TODO use templates?
        return str(entry)
