import sys
import logging
from typing import Optional

from PyQt5.QtGui import QHideEvent, QMouseEvent
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

LOG = logging.getLogger(__name__)

class NavItem(QWidget):
    def __init__(self, text=None, parent=None):
        super().__init__(parent)
        self.setProperty("class", ["navitem"])

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.NoFocus)

        self.text = text

        self.menu: Optional["NavMenu"] = None

        self.activated = False

    def setActivated(self, activated: bool):
        self.activated = activated
        self.update()

    def sizeHint(self):
        return QSize(120, 40)

    def set_menu(self, menu):
        self.menu = menu

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        if self.activated:
            painter.fillRect(event.rect(), QColor(255, 0, 0, 200))
        painter.drawRect(self.rect())
        painter.drawText(event.rect(), Qt.AlignCenter, self.text)

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

        # 点击项 / triggered action
        self.sync_item: Optional[NavItem] = None

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

    def set_active_item(self, item: Optional[NavItem], popup: int = -1, reason=None, activateFirst: bool = False):
        """
        选中菜单项

        :param item:
        :param popup:
                popup == -1 means do not popup, 0 means immediately, others mean use a timer
        :param reason:
        :param activateFirst:
        :return:
        """
        LOG.debug("set active item: %s", item)
        hide_active_menu = self.active_menu
        prev_item = self.active_item
        self.active_item = item
        if item:
            item.setActivated(True)

        if prev_item and prev_item != self.active_item:
            prev_item.setActivated(False)

        if hide_active_menu and prev_item != self.active_item:
            if popup == -1:
                self.hideMenu(hide_active_menu)
            return

        # 弹出子菜单
        if item and item.menu and popup != -1:
            LOG.debug("popup item: %s", item)
            self.popupItem(item)

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
            if caused.rect().contains(cpos) and e.type() != QEvent.MouseButtonRelease:
                new_e = QMouseEvent(e.type(), cpos, caused.mapTo(caused.window(), cpos), e.screenPos(),
                e.button(), e.buttons(), e.modifiers(), e.source())
                QApplication.sendEvent(caused, new_e)
                return True

            caused = caused.causedPopup.widget

        return False

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        # 只处理当前菜单区域的事件
        if not self.isVisible() or self.mouseEventTaken(e):
            return

        hasMouse = self.rect().contains(e.pos())
        item = self.item_at(e.pos())

        LOG.debug('mouseMoveEvent: %s, hasMouse: %s, item: %s', self.text, hasMouse, item)
        if item is not None:
            # if self.active_item is None or self.active_item.menu is None or not self.active_item.menu.isVisible():
            #     self.set_active_item(item)
            if item.menu is not None:
                if not item.menu.isVisible():
                    # 弹出子菜单
                    self.set_active_item(item, 0)
                else:
                    # 取消子菜单中选中项
                    item.menu.set_active_item(None)
            else:
                # 选中菜单项
                self.set_active_item(item)
            return
        # else:
        #     self.set_active_item(None)

        if self.active_menu:
            self.active_menu.set_active_item(None)

        return super().mouseMoveEvent(e)

    def mousePressEvent(self, e: QMouseEvent):
        LOG.debug('mousePressEvent: %s - %s', self.text, e.pos())
        if not self.isVisible() or self.mouseEventTaken(e):
            return

        self.setSyncItem()
        item = self.item_at(e.pos())
        if item is not None and item == self.active_item:
            self.set_active_item(item, 0)
        elif item is None or item.isEnabled:
            self.hideUpToMenuBar()

        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent):
        LOG.debug('mouseReleaseEvent: %s - %s', self.text, e.pos())
        if not self.isVisible() or self.mouseEventTaken(e):
            return

        item = self.item_at(e.pos())
        if item is not None and item.menu is None and item == self.active_item:
            self.setSyncItem()
            self.hideUpToMenuBar()
            pass

        super().mouseReleaseEvent(e)

    def setSyncItem(self):
        item = self.active_item
        if item is not None and (not item.isEnabled() or item.menu is not None):
            item = None

        caused = self
        while caused is not None:
            if caused._eventloop is not None:
                caused.sync_item = item
                break
            caused = caused.causedPopup.widget

    def hideUpToMenuBar(self):
        """
        关闭菜单
        """
        caused = self.causedPopup.widget
        self.hideMenu(self)
        while caused is not None:
            LOG.debug("hide menu: %s", caused.text)
            next = caused.causedPopup.widget
            self.hideMenu(caused)
            caused = next

    def hideMenu(self, menu: "NavMenu"):
        if menu:
            if self.active_menu == menu:
                self.active_menu = None

            menu.causedPopup.item = None
            menu.close()
            menu.causedPopup.widget = None

            menu.set_active_item(None)
        pass

    def hideEvent(self, e: QHideEvent) -> None:
        if self._eventloop:
            self._eventloop.exit()

        if self.active_menu:
            self.hideMenu(self.active_menu)

        self.causedPopup.widget = None
        self.causedPopup.item = None

    def popupItem(self, item: NavItem):
        pos = self.mapToGlobal(item.geometry().bottomLeft()) + QPoint(-20, 40)

        if self.active_menu and self.active_menu != item.menu:
            self.hideMenu(self.active_menu)

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

        LOG.debug("menu exited: %s", self.sync_item)

    def __repr__(self):
        return f"<NavMenu {self.text} at {id(self)}>"


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

qss = """
.navitem {
  background-color: "white";
}

.navitem:hover {
  background-color: "red";
}
"""


if __name__ == '__main__':
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    logging.basicConfig(level=logging.WARN, format="%(asctime)s %(levelname)s %(message)s")
    LOG.setLevel(logging.DEBUG)

    app = QApplication(sys.argv)
    # app.setStyleSheet(qss)

    w = MainWindow()
    w.show()

    sys.exit(app.exec_())
