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
Contains utilities shared between project items.

:authors: A. Soininen (VTT)
:date:    1.4.2020
"""

from datetime import datetime
import os.path
import re
from time import time
from contextlib import contextmanager
from spinedb_api.spine_db_server import start_spine_db_server, shutdown_spine_db_server
from spine_engine.project_item.project_item_resource import extract_packs


def labelled_resource_filepaths(resources):
    """Returns a dict mapping resource labels to file paths available in given resources.
    The label acts as an identifier for a 'transient_file'.
    """
    return {resource.label: resource.path for resource in resources if resource.hasfilepath}


class CmdLineArg:
    """Command line argument for items that execute shell commands."""

    def __init__(self, arg):
        """
        Args:
            arg (str): command line argument
        """
        self.arg = arg

    def __eq__(self, other):
        if not isinstance(other, CmdLineArg):
            return NotImplemented
        return self.arg == other.arg

    def __str__(self):
        return self.arg

    def to_dict(self):
        """Serializes argument to JSON compatible dict.

        Returns:
            dict: serialized command line argument
        """
        return {"type": "literal", "arg": self.arg}


class LabelArg(CmdLineArg):
    """Command line argument that gets replaced by a project item's resource URL/file path."""

    def to_dict(self):
        """See base class."""
        return {"type": "resource", "arg": self.arg}


def cmd_line_arg_from_dict(arg_dict):
    """Deserializes argument from dictionary.

    Args:
        arg_dict (dict): serialized command line argument

    Returns:
        CmdLineArg: deserialized command line argument
    """
    type_ = arg_dict["type"]
    construct = {"literal": CmdLineArg, "resource": LabelArg}[type_]
    return construct(arg_dict["arg"])


@contextmanager
def labelled_resource_args(resources, use_db_server=False):
    """
    Args:
        resources (Iterable of ProjectItemResource): resources to process
        use_db_server (bool): if True, use database server

    Yields:
        dict: mapping from resource label to resource args.
    """
    result = {}
    server_urls = []
    single_resources, pack_resources = extract_packs(resources)
    for resource in single_resources:
        if resource.type_ != "database":
            result[resource.label] = resource.path if resource.hasfilepath else ""
            continue
        if use_db_server:
            server_url = result[resource.label] = start_spine_db_server(resource.url)
            server_urls.append(server_url)
            continue
        result[resource.label] = resource.url
    for label, resources in pack_resources.items():
        result[label] = " ".join(r.path for r in resources if r.hasfilepath)
    try:
        yield result
    finally:
        for server_url in server_urls:
            shutdown_spine_db_server(server_url)


def expand_cmd_line_args(args, label_to_arg, logger):
    """Expands command line arguments by replacing resource labels by URLs/paths.

    Args:
        args (list of CmdLineArg): command line arguments
        label_to_arg (dict): a mapping from resource label to cmd line argument
        logger (LoggerInterface): a logger

    Returns:
        list of str: command line arguments as strings
    """
    expanded_args = list()
    for arg in args:
        if not isinstance(arg, LabelArg):
            expanded_args.append(str(arg))
            continue
        expanded = label_to_arg.get(str(arg))
        if expanded is None:
            logger.msg_warning.emit(f"Label '{arg}' used as command line argument not found in resources.")
            continue
        if expanded:
            expanded_args.append(expanded)
    return expanded_args


def database_label(provider_name):
    """Creates a standardized label for database resources.

    Args:
        provider_name (str): resource provider's name

    Returns:
        str: resource label
    """
    return "db_url@" + provider_name


def unique_name(prefix, existing):
    """
    Creates a unique name in the form "prefix X" where X is a number.

    Args:
        prefix (str): name prefix
        existing (Iterable of str): existing names

    Returns:
        str: unique name
    """
    pattern = re.compile(fr"^{prefix} [0-9]+$")
    reserved = set()
    for name in existing:
        if pattern.fullmatch(name) is not None:
            _, _, number = name.partition(" ")
            reserved.add(int(number))
    free = len(reserved) + 1
    for i in range(len(reserved)):
        if i + 1 not in reserved:
            free = i + 1
            break
    return f"{prefix} {free}"


class Database:
    """
    Database specific export settings.

    Attributes:
        url (str): database URL
        output_file_name (str): output file name (relative to item's data dir)
    """

    def __init__(self):
        self.url = ""
        self.output_file_name = ""

    def to_dict(self):
        """
        Serializes :class:`Database` into a dictionary.

        Returns:
            dict: serialized :class:`Database`
        """
        return {"output_file_name": self.output_file_name}

    @staticmethod
    def from_dict(database_dict):
        """
        Deserializes :class:`Database` from a dictionary.

        Args:
            database_dict (dict): serialized :class:`Database`

        Returns:
            Database: deserialized instance
        """
        db = Database()
        db.output_file_name = database_dict["output_file_name"]
        return db


class ExporterNotifications:
    """
    Holds flags for different exporter error conditions.

    Attributes:
        duplicate_output_file_name (bool): True if there are duplicate output file names
        missing_output_file_name (bool): True if the output file name is missing
        missing_specification (bool): True if export specification is missing
    """

    def __init__(self):
        self.duplicate_output_file_name = False
        self.missing_output_file_name = False
        self.missing_specification = False


def subdirectory_for_fork(output_file_name, data_dir, output_time_stamps, fork):
    """
    Creates scenario/tool based output directory for forked workflow.

    Args:
        output_file_name (str): file name
        data_dir (str): project item's data directory
        output_time_stamps (bool): True if time stamp data should be included in the output path
        fork (list of str): list of scenario and tool names

    Returns:
        str: absolute output path
    """
    if output_time_stamps:
        stamp = datetime.fromtimestamp(time())
        time_stamp = "run@" + stamp.isoformat(timespec="seconds").replace(":", ".")
    else:
        time_stamp = ""
    fork_name = ".".join(fork)
    if fork_name:
        if time_stamp:
            path = os.path.join(data_dir, fork_name + "_" + time_stamp, output_file_name)
        else:
            path = os.path.join(data_dir, fork_name, output_file_name)
    else:
        path = os.path.join(data_dir, time_stamp, output_file_name)
    return path
