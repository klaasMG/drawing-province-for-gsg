from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
import sys
from PyQt5.QtWidgets import QApplication

class Worker(QObject):
    finished = pyqtSignal()

    def do_work(self):
        print("[Worker] Doing work...")
        # Doe hier je werk
        self.finished.emit()

app = QApplication(sys.argv)

thread = QThread()
worker = Worker()

worker.moveToThread(thread)

# Connect start van thread naar je method
thread.started.connect(worker.do_work)

# Optioneel: sluit thread als klaar
worker.finished.connect(thread.quit)
worker.finished.connect(worker.deleteLater)
thread.finished.connect(thread.deleteLater)

thread.start()

sys.exit(app.exec_())
