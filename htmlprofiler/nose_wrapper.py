import nose
from htmlprofiler import HtmlProfiler

if __name__ == '__main__':
        nose.main(addplugins=[HtmlProfiler()])
