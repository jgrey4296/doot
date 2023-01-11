##-- imports
from __future__ import annotations

import datetime
import pathlib as pl
import shutil
from collections import defaultdict
from doit.action import CmdAction

import doot
from doot.utils.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.tasker import DootTasker

##-- end imports

log_fmt     = doot.config.or_get(["%aI", "%h", "%al", "%s"]).tool.doot.git.fmt()
default_sep = doot.config.or_get(" :: ").tool.doot.git.sep()
group_hours = doot.config.or_get(2).tool.doot.git.group_by_hours()
bar_fmt     = doot.config.or_get("~").tool.doot.git.bar_fmt()
bar_max     = doot.config.or_get(40).tool.doot.git.bar_max()

def roundTime(dt=None, roundTo=60):
   """Round a datetime object to any time lapse in seconds
   dt : datetime.datetime object, default now.
   roundTo : Closest number of seconds to round to, default 1 minute.
   Author: Thierry Husson 2012 - Use it as you want but don't blame me.
   from: https://stackoverflow.com/questions/3463930
   """
   dt = dt or datetime.datetime.now()
   seconds = (dt.replace(tzinfo=None) - dt.min).seconds
   rounding = (seconds+roundTo/2) // roundTo * roundTo
   return dt + datetime.timedelta(0,rounding-seconds,-dt.microsecond)



class GitLogTask(DootTasker):
    """
    ([root] -> temp) Output a summary of the git repo, with a specific format
    see: https://git-scm.com/docs/git-log
    """

    def __init__(self, dirs:DootLocData, fmt:list[str]=None, sep:str=default_sep):
        super().__init__("git::logs", dirs)
        self.format = fmt or log_fmt
        self.sep    = sep

    def task_detail(self, task):
        task.update({
            "actions"  : [ CmdAction(self.get_log, shell=False, save_out="result"),
                           self.save_log,
                          ],
            "targets"  : [ self.dirs.temp / "full_git.log" ],
            "clean"    : True,
        })
        return task


    def get_log(self):
        log_format = self.sep.join(self.format)
        return ["git", "log", f"--pretty=format:{log_format}"]

    def save_log(self, task, targets):
        result = task.values['result']
        pl.Path(targets[0]).write_text(result)
        print("\n")

class GitLogAnalyseTask(DootTasker):
    """
    (temp -> build) separate the printed log
    """

    def __init__(self, dirs=None, sep=default_sep):
        super().__init__("git::analysis", dirs)
        self.sep           = sep
        self.group_by      = datetime.timedelta(hours=group_hours)
        self.total         = 0
        self.grouped_total = 0
        self.year_max      = None
        self.year_min      = None
        self.times         = defaultdict(lambda: 0)
        self.weekday_times = defaultdict(lambda: 0)
        self.weekdays      = defaultdict(lambda: 0)
        self.days          = defaultdict(lambda: 0)
        self.day_times     = defaultdict(lambda: 0)
        self.months        = defaultdict(lambda: 0)
        self.month_days    = defaultdict(lambda: 0)
        self.month_times   = defaultdict(lambda: 0)

        # Deltas in Days:
        self.deltas        = defaultdict(lambda: 0)
        # streaks / breaks
        # weekends / weekdays
        # day / night
        # tags
        # files touched

    def task_detail(self, task):
        task.update({
            "targets"  : [ self.dirs.build / "git.report",

                          ],
            "file_dep" : [ self.dirs.temp / "full_git.log" ],
            "actions"  : [
                self.process_log,
                self.write_distributions,
                     ],
        })
        return task

    def process_log(self, dependencies):
        last = None
        totals = []
        linecount = 0
        for line in pl.Path(dependencies[0]).read_text().split("\n"):
            linecount += 1
            if not bool(line.strip()):
                continue
            parts = line.split(self.sep)

            assert(len(parts) == 4), linecount
            commit : datetime = roundTime(datetime.datetime.fromisoformat(parts[0]), roundTo=60*60)
            totals.append(commit)


        totals.sort()
        self.total = len(totals)
        for commit in totals:
            if self.year_max is None:
                self.year_max = commit.year
            else:
                self.year_max = max(self.year_max, commit.year)
            if self.year_min is None:
                self.year_min = commit.year
            else:
                self.year_min = min(self.year_min, commit.year)

            
            # Deltas:
            diff = None
            if last is not None:
                diff = max(last, commit) - min(last, commit)
                self.deltas[diff.days] += 1

            last = commit
            if diff is not None and diff < self.group_by:
                continue

            self.grouped_total += 1
            self.times[commit.strftime("%H:%M")]                  += 1
            self.weekday_times[commit.strftime("%w: %H:%M (%a)")] += 1
            self.weekdays[commit.strftime("%w (%a)")]             += 1
            self.days[commit.strftime("%d")]                      += 1
            self.day_times[commit.strftime("%d: %H:%M")]          += 1
            self.months[commit.strftime("%m (%b)")]               += 1
            self.month_days[commit.strftime("%m %d (%b)")]        += 1
            self.month_times[commit.strftime("%m : %H:%M (%b)")]  += 1






    def write_distributions(self, targets):
        with open(targets[0], 'w') as f:
            print(f"Git Report", file=f)
            print(f"Total commits: {self.total}", file=f)
            print(f"With at least a day in between commits: {self.grouped_total}", file=f)
            print(f"Covering {self.year_min} - {self.year_max}", file=f)
            print("----------", file=f)
            print("", file=f)

            for name, data in zip(["times", "times by weekday", "weekday", "days of the month", "times by day of month", "month", "day by month", "time by month", "time between activity (to nearest day)"],
                                  [self.times, self.weekday_times, self.weekdays, self.days, self.day_times, self.months, self.month_days, self.month_times, self.deltas]):
                print("", file=f)
                print("----------", file=f)
                print(name, file=f)
                print("----------", file=f)
                print("", file=f)
                max_count = max(data.values())
                norm = bar_max / max_count
                for x,y in sorted(data.items()):
                    bar = bar_fmt * int(y * norm)
                    print(f"{x:>4} = {y:>7} |{bar}", file=f)
