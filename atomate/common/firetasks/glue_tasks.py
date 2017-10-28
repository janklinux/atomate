# coding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import os

import six
import monty

from fireworks import explicit_serialize, FiretaskBase, FWAction

from atomate.utils.utils import env_chk, load_class, recursive_get_result
from atomate.utils.fileio import FileClient

__author__ = 'Anubhav Jain'
__email__ = 'ajain@lbl.gov'


@explicit_serialize
class PassCalcLocs(FiretaskBase):
    """
    Passes information about where the current calculation is located
    for the next FireWork. This is achieved by passing a key to
    the fw_spec called "calc_locs" with this information.

    Required params:
        name (str): descriptive name for this calculation file/dir

    Optional params:
        filesystem (str or custom user format): name of filesystem. Supports env_chk. 
            defaults to None
        path (str): The path to the directory containing the calculation. defaults to
            current working directory.
    """

    required_params = ["name"]
    optional_params = ["filesystem", "path"]

    def run_task(self, fw_spec):
        calc_locs = list(fw_spec.get("calc_locs", []))
        calc_locs.append({"name": self["name"],
                          "filesystem": env_chk(self.get('filesystem', None), fw_spec),
                          "path": self.get("path", os.getcwd())})

        return FWAction(mod_spec=[{'_push_all': {'calc_locs': calc_locs}}])


def get_calc_loc(target_name, calc_locs):
    """
    This is a helper method that helps you pick out a certain calculation
    from an array of calc_locs.

    There are three modes:
        - If you set target_name to a String, search for most recent calc_loc
            with matching nameget_
        - Otherwise, return most recent calc_loc overall

    Args:
        target_name: (bool or str) If str, will search for calc_loc with
            matching name, else use most recent calc_loc
        calc_locs: (dict) The dictionary of all calc_locs

    Returns:
        (dict) dict with subkeys path, filesystem, and name
    """

    if isinstance(target_name, six.string_types):
        for doc in reversed(calc_locs):
            if doc["name"] == target_name:
                return doc
        raise ValueError("Could not find the target_name: {}".format(target_name))
    else:
        return calc_locs[-1]


@explicit_serialize
class CopyFilesFromCalcLoc(FiretaskBase):
    """
    Based on CopyVaspOutputs but for general file copying.

    Required params:
        filenames (str): filenames to copy.
        name_prepend (str): string to prepend filenames, e.g. can be a directory.
        name_append (str): string to append to filenames.

    Optional params:
        calc_dir: directory to copy from.
        calc_loc: name of fw to get location for.
    """

    required_params = ["filenames", "name_prepend","name_append"]
    optional_params = ["calc_dir", "calc_loc"]

    def run_task(self,fw_spec=None):

        if self.get('calc_dir',False):
            filesystem = None
        elif self.get('calc_loc',False):
            calc_loc = get_calc_loc(self.get('calc_loc',False), fw_spec["calc_locs"])
            calc_dir = calc_loc["path"]
            filesystem = calc_loc["filesystem"]
        else:
            raise ValueError("Must specify either calc_dir or calc_loc!")

        fileclient = FileClient(filesystem=filesystem)
        calc_dir = fileclient.abspath(calc_dir)

        all_files = fileclient.listdir(calc_dir)

        if self.get('filenames',False):
            if type(self.get('filenames',False)) == list:
                files_to_copy = self.get('filenames',False)
            elif isinstance(self.get('filenames',False), six.string_types):
                files_to_copy = [ self.get('filenames',False) ]
            else:
                ValueError("Must have a list of strings or a strings!")
        else:
            raise ValueError("Must have a list of filenames!")

        # determine what files need to be copied
        if "$ALL" in self.get('filenames',False):
            files_to_copy = all_files

        # start file copy
        for f in files_to_copy:
            prev_path_full = os.path.join(calc_dir, f)
            # prev_path = os.path.join(os.path.split(calc_dir)[1], f)
            dest_fname = self.get('name_prepend',"")+f+self.get('name_append',"")
            dest_path = os.path.join(os.getcwd(), dest_fname)

            # copy the file (minus the relaxation extension)
            fileclient.copy(prev_path_full, dest_path)
            print(prev_path_full)
            print(dest_path)


@explicit_serialize
class CreateFolder(FiretaskBase):
    """
    FireTask to create new folder with the option of changing directory to the new folder.

    Required params:
        folder_name (str): folder name.

    Optional params:
        change_to (bool): change to new folder. Defaults to False.
        local (bool): whether folder name is relative or absolute. Defaults to True.
    """
    required_params = ["folder_name"]
    optional_params = ["change_to", "local"]

    def run_task(self, fw_spec):

        if self.get("local", True):
            new_dir = os.path.join(os.getcwd(), self["folder_name"])
        else:
            new_dir = os.path.join(self["folder_name"])
        if not os.path.exists(new_dir):
            os.makedirs(new_dir)
        if self.get("change_to", False):
            os.chdir(new_dir)


@explicit_serialize
class PassResult(FiretaskBase):
    """
    Passes properties and corresponding user-specified data resulting from a run from parent
    to child fireworks.  Uses a string syntax similar to Mongo-style queries to designate
    values of output file dictionaries to retrieve.  For example, one could specify
    a task to pass the stress from the current calculation using:
    
    PassResult(pass_dict={'stress': ">>ionic_steps.-1.stress"})

    Required params:
        pass_dict (dict): dictionary designating keys and values to pass
            to child fireworks.  If value is a string beginning with '>>',
            the firework will search the parsed VASP output dictionary
            for the designated property by following the sequence of keys
            separated with periods, e. g. ">>ionic_steps.-1.stress" is used
            to designate the stress from the last ionic_step. If the value
            is not a string or does not begin with ">>", it is passed as is.
        parse_class (str): string representation of complete path to a class 
            with which to parse the output, e. g. pymatgen.io.vasp.Vasprun
            or pymatgen.io.feff.LDos.from_file, class must be MSONable
        parse_kwargs (str): dict of kwargs for the parse class,
            e. g. {"filename": "vasprun.xml", "parse_dos": False, 
            "parse_eigen": False}

    Optional params:
        calc_dir (str): path to dir that contains VASP output files, defaults
            to '.', e. g. current directory
        mod_spec_cmd (str): command to issue for mod_spec, e. g. "_set" or "_push",
            defaults to "_set"
        mod_spec_key (str): key to pass to mod_spec _set dictmod command, defaults
            to "prev_calc_result"
    """

    required_params = ["pass_dict", "parse_class", "parse_kwargs"]
    optional_params = ["calc_dir", "mod_spec_cmd", "mod_spec_key"]
                       
    def run_task(self, fw_spec):
        pass_dict = self.get("pass_dict")
        parse_kwargs = self.get("parse_kwargs")
        pc_string = self.get("parse_class")
        parse_class = load_class(*pc_string.rsplit(".", 1))
        calc_dir = self.get("calc_dir", ".")
        with monty.os.cd(calc_dir):
            result = parse_class(**parse_kwargs)

        pass_dict = recursive_get_result(pass_dict, result)
        mod_spec_key = self.get("mod_spec_key", "prev_calc_result")
        mod_spec_cmd = self.get("mod_spec_cmd", "_set")
        return FWAction(mod_spec=[{mod_spec_cmd: {mod_spec_key: pass_dict}}])


#TODO: not sure this is the best to do this, will mull over it and do the recatoring later - matk
@explicit_serialize
class CopyFiles(FiretaskBase):
    """
    Task to copy the given list of files from the given directory to the destination directory.
    To customize override the setup_copy and copy_files methods.

    Optional params:
        from_dir (str): path to the directory containing the files to be copied.
        to_dir (str): path to the destination directory
        filesystem (str)
        files_to_copy (list): list of file names.
        exclude_files (list): list of file names to be excluded.
    """

    optional_params = ["from_dir", "to_dir", "filesystem", "files_to_copy", "exclude_files"]

    def setup_copy(self, from_dir, to_dir=None, filesystem=None, files_to_copy=None, exclude_files=None,
                   from_path_dict=None):
        """
        setup the copy i.e setup the from directory, filesystem, destination directory etc.

        Args:
            from_dir (str)
            to_dir (str)
            filesystem (str)
            files_to_copy (list): if None all the files in the from_dir will be copied
            exclude_files (list)
            from_path_dict (dict): dict specification of the path. If specified must contain atleast
                the key "path" that specifies the path to the from_dir.
        """
        from_path_dict = from_path_dict or {}
        from_dir = from_dir or from_path_dict.get("path", None)
        filesystem = filesystem or from_path_dict.get("filesystem", None)
        if from_dir is None:
            raise ValueError("Must specify from_dir!")
        self.fileclient = FileClient(filesystem=filesystem)
        self.from_dir = self.fileclient.abspath(from_dir)
        self.to_dir = to_dir or os.getcwd()
        exclude_files = exclude_files or []
        self.files_to_copy = files_to_copy or [f for f in self.fileclient.listdir(self.from_dir) if f not in exclude_files]

    def copy_files(self):
        """
        Defines the copy operation. Override this to customize copying.
        """
        for f in self.files_to_copy:
            prev_path_full = os.path.join(self.from_dir, f)
            dest_path = os.path.join(self.to_dir, f)
            self.fileclient.copy(prev_path_full, dest_path)

    def run_task(self, fw_spec):
        self.setup_copy(self.get("from_dir", None), to_dir=self.get("to_dir", None),
                        filesystem=self.get("filesystem", None),
                        files_to_copy=self.get("files_to_copy", None),
                        exclude_files=self.get("exclude_files", []))
        self.copy_files()
