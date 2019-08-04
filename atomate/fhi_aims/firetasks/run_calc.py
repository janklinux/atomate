# coding: utf-8

from __future__ import division, print_function, unicode_literals, absolute_import

from monty.os.path import zpath
from monty.serialization import loadfn

"""
This module defines tasks that support running vasp in various ways.
"""

import shlex
import os
import six
import subprocess

from custodian import Custodian
from custodian.fhi_aims.jobs import AimsJob
from custodian.fhi_aims.handlers import FrozenJobErrorHandler, AimsErrorHandler
from custodian.fhi_aims.validators import AimsConvergedValidator, AimsSecondValidator


from fireworks import explicit_serialize, FiretaskBase, FWAction

from atomate.utils.utils import env_chk, get_logger


__author__ = 'Anubhav Jain <ajain@lbl.gov>'
__credits__ = 'Shyue Ping Ong <ong.sp>'

logger = get_logger(__name__)


@explicit_serialize
class RunAimsDirect(FiretaskBase):
    """
    Execute a command directly (no custodian).

    Required params:
        cmd (str): the name of the full executable to run. Supports env_chk.
    Optional params:
        expand_vars (str): Set to true to expand variable names in the cmd.
    """

    required_params = ["aims_cmd"]
    optional_params = ["expand_vars"]

    def run_task(self, fw_spec):
        cmd = env_chk(self["aims_cmd"], fw_spec)
        if self.get("expand_vars", False):
            cmd = os.path.expandvars(cmd)

        logger.info("Running command: {}".format(cmd))
        return_code = subprocess.call(cmd, shell=True)
        logger.info("Command {} finished running with returncode: {}".format(cmd, return_code))


@explicit_serialize
class RunAimsCustodian(FiretaskBase):
    """
    Run VASP using custodian "on rails", i.e. in a simple way that supports most common options.

    Required params:
        vasp_cmd (str): the name of the full executable for running VASP. Supports env_chk.

    Optional params:
        job_type: (str) - choose from "normal" (default), "double_relaxation_run" (two consecutive 
            jobs), "full_opt_run" (multiple optimizations), and "neb"
        handler_group: (str or [ErrorHandler]) - group of handlers to use. See handler_groups dict in the code for
            the groups and complete list of handlers in each group. Alternatively, you can
            specify a list of ErrorHandler objects.
        max_force_threshold: (float) - if >0, adds MaxForceErrorHandler. Not recommended for 
            nscf runs.
        scratch_dir: (str) - if specified, uses this directory as the root scratch dir. 
            Supports env_chk.
        gzip_output: (bool) - gzip output (default=T)
        max_errors: (int) - maximum # of errors to fix before giving up (default=5)
        ediffg: (float) shortcut for setting EDIFFG in special custodian jobs
        auto_npar: (bool) - use auto_npar (default=F). Recommended set to T
            for single-node jobs only. Supports env_chk.
        gamma_vasp_cmd: (str) - cmd for Gamma-optimized VASP compilation.
            Supports env_chk.
        wall_time (int): Total wall time in seconds. Activates WalltimeHandler if set.
        half_kpts_first_relax (bool): Use half the k-points for the first relaxation
    """
    required_params = ["aims_cmd"]
    optional_params = ["job_type", "handler_group", "max_force_threshold", "scratch_dir",
                       "gzip_output", "max_errors", "wall_time"]

    def run_task(self, fw_spec):

        handler_groups = {
            "default": [AimsErrorHandler(), FrozenJobErrorHandler()],
            "no_handler": []
            }

        aims_cmd = env_chk(self["aims_cmd"], fw_spec)
        # aims_basis_files = env_chk(self["aims_basis_files"], fw_spec)

        if isinstance(aims_cmd, six.string_types):
            aims_cmd = os.path.expandvars(aims_cmd)
            aims_cmd = shlex.split(aims_cmd)

        # initialize variables
        job_type = self.get("job_type", "light_and_tight_relax")
        scratch_dir = env_chk(self.get("scratch_dir"), fw_spec)
        gzip_output = self.get("gzip_output", True)
        max_errors = self.get("max_errors", 10)

        # construct jobs
        if job_type == "relax":
            jobs = [AimsJob(aims_cmd=aims_cmd)]  # , aims_basis_files=aims_basis_files)]
        else:
            raise ValueError('Unknown job type')

        # construct handlers
        handler_group = self.get("handler_group", "default")
        if isinstance(handler_group, six.string_types):
            handlers = handler_groups[handler_group]
        else:
            handlers = handler_group

        # if job_type == "relax":
        validators = [AimsSecondValidator()]

#        if self.get("max_force_threshold"):
#            handlers.append(MaxForceErrorHandler(max_force_threshold=self["max_force_threshold"]))

        c = Custodian(handlers, jobs, validators=validators, max_errors=max_errors,
                      scratch_dir=scratch_dir, gzipped_output=gzip_output)

        c.run()

        if os.path.exists(zpath("custodian.json")):
            stored_custodian_data = {"custodian": loadfn(zpath("custodian.json"))}
            return FWAction(stored_data=stored_custodian_data)
