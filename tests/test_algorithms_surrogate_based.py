"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Copyright: (c) 2020, Deutsches Zentrum fuer Luft- und Raumfahrt e.V.
Contact: jasper.bussemaker@dlr.de
"""

import pytest
import numpy as np
from pymoo.model.problem import Problem
from pymoo.factory import get_problem, get_reference_directions

from smt.surrogate_models.rbf import RBF

from arch_opt_exp.experimenter import *
from arch_opt_exp.metrics.performance import *
from arch_opt_exp.algorithms.surrogate.func_estimate import *
from arch_opt_exp.algorithms.surrogate.surrogate_infill import *
from arch_opt_exp.algorithms.surrogate.p_of_feasibility import *


@pytest.fixture
def problem() -> Problem:
    return get_problem('zdt1')


def test_surrogate_infill(problem):
    sbo = SurrogateBasedInfill(
        surrogate_model=RBF(d0=1., poly_degree=-1, reg=1e-10),
        infill=FunctionEstimateInfill(),
    )
    algorithm = sbo.algorithm(infill_size=10, init_size=20)

    metric = IGDMetric(problem.pareto_front())
    exp = Experimenter(problem, algorithm, n_eval_max=100, algorithm_name=sbo.name, metrics=[metric])
    result = exp.run_effectiveness(repeat_idx=0, seed=0)

    values = result.metrics[metric.name].values['indicator']
    assert len(values) == 9
    assert values[-1] < values[0]


def test_surrogate_infill_parallel(problem):
    sbo = SurrogateBasedInfill(
        surrogate_model=RBF(d0=1., poly_degree=-1, reg=1e-10),
        infill=FunctionEstimateInfill(),
        termination=5,
    )
    algorithm = sbo.algorithm(infill_size=10, init_size=20)

    metric = DeltaHVMetric(problem.pareto_front())
    exp = Experimenter(problem, algorithm, n_eval_max=100, algorithm_name=sbo.name, metrics=[metric])
    results = exp.run_effectiveness_parallel(n_repeat=2)

    assert len(results) == 2


def test_surrogate_infill_constrained():
    problem = get_problem('C1DTLZ1')
    ref_dirs = get_reference_directions('das-dennis', 3, n_partitions=12)

    sbo = SurrogateBasedInfill(
        surrogate_model=RBF(d0=1., poly_degree=-1, reg=1e-10),
        infill=FunctionEstimateInfill(),
    )
    algorithm = sbo.algorithm(infill_size=10, init_size=20)

    igd_metric = IGDMetric(problem.pareto_front(ref_dirs))
    max_cv = MaxConstraintViolationMetric()
    exp = Experimenter(problem, algorithm, n_eval_max=100, algorithm_name=sbo.name, metrics=[igd_metric, max_cv])
    result = exp.run_effectiveness(repeat_idx=0, seed=0)

    values = result.metrics[igd_metric.name].values['indicator']
    assert len(values) == 9
    assert values[-1] < values[0]

    max_cv_values = result.metrics[max_cv.name].values['max_cv']
    assert max_cv_values[0] > max_cv_values[-1]


def test_pof():
    g = np.array([[0, 0, 1, 1, -1, -1]]).T
    g_var = np.array([[1, 2, 1, 2, 1, 2]]).T
    pof = ProbabilityOfFeasibilityInfill._pof(g, g_var)
    assert np.all(pof[:, 0]-[.5, .5, .159, .309, 1-.159, 1-.309] < 1e-2)
