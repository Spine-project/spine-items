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
Tool class.

:author: P. Savolainen (VTT)
:date:   19.12.2017
"""
import os
from PySide2.QtCore import Slot, Signal
from PySide2.QtWidgets import QAction
from spinetoolbox.project_item.project_item import ProjectItem
from spinetoolbox.helpers import open_url
from spine_engine.config import TOOL_OUTPUT_DIR
from .commands import UpdateToolExecuteInWorkCommand, UpdateToolOptionsCommand
from ..commands import UpdateCmdLineArgsCommand
from .item_info import ItemInfo
from .widgets.custom_menus import ToolSpecificationMenu
from .widgets.options_widgets import JuliaOptionsWidget
from .executable_item import ExecutableItem
from .utils import flatten_file_path_duplicates, find_file
from ..utils import CmdLineArg, cmd_line_arg_from_dict
from ..models import ToolCommandLineArgsModel, FileListModel
from .output_resources import scan_for_resources


class Tool(ProjectItem):

    python_console_requested = Signal(str, str, str)
    julia_console_requested = Signal(str, str, str)

    def __init__(
        self,
        name,
        description,
        x,
        y,
        toolbox,
        project,
        specification_name="",
        execute_in_work=True,
        cmd_line_args=None,
        options=None,
    ):
        """Tool class.

        Args:
            name (str): Object name
            description (str): Object description
            x (float): Initial X coordinate of item icon
            y (float): Initial Y coordinate of item icon
            toolbox (ToolboxUI): QMainWindow instance
            project (SpineToolboxProject): the project this item belongs to
            specification_name (str): Name of this Tool's Tool specification
            execute_in_work (bool): Execute associated Tool specification in work (True) or source directory (False)
            cmd_line_args (list, optional): Tool command line arguments
            options (dict, optional): misc tool options. At the moment it just holds the location of the julia sysimage
        """
        super().__init__(name, description, x, y, project)
        self._toolbox = toolbox
        self.execute_in_work = None
        self.undo_execute_in_work = None
        if cmd_line_args is None:
            cmd_line_args = []
        self.cmd_line_args = cmd_line_args
        self._cmdline_args_model = ToolCommandLineArgsModel(self)
        self._specification = self._toolbox.specification_model.find_specification(specification_name)
        if specification_name and not self._specification:
            self._logger.msg_error.emit(
                f"Tool <b>{self.name}</b> should have a Tool specification <b>{specification_name}</b> but it was not found"
            )
        self._cmdline_args_model.args_updated.connect(self._push_update_cmd_line_args_command)
        self._populate_cmdline_args_model()
        self._input_file_model = FileListModel(header_label="Available resources", draggable=True)
        # Make directory for results
        self.output_dir = os.path.join(self.data_dir, TOOL_OUTPUT_DIR)
        self.do_update_execution_mode(execute_in_work)
        self.python_console_requested.connect(self._setup_python_console)
        self.julia_console_requested.connect(self._setup_julia_console)
        self._specification_menu = None
        self._options = options if options is not None else {}

    def _get_options_widget(self):
        """Returns a widget to specify the options for this tool.
        It is embedded in the ui in ``self._update_tool_ui()``.

        Returns:
            OptionsWidget
        """
        # At the moment only Julia has options, but the code is made generic
        constructors = {"julia": JuliaOptionsWidget}  # Add others as needed
        tooltype = self.specification().tooltype
        constructor = constructors.get(tooltype)
        if constructor is None:
            return None
        if tooltype not in self._properties_ui.options_widgets:
            self._properties_ui.options_widgets[tooltype] = constructor()
        options_widget = self._properties_ui.options_widgets[tooltype]
        options_widget.set_tool(self)
        options_widget.do_update_options(self._options)
        return options_widget

    @staticmethod
    def item_type():
        """See base class."""
        return ItemInfo.item_type()

    @staticmethod
    def item_category():
        """See base class."""
        return ItemInfo.item_category()

    def make_signal_handler_dict(self):
        """Returns a dictionary of all shared signals and their handlers.
        This is to enable simpler connecting and disconnecting."""
        s = super().make_signal_handler_dict()
        s[self._properties_ui.toolButton_tool_specification.clicked] = self.show_specification_window
        s[self._properties_ui.toolButton_tool_open_dir.clicked] = lambda checked=False: self.open_directory()
        s[self._properties_ui.pushButton_tool_results.clicked] = self._open_results_directory
        s[self._properties_ui.comboBox_tool.textActivated] = self.update_specification
        s[self._properties_ui.radioButton_execute_in_work.toggled] = self.update_execution_mode
        s[self._properties_ui.toolButton_add_file_path_arg.clicked] = self._add_selected_file_path_args
        s[self._properties_ui.toolButton_remove_arg.clicked] = self._remove_arg
        return s

    def restore_selections(self):
        """Restore selections into shared widgets when this project item is selected."""
        self._properties_ui.label_tool_name.setText(self.name)
        self._properties_ui.treeView_input_files.setModel(self._input_file_model)
        self._properties_ui.treeView_cmdline_args.setModel(self._cmdline_args_model)
        self._properties_ui.treeView_cmdline_args.expandAll()
        self.update_execute_in_work_button()
        self._update_tool_ui()

    @Slot(bool)
    def show_specification_window(self, _=True):
        """Opens the settings window."""
        self._toolbox.show_specification_form(self.item_type(), self.specification(), self)

    @Slot(bool)
    def update_execution_mode(self, checked):
        """Pushes a new UpdateToolExecuteInWorkCommand to the toolbox stack."""
        self._toolbox.undo_stack.push(UpdateToolExecuteInWorkCommand(self, checked))

    def do_update_execution_mode(self, execute_in_work):
        """Updates execute_in_work setting."""
        if self.execute_in_work == execute_in_work:
            return
        self.execute_in_work = execute_in_work
        self.update_execute_in_work_button()

    def update_execute_in_work_button(self):
        """Sets the execute in work radio button check state according to
        execute_in_work instance variable."""
        if not self._active:
            return
        self._properties_ui.radioButton_execute_in_work.blockSignals(True)
        if self.execute_in_work:
            self._properties_ui.radioButton_execute_in_work.setChecked(True)
        else:
            self._properties_ui.radioButton_execute_in_source.setChecked(True)
        self._properties_ui.radioButton_execute_in_work.blockSignals(False)

    @Slot(str)
    def update_specification(self, text):
        """Update Tool specification according to selection in the specification comboBox.

        Args:
            text (str): Tool specification name in the comboBox
        """
        spec = self._toolbox.specification_model.find_specification(text)
        self.set_specification(spec)

    @Slot(bool)
    def _remove_arg(self, _=False):
        removed_rows = [index.row() for index in self._properties_ui.treeView_cmdline_args.selectedIndexes()]
        cmd_line_args = [arg for row, arg in enumerate(self.cmd_line_args) if row not in removed_rows]
        self._push_update_cmd_line_args_command(cmd_line_args)

    @Slot(bool)
    def _add_selected_file_path_args(self, _=False):
        new_args = [index.data() for index in self._properties_ui.treeView_input_files.selectedIndexes()]
        self._push_update_cmd_line_args_command(self.cmd_line_args + new_args)

    @Slot(list)
    def _push_update_cmd_line_args_command(self, cmd_line_args):
        if self.cmd_line_args == cmd_line_args:
            return
        self._toolbox.undo_stack.push(UpdateCmdLineArgsCommand(self, cmd_line_args))

    def update_cmd_line_args(self, cmd_line_args):
        """Updates instance cmd line args list and sets the list as text to the line edit widget.

        Args:
            cmd_line_args (list): Tool cmd line args
        """
        self.cmd_line_args = cmd_line_args
        self._populate_cmdline_args_model()

    def _populate_cmdline_args_model(self):
        spec_args = [CmdLineArg(arg) for arg in self._specification.cmdline_args] if self._specification else []
        tool_args = self.cmd_line_args
        self._cmdline_args_model.reset_model(spec_args, tool_args)
        if self._active:
            self._properties_ui.treeView_cmdline_args.setFocus()

    def do_set_specification(self, specification):
        """see base class"""
        if not super().do_set_specification(specification):
            return False
        self._populate_cmdline_args_model()
        if self._active:
            self._update_tool_ui()
        if self.undo_execute_in_work is None:
            self.undo_execute_in_work = self.execute_in_work
        if specification:
            self.do_update_execution_mode(specification.execute_in_work)
        self.item_changed.emit()
        return True

    def undo_set_specification(self):
        """see base class"""
        super().undo_set_specification()
        self.do_update_execution_mode(self.undo_execute_in_work)
        self.undo_execute_in_work = None

    def update_options(self, options):
        """Pushes a new UpdateToolOptionsCommand to the toolbox stack."""
        self._toolbox.undo_stack.push(UpdateToolOptionsCommand(self, options))

    def do_set_options(self, options):
        """Sets options for this tool.

        Args:
            options (dict): The new options dictionary, must include *ALL* the options, not only changed ones.
        """
        self._options = options
        if self._active:
            _ = self._get_options_widget()

    def _update_tool_ui(self):
        """Updates Tool UI to show Tool specification details. Used when Tool specification is changed.
        Overrides execution mode (work or source) with the specification default."""
        options_widget = self._properties_ui.horizontalLayout_options.takeAt(0)
        if options_widget:
            options_widget.widget().hide()
        if not self.specification():
            self._properties_ui.comboBox_tool.setCurrentIndex(-1)
            self.do_update_execution_mode(True)
            self._properties_ui.toolButton_tool_specification.setMenu(None)
        else:
            self._properties_ui.comboBox_tool.setCurrentText(self.specification().name)
            self._update_specification_menu()
            self._properties_ui.toolButton_tool_specification.setMenu(self._specification_menu)
            options_widget = self._get_options_widget()
            if options_widget:
                self._properties_ui.horizontalLayout_options.addWidget(options_widget)
                options_widget.show()

    def _update_specification_menu(self):
        spec_model_index = self._toolbox.specification_model.specification_index(self.specification().name)
        self._specification_menu = ToolSpecificationMenu(self._toolbox, spec_model_index, self)
        self._specification_menu.setTitle("Specification...")

    @Slot(bool)
    def _open_results_directory(self, _):
        """Open output directory in file browser."""
        if not os.path.exists(self.output_dir):
            self._logger.msg_warning.emit(f"Tool <b>{self.name}</b> has no results. Click Execute to generate them.")
            return
        url = "file:///" + self.output_dir
        # noinspection PyTypeChecker, PyCallByClass, PyArgumentList
        res = open_url(url)
        if not res:
            self._logger.msg_error.emit(f"Failed to open directory: {self.output_dir}")

    def specification(self):
        """Returns Tool specification."""
        return self._specification

    def update_name_label(self):
        """Update Tool tab name label. Used only when renaming project items."""
        self._properties_ui.label_tool_name.setText(self.name)

    def resources_for_direct_successors(self):
        """See base class"""
        return scan_for_resources(self, self.specification(), self.output_dir)

    @property
    def executable_class(self):
        return ExecutableItem

    def _find_input_files(self, resources):
        """Iterates files in required input files model and looks for them in the given resources.

        Args:
            resources (list): resources available

        Returns:
            Dictionary mapping required files to path where they are found, or to None if not found
        """
        if not self.specification():
            return {}
        file_paths = dict()
        for req_file_path in self.specification().inputfiles:
            # Just get the filename if there is a path attached to the file
            _, filename = os.path.split(req_file_path)
            if not filename:
                # It's a directory
                continue
            file_paths[req_file_path] = find_file(filename, resources)
        return file_paths

    def _do_handle_dag_changed(self, upstream_resources, downstream_resources):
        """See base class."""
        if not self.specification():
            self.add_notification("This Tool does not have a specification. Set it in the Tool Properties Panel.")
        if self.specification() is not None and not self.specification().path:
            n = self.specification().name
            self.add_notification(
                f"Tool specification <b>{n}</b> path does not exist. Fix this in Tool specification editor."
            )
        resources = upstream_resources + downstream_resources
        self._input_file_model.update(resources)
        self._notify_if_duplicate_file_paths()
        file_paths = self._find_input_files(resources)
        file_paths = flatten_file_path_duplicates(file_paths, self._logger)
        not_found = [k for k, v in file_paths.items() if v is None]
        if not_found:
            self.add_notification(
                "File(s) {0} needed to execute this Tool are not provided by any input item. "
                "Connect items that provide the required files to this Tool.".format(", ".join(not_found))
            )
        # Update cmdline args
        cmd_line_args = self.cmd_line_args.copy()
        for resource in resources:
            updated_from = resource.metadata.get("updated_from")
            try:
                i = cmd_line_args.index(updated_from)
            except ValueError:
                continue
            cmd_line_args[i] = resource.label
        self.update_cmd_line_args(cmd_line_args)

    def _notify_if_duplicate_file_paths(self):
        """Adds a notification if file_list contains duplicate entries."""
        duplicates = self._input_file_model.duplicate_paths()
        if duplicates:
            self.add_notification("Duplicate input files:<br>{}".format("<br>".join(duplicates)))

    def item_dict(self):
        """Returns a dictionary corresponding to this item."""
        d = super().item_dict()
        if not self.specification():
            d["specification"] = ""
        else:
            d["specification"] = self.specification().name
        d["execute_in_work"] = self.execute_in_work
        d["cmd_line_args"] = [arg.to_dict() for arg in self.cmd_line_args]
        if self._options:
            d["options"] = self._options
        return d

    @staticmethod
    def from_dict(name, item_dict, toolbox, project):
        """See base class."""
        description, x, y = ProjectItem.parse_item_dict(item_dict)
        specification_name = item_dict.get("specification", "")
        execute_in_work = item_dict.get("execute_in_work", True)
        cmd_line_args = item_dict.get("cmd_line_args", [])
        cmd_line_args = [cmd_line_arg_from_dict(arg) for arg in cmd_line_args]
        options = item_dict.get("options", {})
        return Tool(
            name, description, x, y, toolbox, project, specification_name, execute_in_work, cmd_line_args, options
        )

    def rename(self, new_name, rename_data_dir_message):
        """See base class."""
        if not super().rename(new_name, rename_data_dir_message):
            return False
        self.output_dir = os.path.join(self.data_dir, TOOL_OUTPUT_DIR)
        self.item_changed.emit()
        return True

    def notify_destination(self, source_item):
        """See base class."""
        if source_item.item_type() == "Data Store":
            self._logger.msg.emit(
                f"Link established. Data Store <b>{source_item.name}</b> url will "
                f"be passed to Tool <b>{self.name}</b> when executing."
            )
        elif source_item.item_type() == "Data Connection":
            self._logger.msg.emit(
                f"Link established. Tool <b>{self.name}</b> will look for input "
                f"files from <b>{source_item.name}</b>'s references and data directory."
            )
        elif source_item.item_type() in ("GdxExporter", "Exporter"):
            self._logger.msg.emit(
                f"Link established. The file exported by <b>{source_item.name}</b> will "
                f"be available in <b>{self.name}</b>."
            )
        elif source_item.item_type() in ["Data Transformer", "Tool"]:
            self._logger.msg.emit("Link established")
        elif source_item.item_type() == "Gimlet":
            self._logger.msg.emit(
                f"Link established. Tool <b>{self.name}</b> will look for input "
                f"files from <b>{source_item.name}</b>."
            )
        else:
            super().notify_destination(source_item)

    @Slot(str, str, str)
    def _setup_python_console(self, filter_id, kernel_name, connection_file):
        """Sets up python console, eventually for a filter execution.

        Args:
            filter_id (str): filter identifier
            kernel_name (str): jupyter kernel name
            connection_file (str): path to connection file
        """
        if not filter_id:
            self._setup_main_python_console(kernel_name, connection_file)
        else:
            self._setup_filter_python_console(filter_id, kernel_name, connection_file)

    def _setup_main_python_console(self, kernel_name, connection_file):
        # pylint: disable=attribute-defined-outside-init
        self.python_console = self._toolbox.make_console("Python Console", self, kernel_name, connection_file)
        self._project.toolbox().override_python_console()

    def _setup_filter_python_console(self, filter_id, kernel_name, connection_file):
        self._filter_consoles.setdefault(filter_id, {}).setdefault(
            "python", self._toolbox.make_console("Python Console", self, kernel_name, connection_file)
        )
        self._project.toolbox().ui.listView_executions.model().layoutChanged.emit()

    @Slot(str, str, str)
    def _setup_julia_console(self, filter_id, kernel_name, connection_file):
        """Sets up julia console, eventually for a filter execution.

        Args:
            filter_id (str): filter identifier
            kernel_name (str): jupyter kernel name
            connection_file (str): path to connection file
        """
        if not filter_id:
            self._setup_main_julia_console(kernel_name, connection_file)
        else:
            self._setup_filter_julia_console(filter_id, kernel_name, connection_file)

    def _setup_main_julia_console(self, kernel_name, connection_file):
        # pylint: disable=attribute-defined-outside-init
        self.julia_console = self._toolbox.make_console("Julia Console", self, kernel_name, connection_file)
        self._project.toolbox().override_julia_console()

    def _setup_filter_julia_console(self, filter_id, kernel_name, connection_file):
        self._filter_consoles.setdefault(filter_id, {}).setdefault(
            "julia", self._toolbox.make_console("Julia Console", self, kernel_name, connection_file)
        )
        self._project.toolbox().ui.listView_executions.model().layoutChanged.emit()

    def actions(self):
        # pylint: disable=attribute-defined-outside-init
        if self.specification() is not None:
            if self._specification_menu is None:
                self._update_specification_menu()
            self._actions = [self._specification_menu.menuAction()]
        else:
            action = QAction("New specification")
            action.triggered.connect(self.show_specification_window)
            self._actions = [action]
        self._actions.append(QAction("Open results directory"))
        self._actions[-1].triggered.connect(self._open_results_directory)
        return self._actions

    @staticmethod
    def upgrade_v1_to_v2(item_name, item_dict):
        """Upgrades item's dictionary from v1 to v2.

        Changes:
        - 'tool' key is renamed to 'specification'

        Args:
            item_name (str): item's name
            item_dict (dict): Version 1 item dictionary

        Returns:
            dict: Version 2 Tool dictionary
        """
        item_dict["specification"] = item_dict.pop("tool", "")
        return item_dict
