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

import numpy as np
import matplotlib.pyplot as plt
from pymoo.model.population import Population
from arch_opt_exp.problems.discretization import *

__all__ = ['MixedIntGoldsteinProblem']


class MixedIntGoldsteinProblem(MixedIntBaseProblem):
    """
    Mixed-integer version of the Branin problem that introduces two discrete variables that transform the original
    Branin space in different ways.

    Implementation based on:
    Pelamatti 2020: "Overview and Comparison of Gaussian Process-Based Surrogate Models for Mixed Continuous and
    Discrete Variables", section 4.1
    """

    def __init__(self):
        xl, xu = np.zeros((4,)), np.array([100., 100., 2, 2])
        self.is_int_mask = np.array([False, False, True, True], dtype=bool)
        self.is_cat_mask = np.array([False]*4, dtype=bool)
        super(MixedIntGoldsteinProblem, self).__init__(n_var=4, n_obj=1, xl=xl, xu=xu)

    def _evaluate(self, x, out, *args, **kwargs):
        x = self.correct_x(x)

        _x3 = [20, 50, 80]
        _x4 = [20, 50, 80]

        f = np.empty((x.shape[0], 1))
        for i in range(x.shape[0]):
            x3, x4 = _x3[int(x[i, 2])], _x4[int(x[i, 3])]
            f[i, 0] = self._h(x[i, 0], x[i, 1], x3, x4)

        out['F'] = f

    @staticmethod
    def _h(x1, x2, x3, x4):
        return sum([
            53.3108,
            .184901 * x1,
            -5.02914 * x1**3 * 1e-6,
            7.72522 * x1**4 * 1e-8,
            0.0870775 * x2,
            -0.106959 * x3,
            7.98772 * x3**3 * 1e-6,
            0.00242482 * x4,
            1.32851 * x4**3 * 1e-6,
            -0.00146393 * x1 * x2,
            -0.00301588 * x1 * x3,
            -0.00272291 * x1 * x4,
            0.0017004 * x2 * x3,
            0.0038428 * x2 * x4,
            -0.000198969 * x3 * x4,
            1.86025 * x1 * x2 * x3 * 1e-5,
            -1.88719 * x1 * x2 * x4 * 1e-6,
            2.50923 * x1 * x3 * x4 * 1e-5,
            -5.62199 * x2 * x3 * x4 * 1e-5,
        ])

    def plot(self, z1=0, z2=0, show=True):
        xx, yy = np.meshgrid(np.linspace(0, 100, 50), np.linspace(0, 100, 50))
        x = np.column_stack([xx.ravel(), yy.ravel(), np.ones((xx.size,))*z1, np.ones((xx.size,))*z2])

        out = Population.new(X=x)
        out = self.evaluate(x, out)
        ff = out.reshape(xx.shape)

        plt.figure(), plt.title('Discrete Goldstein: $z_1$ = %d, $z_2$ = %d' % (z1, z2))
        plt.colorbar(plt.contourf(xx, yy, ff, 50, cmap='viridis'))
        plt.xlabel('$x_1$'), plt.ylabel('$x_2$')
        plt.xlim([0, 100]), plt.ylim([0, 100])

        if show:
            plt.show()


if __name__ == '__main__':
    MixedIntGoldsteinProblem().plot(z1=0, z2=0)