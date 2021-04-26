#####################################################
# Copyright (c) Xuanyi Dong [GitHub D-X-Y], 2021.03 #
#####################################################
import math
import abc
import copy
import numpy as np
from typing import Optional
import torch
import torch.utils.data as data

from .math_base_funcs import FitFunc
from .math_base_funcs import QuadraticFunc
from .math_base_funcs import QuarticFunc


class DynamicQuadraticFunc(FitFunc):
    """The dynamic quadratic function that outputs f(x) = a * x^2 + b * x + c.
    The a, b, and c is a function of timestamp.
    """

    def __init__(self, list_of_points=None):
        super(DynamicQuadraticFunc, self).__init__(3, list_of_points)
        self._timestamp = None

    def __call__(self, x, timestamp=None):
        self.check_valid()
        if timestamp is None:
            timestamp = self._timestamp
        a = self._params[0](timestamp)
        b = self._params[1](timestamp)
        c = self._params[2](timestamp)
        convert_fn = lambda x: x[-1] if isinstance(x, (tuple, list)) else x
        a, b, c = convert_fn(a), convert_fn(b), convert_fn(c)
        return a * x * x + b * x + c

    def _getitem(self, x, weights):
        raise NotImplementedError

    def set_timestamp(self, timestamp):
        self._timestamp = timestamp

    def __repr__(self):
        return "{name}({a} * x^2 + {b} * x + {c})".format(
            name=self.__class__.__name__,
            a=self._params[0],
            b=self._params[1],
            c=self._params[2],
        )


class ConstantFunc(FitFunc):
    """The constant function: f(x) = c."""

    def __init__(self, constant=None):
        param = dict()
        param[0] = constant
        super(ConstantFunc, self).__init__(0, None, param)

    def __call__(self, x):
        self.check_valid()
        return self._params[0]

    def fit(self, **kwargs):
        raise NotImplementedError

    def _getitem(self, x, weights):
        raise NotImplementedError

    def __repr__(self):
        return "{name}({a})".format(name=self.__class__.__name__, a=self._params[0])


class ComposedSinFunc(FitFunc):
    """The composed sin function that outputs:
      f(x) = amplitude-scale-of(x) * sin( period-phase-shift-of(x) )
    - the amplitude scale is a quadratic function of x
    - the period-phase-shift is another quadratic function of x
    """

    def __init__(self, **kwargs):
        super(ComposedSinFunc, self).__init__(0, None)
        self.fit(**kwargs)

    def __call__(self, x):
        self.check_valid()
        scale = self._params["amplitude_scale"](x)
        period_phase = self._params["period_phase_shift"](x)
        return scale * math.sin(period_phase)

    def fit(self, **kwargs):
        num_sin_phase = kwargs.get("num_sin_phase", 7)
        min_amplitude = kwargs.get("min_amplitude", 1)
        max_amplitude = kwargs.get("max_amplitude", 4)
        phase_shift = kwargs.get("phase_shift", 0.0)
        # create parameters
        amplitude_scale = QuadraticFunc(
            [(0, min_amplitude), (0.5, max_amplitude), (1, min_amplitude)]
        )
        fitting_data = []
        temp_max_scalar = 2 ** (num_sin_phase - 1)
        for i in range(num_sin_phase):
            value = (2 ** i) / temp_max_scalar
            next_value = (2 ** (i + 1)) / temp_max_scalar
            for _phase in (0, 0.25, 0.5, 0.75):
                inter_value = value + (next_value - value) * _phase
                fitting_data.append((inter_value, math.pi * (2 * i + _phase)))
        period_phase_shift = QuarticFunc(fitting_data)
        self.set(
            dict(amplitude_scale=amplitude_scale, period_phase_shift=period_phase_shift)
        )

    def _getitem(self, x, weights):
        raise NotImplementedError

    def __repr__(self):
        return "{name}({amplitude_scale} * sin({period_phase_shift}))".format(
            name=self.__class__.__name__,
            amplitude_scale=self._params["amplitude_scale"],
            period_phase_shift=self._params["period_phase_shift"],
        )