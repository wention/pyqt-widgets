import sys
import logging

from PyQt5.QtGui import QHideEvent, QMouseEvent
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

LOG = logging.getLogger(__name__)

class NavItem(QPushButton):
    def __init__(self, *args):
        super().__init__(*args)

        self.nav_menu = None

    def set_menu(self, menu):
        self.nav_menu = menu


class NavMenu(QWidget):
    def __init__(self, text=None, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setMouseTracking(True)

        self._eventloop = None

        self.text = text
        self.items = []
        self.active_item = None

        # UI
        self.lt = QHBoxLayout()
        self.setLayout(self.lt)

    def create_menu_item(self, text):
        item = NavItem(text, self)
        item.installEventFilter(self)
        self.lt.addWidget(item)
        self.items.append(item)
        return item

    def add_item(self, text):
        item = self.create_menu_item(text)
        return item

    def add_menu(self, text):
        item = self.create_menu_item(text)
        menu = NavMenu(text, self)

        item.set_menu(menu)

        return menu

    def set_active_item(self, item: NavItem):
        if self.active_item:
            pass

        if item.nav_menu:
            pos = self.mapToGlobal(item.geometry().bottomLeft())
            item.nav_menu.popup(pos)

        self.active_item = item

    def mouseMoveEvent(self, a0: QMouseEvent) -> None:
        return super().mouseMoveEvent(a0)

    def eventFilter(self, obj, event):
        type = event.type()
        if type == QEvent.Enter:
            LOG.debug("enter %s", obj.text())
            self.set_active_item(obj)
        elif type == QEvent.Leave:
            LOG.debug("leave %s", obj.text())

        return super().eventFilter(obj, event)

    def hideEvent(self, a0: QHideEvent) -> None:
        if self._eventloop:
            self._eventloop.exit()
        return super().hideEvent(a0)

    def popup(self, pos, item=None):
        self.move(pos)
        self.show()

    def exec_(self):
        pos = QCursor.pos()
        self.popup(pos)

        self._eventloop = QEventLoop()
        self._eventloop.exec_()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi()

    def setupUi(self):
        lt = QHBoxLayout()

        for i in range(5):
            btn = QPushButton('Button %d' % i)
            btn.clicked.connect(self.handle_btn_clicked)
            lt.addWidget(btn)

        w = QWidget(self)
        w.setLayout(lt)
        self.setCentralWidget(w)

    def handle_btn_clicked(self):
        menu = NavMenu()

        for i in range(5):
            m = menu.add_menu(f"item {i}")
            for k in range(5):
                mk = m.add_menu(f"item {i}:{k}")
                for j in range(5):
                    mk.add_item(f"item {i}:{k}:{j}")
        
        menu.exec_()


if __name__ == '__main__':
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    logging.basicConfig(level=logging.WARN, format="%(asctime)s %(levelname)s %(message)s")
    LOG.setLevel(logging.DEBUG)

    app = QApplication(sys.argv)

    w = MainWindow()
    w.show()

    sys.exit(app.exec_())
