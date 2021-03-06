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
Unit tests for export mapping setup table.

:author: A. Soininen (VTT)
:date:   11.12.2020
"""
import unittest
from unittest.mock import MagicMock
from PySide2.QtWidgets import QApplication, QUndoStack
from spinedb_api.export_mapping import object_export, Position
from spine_items.exporter.mvcmodels.mapping_table_model import MappingTableModel


class TestMappingTableModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            QApplication()

    def setUp(self):
        self._undo_stack = QUndoStack()

    def test_columnCount(self):
        model = MappingTableModel(
            "mapping", object_export(Position.hidden, Position.hidden), self._undo_stack, MagicMock()
        )
        self.assertEqual(model.rowCount(), 2)

    def test_rowCount(self):
        mapping_root = object_export(Position.hidden, Position.hidden)
        model = MappingTableModel("mapping", mapping_root, self._undo_stack, MagicMock())
        self.assertEqual(model.rowCount(), mapping_root.count_mappings())

    def test_data(self):
        model = MappingTableModel("mapping", object_export(1, 2), self._undo_stack, MagicMock())
        self.assertEqual(model.rowCount(), 2)
        self.assertEqual(model.index(0, 0).data(), "Object classes")
        self.assertEqual(model.index(0, 1).data(), "2")
        self.assertEqual(model.index(1, 0).data(), "Objects")
        self.assertEqual(model.index(1, 1).data(), "3")

    def test_setData_column_number(self):
        model = MappingTableModel(
            "mapping", object_export(Position.hidden, Position.hidden), self._undo_stack, MagicMock()
        )
        self.assertTrue(model.setData(model.index(0, 1), "23"))
        self.assertEqual(model.index(0, 1).data(), "23")


if __name__ == "__main__":
    unittest.main()
