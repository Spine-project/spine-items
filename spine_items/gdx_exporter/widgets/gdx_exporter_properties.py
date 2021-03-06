######################################################################################################################
# Copyright (C) 2017-2021 Spine project consortium
# This file is part of Spine Items.
# Spine Items is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
# any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
# Public License for more details. You should have received a copy of the GNU Lesser General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
######################################################################################################################

"""
GdxExporter properties widget.

:author: A. Soininen (VTT)
:date:   25.9.2019
"""

from PySide2.QtWidgets import QWidget
from ..item_info import ItemInfo


class GdxExporterProperties(QWidget):
    """A main window widget to show GdxExport item's properties."""

    def __init__(self, toolbox):
        """
        Args:
            toolbox (ToolboxUI): a main window instance
        """
        from spine_items.gdx_exporter.ui.gdx_exporter_properties import (
            Ui_Form,
        )  # pylint: disable=import-outside-toplevel

        super().__init__()
        self._ui = Ui_Form()
        self._ui.setupUi(self)
        toolbox.ui.tabWidget_item_properties.addTab(self, ItemInfo.item_type())

    @property
    def ui(self):
        """The UI form of this widget."""
        return self._ui
