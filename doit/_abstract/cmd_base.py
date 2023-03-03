import inspect
import sys
from collections import deque
from collections import defaultdict
import textwrap

from .globals import Globals
from . import version
from .cmdparse import CmdOption, CmdParse
from .exceptions import InvalidCommand, InvalidDodoFile
from .dependency import CHECKERS, DbmDB, JsonDB, SqliteDB, Dependency, JSONCodec
from .action import CmdAction
from .plugin import PluginDict
from . import loader

def _wrap(content, indent_level):
    """wrap multiple lines keeping the indentation"""
    indent = ' ' * indent_level
    wrap_opt = {
        'initial_indent': indent,
        'subsequent_indent': indent,
    }
    lines = []
    for paragraph in content.splitlines():
        if not paragraph:
            lines.append('')
            continue
        lines.extend(textwrap.wrap(paragraph, **wrap_opt))
    return lines


class Command(object):
    """third-party should subclass this for commands that do no use tasks

    :cvar name: (str) name of sub-cmd to be use from cmdline
    :cvar doc_purpose: (str) single line cmd description
    :cvar doc_usage: (str) describe accepted parameters
    :cvar doc_description: (str) long description/help for cmd
    :cvar cmd_options:
          (list of dict) see cmdparse.CmdOption for dict format
    """

    # if not specified uses the class name
    name = None

    # doc attributes, should be sub-classed
    doc_purpose = ''
    doc_usage = ''
    doc_description = None  # None value will completely omit line from doc

    # sequence of dicts
    cmd_options = tuple()

    # `execute_tasks` indicates whether this command execute task's actions.
    # This is used by the loader to indicate when delayed task creation
    # should be used.
    execute_tasks = False

    def __init__(self, config=None, bin_name='doit', opt_vals=None, **kwargs):
        """configure command

        :param bin_name: str - name of command line program
        :param config: dict

        Set extra configuration values, this vals can come from:
         * directly passed when using the API - through DoitMain.run()
         * from an INI configuration file
        """
        self.bin_name = bin_name
        self.name = self.get_name()
        # config includes all option values and plugins
        self.config = config if config else {}
        self._cmdparser = None
        # option values (i.e. loader options)
        self.opt_vals = opt_vals if opt_vals else {}

        # config_vals contains cmd option values
        self.config_vals = {}
        if 'GLOBAL' in self.config:
            self.config_vals.update(self.config['GLOBAL'])
        if self.name in self.config:
            self.config_vals.update(self.config[self.name])

        # Use post-mortem PDB in case of error loading tasks.
        # Only available for `run` command.
        self.pdb = False


    @classmethod
    def get_name(cls):
        """get command name as used from command line"""
        return cls.name or cls.__name__.lower()

    @property
    def cmdparser(self):
        """get CmdParser instance for this command

        initialize option values:
          - Default are taken from harded option definition
          - Defaults are overwritten from user's cfg (INI) file
        """
        if not self._cmdparser:
            self._cmdparser = CmdParse(self.get_options())
            self._cmdparser.overwrite_defaults(self.config_vals)
        return self._cmdparser


    def get_options(self):
        """@reutrn list of CmdOption
        """
        return [CmdOption(opt) for opt in self.cmd_options]


    def execute(self, opt_values, pos_args):  # pragma: no cover
        """execute command
        :param opt_values: (dict) with cmd_options values
        :param pos_args: (list) of cmd-line positional arguments
        """
        raise NotImplementedError()


    def parse_execute(self, in_args):
        """helper. just parse parameters and execute command

        @args: see method parse
        @returns: result of self.execute
        """
        params, args = self.cmdparser.parse(in_args)
        self.pdb = params.get('pdb', False)
        params.update(self.opt_vals)
        return self.execute(params, args)

    def help(self):
        """return help text"""
        text = []
        text.append("PURPOSE")
        text.extend(_wrap(self.doc_purpose, 4))

        text.append("\nUSAGE")
        usage = "{} {} {}".format(self.bin_name, self.name, self.doc_usage)
        text.extend(_wrap(usage, 4))

        text.append("\nOPTIONS")
        options = defaultdict(list)
        for opt in self.cmdparser.options:
            options[opt.section].append(opt)
        for section, opts in sorted(options.items()):
            section_name = '\n{}'.format(section or self.name)
            text.extend(_wrap(section_name, 4))
            for opt in opts:
                # ignore option that cant be modified on cmd line
                if not (opt.short or opt.long):
                    continue
                text.extend(_wrap(opt.help_param(), 6))
                # TODO It should always display option's default value
                opt_help = opt.help % {'default': opt.default}
                opt_choices = opt.help_choices()
                opt_config = 'config: {}'.format(opt.name)
                if opt.env_var:
                    opt_env = ', environ: {}'.format(opt.env_var)
                else:
                    opt_env = ''
                desc = '{} {} ({}{})'.format(opt_help, opt_choices,
                                             opt_config, opt_env)
                text.extend(_wrap(desc, 12))

                # print bool inverse option
                if opt.inverse:
                    text.extend(_wrap('--{}'.format(opt.inverse), 6))
                    text.extend(_wrap('opposite of --{}'.format(opt.long), 12))

        if self.doc_description is not None:
            text.append("\n\nDESCRIPTION")
            text.extend(_wrap(self.doc_description, 4))
        return "\n".join(text)


######################################################################

# choose internal dependency file.
