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

logging    = logmod.getLogger(__name__)
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
