# -*- coding: utf-8 -*-

from abc import ABCMeta, ABC

from tvb_multiscale.core.interfaces.models.basal_ganglia_izhikevich import \
    BasalGangliaIzhikevichTVBSpikeNetInterfaceBuilder, \
    BasalGangliaIzhikevichSpikeNetRemoteInterfaceBuilder, BasalGangliaIzhikevichSpikeNetTransformerInterfaceBuilder, \
    BasalGangliaIzhikevichSpikeNetOutputTransformerInterfaceBuilder, \
    BasalGangliaIzhikevichSpikeNetInputTransformerInterfaceBuilder, \
    BasalGangliaIzhikevichSpikeNetInterfaceBuilder, BasalGangliaIzhikevichSpikeNetProxyNodesBuilder

from tvb_multiscale.tvb_nest.interfaces.builders import NESTProxyNodesBuilder, NESTInterfaceBuilder, \
    NESTRemoteInterfaceBuilder, TVBNESTInterfaceBuilder, \
    NESTTransformerInterfaceBuilder, NESTOutputTransformerInterfaceBuilder, NESTInputTransformerInterfaceBuilder


class BasalGangliaIzhikevichNESTProxyNodesBuilder(NESTProxyNodesBuilder,
                                                  BasalGangliaIzhikevichSpikeNetProxyNodesBuilder, ABC):
    __metaclass__ = ABCMeta

    pass


class BasalGangliaIzhikevichNESTInterfaceBuilder(BasalGangliaIzhikevichNESTProxyNodesBuilder, NESTInterfaceBuilder, 
                                                 BasalGangliaIzhikevichSpikeNetInterfaceBuilder):

    pass


class BasalGangliaIzhikevichNESTRemoteInterfaceBuilder(BasalGangliaIzhikevichNESTInterfaceBuilder,
                                                       NESTRemoteInterfaceBuilder,
                                                       BasalGangliaIzhikevichSpikeNetRemoteInterfaceBuilder):

    def default_output_config(self):
        BasalGangliaIzhikevichSpikeNetRemoteInterfaceBuilder.default_output_config(self)

    def default_input_config(self):
        BasalGangliaIzhikevichSpikeNetRemoteInterfaceBuilder.default_input_config(self)


class BasalGangliaIzhikevichNESTOutputTransformerInterfaceBuilder(
    BasalGangliaIzhikevichNESTInterfaceBuilder, NESTOutputTransformerInterfaceBuilder,
    BasalGangliaIzhikevichSpikeNetOutputTransformerInterfaceBuilder):

    def default_output_config(self):
        BasalGangliaIzhikevichSpikeNetOutputTransformerInterfaceBuilder.default_output_config(self)

    def default_input_config(self):
        BasalGangliaIzhikevichSpikeNetOutputTransformerInterfaceBuilder.default_input_config(self)


class BasalGangliaIzhikevichNESTInputTransformerInterfaceBuilder(
    BasalGangliaIzhikevichNESTInterfaceBuilder, NESTInputTransformerInterfaceBuilder,
    BasalGangliaIzhikevichSpikeNetInputTransformerInterfaceBuilder):

    def default_output_config(self):
        BasalGangliaIzhikevichSpikeNetInputTransformerInterfaceBuilder.default_output_config(self)

    def default_input_config(self):
        BasalGangliaIzhikevichSpikeNetInputTransformerInterfaceBuilder.default_input_config(self)


class BasalGangliaIzhikevichNESTTransformerInterfaceBuilder(
    BasalGangliaIzhikevichNESTInterfaceBuilder, NESTTransformerInterfaceBuilder,
    BasalGangliaIzhikevichSpikeNetTransformerInterfaceBuilder):

    def default_output_config(self):
        BasalGangliaIzhikevichSpikeNetTransformerInterfaceBuilder.default_output_config(self)

    def default_input_config(self):
        BasalGangliaIzhikevichSpikeNetTransformerInterfaceBuilder.default_input_config(self)


class BasalGangliaIzhikevichTVBNESTInterfaceBuilder(
    BasalGangliaIzhikevichNESTProxyNodesBuilder, TVBNESTInterfaceBuilder,
    BasalGangliaIzhikevichTVBSpikeNetInterfaceBuilder):

    def default_output_config(self):
        BasalGangliaIzhikevichTVBSpikeNetInterfaceBuilder.default_output_config(self)

    def default_input_config(self):
        BasalGangliaIzhikevichTVBSpikeNetInterfaceBuilder.default_input_config(self)
