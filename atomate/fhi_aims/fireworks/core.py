# coding: utf-8

from __future__ import absolute_import, division, print_function, \
    unicode_literals


"""
Defines standardized Fireworks that can be chained easily to perform various
sequences of FHI-aims calculations.
"""

from fireworks import Firework

from atomate.common.firetasks.glue_tasks import PassCalcLocs

from atomate.fhi_aims.firetasks.run_calc import RunAimsCustodian
from atomate.fhi_aims.firetasks.write_inputs import WriteAimsFromIOSet

class OptimizeFW(Firework):

    def __init__(self, control, structure, name="Relaxation",
                 aims_cmd='mpirun aims',
                 job_type="relax",
                 max_force_threshold=0.01,
                 parents=None, **kwargs):
        """
        Optimize the given structure.

        Args:
            structure (Structure): Input structure.
            name (str): Name for the Firework.
            vasp_input_set (VaspInputSet): input set to use. Defaults to MPRelaxSet() if None.
            override_default_vasp_params (dict): If this is not None, these params are passed to 
                the default vasp_input_set, i.e., MPRelaxSet. This allows one to easily override 
                some settings, e.g., user_incar_settings, etc.
            vasp_cmd (str): Command to run vasp.
            ediffg (float): Shortcut to set ediffg in certain jobs
            db_file (str): Path to file specifying db credentials to place output parsing.
            force_gamma (bool): Force gamma centered kpoint generation
            job_type (str): custodian job type (default "double_relaxation_run")
            max_force_threshold (float): max force on a site allowed at end; otherwise, reject job
            auto_npar (bool or str): whether to set auto_npar. defaults to env_chk: ">>auto_npar<<"
            half_kpts_first_relax (bool): whether to use half the kpoints for the first relaxation
            parents ([Firework]): Parents of this particular Firework.
            \*\*kwargs: Other kwargs that are passed to Firework.__init__.
        """

        t = []
        t.append(WriteAimsFromIOSet(control=control, structure=structure))

        t.append(RunAimsCustodian(aims_cmd=aims_cmd, job_type=job_type, max_force_threshold=max_force_threshold))

        t.append(PassCalcLocs(name=name))

#        t.append(
#            VaspToDb(db_file=db_file, additional_fields={"task_label": name}))

        super(OptimizeFW, self).__init__(t, parents=parents, name="{}-{}".
                                         format('FHI-aims: ', name), **kwargs)
