#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging



class CmdAction(BaseAction):
    """
    Command line action. Spawns a new process.

    @ivar action(str,list,callable): subprocess command string or string list,
         see subprocess.Popen first argument.
         It may also be a callable that generates the command string.
         Strings may contain python mappings with the keys: dependencies,
         changed and targets. ie. "zip %(targets)s %(changed)s"
    @ivar task(Task): reference to task that contains this action
    @ivar save_out: (str) name used to save output in `values`
    @ivar shell: use shell to execute command
                 see subprocess.Popen `shell` attribute
    @ivar encoding (str): encoding of the process output
    @ivar decode_error (str): value for decode() `errors` param
                              while decoding process output
    @ivar pkwargs: Popen arguments except 'stdout' and 'stderr'
    """

    STRING_FORMAT = 'old'

    def __init__(self, action, task=None, save_out=None, shell=True,
                 encoding='utf-8', decode_error='replace', buffering=0,
                 **pkwargs):  # pylint: disable=W0231
        '''
        :ivar buffering: (int) stdout/stderr buffering.
               Not to be confused with subprocess buffering
               -   0 -> line buffering
               -   positive int -> number of bytes
        '''
        for forbidden in ('stdout', 'stderr'):
            if forbidden in pkwargs:
                msg = "CmdAction can't take param named '{0}'."
                raise InvalidTask(msg.format(forbidden))
        self._action = action
        self.task = task
        self.out = None
        self.err = None
        self.result = None
        self.values = {}
        self.save_out = save_out
        self.shell = shell
        self.encoding = encoding
        self.decode_error = decode_error
        self.pkwargs = pkwargs
        self.buffering = buffering

    @property
    def action(self):
        if isinstance(self._action, (str, list)):
            return self._action
        else:
            # action can be a callable that returns a string command
            ref, args, kw = normalize_callable(self._action)
            kwargs = self._prepare_kwargs(self.task, ref, args, kw)
            return ref(*args, **kwargs)


    def _print_process_output(self, process, input_, capture, realtime):
        """Reads 'input_' until process is terminated.
        Writes 'input_' content to 'capture' (string)
        and 'realtime' stream
        """
        if self.buffering:
            read = lambda: input_.read(self.buffering)
        else:
            # line buffered
            read = lambda: input_.readline()
        while True:
            try:
                line = read().decode(self.encoding, self.decode_error)
            except Exception:
                # happens when fails to decoded input
                process.terminate()
                input_.read()
                raise
            if not line:
                break
            capture.write(line)
            if realtime:
                realtime.write(line)
                realtime.flush()  # required if on byte buffering mode


    def execute(self, out=None, err=None):
        """
        Execute command action

        both stdout and stderr from the command are captured and saved
        on self.out/err. Real time output is controlled by parameters
        @param out: None - no real time output
                    a file like object (has write method)
        @param err: idem
        @return failure:
            - None: if successful
            - TaskError: If subprocess return code is greater than 125
            - TaskFailed: If subprocess return code isn't zero (and
        not greater than 125)
        """
        try:
            action = self.expand_action()
        except Exception as exc:
            return TaskError(
                "CmdAction Error creating command string", exc)

        # set environ to change output buffering
        subprocess_pkwargs = self.pkwargs.copy()
        env = None
        if 'env' in subprocess_pkwargs:
            env = subprocess_pkwargs['env']
            del subprocess_pkwargs['env']
        if self.buffering:
            if not env:
                env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'

        capture_io = self.task.io.capture if self.task else True
        if capture_io:
            p_out = p_err = subprocess.PIPE
        else:
            if capture_io is False:
                p_out = out
                p_err = err
            else:  # None
                p_out = p_err = open(os.devnull, "w")

        # spawn task process
        process = subprocess.Popen(
            action,
            shell=self.shell,
            # bufsize=2, # ??? no effect use PYTHONUNBUFFERED instead
            stdout=p_out,
            stderr=p_err,
            env=env,
            **subprocess_pkwargs)

        if capture_io:
            output = StringIO()
            errput = StringIO()
            t_out = Thread(target=self._print_process_output,
                           args=(process, process.stdout, output, out))
            t_err = Thread(target=self._print_process_output,
                           args=(process, process.stderr, errput, err))
            t_out.start()
            t_err.start()
            t_out.join()
            t_err.join()

            self.out = output.getvalue()
            self.err = errput.getvalue()
            self.result = self.out + self.err

        # make sure process really terminated
        process.wait()

        # task error - based on:
        # http://www.gnu.org/software/bash/manual/bashref.html#Exit-Status
        # it doesnt make so much difference to return as Error or Failed anyway
        if process.returncode > 125:
            return TaskError("Command error: '%s' returned %s" %
                             (action, process.returncode))

        # task failure
        if process.returncode != 0:
            return TaskFailed("Command failed: '%s' returned %s" %
                              (action, process.returncode))

        # save stdout in values
        if self.save_out:
            self.values[self.save_out] = self.out


    def expand_action(self):
        """Expand action using task meta informations if action is a string.
        Convert `Path` elements to `str` if action is a list.
        @returns: string -> expanded string if action is a string
                  list - string -> expanded list of command elements
        """
        if not self.task:
            return self.action

        # cant expand keywords if action is a list of strings
        if isinstance(self.action, list):
            action = []
            for element in self.action:
                if isinstance(element, str):
                    action.append(element)
                elif isinstance(element, PurePath):
                    action.append(str(element))
                else:
                    msg = ("%s. CmdAction element must be a str "
                           "or Path from pathlib. Got '%r' (%s)")
                    raise InvalidTask(
                        msg % (self.task.name, element, type(element)))
            return action

        subs_dict = {
            'targets': " ".join(self.task.targets),
            'dependencies': " ".join(self.task.file_dep),
        }

        # dep_changed is set on get_status()
        # Some commands (like `clean` also uses expand_args but do not
        # uses get_status, so `changed` is not available.
        if self.task.dep_changed is not None:
            subs_dict['changed'] = " ".join(self.task.dep_changed)

        # task option parameters
        subs_dict.update(self.task.options)
        # convert positional parameters from list space-separated string
        if self.task.pos_arg:
            if self.task.pos_arg_val:
                pos_val = ' '.join(self.task.pos_arg_val)
            else:
                pos_val = ''
            subs_dict[self.task.pos_arg] = pos_val

        if self.STRING_FORMAT == 'old':
            return self.action % subs_dict
        elif self.STRING_FORMAT == 'new':
            return self.action.format(**subs_dict)
        else:
            assert self.STRING_FORMAT == 'both'
            return self.action.format(**subs_dict) % subs_dict

    def __str__(self):
        return "Cmd: %s" % self._action

    def __repr__(self):
        return "<CmdAction: '%s'>" % str(self._action)
