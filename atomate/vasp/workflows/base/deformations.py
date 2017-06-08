# coding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

"""
This module defines the deformation workflow: structure optimization followed by transmuter fireworks.
"""

from fireworks import Workflow

from pymatgen.io.vasp.sets import MPRelaxSet, MPStaticSet

from atomate.utils.utils import get_logger
from atomate.vasp.firetasks.glue_tasks import pass_vasp_result
from atomate.vasp.fireworks.core import OptimizeFW, TransmuterFW

__author__ = 'Kiran Mathew'
__credits__ = 'Joseph Montoya'
__email__ = 'kmathew@lbl.gov'

logger = get_logger(__name__)


def get_wf_deformations(structure, deformations, name="deformation",
                        lepsilon=False, vasp_cmd="vasp", db_file=None, user_kpoints_settings=None,
                        pass_stress_strain=False, tag="", relax_deformed=False,
                        copy_vasp_outputs=True, metadata=None):
    """
    Returns a structure deformation workflow.

    Firework 1 : structural relaxation
    Firework 2 - len(deformations): Deform the optimized structure and run static calculations.


    Args:
        structure (Structure): input structure to be optimized and run
        deformations (list of 3x3 array-likes): list of deformations
        name (str): some appropriate name for the transmuter fireworks.
        vasp_input_set (DictVaspInputSet): vasp input set.
        lepsilon (bool): whether or not compute static dielectric constant/normal modes
        vasp_cmd (str): command to run
        db_file (str): path to file containing the database credentials.
        user_kpoints_settings (dict): example: {"grid_density": 7000}
        pass_stress_strain (bool): if True, stress and strain will be parsed and passed on.
        tag (str): some unique string that will be appended to the names of the fireworks so that
            the data from those tagged fireworks can be queried later during the analysis.
        relax_deformed (bool): whether or not to relax the deformed structures.
        copy_vasp_outputs (bool):
        metadata (dict): meta data

    Returns:
        Workflow
    """

    fws, parents = [], []

    uis_static = {"ISIF": 2, "ISTART":1}
    if relax_deformed:
        uis_static["IBRION"] = 2
        uis_static["NSW"] = 99

    # static input set for the transmuter firework
    vis_static = MPStaticSet(structure, force_gamma=True, lepsilon=lepsilon,
                             user_kpoints_settings=user_kpoints_settings,
                             user_incar_settings=uis_static)

    # Deformation fireworks with the task to extract and pass stress-strain appended to it.
    for n, deformation in enumerate(deformations):
        fw = TransmuterFW(name="{} {} {}".format(tag, name, n), structure=structure,
                          transformations=['DeformStructureTransformation'],
                          transformation_params=[{"deformation": deformation.tolist()}],
                          vasp_input_set=vis_static, copy_vasp_outputs=copy_vasp_outputs,
                          parents=parents, vasp_cmd=vasp_cmd, db_file=db_file)
        if pass_stress_strain:
            pass_dict = {'strain': deformation.green_lagrange_strain.tolist(),
                         'stress': '>>output.ionic_steps.-1.stress',
                         'deformation_matrix': deformation.tolist()}
            fw.tasks.append(pass_vasp_result(pass_dict=pass_dict,
                                             mod_spec_key="deformation_tasks->{}".format(n)))
        fws.append(fw)

    wfname = "{}:{}".format(structure.composition.reduced_formula, name)

    return Workflow(fws, name=wfname, metadata=metadata)
