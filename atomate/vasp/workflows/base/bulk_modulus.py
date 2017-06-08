# coding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

"""
This module defines the bulk modulus workflow.
"""

from uuid import uuid4

from fireworks import Firework, Workflow

from pymatgen.analysis.elasticity.strain import Deformation

from atomate.utils.utils import get_logger
from atomate.vasp.firetasks.parse_outputs import FitEOSToDb
from atomate.vasp.workflows.base.deformations import get_wf_deformations

__author__ = 'Kiran Mathew'
__email__ = 'kmathew@lbl.gov'

logger = get_logger(__name__)


def get_wf_bulk_modulus(structure, deformations, vasp_cmd="vasp", db_file=None,
                        user_kpoints_settings=None, eos="vinet", tag=None):
    """
    Returns the workflow that computes the bulk modulus by fitting to the given equation of state.

    Args:
        structure (Structure): input structure.
        deformations (list): list of deformation matrices(list of lists).
        vasp_input_set (VaspInputSet)
        vasp_cmd (str): vasp command to run.
        db_file (str): path to the db file.
        user_kpoints_settings (dict): example: {"grid_density": 7000}
        eos (str): equation of state used for fitting the energies and the volumes.
            supported equation of states: "quadratic", "murnaghan", "birch", "birch_murnaghan",
            "pourier_tarantola", "vinet", "deltafactor". See pymatgen.analysis.eos.py

    Returns:
        Workflow
    """

    tag = tag or "bulk_modulus group: >>{}<<".format(str(uuid4()))

    deformations = [Deformation(defo_mat) for defo_mat in deformations]
    wf_bulk_modulus = get_wf_deformations(structure, deformations, name="bulk_modulus deformation",
                                          lepsilon=False,
                                          vasp_cmd=vasp_cmd, db_file=db_file, relax_deformed=True,
                                          user_kpoints_settings=user_kpoints_settings, tag=tag)

    fw_analysis = Firework(FitEOSToDb(tag=tag, db_file=db_file, eos=eos), name="fit equation of state")

    wf_bulk_modulus.append_wf(Workflow.from_Firework(fw_analysis), wf_bulk_modulus.leaf_fw_ids)

    wf_bulk_modulus.name = "{}:{}".format(structure.composition.reduced_formula, "Bulk modulus")

    return wf_bulk_modulus
