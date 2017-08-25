import htmlprofiler.version
import setuptools

setuptools.setup(
    name="nosehtmlprofiler",
    version=htmlprofiler.version.__version__,
    author='Sveinung Gundersen',
    description="Nose plugin to output the test results as a HTML file "
                "including per-test profiling. Optionally also supports "
                "the generation of call graph visualizations.",
    license="Apache License, Version 2.0",
    url="https://github.com/hyperbrowser/nose-html-output",
    packages=["htmlprofiler"],
    install_requires=['nose', 'six', 'pygraphviz', 'gprof2dot'],
    obsoletes=['nosehtmloutput'],
    classifiers=[
        "Environment :: Console",
        "Topic :: Software Development :: Testing",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python"
    ],
    entry_points={
        'nose.plugins.0.10': [
            'html-profiler = htmlprofiler.htmlprofiler:HtmlProfiler'
        ]
    }
)
