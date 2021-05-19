"""
Licensed under the GNU General Public License, Version 3.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.gnu.org/licenses/gpl-3.0.html.en

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Copyright: (c) 2021, Deutsches Zentrum fuer Luft- und Raumfahrt e.V.
Contact: jasper.bussemaker@dlr.de
"""

from pymoo.model.problem import Problem
from arch_opt_exp.experiments.moea_helpers import *

from arch_opt_exp.experiments import runner
from arch_opt_exp.metrics.performance import *
from arch_opt_exp.problems.hierarchical import *
from arch_opt_exp.algorithms.surrogate.validation import *
from arch_opt_exp.algorithms.surrogate.mo.min_var_pf import *
from arch_opt_exp.algorithms.surrogate.func_estimate import *
from arch_opt_exp.algorithms.surrogate.mo.enhanced_poi import *
from arch_opt_exp.algorithms.surrogate.surrogate_infill import *
from arch_opt_exp.algorithms.surrogate.so_probabilities import *
from arch_opt_exp.algorithms.surrogate.p_of_feasibility import *
from arch_opt_exp.algorithms.surrogate.mo.hv_improvement import *
from arch_opt_exp.algorithms.surrogate.mo.expected_maximin import *

from arch_opt_exp.surrogates.smt_models.smt_krg import *
from arch_opt_exp.surrogates.smt_models.smt_rbf import *


def run_effectiveness_analytical(do_run=True):
    problem = get_analytical_problem()
    run_effectiveness(problem, 'eff_an_1', do_run=do_run)


def run_effectiveness_analytical_mo(do_run=True):
    problem = get_analytical_problem()
    run_effectiveness(problem, 'eff_an_5', n_infill=5, do_run=do_run)


def run_effectiveness(problem: Problem, results_key, n_infill=1, do_run=True):
    metrics, plot_metric_values = get_metrics(problem, include_loo_cv=False)

    n_init = 5*problem.n_var
    n_rep = 8
    n_term = 100

    n_iter = 400-n_init
    n_eval_max = n_init+min(n_iter*n_infill, 1000)

    nsga2 = get_algo(problem, n_init=n_init)
    nsga2_name = 'NSGA2'

    rbf_sm = SMTRBFSurrogateModel(d0=1., deg=-1, reg=1e-10)
    rbf_algorithms = [
        SurrogateBasedInfill(infill=FunctionEstimateInfill(), surrogate_model=rbf_sm, termination=n_term, verbose=True)
            .algorithm(infill_size=n_infill, init_size=n_init),
        SurrogateBasedInfill(infill=FunctionEstimateDistanceInfill(), surrogate_model=rbf_sm, termination=n_term,
                             verbose=True).algorithm(infill_size=n_infill, init_size=n_init),
    ]
    rbf_algo_names = ['RBF(y)', 'RBF(y-Dist)']

    infills = {
        'y': (FunctionEstimatePoFInfill, FunctionEstimatePoFInfill, {}),
        's': (FunctionVariancePoFInfill, FunctionVariancePoFInfill, {}),
        'lcb': (LowerConfidenceBoundInfill, LowerConfidenceBoundInfill, {'alpha': 2.}),
        'ei': (ExpectedImprovementInfill, ExpectedImprovementInfill, {}),
        'poi': (ProbabilityOfImprovementInfill, ProbabilityOfImprovementInfill, {}),

        'eei': (EuclideanEIInfill, ModEuclideanEIInfill, {}),
        # 'ehvi': (ExpectedHypervolumeImprovementInfill, ModExpectedHypervolumeImprovementInfill, {}),
        'epoi': (EnhancedPOIInfill, ModEnhancedPOIInfill, {}),
        'mpoi': (MinimumPOIInfill, ModMinimumPOIInfill, {}),
        'mepoi': (MinimumPOIInfill, ModMinimumPOIInfill, {'euclidean': True}),
        'emfi': (ExpectedMaximinFitnessInfill, ModExpectedMaximinFitnessInfill, {}),
        'mvpf': (MinVariancePFInfill, MinVariancePFInfill, {}),
    }

    def _get_kriging_algo(sm, infill_key):
        infill = infills[infill_key][0 if n_infill == 1 else 1](**infills[infill_key][2])
        return SurrogateBasedInfill(infill=infill, surrogate_model=sm, termination=n_term, verbose=True)\
            .algorithm(infill_size=n_infill, init_size=n_init)

    smt_kwargs = {'theta0': 1.}
    sms = [
        (SMTKrigingSurrogateModel(auto_wrap_mixed_int=False, **smt_kwargs), 'cont_relax'),
    ]
    infill_keys = list(infills.keys())

    kr_algos = [_get_kriging_algo(sm, key) for key in infill_keys for sm, _ in sms]
    kr_algo_names = [('SBO(%s, %s)' % (name, key.upper())) for key in infill_keys for _, name in sms]

    algorithms = [nsga2]+rbf_algorithms+kr_algos
    algorithm_names = [nsga2_name]+rbf_algo_names+kr_algo_names
    run(results_key, problem, algorithms, algorithm_names, metrics, plot_metric_values, n_repeat=n_rep, do_run=do_run,
        n_eval_max=n_eval_max)


def get_analytical_problem():
    return MOHierarchicalTestProblem()


def get_metrics(problem: Problem, include_loo_cv=True):
    pf = problem.pareto_front()
    metrics = [
        DeltaHVMetric(pf),
        IGDMetric(pf),
        SpreadMetric(),
        MaxConstraintViolationMetric(),
        SurrogateQualityMetric(include_loo_cv=include_loo_cv, n_loo_cv=4),
        TrainingMetric(),
        InfillMetric(),
    ]
    plot_metric_values = {
        'delta_hv': ['delta_hv'],
        'IGD': None,
        'spread': ['delta'],
        'max_cv': ['max_cv'],
        'sm_quality': ['rmse', 'loo_cv'] if include_loo_cv else ['rmse'],
        'training': ['n_train', 'n_samples', 'time_train'],
        'infill': ['time_infill'],
    }
    return metrics, plot_metric_values


def run(results_key, problem, algorithms, algorithm_names, metrics, plot_metric_values, n_repeat=8, n_eval_max=300,
        do_run=True):
    runner.set_results_folder(results_key)
    exp = runner.get_experimenters(problem, algorithms, metrics, n_eval_max=n_eval_max, algorithm_names=algorithm_names)

    if do_run:
        runner.run_effectiveness_multi(exp, n_repeat=n_repeat)
    runner.plot_effectiveness_results(exp, plot_metric_values=plot_metric_values, save=True, show=False)


if __name__ == '__main__':
    run_effectiveness_analytical(
        # do_run=False,
    )