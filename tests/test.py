# ----------------------------------------------------------------------
# Copyright 2018 Marco Inacio <pythonpackages@marcoinacio.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.    If not, see <http://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------

import torch
import torch.nn.functional as F

import numpy as np
import scipy.stats as stats

from nnstacking import NNS, NNPredict
from sklearn.model_selection import GridSearchCV, ShuffleSplit
from sklearn import svm, linear_model, ensemble, neighbors

import hashlib
import pickle
from sklearn.externals import joblib
import os

from generate_data import generate_data, true_pdf_calc

if __name__ == "__main__":
    n_train = 10_000
    n_test = 5_000
    x_train, y_train = generate_data(n_train)
    x_test, y_test = generate_data(n_test)

    print(y_train)
    print(min(y_train))
    print(max(y_train))

    estimators = [
        # svm.SVR(),
        neighbors.KNeighborsRegressor(),
        ensemble.RandomForestRegressor(),
        ensemble.GradientBoostingRegressor(),
        ensemble.AdaBoostRegressor(),
        ensemble.BaggingRegressor(),
        linear_model.PassiveAggressiveRegressor(),
        linear_model.OrthogonalMatchingPursuit(),
        linear_model.HuberRegressor(),
        linear_model.BayesianRidge(),
        linear_model.LinearRegression(),
        linear_model.Lasso(alpha=0.5),
        linear_model.Lasso(alpha=1.0),
        linear_model.Lasso(alpha=2.0),
        linear_model.Ridge(alpha=0.5),
        linear_model.Ridge(alpha=1.0),
        linear_model.Ridge(alpha=2.0),
        linear_model.ElasticNet(alpha=0.5),
        linear_model.ElasticNet(alpha=1.0),
        linear_model.ElasticNet(alpha=2.0),
        linear_model.LassoLars(alpha=0.5),
        linear_model.LassoLars(alpha=1.0),
        linear_model.LassoLars(alpha=2.0),
    ]

    nnstacking_obj = NNS(
        verbose=2,
        nn_weight_decay=0.0,
        es=True,
        hidden_size=100,
        num_layers=10,
        base_estimators=estimators,
        gpu=True,
        nworkers=3,
        ensemble_method="UNNS",
    )
    nnstacking_obj.fit(x_train, y_train)

    nnstacking_obj2 = NNS(
        verbose=2,
        nn_weight_decay=0.0,
        es=True,
        hidden_size=100,
        num_layers=10,
        base_estimators=nnstacking_obj.estimators,
        gpu=True,
        nworkers=3,
    )
    nnstacking_obj2.fit(x_train, y_train, nnstacking_obj.predictions)

    nnpredict_obj = NNPredict(
        verbose=2,
        nn_weight_decay=0.0,
        es=True,
        hidden_size=100,
        num_layers=10,
        gpu=True,
        dataloader_workers=3,
    )
    nnpredict_obj.fit(x_train, y_train)

    # print("Risk on train (ensembler):", - nnstacking_obj.score(x_train, y_train))
    # for i, estimator in enumerate(nnstacking_obj.estimators):
    #    print("Risk on train for estimator", i, "is:",
    #          ((estimator.predict(x_train) - y_train)**2).mean()
    #         )

    nnstacking_obj.verbose = 0
    print("Risk on test (ensembler):", -nnstacking_obj.score(x_test, y_test))
    print(
        "Risk on test (ensembler):",
        ((nnstacking_obj.predict(x_test) - y_test) ** 2).mean(),
    )

    nnstacking_obj2.verbose = 0
    print("Risk on test (ensembler 2):", -nnstacking_obj2.score(x_test, y_test))
    print(
        "Risk on test (ensembler 2):",
        ((nnstacking_obj2.predict(x_test) - y_test) ** 2).mean(),
    )

    print("Risk on test (direct neural network):", -nnpredict_obj.score(x_test, y_test))
    print(
        "Risk on test (direct neural network):",
        ((nnpredict_obj.predict(x_test) - y_test) ** 2).mean(),
    )

    risks = []
    for i, estimator in enumerate(nnstacking_obj.estimators):
        prediction = estimator.predict(x_test)
        if len(prediction.shape) == 1:
            prediction = prediction[:, None]
            risks.append(((prediction - y_test) ** 2).mean())

    ind_risks = sorted(range(len(risks)), key=lambda k: risks[k])
    for ind_risk in ind_risks:
        print("Risk on test for estimator", ind_risk, "is:", risks[ind_risk])

    """
    #Check using true density information
    est_pdf = nnstacking_obj.predict(x_test)[:, 1:-1]
    true_pdf = true_pdf_calc(x_test, nnstacking_obj.y_grid[1:-1][:,None]).T
    sq_errors = (est_pdf - true_pdf)**2
    #print("Squared density errors for test:\n", sq_errors)
    print("\nAverage squared density errors for test:\n", sq_errors.mean())

    import matplotlib.pyplot as plt
    plt.plot(true_pdf[1])
    plt.plot(est_pdf[1])
    plt.show()
    """

    # Get ensembler weights
    nnstacking_obj.get_weights(x_test)
