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
The CombinerFactory class.

:author: M. Marin (KTH)
:date:   15.4.2020
"""

from ..project_item import ProjectItemFactory
from .combiner import Combiner
from .combiner_icon import CombinerIcon
from .widgets.combiner_properties_widget import CombinerPropertiesWidget
from .widgets.add_combiner_widget import AddCombinerWidget


class CombinerFactory(ProjectItemFactory):
    @staticmethod
    def item_class():
        return Combiner

    @staticmethod
    def icon():
        return ":/icons/item_icons/blender.svg"

    @staticmethod
    def make_add_item_widget(toolbox, x, y, specification):
        return AddCombinerWidget(toolbox, x, y, specification)

    @staticmethod
    def make_icon(toolbox, x, y, project_item):
        return CombinerIcon(toolbox, x, y, project_item, CombinerFactory.icon())

    @staticmethod
    def make_item(name, item_dict, toolbox, project, logger):
        return Combiner.from_dict(name, item_dict, toolbox, project, logger)

    @staticmethod
    def make_properties_widget(toolbox):
        return CombinerPropertiesWidget(toolbox)

    @staticmethod
    def make_specification_menu(parent, index):
        raise NotImplementedError()

    @staticmethod
    def make_specification_widget(toolbox, specification=None):
        """See base class."""
        raise NotImplementedError()
