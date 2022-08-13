#!/usr/bin/env python
##-- imports
from __future__ import annotations

from math import ceil
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import matplotlib
import matplotlib.pyplot as plt
##-- end imports

#plt.figure()
#plt.style.use('classic')
#plt.plot(X,Y)
#plt.imshow(matrx, cmap=plt.cm.gray_r)
#plt.show() / plt.draw() / plt.close()


def make_bar(k, v, left_pad_v, right_scale_v):
    pad = ((10 + left_pad_v) - len(k))
    bar_graph = ceil(((100 - pad) / right_scale_v) * v)
    full_str = "{}{}({}) : {}>\n".format(k, " " * pad, v, "=" *  bar_graph)
    return full_str
