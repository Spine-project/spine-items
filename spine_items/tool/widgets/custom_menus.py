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
Classes for custom context menus and pop-up menus.

:author: P. Savolainen (VTT)
:date:   9.1.2018
"""
import os
from PySide2.QtCore import QUrl, Slot
from spinetoolbox.helpers import open_url
from spinetoolbox.widgets.custom_menus import ItemSpecificationMenu, CustomPopupMenu


class ToolSpecificationMenu(ItemSpecificationMenu):
    """Menu class for Tool specifications."""

    def __init__(self, toolbox, index, item=None):
        """
        Args:
            toolbox (ToolboxUI): the toolbox that request this menu
            index (QModelIndex): the index from specification model
            item (Tool, optional): The item that owns the menu
        """
        super().__init__(toolbox, index, item)
        self.addSeparator()
        self.add_action("Open main program file", self._open_main_program_file)
        self.add_action("Open main program directory", self._open_main_program_dir)

    @Slot()
    def _open_main_program_file(self):
        spec = self.parent().specification_model.specification(self.index.row())
        if not spec.path or not os.path.isdir(spec.path):
            self._toolbox.msg_error.emit(
                f"Opening Tool spec main program file <b>{spec.includes[0]}</b> failed. "
                f"Main program directory does not exist."
            )
            return
        file_path = os.path.join(spec.path, spec.includes[0])
        # Check that file exists
        if not os.path.isfile(file_path):
            self._toolbox.msg_error.emit("Tool spec main program file <b>{0}</b> not found.".format(file_path))
            return
        ext = os.path.splitext(os.path.split(file_path)[1])[1]
        if ext in [".bat", ".exe"]:
            self._toolbox.msg_warning.emit(
                "Sorry, opening files with extension <b>{0}</b> not supported. "
                "Please open the file manually.".format(ext)
            )
            return
        main_program_url = "file:///" + file_path
        res = open_url(main_program_url)
        if not res:
            filename, file_extension = os.path.splitext(file_path)
            self._toolbox.msg_error.emit(
                "Unable to open Tool specification main program file {0}. "
                "Make sure that <b>{1}</b> "
                "files are associated with an editor. E.g. on Windows "
                "10, go to Control Panel -> Default Programs to do this.".format(filename, file_extension)
            )

    @Slot()
    def _open_main_program_dir(self):
        tool_specification_path = self._toolbox.specification_model.specification(self.index.row()).path
        if not tool_specification_path:
            self._toolbox.msg_error.emit("Main program directory does not exist. Fix this in Tool spec editor.")
            return
        path_url = "file:///" + tool_specification_path
        self._toolbox.open_anchor(QUrl(path_url, QUrl.TolerantMode))


class AddProgramFilesPopupMenu(CustomPopupMenu):
    """Popup menu class for add includes button in Tool specification editor widget."""

    def __init__(self, parent):
        """
        Args:
            parent (QWidget): Parent widget (ToolSpecificationEditorWindow)
        """
        super().__init__(parent)
        self._parent = parent
        # Open a tool specification file
        self.add_action("New file", self._parent.new_program_file)
        self.addSeparator()
        self.add_action("Open files...", self._parent.show_add_program_files_dialog)
