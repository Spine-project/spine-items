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
Unit tests for Data Connection project item.

:author: A. Soininen (VTT), P. Savolainen (VTT)
:date:   4.10.2019
"""

import os
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest
from unittest import mock
from unittest.mock import MagicMock, NonCallableMagicMock
from PySide2.QtWidgets import QApplication
from PySide2.QtGui import QStandardItemModel, Qt
from spine_items.data_connection.data_connection import DataConnection
from spine_items.data_connection.data_connection_factory import DataConnectionFactory
from spine_items.data_connection.item_info import ItemInfo
from ..mock_helpers import mock_finish_project_item_construction, create_mock_project, create_mock_toolbox


class TestDataConnection(unittest.TestCase):
    def setUp(self):
        """Set up."""
        self.toolbox = create_mock_toolbox()
        factory = DataConnectionFactory()
        item_dict = {"type": "Data Connection", "description": "", "references": [], "x": 0, "y": 0}
        self._temp_dir = TemporaryDirectory()
        self.project = create_mock_project(self._temp_dir.name)
        self.toolbox.project.return_value = self.project
        self.data_connection = factory.make_item("DC", item_dict, self.toolbox, self.project)
        mock_finish_project_item_construction(factory, self.data_connection, self.toolbox)

    def tearDown(self):
        self.data_connection.tear_down()
        self._temp_dir.cleanup()

    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            QApplication()

    def test_item_type(self):
        self.assertEqual(DataConnection.item_type(), ItemInfo.item_type())

    def test_item_category(self):
        self.assertEqual(DataConnection.item_category(), ItemInfo.item_category())

    def test_add_references(self):
        temp_dir = Path(self._temp_dir.name, "references")
        temp_dir.mkdir()
        with mock.patch("spine_items.data_connection.data_connection.QFileDialog.getOpenFileNames") as mock_filenames:
            a = Path(temp_dir, "a.txt")
            a.touch()
            b = Path(temp_dir, "b.txt")
            b.touch()
            c = Path(temp_dir, "c.txt")  # Note. Does not exist
            # Add nothing
            mock_filenames.return_value = ([], "*.*")
            self.data_connection.show_add_references_dialog()
            self.assertEqual(1, mock_filenames.call_count)
            self.assertEqual(0, len(self.data_connection.file_references()))
            self.assertEqual(0, self.data_connection.reference_model.rowCount())
            # Add one file
            mock_filenames.return_value = ([str(a)], "*.*")
            self.data_connection.show_add_references_dialog()
            self.assertEqual(2, mock_filenames.call_count)
            self.assertEqual(1, len(self.data_connection.file_references()))
            self.assertEqual(1, self.data_connection.reference_model.rowCount())
            # Try to add a path that has already been added
            self.data_connection.show_add_references_dialog()
            self.assertEqual(3, mock_filenames.call_count)
            self.assertEqual(1, len(self.data_connection.file_references()))
            self.assertEqual(1, self.data_connection.reference_model.rowCount())
            self.data_connection.references = list()
            self.data_connection.reference_model = QStandardItemModel()
            # Add two references (the other one is non-existing)
            # Note: non-existing files cannot be added with the toolbox but this tests a situation when
            # project.json file has references to files that do not exist anymore and user tries to add a
            # new reference to a Data Connection that contains non-existing file references
            mock_filenames.return_value = ([str(b), str(c)], "*.*")
            self.data_connection.show_add_references_dialog()
            self.assertEqual(4, mock_filenames.call_count)
            self.assertEqual(1, len(self.data_connection.file_references()))
            self.assertEqual(1, self.data_connection.reference_model.rowCount())
            # Now add new reference
            mock_filenames.return_value = ([str(a)], "*.*")
            self.data_connection.show_add_references_dialog()
            self.assertEqual(5, mock_filenames.call_count)
            self.assertEqual(2, len(self.data_connection.file_references()))
            self.assertEqual(2, self.data_connection.reference_model.rowCount())

    def test_remove_references(self):
        temp_dir = Path(self._temp_dir.name, "references")
        temp_dir.mkdir()
        with mock.patch(
            "spine_items.data_connection.data_connection.QFileDialog.getOpenFileNames"
        ) as mock_filenames, mock.patch.object(
            self.data_connection._properties_ui.treeView_dc_references, "selectedIndexes"
        ) as mock_selected_indexes:
            a = Path(temp_dir, "a.txt")
            a.touch()
            b = Path(temp_dir, "b.txt")
            b.touch()
            c = Path(temp_dir, "c.txt")  # Note. This file is not actually created
            d = Path(temp_dir, "d.txt")  # Note. This file is not actually created
            self.assertTrue(os.path.isfile(str(a)) and os.path.isfile(str(b)))  # existing files
            self.assertFalse(os.path.isfile(str(c)))  # non-existing file
            self.assertFalse(os.path.isfile(str(d)))  # non-existing file
            # First add a couple of files as refs
            mock_filenames.return_value = ([str(a), str(b)], "*.*")
            self.data_connection.show_add_references_dialog()
            self.assertEqual(1, mock_filenames.call_count)
            self.assertEqual(2, len(self.data_connection.file_references()))
            self.assertEqual(2, self.data_connection.reference_model.rowCount())
            # Test with no indexes selected
            mock_selected_indexes.return_value = []
            self.data_connection.remove_references()
            self.assertEqual(1, mock_selected_indexes.call_count)
            self.assertEqual(2, len(self.data_connection.file_references()))
            self.assertEqual(2, self.data_connection.reference_model.rowCount())
            # Set one selected and remove it
            a_index = self.data_connection.reference_model.index(0, 0)
            mock_selected_indexes.return_value = [a_index]
            self.data_connection.remove_references()
            self.assertEqual(2, mock_selected_indexes.call_count)
            self.assertEqual(1, len(self.data_connection.file_references()))
            self.assertEqual(1, self.data_connection.reference_model.rowCount())
            # Check that the remaining item is the one that's supposed to be there
            self.assertEqual([str(b)], self.data_connection.file_references())
            self.assertEqual(str(b), self.data_connection.reference_model.item(0).data(Qt.DisplayRole))
            # Now remove the remaining one
            b_index = self.data_connection.reference_model.index(0, 0)
            mock_selected_indexes.return_value = [b_index]
            self.data_connection.remove_references()
            self.assertEqual(3, mock_selected_indexes.call_count)
            self.assertEqual(0, len(self.data_connection.file_references()))
            self.assertEqual(0, self.data_connection.reference_model.rowCount())
            # Add a and b back and the two non-existing files as well
            # Select non-existing file c and remove it
            mock_filenames.return_value = ([str(a), str(b), str(c), str(d)], "*.*")
            self.data_connection.show_add_references_dialog()
            self.assertEqual(2, mock_filenames.call_count)
            self.assertEqual(2, len(self.data_connection.file_references()))
            self.assertEqual(2, self.data_connection.reference_model.rowCount())
            # Check that the two remaining items are the ones that are supposed to be there
            self.assertEqual(str(a), self.data_connection.file_references()[0])
            self.assertEqual(str(a), self.data_connection.reference_model.item(0).data(Qt.DisplayRole))
            self.assertEqual(str(b), self.data_connection.file_references()[1])
            self.assertEqual(str(b), self.data_connection.reference_model.item(1).data(Qt.DisplayRole))
            # Now select the two remaining ones and remove them
            a_index = self.data_connection.reference_model.index(0, 0)
            b_index = self.data_connection.reference_model.index(1, 0)
            mock_selected_indexes.return_value = [a_index, b_index]
            self.data_connection.remove_references()
            self.assertEqual(4, mock_selected_indexes.call_count)
            self.assertEqual(0, len(self.data_connection.file_references()))
            self.assertEqual(0, self.data_connection.reference_model.rowCount())
            # Add a, b, c, and d back Select all and remove.
            mock_filenames.return_value = ([str(a), str(b), str(c), str(d)], "*.*")
            self.data_connection.show_add_references_dialog()
            self.assertEqual(3, mock_filenames.call_count)
            a_index = self.data_connection.reference_model.index(0, 0)
            b_index = self.data_connection.reference_model.index(1, 0)
            mock_selected_indexes.return_value = [a_index, b_index]
            self.data_connection.remove_references()
            self.assertEqual(5, mock_selected_indexes.call_count)
            self.assertEqual(0, len(self.data_connection.file_references()))
            self.assertEqual(0, self.data_connection.reference_model.rowCount())

    def test_item_dict(self):
        """Tests Item dictionary creation."""
        d = self.data_connection.item_dict()
        a = ["type", "description", "x", "y", "references"]
        for k in a:
            self.assertTrue(k in d, f"Key '{k}' not in dict {d}")

    def test_notify_destination(self):
        self.data_connection.logger.msg = MagicMock()
        self.data_connection.logger.msg_warning = MagicMock()
        source_item = NonCallableMagicMock()
        source_item.name = "source name"
        source_item.item_type = MagicMock(return_value="Importer")
        self.data_connection.notify_destination(source_item)
        self.data_connection.logger.msg.emit.assert_called_with("Link established")
        source_item.item_type = MagicMock(return_value="Data Store")
        self.data_connection.notify_destination(source_item)
        self.data_connection.logger.msg.emit.assert_called_with("Link established")
        source_item.item_type = MagicMock(return_value="GdxExporter")
        self.data_connection.notify_destination(source_item)
        self.data_connection.logger.msg_warning.emit.assert_called_with(
            "Link established. Interaction between a <b>GdxExporter</b> and"
            " a <b>Data Connection</b> has not been implemented yet."
        )
        source_item.item_type = MagicMock(return_value="Tool")
        self.data_connection.notify_destination(source_item)
        self.data_connection.logger.msg.emit.assert_called_with(
            "Link established. Tool <b>source name</b> output files"
            " will be passed as references to item <b>DC</b> after execution."
        )
        source_item.item_type = MagicMock(return_value="View")
        self.data_connection.notify_destination(source_item)
        self.data_connection.logger.msg_warning.emit.assert_called_with(
            "Link established. Interaction between a <b>View</b> and"
            " a <b>Data Connection</b> has not been implemented yet."
        )

    def test_rename(self):
        """Tests renaming a Data Connection."""
        self.data_connection.activate()
        expected_name = "ABC"
        expected_short_name = "abc"
        expected_data_dir = os.path.join(self.project.items_dir, expected_short_name)
        self.data_connection.rename(expected_name, "")
        # Check name
        self.assertEqual(expected_name, self.data_connection.name)  # item name
        self.assertEqual(expected_name, self.data_connection._properties_ui.label_dc_name.text())  # name label in props
        self.assertEqual(expected_name, self.data_connection.get_icon().name_item.text())  # name item on Design View
        # Check data_dir
        self.assertEqual(expected_data_dir, self.data_connection.data_dir)  # Check data dir
        # Check that file_system_watcher has one path (new data_dir)
        watched_dirs = self.data_connection.file_system_watcher.directories()
        self.assertEqual(1, len(watched_dirs))
        self.assertEqual(self.data_connection.data_dir, watched_dirs[0])


if __name__ == "__main__":
    unittest.main()
