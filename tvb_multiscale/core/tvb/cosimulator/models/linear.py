# -*- coding: utf-8 -*-
#
#
#  TheVirtualBrain-Scientific Package. This package holds all simulators, and
# analysers necessary to run brain-simulations. You can use it stand alone or
# in conjunction with TheVirtualBrain-Framework Package. See content of the
# documentation-folder for more details. See also http://www.thevirtualbrain.org
#
# (c) 2012-2020, Baycrest Centre for Geriatric Care ("Baycrest") and others
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this
# program.  If not, see <http://www.gnu.org/licenses/>.
#
#
#   CITATION:
# When using The Virtual Brain for scientific publications, please cite it as follows:
#
#   Paula Sanz Leon, Stuart A. Knock, M. Marmaduke Woodman, Lia Domide,
#   Jochen Mersmann, Anthony R. McIntosh, Viktor Jirsa (2013)
#       The Virtual Brain: a simulator of primate brain network dynamics.
#   Frontiers in Neuroinformatics (7:10. doi: 10.3389/fninf.2013.00010)

"""
Generic linear model.

"""

import numpy
from tvb.simulator.models.base import Model
from tvb.basic.neotraits.api import NArray, Final, List, Range


class Linear(Model):

    tau = NArray(
        label=r":math:`\tau`",
        default=numpy.array([100.0]),
        domain=Range(lo=-0.1, hi=100.0, step=0.1),
        doc="Time constant")

    gamma = NArray(
        label=r":math:`\gamma`",
        default=numpy.array([-1.0]),
        domain=Range(lo=-100.0, hi=0.0, step=1.0),
        doc="The damping coefficient specifies how quickly the node's activity relaxes, must be larger"
            " than the node's in-degree in order to remain stable.")

    I_o = NArray(
        label=r":math:`I_o`",
        default=numpy.array([0.0]),
        domain=Range(lo=-100.0, hi=100.0, step=1.0),
        doc="External stimulus")

    G = NArray(
        label=r":math:`G`",
        default=numpy.array([2.0]),
        domain=Range(lo=-0.0, hi=100.0, step=1.0),
        doc="Global coupling scaling")

    state_variable_range = Final(
        label="State Variable ranges [lo, hi]",
        default={"R": numpy.array([0, 100.0])},
        doc="Range used for state variable initialization and visualization.")

    state_variable_boundaries = Final(
        default={"R": numpy.array([0.0, None])},
        label="State Variable boundaries [lo, hi]",
        doc="""The values for each state-variable should be set to encompass
                the boundaries of the dynamic range of that state-variable. 
                Set None for one-sided boundaries""")

    variables_of_interest = List(
        of=str,
        label="Variables watched by Monitors",
        choices=("R",),
        default=("R",), )

    state_variables = ('R',)
    _nvar = 1
    cvar = numpy.array([0], dtype=numpy.int32)

    def dfun(self, state, coupling, local_coupling=0.0):
        """
        .. math::
            dR = ({\gamma}R + G * coupling + local_coupling * R)/{\tau} + I_o
        """
        R, = state
        c, = coupling
        dR = (self.gamma * R + self.G * c + local_coupling * R) / self.tau + self.I_o
        return numpy.array([dR])
