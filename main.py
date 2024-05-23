import sys
import logging
from typing import Optional

from PyQt5.QtGui import QHideEvent, QMouseEvent
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

LOG = logging.getLogger(__name__)

class NavItem(QFrame):
    def __init__(self, text=None, parent=None):
        super().__init__(parent)

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.NoFocus)

        self.text = text

        self.menu: Optional["NavMenu"] = None

    def sizeHint(self):
        return QSize(60, 20)

    def set_menu(self, menu):
        self.menu = menu

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.drawRect(self.rect())
        painter.drawText(event.rect(), Qt.AlignCenter, self.text)

    def mouseMoveEvent(self, event: QMouseEvent):
        # LOG.debug('mouseMoveEvent: %s, pos: %s', self, event.pos())
        super().mouseMoveEvent(event)
        pass

    def __repr__(self):
        return f"<NavItem(text={self.text}, at {id(self)})>"

class CausedPopup:
    def __init__(self):
        self.widget: Optional[NavMenu] = None
        self.item: Optional[NavItem] = None

class NavMenu(QWidget):
    def __init__(self, text=None, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setMouseTracking(True)

        self._eventloop = None

        self.text = text
        self.items = []
        self.active_item: Optional[NavItem] = None
        self.active_menu: Optional[NavMenu] = None

        self.causedPopup = CausedPopup()

        # UI
        self.lt = QHBoxLayout()
        self.setLayout(self.lt)

    def create_menu_item(self, text):
        item = NavItem(text, self)
        # item.installEventFilter(self)
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

    def set_active_item(self, item: NavItem, popup: int, reason=None, activateFirst: bool=False):
        """
        :param item:
        :param popup:
                popup == -1 means do not popup, 0 means immediately, others mean use a timer
        :param reason:
        :param activateFirst:
        :return:
        """
        if self.active_item:
            pass

        if item.menu and popup == 0:
            self.popupItem(item)

        self.active_item = item

    def item_at(self, pos: QPoint):
        for item in self.items:
            if item.geometry().contains(pos):
                return item

    def mouseEventTaken(self, e: QMouseEvent) -> bool:
        if self.frameGeometry().contains(e.globalPos()):
            return False # otherwise if the event is in our rect we want it..

        caused = self.causedPopup.widget
        while caused is not None:
            cpos = caused.mapFromGlobal(e.globalPos())
            if caused.rect().contains(cpos):
                new_e = QMouseEvent(e.type(), cpos, caused.mapTo(caused.window(), cpos), e.screenPos(),
                e.button(), e.buttons(), e.modifiers(), e.source())
                QApplication.sendEvent(caused, new_e)
                return True

            caused = caused.causedPopup.widget

        return False

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if not self.isVisible() or self.mouseEventTaken(e):
            return

        hasMouse = self.rect().contains(e.pos())
        item = self.item_at(e.pos())

        LOG.debug('mouseMoveEvent: %s, hasMouse: %s, item: %s', self.text, hasMouse, item)
        if item is not None:
            self.set_active_item(item, 0)

        return super().mouseMoveEvent(e)

    def mousePressEvent(self, e: QMouseEvent):
        LOG.debug('mousePressEvent: %s - %s', self.text, e.pos())
        if not self.isVisible() or self.mouseEventTaken(e):
            return
        pass

    def mouseReleaseEvent(self, e: QMouseEvent):
        LOG.debug('mouseReleaseEvent: %s - %s', self.text, e.pos())
        if not self.isVisible() or self.mouseEventTaken(e):
            return

    def eventFilter(self, obj, e):
        type = e.type()
        if type == QEvent.Enter:
            LOG.debug("enter %s", obj.text())
            self.set_active_item(obj)
        elif type == QEvent.Leave:
            LOG.debug("leave %s", obj.text())

        return super().eventFilter(obj, e)

    def hideMenu(self, menu: "NavMenu"):
        if menu:
            menu.causedPopup.widget = None
            menu.causedPopup.item = None
            menu.close()
        pass

    def hideEvent(self, e: QHideEvent) -> None:
        if self._eventloop:
            self._eventloop.exit()

        if self.active_menu:
            self.hideMenu(self.active_menu)

        self.causedPopup.widget = None
        self.causedPopup.item = None

    def popupItem(self, item: NavItem):
        pos = self.mapToGlobal(item.geometry().bottomLeft())

        self.active_menu = item.menu

        self.active_menu.causedPopup.widget = self
        self.active_menu.causedPopup.item = item

        self.active_menu.popup(pos)

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
