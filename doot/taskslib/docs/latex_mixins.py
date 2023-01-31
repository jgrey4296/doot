
##-- imports
from __future__ import annotations

import logging as logmod
from collections import defaultdict
from importlib.resources import files
from string import Template, ascii_uppercase

from instal.defaults import STATE_HOLDSAT_GROUPS, TEX_loc
from instal.interfaces.reporter import InstalReporter_i

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

##-- data
tex_path        = files("doot.__templates.text")

CHAIN_LINK      = Template((tex_path / "chain_link.tex").read_text())
CHAIN_NODE      = Template((tex_path / "chain_node.tex").read_text())

EVENT_LINK      = Template((tex_path / "event_link.tex").read_text())
EVENT_MACRO     = Template((tex_path / "event_macro.tex").read_text())
EVENT_SUBCHAIN  = Template((tex_path / "event_subchain.tex").read_text())

FLUENT          = Template((tex_path / "fluent.tex").read_text())
FLUENT_LINK     = Template((tex_path / "fluent_link.tex").read_text())
FLUENT_MACRO    = Template((tex_path / "fluent_macro.tex").read_text())
FLUENT_SUBCHAIN = Template((tex_path / "fluent_subchain.tex").read_text())

GANTT_BAR       = Template((tex_path / "gantt_bar.tex").read_text())
GANTT_CHART     = Template((tex_path / "gantt_chart.tex").read_text())
GANTT_MILESTONE = Template((tex_path / "gantt_milestone.tex").read_text())
GANTT_PRELUDE   = Template((tex_path / "gantt_prelude.tex").read_text())

HEADER_PAT      = Template((tex_path / "header_pattern").read_text())
INST_TERM       = Template((tex_path / "inst_term.tex").read_text())
PDF_PRELUDE     = Template((tex_path / "pdf_prelude.tex").read_text())
SUB_CHAIN       = Template((tex_path / "subchain.tex").read_text())
TERM            = Template((tex_path / "term.tex").read_text())
TERM_BODY       = Template((tex_path / "term_body.tex").read_text())
TRACE           = Template((tex_path / "trace.tex").read_text())
##-- end data

BOLD  : Final =  r"\textbf"
SOUT  : Final =  r"\sout"
EMPTY : Final = [r"$\emptyset$"]

def macro_key(num):
    """
    a simple conversion of digits to letters,
    for use in latex macro commands,
    without an external dependency
    """
    digits = str(num)
    letters = [ascii_uppercase[int(x)] for x in digits]
    return "".join(letters)

class LatexCompilerBase:
    _compiled_text = []

    def clear(self):
        self._compiled_text = []

    def expand(self, pattern:str|Template, **kwargs):
        match pattern:
            case Template():
                return pattern.safe_substitute(kwargs)
            case str() if not bool(kwargs):
                return pattern
            case str():
                return pattern.format_map(kwargs)
            case _:
                raise TypeError("Unrecognised compile pattern type", pattern)

    def insert(self, pattern:str|Template, **kwargs):
        """
        insert a given pattern text into the compiled output,
        formatting it with kwargs.
        """
        self._compiled_text.append(self.expand(pattern, **kwargs))

class GanttLatexMixin(LatexCompilerBase):
    """
    InstalGanttTracer
    Implementation of Reporter for gantt output.

    Milestones are events
    Bars are fluents
    """

    def prepare2(self):
        for t in range(1, len(observed) + 1):
            for x in occurred[t][:]:
                l = (str(x.arguments[0]) + ": " +
                        str(x.arguments[1])).replace('_', '\_')
                print("\\ganttmilestone{{{l}}}{{{f}}}\\ganttnewline"
                        .format(l=l, f=t - 1), file=tfile)

        facts = invert(holdsat)
        keys = sorted(facts, key=lambda atom: atom.arguments[0].name)
        for f in keys:
            print(
                r"\begin{ganttchart}[hgrid,vgrid,canvas/.style={draw=none},bar/.append style={fill=gray},x unit=0.5cm,y unit chart=0.5cm]{0}" +
                "{{{t}}}\n".format(t=len(observed) + 1), file=tfile)
            i = facts[f][0]
            l = (str(f.arguments[0]) + ": " +
                    str(f.arguments[1])).replace('_', '\_')
            print("\\ganttbar{{{label}}}{{{start}}}{{{finish}}}"
                    .format(label=l, start=i, finish=i), file=tfile)

    def render_term(self, term, inst=None) -> str:
        """
        Render a passed in ASTTerm into a useable latex string.
        Adapts to handle institutional terms and non.
        """
        body = ""
        if bool(term.params):
            body = self.expand(TERM_BODY, body=",".join(str(x) for x in term.params))

        match inst:
            case None:
                return self.expand(TERM,
                                   head=term.value,
                                   body=body.strip()).strip().replace("_", "\_").strip()
            case _:
                return self.expand(INST_TERM,
                                   head=term.value,
                                   body=body.strip(),
                                   inst=inst).strip().replace("_", "\_").strip()

    def render_fluents(self, state, prior_state=None) -> tuple[set, set, set]:
        """
        Separate out fluents in a state into
        {holding}, {initiated}, and {terminated} sets.

        """
        init   = {self.render_term(x.params[0]) for x in state.fluents if prior_state is None or x not in prior_state}
        holds  = {self.render_term(x.params[0]) for x in prior_state.fluents if x in state} if prior_state is not None else {}
        termin = {self.render_term(x.params[0]) for x in prior_state.fluents if x not in state} if prior_state is not None else {}

        init_render   = {self.expand(FLUENT, mod=BOLD,  term=term).strip() for term in init}
        holds_render  = {self.expand(FLUENT, mod="",    term=term).strip() for term in holds}
        termin_render = {self.expand(FLUENT, mod=SOUT, term=term).strip() for term in termin}

        return sorted(init_render), sorted(holds_render), sorted(termin_render)

    def render_milestones(self, trace, title="Observed Events", caption="Tracking the events in the trace") -> str:
        """
        Convert the trace to a gantt chart of milestones,
        where each milestone is an event observed in the trace
        """
        content = []

        for state in trace:
            for event in state.observed:
                event_s : str = self.render_term(event.params[0])
                milestone = self.expand(GANTT_MILESTONE,
                                        text=event_s,
                                        num=state.timestep,
                                        )
                content.append(milestone)

        chart = self.expand(GANTT_CHART,
                            content="\n".join(sorted(content)),
                            num=len(trace),
                            numPlusOne=len(trace)+1,
                            title=title,
                            caption=caption
                            )

        return chart

    def render_bars(self, trace, title="Fluents", caption="Gantt Chart for Fluent lives") -> str:
        """
        Convert the trace to a gantt chart,
        where the durations of each fluent are displayed
        """
        content = []
        intervals = trace.fluent_intervals()
        ## a a bar for the fact from start to finish
        for term, start, fin in intervals:
            term_s : str = self.render_term(term.params[0])
            content.append(self.expand(GANTT_BAR,
                                       text=term_s,
                                       start=str(start),
                                       end=str(fin)))

        # wrap in a chart, add to results
        chart = self.expand(GANTT_CHART,
                            content="\n".join(sorted(content)),
                            num=len(trace),
                            numPlusOne=len(trace)+1,
                            title=title,
                            caption=caption,
                            )
        return chart

    def render_bars_by_institution(self, trace) -> list[str]:
        """
        Convert the trace to n gantt charts,
        one for each institution
        """
        institution_list = trace.metadata['institutions']
        charts           = []

        for inst in institution_list:
            rejections = [x for x in institution_list if x != inst]
            f_trace    = trace.filter(allow=[inst], reject=rejections)
            inst_chart = self.render_bars(f_trace,
                                          title=f"{inst} Fluents",
                                          caption=f"Fluent Lives in institution {inst}")
            charts.append(inst_chart)

        return charts

    def trace_to_file(self, trace, path):
        self.clear()
        all_gantts = []
        # build event gantt
        all_gantts.append(self.render_milestones(trace))
        # build fluent gantt
        all_gantts.append(self.render_bars(trace))
        all_gantts += self.render_bars_by_institution(trace)

        # Insert prelude
        self.insert(GANTT_PRELUDE,
                    body="\n".join(all_gantts))

        with open(path, 'w') as f:
            f.write("\n".join(self._compiled_text))

class StateTracerMixin(LatexCompilerBase):
    """
        InstalPDFTracer
        Implementation of ABC InstalTracer for pdf output.
    """

    def render_term(self, term, inst=None) -> str:
        """
        Render a passed in ASTTerm into a useable latex string.
        Adapts to handle institutional terms and non.
        """
        body = ""
        if bool(term.params):
            body = self.expand(TERM_BODY,
                               body=",".join(str(x) for x in term.params))

        match inst:
            case None:
                return self.expand(TERM,
                                   head=term.value,
                                   body=body.strip()).strip().replace("_", "\_").strip()
            case _:
                return self.expand(INST_TERM,
                                   head=term.value,
                                   body=body.strip(),
                                   inst=inst).strip().replace("_", "\_").strip()

    def render_fluents(self, state, prior_state=None) -> tuple[set, set, set]:
        """
        Separate out fluents in a state into
        {holding}, {initiated}, and {terminated} sets.

        """
        init   = {self.render_term(x.params[0]) for x in state.fluents if prior_state is None or x not in prior_state}
        holds  = {self.render_term(x.params[0]) for x in prior_state.fluents if x in state} if prior_state is not None else {}
        termin = {self.render_term(x.params[0]) for x in prior_state.fluents if x not in state} if prior_state is not None else {}

        init_render   = {self.expand(FLUENT, mod=BOLD,  term=term).strip() for term in init}
        holds_render  = {self.expand(FLUENT, mod="",    term=term).strip() for term in holds}
        termin_render = {self.expand(FLUENT, mod=SOUT, term=term).strip() for term in termin}

        return sorted(init_render), sorted(holds_render), sorted(termin_render)

    def render_macros(self, trace) -> tuple[list, list]:
        event_macros  = []
        fluent_macros = []
        # Generate Macros
        for i, state, pre, post in trace.contextual_iter():
            macro = macro_key(i)
            # Render events to text
            obs   = [self.render_term(x.params[0]) for x in state.observed]
            occ   = [self.render_term(x.params[0]) for x in state.occurred]
            # Render states to text
            init, holds, term = self.render_fluents(state, pre)
            empty_state       = ["\item" + EMPTY[0]] if not any((init, holds, term)) else []

            event_macros.append(self.expand(EVENT_MACRO,
                                            key=macro,
                                            observed="\\\\\n    ".join(obs or EMPTY),
                                            occurred="\\\\\n    ".join(occ or EMPTY),
                                            )
                                )

            fluent_macros.append(self.expand(FLUENT_MACRO,
                                             key=macro,
                                             holding="\n    ".join(holds or empty_state),
                                             initiated="\n    ".join(init),
                                             terminated="\n    ".join(term),
                                             )
                                 )

        return (event_macros, fluent_macros)

    def trace_to_file(self, trace, path):
        """
        Write to a path the given trace, converted to latex
        """
        self.clear()

        try:
            trace_caption= trace.metadata['filename'].replace("_", "\_")
        except:
            trace_caption = "An Instal Trace"

        # Build the macros
        event_m, fluent_m = self.render_macros(trace)
        # build State chain args
        subchains         = [self.expand(SUB_CHAIN, num=i).strip() for i in range(len(trace))]
        # build State chain nodes
        chain_nodes       = [self.expand(CHAIN_NODE, num=i).strip() for i in range(len(trace))]
        # link the main states together
        chain_links       = [self.expand(CHAIN_LINK, num=i, numPlus=i+1).strip() for i in range(len(trace)-1)]

        # build event subchains
        event_subchains   = [self.expand(EVENT_SUBCHAIN, key=macro_key(i), num=i).strip() for i in range(len(trace)-1)]
        # build fluent subchains
        fluent_subchains  = [self.expand(FLUENT_SUBCHAIN, num=i, key=macro_key(i)) for i in range(len(trace))]
        # link event subchains to main
        event_links       = [self.expand(EVENT_LINK, num=i).strip() for i in range(len(trace)-1)]
        # link fluent subchains to main
        fluent_links      = [self.expand(FLUENT_LINK, num=i).strip() for i in range(len(trace))]

        # Trace
        trace_template = TRACE

        is_partial = True if trace[0].timestep != 0 else False
        is_vertical = False

        trace = self.expand(trace_template,
                            is_partial=r"\IsPartialTracetrue" if is_partial else "",
                            is_vertical=r"\IsVerticalTracetrue" if is_vertical else "",
                            last=len(trace)-1,
                            subchains="\n".join(subchains),
                            chain_nodes="\n".join(chain_nodes),
                            chain_links="\n".join(chain_links),
                            fluent_subchains="\n".join(fluent_subchains),
                            event_subchains="\n".join(event_subchains),
                            fluent_links="\n".join(fluent_links),
                            event_links="\n".join(event_links))

        # Combine it all in the prelude:
        self.insert(PDF_PRELUDE,
                    event_macros="\n".join(event_m),
                    fluent_macros="\n".join(fluent_m),
                    trace=trace,
                    caption=trace_caption
                    )

        # write
        with open(path, 'w') as f:
            f.write("\n".join(self._compiled_text))
