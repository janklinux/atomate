# coding: utf-8

from __future__ import division, print_function, unicode_literals, absolute_import

"""
This module defines tasks for writing vasp input sets for various types of vasp calculations
"""


from fireworks import FiretaskBase, explicit_serialize


__author__ = 'Anubhav Jain, Shyue Ping Ong, Kiran Mathew, Jan Kloppenburg'
__email__ = 'ajain@lbl.gov'


@explicit_serialize
class WriteAimsFromIOSet(FiretaskBase):
    """
    Create VASP input files using implementations of pymatgen's AbstractVaspInputSet. An input set 
    can be provided as an object or as a String/parameter combo.

    Required params:
        structure (Structure): structure
        vasp_input_set (AbstractVaspInputSet or str): Either a VaspInputSet object or a string 
            name for the VASP input set (e.g., "MPRelaxSet").

    Optional params:
        vasp_input_params (dict): When using a string name for VASP input set, use this as a dict 
            to specify kwargs for instantiating the input set parameters. For example, if you want 
            to change the user_incar_settings, you should provide: {"user_incar_settings": ...}. 
            This setting is ignored if you provide the full object representation of a VaspInputSet 
            rather than a String.
    """

    required_params = ['control', 'structure']  # , 'aims_basis_set', 'aims_basis_files']
    optional_params = ['aims_input_changes']

    def run_task(self, fw_spec):
        element_list = []
        with open('geometry.in', 'wt') as f:
            for line in self['structure']:
                f.write(line)
                atom = line.split()[4]
                if element_list.count(atom) == 0:
                    element_list.append(atom)

        with open('control.in', 'wt') as f:
            for line in self['control']:
                f.write(line)

#        basis_files = []
#        for el in element_list:
#            file_pattern = os.path.join(self['aims_basis_files'], self['aims_basis_set'], '**'+el+'_default')
#            for basis_file in glob.glob(file_pattern):
#                basis_files.append(basis_file)

#        with open('control.in', 'at') as ctrl:
#            for src in basis_files:
#                with open(src, 'rt') as f_in:
#                    ctrl.write(f_in.read())


@explicit_serialize
class ModifyControl(FiretaskBase):
    """
    Modify the control.in file.

    Required params:
        (none)

    Optional params:
        incar_update (dict): overwrite Incar dict key. Supports env_chk.
        incar_multiply ([{<str>:<float>}]) - multiply Incar key by a constant
            factor. Supports env_chk.
        incar_dictmod ([{}]): use DictMod language to change Incar.
            Supports env_chk.
        input_filename (str): Input filename (if not "INCAR")
        output_filename (str): Output filename (if not "INCAR")
    """

    optional_params = ["incar_update", "incar_multiply", "incar_dictmod", "input_filename",
                       "output_filename"]

    def run_task(self, fw_spec):
        pass
