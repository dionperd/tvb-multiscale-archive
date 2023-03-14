# -*- coding: utf-8 -*-
from collections import OrderedDict
from xarray import DataArray
import numpy as np

from tvb.simulator.plot.time_series_plotter import TimeSeriesPlotter
from tvb.contrib.scripts.datatypes.time_series import TimeSeries
from tvb.contrib.scripts.datatypes.time_series_xarray import TimeSeries as TimeSeriesXarray


class MultimeterPlotter(TimeSeriesPlotter):

    def _confirm_TimeSeries(self, input_time_series, time_series_class=TimeSeriesXarray, time_series_args={}):
        if isinstance(input_time_series, DataArray):
            # if the input is a xarray DataArray, convert it to a TVB TimeSeries
            return time_series_class().from_xarray_DataArray(input_time_series, **time_series_args)
        else:
            return input_time_series

    def _join_variables_and_populations(self, time_series,
                                        var_pop_join_str=" - ", default_population_label="population"):
        # This method will reshape the Time Series by creating a new TimeSeries
        # with all combinations of (state) variables and spiking neurons' populations
        n_pops = time_series.shape[3]
        n_vars = time_series.shape[1]
        data = np.empty((time_series.time_length, n_vars*n_pops, time_series.shape[2], 1))
        var_pop_join_str = str(var_pop_join_str)
        try:
            pop_labels = time_series.labels_dimensions[time_series.labels_ordering[3]]
        except:
            pop_labels = [default_population_label + " %d" % (i_pop+1) for i_pop in range(n_pops)]
        variable_label = lambda var_label, i_pop: var_pop_join_str.join([var_label, pop_labels[i_pop]])
        new_variable_label = var_pop_join_str.join([time_series.labels_ordering[1],
                                                  time_series.labels_ordering[3]])
        labels_ordering = [time_series.labels_ordering[0],
                           new_variable_label,
                           time_series.labels_ordering[2], "Modes"]
        labels_dimensions = OrderedDict()
        try:
            labels_dimensions[labels_ordering[0]] = \
                time_series.labels_dimensions[time_series.labels_ordering[0]]
        except:
            pass
        try:
            labels_dimensions[labels_ordering[2]] = \
                time_series.labels_dimensions[time_series.labels_ordering[2]]
        except:
            pass
        labels_dimensions[new_variable_label] = []
        for i_var, var in enumerate(time_series.labels_dimensions[time_series.labels_ordering[1]]):
            for i_pop in range(n_pops):
                labels_dimensions[new_variable_label].append(variable_label(var, i_pop))
                data[:, i_var * n_pops + i_pop, :, 0] = time_series.data[:, i_var, :, i_pop]
        return time_series.duplicate(data=data, time=time_series.time,
                                     labels_ordering=labels_ordering, labels_dimensions=labels_dimensions)

    def _plot_per_variable(self, fun, time_series, **kwargs):
        plot_outputs = []
        base_title = kwargs.pop("title", "")
        base_figure_name = kwargs.pop("figure_name", None)
        if base_figure_name is None:
            base_figure_name = base_title
        for var in time_series.labels_dimensions[time_series.labels_ordering[1]]:
            title = base_title + ": %s" % var
            figure_name = base_figure_name + "_%s" % var
            plot_outputs.append(fun(time_series.get_state_variables_by_label(var), None, False,
                                    title=title, figure_name=figure_name, **kwargs))
        return plot_outputs

    def plot_multimeter_timeseries(self, input_time_series, plot_per_variable=True,
                                   time_series_class=TimeSeries,  time_series_args={},
                                   var_pop_join_str=" - ", default_population_label="population",
                                   **kwargs):
        time_series = self._confirm_TimeSeries(input_time_series, time_series_class, time_series_args)
        if time_series.shape[3] > 1:
            time_series = self._join_variables_and_populations(time_series, var_pop_join_str, default_population_label)
        if isinstance(time_series, TimeSeriesXarray):
            return time_series.plot_timeseries(plotter_config=self.config, per_variable=plot_per_variable,
                                               figsize=self.config.LARGE_SIZE, **kwargs)
        if plot_per_variable:
            # One figure per (state) variable
            return self._plot_per_variable(self.plot_multimeter_timeseries, time_series, **kwargs)
        return self.plot_time_series(time_series, **kwargs)

    def plot_multimeter_raster(self, input_time_series, plot_per_variable=True,
                               time_series_class=TimeSeries,  time_series_args={},
                               var_pop_join_str=" - ", default_population_label="population",
                               **kwargs):
        time_series = self._confirm_TimeSeries(input_time_series, time_series_class, time_series_args)
        if time_series.shape[3] > 1:
            time_series = self._join_variables_and_populations(time_series, var_pop_join_str, default_population_label)
        if isinstance(time_series, TimeSeriesXarray):
            return time_series.plot_raster(plotter_config=self.config, per_variable=plot_per_variable,
                                           figsize=self.config.LARGE_SIZE, **kwargs)
        if plot_per_variable:
            # One figure per (state) variable
            return self._plot_per_variable(self.plot_multimeter_raster, time_series, **kwargs)
        return self.plot_raster(time_series, **kwargs)
