import sys
from PyQt5 import QtCore
import rules


if __name__ == '__main__':
    app = QtCore.QCoreApplication(sys.argv)
    monitor  = rules.RulesMonitor()
    sys.exit(app.exec_())
