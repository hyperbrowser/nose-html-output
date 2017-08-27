# -*- coding: iso-8859-1 -*-

"""
Copyright 2011-2017 Sveinung Gundersen and Øyvind Ingebrigtsen Øvergaard

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

------------------------------------------------------------------------

This module extends "htmloutput.py" to add profiling and call-
graph reporting to the HTML report, for each test.
"""

import cProfile
import cgi

import gprof2dot
import os
import pstats
import sys

try:
    import pygraphviz
except ImportError:
    pygraphviz = None

from htmloutput import HtmlOutput
from StringIO import StringIO
from xml.sax import saxutils


class HtmlProfiler(HtmlOutput):
    """Outputs the test results as a HTML file, including per-test profiling. Optionally also
supports the generation of call graph visualizations."""
    STATS_FILENAME = 'test.cprof'
    DOT_SUFFIX = '.dot'
    GRAPH_SUFFIX = '.png'

    CUMULATIVE = 'cumulative'
    INTERNAL = 'time'
    
    PROFILE_HEADER = {CUMULATIVE: '--- PROFILE (SORTED BY CUMULATIVE TIME)---\n',
                      INTERNAL: '--- PROFILE (SORTED BY INTERNAL TIME)---\n'}
    PROFILE_FOOTER = '--- END PROFILE ---'
    PROFILE_LINK = {CUMULATIVE: 'Profiling report (cumulative time)',
                    INTERNAL: 'Profiling report (internal time)'}

    PRUNED_CUMULATIVE = 'pruned_cumulative'
    PRUNED_INTERNAL = 'pruned_internal'
    NON_PRUNED = 'non_pruned'

    CALLGRAPH_NAME = {PRUNED_CUMULATIVE: 'call_graph_pruned_cumulative',
                      PRUNED_INTERNAL: 'call_graph_pruned_internal',
                      NON_PRUNED: 'call_graph_non_pruned'}
    CALLGRAPH_TITLE = {PRUNED_CUMULATIVE: 'Call-graph (pruned, colored by cumulative time)',
                       PRUNED_INTERNAL: 'Call-graph (pruned, colored by internal time)',
                       NON_PRUNED: 'Call-graph (not pruned, colored by cumulative time)'}

    LINK_TEMPLATE = """
</pre>
<a class ="popup_link" onfocus="this.blur();" href="javascript:showTestDetail('{0}')">{1}</a>
<p>
<div id='{0}' class="popup_window" style="background-color: #D9D9D9; margin-top: 10; margin-bottom: 10">
    <div style='text-align: right; color:black;cursor:pointer'>
        <a onfocus='this.blur();' onclick="document.getElementById('{0}').style.display = 'none' " >
           [x]</a>
    </div>
    <pre>{2}</pre>
</div>
</p>
<pre>"""  # divId, linkText, content

    IMG_TEMPLATE = """
<img src="{0}">
"""  # graph_filename

    TEMPERATURE_COLORMAP = gprof2dot.Theme(
        mincolor=(2.0 / 3.0, 0.80, 0.25),  # dark blue
        maxcolor=(0.0, 1.0, 0.5),  # satured red
        gamma=1.0,
        fontname='vera'
    )

    name = 'html-profiler'

    def __init__(self):
        super(HtmlProfiler, self).__init__()

    def options(self, parser, env=os.environ):
        if not self.available():
            return

        super(HtmlProfiler, self).options(parser, env=env)
        if pygraphviz:
            parser.add_option("--html-call-graph", action="store_true",
                              dest='call_graph',
                              help="Adds call graphs based on the profiling to the HTML file for "
                                   "each test.")
        parser.add_option("--html-profile-dir", action="store",
                          default=env.get('NOSE_HTML_PROFILE_DIR', 'results_profiles'),
                          dest="profile_dir",
                          metavar="FILE",
                          help="Use the specified directory to store the directory containing "
                               "call graph and statistic files for each individual test. The "
                               "result HTML file links to the call graph files thus created.")

    @classmethod
    def available(cls):
        return True

    def configure(self, options, conf):
        super(HtmlProfiler, self).configure(options, conf)

        if not self.available():
            return

        if not self.enabled:
            return

        self._profile_dir = os.path.abspath(options.profile_dir)
        if not os.path.exists(self._profile_dir):
            os.makedirs(self._profile_dir)

        self._call_graph = hasattr(options, 'call_graph') and options.call_graph

    def begin(self):
        if not self.available():
            return

        super(HtmlProfiler, self).begin()

    def prepareTestCase(self, test):
        """Wrap test case run in :func:`prof.runcall`.
        """
        if not self.available():
            return

        test_profile_filename = self._get_test_profile_filename(test)
        test_profile_dir = os.path.dirname(test_profile_filename)

        if not os.path.exists(test_profile_dir):
            os.makedirs(test_profile_dir)

        def run_and_profile(result, test=test):
            cProfile.runctx("test.test(result)", globals(), locals(),
                            filename=test_profile_filename, sort=1)

        return run_and_profile

    def _get_test_profile_dir(self, test):
        return os.path.join(self._profile_dir, self.startTime.strftime("%Y_%m_%d_%H_%M_%S"),
                            test.id())

    def _get_test_profile_filename(self, test):
        return os.path.join(self._get_test_profile_dir(test), self.STATS_FILENAME)

    def _get_test_dot_filename(self, test, prune):
        return os.path.join(self._get_test_profile_dir(test),
                            self.CALLGRAPH_NAME[prune] + self.DOT_SUFFIX)

    def _get_test_graph_filename(self, test, prune):
        return os.path.join(self._get_test_profile_dir(test),
                            self.CALLGRAPH_NAME[prune] + self.GRAPH_SUFFIX)

    def _generate_report_test(self, rows, cid, tid, n, t, o, e):
        o = saxutils.escape(o)

        o += self._get_profile_report_html(t, self.CUMULATIVE)
        o += self._get_profile_report_html(t, self.INTERNAL)

        if self._call_graph:
            o += self._get_callgraph_report_html(t, self.PRUNED_CUMULATIVE)
            o += self._get_callgraph_report_html(t, self.PRUNED_INTERNAL)
            o += self._get_callgraph_report_html(t, self.NON_PRUNED)

        super(HtmlProfiler, self)._generate_report_test(rows, cid, tid, n, t, o, e)

    def _get_profile_report_html(self, test, type):
        report = self._get_profile_report(test, type)
        return self._link_to_report_html(test, type, self.PROFILE_LINK[type], report)

    def _link_to_report_html(self, test, label, title, report):
        return self.LINK_TEMPLATE.format(test.id() + '.' + label, title, report)

    def _get_profile_report(self, test, type):
        report = capture(self._print_profile_report, test, type)
        report = cgi.escape(report)
        return report

    def _print_profile_report(self, test, type):
        stats = pstats.Stats(self._get_test_profile_filename(test))

        if stats:
            print self.PROFILE_HEADER[type]
            stats.sort_stats(type)
            stats.print_stats()
            print self.PROFILE_FOOTER

    def _get_callgraph_report_html(self, test, prune):
        report = self._get_callgraph_report(test, prune)
        return self._link_to_report_html(test, self.CALLGRAPH_NAME[prune],
                                         self.CALLGRAPH_TITLE[prune], report)

    def _get_callgraph_report(self, test, prune):
        self._write_dot_graph(test, prune)
        self._render_graph(test, prune)
        rel_graph_filename = os.path.relpath(self._get_test_graph_filename(test, prune),
                                             os.path.dirname(self.html_file))
        print>>open('out', 'w'), self._get_test_graph_filename(test, prune), os.path.dirname(self.html_file), rel_graph_filename
        return self.IMG_TEMPLATE.format(rel_graph_filename)

    def _write_dot_graph(self, test, prune=False):
        parser = gprof2dot.PstatsParser(self._get_test_profile_filename(test))
        profile = parser.parse()

        funcId = self._find_func_id_for_test_case(profile, test)
        if funcId:
            profile.prune_root(funcId)

        if prune == self.PRUNED_CUMULATIVE:
            profile.prune(0.005, 0.001, False)
        elif prune == self.PRUNED_INTERNAL:
            profile.prune(0.005, 0.001, True)
        else:
            profile.prune(0, 0, False)

        with open(self._get_test_dot_filename(test, prune), 'wt') as f:
            dot = gprof2dot.DotWriter(f)
            dot.graph(profile, self.TEMPERATURE_COLORMAP)

    def _find_func_id_for_test_case(self, profile, test):
        testName = test.id().split('.')[-1]
        funcIds = [func.id for func in profile.functions.values() if func.name.endswith(testName)]

        if len(funcIds) == 1:
            return funcIds[0]

    def _render_graph(self, test, prune):
        graph = pygraphviz.AGraph(self._get_test_dot_filename(test, prune))
        graph.layout('dot')
        graph.draw(self._get_test_graph_filename(test, prune))

    def finalize(self, result):
        if not self.available():
            return


def capture(func, *args, **kwArgs):
    out = StringIO()
    old_stdout = sys.stdout
    sys.stdout = out
    func(*args, **kwArgs)
    sys.stdout = old_stdout
    return out.getvalue()
