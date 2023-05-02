
from doot.actions.cmd_action import DootCmdAction

class DootPyActionExt(DootCmdAction):
    """
    Python Action with a `build` static method instead of doit.action.create_action
    and refactored `execute` to allow returning Actions from actions
    """

    @staticmethod
    def build(action, task_ref, param_name) -> BaseAction:
        """
        Create action using proper constructor based on the parameter type

        @param action: Action to be created
        @type action: L{BaseAction} subclass object, str, tuple or callable
        @param task_ref: Task object this action belongs to
        @param param_name: str, name of task param. i.e actions, teardown, clean
        @raise InvalidTask: If action parameter type isn't valid
        """
        result = None
        match action:
            case BaseAction():
                action.task = task_ref
                result = action
            case str():
                result = DootCmdAction(action, task_ref, shell=True)
            case list():
                reuslt = DootCmdAction(action, task_ref, shell=False)
            case tuple() if 1 <= len(action) < 4:
                py_callable, args, kwargs = (list(action) + [None] * (3 - len(action)))
                result = DootPyActionExt(py_callable, args, kwargs, task_ref)
            case _ if hasattr(action, '__call__'):
                result = DootPyActionExt(action, task=task_ref)
            case _:
                msg = "Task '{}': invalid '{}' type. got: {!r} {}".format(
                task_ref.name, param_name, action, type(action))
                raise InvalidTask(msg)

        return result

    def execute(self, out=None, err=None):
        """Execute command action

        both stdout and stderr from the command are captured and saved
        on self.out/err. Real time output is controlled by parameters
        @param out: None - no real time output
                    a file like object (has write method)
        @param err: idem

        @return failure: see CmdAction.execute
        """
        capture_io = self.task.io.capture if self.task else True
        # execute action / callable
        old_stdout, old_stderr = sys.stdout, sys.stderr

        if capture_io:
            output, errput = self._capture_io(out, err)
        else:
            if out:
                sys.stdout = out
            if err:
                sys.stderr = err

        try:
            kwargs = self._prepare_kwargs()
            returned_value = self.py_callable(*self.args, **kwargs)
            return self._handle_return(returned_value, self.py_callable)
        except Exception as exception:
            if self.pm_pdb:  # pragma: no cover
                # start post-mortem debugger
                deb = pdb.Pdb(stdin=sys.__stdin__, stdout=sys.__stdout__)
                deb.reset()
                deb.interaction(None, sys.exc_info()[2])
            return TaskError("PythonAction Error", exception)
        finally:
            # restore std streams /log captured streams
            if capture_io:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                self.out = output.getvalue()
                self.err = errput.getvalue()
            else:
                if out:
                    sys.stdout = old_stdout
                if err:
                    sys.stderr = old_stderr

    def _handle_return(self, value, called):
        # if callable returns false. Task failed
        match value:
            case False:
                return TaskFailed("Python Task failed: '%s' returned %s" % (called, value))
            case True | None:
                return None
            case str():
                self.result = value
            case dict():
                self.values = value
                self.result = value
            case BaseAction():
                return value
            case TaskFailed() | TaskError():
                return value
            case _:
                return TaskError("Python Task error: '%s'. It must return:\n"
                                "False for failed task.\n"
                                "True, None, string or dict for successful task\n"
                                "returned %s (%s)" %
                                (called, value, type(value)))

    def _capture_io(self, out, err) -> tuple:
        # set std stream
        output     = StringIO()
        out_writer = Writer()
        # capture output but preserve isatty() from original stream
        out_writer.add_writer(output)
        if out:
            out_writer.add_writer(out, is_original=True)
        sys.stdout = out_writer

        errput     = StringIO()
        err_writer = Writer()
        err_writer.add_writer(errput)
        if err:
            err_writer.add_writer(err, is_original=True)
        sys.stderr = err_writer

        return output, errput
