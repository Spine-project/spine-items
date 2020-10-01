######################################################################################################################
# Copyright (C) 2017-2020 Spine project consortium
# This file is part of Spine Items.
# Spine Items is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
# any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
# Public License for more details. You should have received a copy of the GNU Lesser General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
######################################################################################################################

"""
Classes for drawing graphics items on QGraphicsScene.

:authors: M. Marin (KTH), P. Savolainen (VTT)
:date:   4.4.2018
"""

from PySide2.QtCore import Qt, QPointF, QRectF
from PySide2.QtWidgets import (
    QGraphicsItem,
    QGraphicsTextItem,
    QGraphicsSimpleTextItem,
    QGraphicsRectItem,
    QGraphicsColorizeEffect,
    QGraphicsDropShadowEffect,
    QApplication,
    QToolTip,
)
from PySide2.QtGui import QColor, QPen, QBrush, QTextCursor, QTransform, QPalette, QTextBlockFormat
from PySide2.QtSvg import QGraphicsSvgItem, QSvgRenderer
from spine_items.commands import MoveIconCommand


class ProjectItemIcon(QGraphicsRectItem):

    ITEM_EXTENT = 64

    def __init__(self, toolbox, icon_file, icon_color, background_color):
        """Base class for project item icons drawn in Design View.

        Args:
            toolbox (ToolBoxUI): QMainWindow instance
            icon_file (str): Path to icon resource
            icon_color (QColor): Icon's color
            background_color (QColor): Background color
        """
        super().__init__()
        self._toolbox = toolbox
        self.icon_file = icon_file
        self._moved_on_scene = False
        self._previous_pos = QPointF()
        self._current_pos = QPointF()
        self.icon_group = {self}
        self.renderer = QSvgRenderer()
        self.svg_item = QGraphicsSvgItem(self)
        self.colorizer = QGraphicsColorizeEffect()
        self.setRect(QRectF(-self.ITEM_EXTENT / 2, -self.ITEM_EXTENT / 2, self.ITEM_EXTENT, self.ITEM_EXTENT))
        self.text_font_size = 10  # point size
        # Make item name graphics item.
        self._name = ""
        self.name_item = QGraphicsSimpleTextItem(self._name, self)
        self.set_name_attributes()  # Set font, size, position, etc.
        # Make connector buttons
        self.connectors = dict(
            bottom=ConnectorButton(self, toolbox, position="bottom"),
            left=ConnectorButton(self, toolbox, position="left"),
            right=ConnectorButton(self, toolbox, position="right"),
        )
        # Make exclamation and rank icons
        self.exclamation_icon = ExclamationIcon(self)
        self.rank_icon = RankIcon(self)
        brush = QBrush(background_color)
        self._setup(brush, icon_file, icon_color)
        self.activate()

    def update(self, name, x, y):
        self.update_name_item(name)
        self.moveBy(x, y)

    def activate(self):
        """Adds items to scene and setup graphics effect.
        Called in the constructor and when re-adding the item to the project in the context of undo/redo.
        """
        scene = self._toolbox.ui.graphicsView.scene()
        scene.addItem(self)
        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setOffset(1)
        shadow_effect.setEnabled(False)
        self.setGraphicsEffect(shadow_effect)

    def _setup(self, brush, svg, svg_color):
        """Setup item's attributes.

        Args:
            brush (QBrush): Used in filling the background rectangle
            svg (str): Path to SVG icon file
            svg_color (QColor): Color of SVG icon
        """
        self.setPen(QPen(Qt.black, 1, Qt.SolidLine))
        self.setBrush(brush)
        self.colorizer.setColor(svg_color)
        # Load SVG
        loading_ok = self.renderer.load(svg)
        if not loading_ok:
            self._toolbox.msg_error.emit("Loading SVG icon from resource:{0} failed".format(svg))
            return
        size = self.renderer.defaultSize()
        self.svg_item.setSharedRenderer(self.renderer)
        self.svg_item.setElementId("")  # guess empty string loads the whole file
        dim_max = max(size.width(), size.height())
        rect_w = self.rect().width()  # Parent rect width
        margin = 32
        self.svg_item.setScale((rect_w - margin) / dim_max)
        x_offset = (rect_w - self.svg_item.sceneBoundingRect().width()) / 2
        y_offset = (rect_w - self.svg_item.sceneBoundingRect().height()) / 2
        self.svg_item.setPos(self.rect().x() + x_offset, self.rect().y() + y_offset)
        self.svg_item.setGraphicsEffect(self.colorizer)
        self.setFlag(QGraphicsItem.ItemIsMovable, enabled=True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, enabled=True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, enabled=True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, enabled=True)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        # Set exclamation and rank icons position
        self.exclamation_icon.setPos(self.rect().topRight() - self.exclamation_icon.sceneBoundingRect().topRight())
        self.rank_icon.setPos(self.rect().topLeft())

    def name(self):
        """Returns name of the item that is represented by this icon."""
        return self._name

    def update_name_item(self, new_name):
        """Set a new text to name item. Used when a project item is renamed."""
        self._name = new_name
        self.name_item.setText(new_name)
        self.set_name_attributes()

    def set_name_attributes(self):
        """Set name QGraphicsSimpleTextItem attributes (font, size, position, etc.)"""
        # Set font size and style
        font = self.name_item.font()
        font.setPointSize(self.text_font_size)
        font.setBold(True)
        self.name_item.setFont(font)
        # Set name item position (centered on top of the master icon)
        name_width = self.name_item.boundingRect().width()
        name_height = self.name_item.boundingRect().height()
        self.name_item.setPos(
            self.rect().x() + self.rect().width() / 2 - name_width / 2, self.rect().y() - name_height - 4
        )

    def conn_button(self, position="left"):
        """Returns items connector button (QWidget)."""
        return self.connectors.get(position, self.connectors["left"])

    def outgoing_links(self):
        return [l for conn in self.connectors.values() for l in conn.outgoing_links()]

    def incoming_links(self):
        return [l for conn in self.connectors.values() for l in conn.incoming_links()]

    def hoverEnterEvent(self, event):
        """Sets a drop shadow effect to icon when mouse enters its boundaries.

        Args:
            event (QGraphicsSceneMouseEvent): Event
        """
        self.prepareGeometryChange()
        self.graphicsEffect().setEnabled(True)
        event.accept()

    def hoverLeaveEvent(self, event):
        """Disables the drop shadow when mouse leaves icon boundaries.

        Args:
            event (QGraphicsSceneMouseEvent): Event
        """
        self.prepareGeometryChange()
        self.graphicsEffect().setEnabled(False)
        event.accept()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.icon_group = set(x for x in self.scene().selectedItems() if isinstance(x, ProjectItemIcon)) | {self}
        for icon in self.icon_group:
            icon._previous_pos = icon.scenePos()

    def mouseMoveEvent(self, event):
        """Moves icon(s) while the mouse button is pressed.
        Update links that are connected to selected icons.

        Args:
            event (QGraphicsSceneMouseEvent): Event
        """
        super().mouseMoveEvent(event)
        self.update_links_geometry()

    def moveBy(self, dx, dy):
        super().moveBy(dx, dy)
        self.update_links_geometry()

    def update_links_geometry(self):
        """Updates geometry of connected links to reflect this item's most recent position."""
        links = set(link for icon in self.icon_group for conn in icon.connectors.values() for link in conn.links)
        for link in links:
            link.update_geometry()

    def mouseReleaseEvent(self, event):
        for icon in self.icon_group:
            icon._current_pos = icon.scenePos()
        # pylint: disable=undefined-variable
        if (self._current_pos - self._previous_pos).manhattanLength() > qApp.startDragDistance():
            self._toolbox.undo_stack.push(MoveIconCommand(self))
        super().mouseReleaseEvent(event)

    def notify_item_move(self):
        if self._moved_on_scene:
            self._moved_on_scene = False
            scene = self.scene()
            scene.item_move_finished.emit(self)

    def contextMenuEvent(self, event):
        """Show item context menu.

        Args:
            event (QGraphicsSceneMouseEvent): Mouse event
        """
        self.scene().clearSelection()
        self.setSelected(True)
        self._toolbox.show_item_image_context_menu(event.screenPos(), self.name())

    def keyPressEvent(self, event):
        """Handles deleting and rotating the selected
        item when dedicated keys are pressed.

        Args:
            event (QKeyEvent): Key event
        """
        if event.key() == Qt.Key_Delete and self.isSelected():
            self._toolbox.project().remove_item(self.name())
            event.accept()
        elif event.key() == Qt.Key_R and self.isSelected():
            # TODO:
            # 1. Change name item text direction when rotating
            # 2. Save rotation into project file
            rect = self.mapToScene(self.boundingRect()).boundingRect()
            center = rect.center()
            t = QTransform()
            t.translate(center.x(), center.y())
            t.rotate(90)
            t.translate(-center.x(), -center.y())
            self.setPos(t.map(self.pos()))
            self.setRotation(self.rotation() + 90)
            links = set(lnk for conn in self.connectors.values() for lnk in conn.links)
            for link in links:
                link.update_geometry()
            event.accept()
        else:
            super().keyPressEvent(event)

    def itemChange(self, change, value):
        """
        Reacts to item removal and position changes.

        In particular, destroys the drop shadow effect when the items is removed from a scene
        and keeps track of item's movements on the scene.

        Args:
            change (GraphicsItemChange): a flag signalling the type of the change
            value: a value related to the change

        Returns:
             Whatever super() does with the value parameter
        """
        if change == QGraphicsItem.ItemScenePositionHasChanged:
            self._moved_on_scene = True
        elif change == QGraphicsItem.GraphicsItemChange.ItemSceneChange and value is None:
            self.prepareGeometryChange()
            self.setGraphicsEffect(None)
        return super().itemChange(change, value)

    def show_item_info(self):
        """Update GUI to show the details of the selected item."""
        ind = self._toolbox.project_item_model.find_item(self.name())
        self._toolbox.ui.treeView_project.setCurrentIndex(ind)


class ConnectorButton(QGraphicsRectItem):

    # Regular and hover brushes
    brush = QBrush(QColor(255, 255, 255))  # Used in filling the item
    hover_brush = QBrush(QColor(50, 0, 50, 128))  # Used in filling the item while hovering

    def __init__(self, parent, toolbox, position="left"):
        """Connector button graphics item. Used for Link drawing between project items.

        Args:
            parent (QGraphicsItem): Project item bg rectangle
            toolbox (ToolBoxUI): QMainWindow instance
            position (str): Either "top", "left", "bottom", or "right"
        """
        super().__init__(parent)
        self._parent = parent
        self._toolbox = toolbox
        self.position = position
        self.links = list()
        pen = QPen(Qt.black, 0.5, Qt.SolidLine)
        self.setPen(pen)
        self.setBrush(self.brush)
        parent_rect = parent.rect()
        extent = 0.2 * parent_rect.width()
        rect = QRectF(0, 0, extent, extent)
        if position == "top":
            rect.moveCenter(QPointF(parent_rect.center().x(), parent_rect.top() + extent / 2))
        elif position == "left":
            rect.moveCenter(QPointF(parent_rect.left() + extent / 2, parent_rect.center().y()))
        elif position == "bottom":
            rect.moveCenter(QPointF(parent_rect.center().x(), parent_rect.bottom() - extent / 2))
        elif position == "right":
            rect.moveCenter(QPointF(parent_rect.right() - extent / 2, parent_rect.center().y()))
        self.setRect(rect)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)

    def outgoing_links(self):
        return [l for l in self.links if l.src_connector == self]

    def incoming_links(self):
        return [l for l in self.links if l.dst_connector == self]

    def parent_name(self):
        """Returns project item name owning this connector button."""
        return self._parent.name()

    def mousePressEvent(self, event):
        """Connector button mouse press event. Either starts or closes a link.

        Args:
            event (QGraphicsSceneMouseEvent): Event
        """
        if not event.button() == Qt.LeftButton:
            event.accept()
            return
        self._parent.show_item_info()
        link_drawer = self.scene().link_drawer
        if not link_drawer.isVisible():
            link_drawer.wake_up(self)
        elif event.button() == Qt.LeftButton:
            link_drawer.add_link()

    def set_friend_connectors_enabled(self, enabled):
        """Enables or disables all connectors in the parent. This is called by LinkDrawer to disable invalid connectors
        while drawing and reenabling them back when done."""
        for conn in self._parent.connectors.values():
            conn.setEnabled(enabled)
            conn.setBrush(conn.brush)  # Remove hover brush from src connector that was clicked

    def mouseDoubleClickEvent(self, event):
        """Connector button mouse double click event. Makes sure the LinkDrawer is hidden.

        Args:
            event (QGraphicsSceneMouseEvent): Event
        """
        event.accept()

    def hoverEnterEvent(self, event):
        """Sets a darker shade to connector button when mouse enters its boundaries.

        Args:
            event (QGraphicsSceneMouseEvent): Event
        """
        self.setBrush(self.hover_brush)
        link_drawer = self.scene().link_drawer
        if link_drawer.isVisible():
            link_drawer.dst_connector = self
            link_drawer.update_geometry()

    def hoverLeaveEvent(self, event):
        """Restore original brush when mouse leaves connector button boundaries.

        Args:
            event (QGraphicsSceneMouseEvent): Event
        """
        self.setBrush(self.brush)
        link_drawer = self.scene().link_drawer
        if link_drawer.isVisible():
            link_drawer.dst_connector = None
            link_drawer.update_geometry()


class ExclamationIcon(QGraphicsSvgItem):
    def __init__(self, parent):
        """Exclamation icon graphics item.
        Used to notify that a ProjectItem is missing some configuration.

        Args:
            parent (ProjectItemIcon): the parent item
        """
        super().__init__(parent)
        self._parent = parent
        self._notifications = list()
        self.renderer = QSvgRenderer()
        self.colorizer = QGraphicsColorizeEffect()
        self.colorizer.setColor(QColor("red"))
        # Load SVG
        loading_ok = self.renderer.load(":/icons/item_icons/exclamation-circle.svg")
        if not loading_ok:
            return
        size = self.renderer.defaultSize()
        self.setSharedRenderer(self.renderer)
        dim_max = max(size.width(), size.height())
        rect_w = parent.rect().width()  # Parent rect width
        self.setScale(0.2 * rect_w / dim_max)
        self.setGraphicsEffect(self.colorizer)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, enabled=False)
        self.hide()

    def clear_notifications(self):
        """Clear all notifications."""
        self._notifications.clear()
        self.hide()

    def add_notification(self, text):
        """Add a notification."""
        self._notifications.append(text)
        self.show()

    def hoverEnterEvent(self, event):
        """Shows notifications as tool tip.

        Args:
            event (QGraphicsSceneMouseEvent): Event
        """
        if not self._notifications:
            return
        tip = "<p>" + "<p>".join(self._notifications)
        QToolTip.showText(event.screenPos(), tip)

    def hoverLeaveEvent(self, event):
        """Hides tool tip.

        Args:
            event (QGraphicsSceneMouseEvent): Event
        """
        QToolTip.hideText()


class RankIcon(QGraphicsTextItem):
    def __init__(self, parent):
        """Rank icon graphics item.
        Used to show the rank of a ProjectItem within its DAG

        Args:
            parent (ProjectItemIcon): the parent item
        """
        super().__init__(parent)
        self._parent = parent
        rect_w = parent.rect().width()  # Parent rect width
        self.text_margin = 0.05 * rect_w
        self.bg = QGraphicsRectItem(self.boundingRect(), self)
        bg_brush = QApplication.palette().brush(QPalette.ToolTipBase)
        self.bg.setBrush(bg_brush)
        self.bg.setFlag(QGraphicsItem.ItemStacksBehindParent)
        self.setFlag(QGraphicsItem.ItemIsSelectable, enabled=False)
        font = self.font()
        font.setPointSize(parent.text_font_size)
        font.setBold(True)
        self.setFont(font)
        doc = self.document()
        doc.setDocumentMargin(0)

    def set_rank(self, rank):
        self.setPlainText(str(rank))
        self.adjustSize()
        self.setTextWidth(self.text_margin + self.textWidth())
        self.bg.setRect(self.boundingRect())
        # Align center
        fmt = QTextBlockFormat()
        fmt.setAlignment(Qt.AlignHCenter)
        cursor = self.textCursor()
        cursor.select(QTextCursor.Document)
        cursor.mergeBlockFormat(fmt)
        cursor.clearSelection()
        self.setTextCursor(cursor)
