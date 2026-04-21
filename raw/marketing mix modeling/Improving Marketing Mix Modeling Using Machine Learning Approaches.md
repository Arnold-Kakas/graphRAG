---
title: "Improving Marketing Mix Modeling Using Machine Learning Approaches"
source: "https://towardsdatascience.com/improving-marketing-mix-modeling-using-machine-learning-approaches-25ea4cd6994b/"
author:
  - "[[Slava Kisilevich]]"
published: 2022-06-08
created: 2026-04-20
description: "Building MMM models using tree-based ensembles and explaining media channel performance using SHAP (Shapley Additive Explanations)"
tags:
  - "clippings"
---
![Photo by Adrien Converse on Unsplash](https://towardsdatascience.com/wp-content/uploads/2022/06/1jFaR-0t1MfTGme8Wv36O1g.jpeg)

Photo by Adrien Converse on Unsplash

There are many ways one can build a marketing mix model (MMM) but usually, it boils down to using linear regression for its simple interpretability. Interpretability of more complex non-linear models is the topic of research in the last 5–6 years since such concepts as [LIME](https://github.com/marcotcr/lime) or [SHAP](https://shap.readthedocs.io/en/latest/index.html) were proposed in the machine learning community to explain the output of a model. However, these new concepts seem to be almost unknown in the field of marketing attribution. In this article, I continue investigating practical approaches in marketing mix modeling by building tree-based ensembles using Random Forest and explaining media channel performance using the SHAP concept.

---

In my previous article, I used bayesian programming to build a marketing mix model and compared the results to the [Robyn framework](https://github.com/facebookexperimental/Robyn). My primary interest was to investigate if both approaches are comparable and can be consistent in storytelling. Since Robyn generates multiple solutions, I was able to find the one, which is consistent with the Bayesian solution, namely that shares of effects of both models are consistently higher or lower than shares of spending in each channel. The percentage differences could be attributed to differences in approaches and the ability of models to fit the data well. However, the common between the two approaches is that both describe a linear relationship between media spending and response and are hence unable to capture more complex variable relationships such as interactions.

> [**Modeling Marketing Mix using PyMC3**](https://towardsdatascience.com/modeling-marketing-mix-using-pymc3-ba18dd9e6e68)

One of the first commercial proof of concepts for using more complex algorithms like Gradient Boosting Machines (GBM) along with SHAP in marketing mix modeling, that I could find, was described by [H2O.ai](https://h2o.ai/resources/white-paper/the-benefits-of-budget-allocation-with-ai-driven-marketing-mix-models/).

I summarise the main motivations behind switching to more complex algorithms:

- Classical approaches like linear regression, are challenging and require time and expertise to identify proper model structures such as variable correlations, interactions, or non-linear relationships. In some cases, highly correlated features should be removed. Interaction variables should be explicitly engineered. Non-linearities like saturation and diminishing returns should be explicitly introduced by different transformations.
- Some model structures are sacrificed for the sake of easier model interpretability which may lead to poor model performance.
- More complex machine learning algorithms like tree-based ensembles work well in the presence of highly correlated variables, may capture interactions between variables, are non-linear, and are usually more accurate.

The details behind SHAP for model explanation are explained in many [articles](https://proceedings.neurips.cc/paper/2017/file/8a20a8621978632d76c43dfd28b67767-Paper.pdf) and [books](https://christophm.github.io/interpretable-ml-book/shapley.html). I summarise the main intuition behind SHAP below:

> SHAP (SHapley Additive exPlanations) is a game theoretic approach to explain the output of any machine learning model. It connects optimal credit allocation with local explanations using the classic Shapley values from game theory and their related extensions

- SHAP is a method for explaining individual predictions and answers the question of *how much does each feature contribute to this prediction*
- SHAP values are measures of feature importance
- SHAP values can be negative and positive and show the magnitude of prediction relative to the average of all predictions. The absolute magnitude indicates the strength of the feature for a particular individual prediction
- The average of absolute magnitudes of SHAP values per feature indicates the global importance of the feature
- In some way, SHAP feature importance can be alternative to permutation feature importance. In contrast to SHAP, permutation feature importance is based on an overall decrease in model performance.

---

The biggest challenge in switching to more complex models in MMM was the lack of tools to explain the influence of individual media channels. While the machine learning community is extensively using approaches for model explainability like SHAP, which is suggested by hundreds of papers and conference talks, it is still very difficult to find examples of SHAP usage in the MMM context. This [great article](https://towardsdatascience.com/explainable-ai-application-of-shapely-values-in-marketing-analytics-57b716fc9d1f) connects MMM with SHAP and explains how we may interpret the results of the marketing mix. Motivated by this article, I wrote an almost generic solution to model a marketing mix, by combining ideas of Robyn’s methodology for trend and seasonality decomposition, using a Random Forest estimator (which can be easily changed to other algorithms), and optimizing adstock and model-specific parameters using [Optuna](https://optuna.org/) (hyperparameter optimization framework). The solution allows switching between single objective optimization as is usually done in MMM and multiple objective optimization as is done by Robyn.

## Data

I continue using the dataset made available by [Robyn](https://github.com/facebookexperimental/Robyn) under MIT Licence as in my [first article](https://towardsdatascience.com/modeling-marketing-mix-using-pymc3-ba18dd9e6e68) for consistency and benchmarking, and follow the same data preparation steps by applying Prophet to decompose trends, seasonality, and holidays.

The dataset consists of 208 weeks of revenue (from 2015–11–23 to 2019–11–11) having:

- 5 media spend channels: tv\_S, ooh\_S, print\_S, facebook\_S, search\_S
- 2 media channels that have also the exposure information (Impression, Clicks): facebook\_I, search\_clicks\_P (not used in this article)
- Organic media without spend: newsletter
- Control variables: events, holidays, competitor sales (competitor\_sales\_B**)**

The analysis window is 92 weeks from 2016–11–21 to 2018–08–20.

## Adstock / Carryover Effects

Irrespective of a modeling algorithm, the advertising adstock plays an important role in MMM. Therefore, we have to decide what kind of adstock we are going to experiment with and what are the minimum and maximum values it may potentially have for each media channel (please refer to my [previous article](https://towardsdatascience.com/modeling-marketing-mix-using-pymc3-ba18dd9e6e68) for an overview of various adstock functions). The optimization algorithm will try each adstock value from the range of defined values to find the best one which minimizes the optimization criteria.

I am using the geometric adstock function implemented in scikit-learn as follows:

```
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils import check_array
from sklearn.utils.validation import check_is_fitted
```
```
class AdstockGeometric(BaseEstimator, TransformerMixin):
    def __init__(self, alpha=0.5):
        self.alpha = alpha

    def fit(self, X, y=None):
        X = check_array(X)
        self._check_n_features(X, reset=True)
        return self

    def transform(self, X: np.ndarray):
        check_is_fitted(self)
        X = check_array(X)
        self._check_n_features(X, reset=False)
        x_decayed = np.zeros_like(X)
        x_decayed[0] = X[0]

        for xi in range(1, len(x_decayed)):
            x_decayed[xi] = X[xi] + self.alpha* x_decayed[xi - 1]
        return x_decayed
```

## Diminishing Returns / Saturation Effect

I already mentioned that linear models are not able to capture the non-linear relationships between different levels of advertisement spending and the outcome. Therefore, various non-linear transformations such as [Power, Negative Exponential](https://analyticsartist.wordpress.com/2015/03/08/advertising-diminishing-returns-saturation/), and [Hill](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/46001.pdf) were applied to media channels prior to modeling.

Tree-based algorithms are able to capture non-linearities. Therefore, I don’t apply any non-linear transformation explicitly and let the model learn non-linearities on its own.

## Modeling

Modeling consists of several steps:

**Adstock parameters**

How long the ad may have an effect depends on the media channel. Since we are searching for an optimal adstock decay rate, we have to be realistic about the possible ranges of the parameter. For example, it is known that a TV advertisement may have a long-lasting effect while Print has a shorter effect. So we have to have the flexibility of defining realistic hyperparameters for each media channel. In this example, I am using the exact ranges proposed by Robyn in their demo file.

```
adstock_features_params = {}
adstock_features_params["tv_S_adstock"] = (0.3, 0.8)
adstock_features_params["ooh_S_adstock"] = (0.1, 0.4)
adstock_features_params["print_S_adstock"] = (0.1, 0.4)
adstock_features_params["facebook_S_adstock"] = (0.0, 0.4)
adstock_features_params["search_S_adstock"] = (0.0, 0.3)
adstock_features_params["newsletter_adstock"] = (0.1, 0.4)
```

**Time Series Cross-Validation**

We want to find parameters that generalize well to unseen data. We have to split our data into a training and test set. Since our data represents spending and revenues occurring along the timeline we have to apply a time series cross-validation such that the training set consists only of events that occurred prior to events in the test set.

Machine learning algorithms work best when they are trained on big amounts of data. The Random Forest algorithm is not an exception and in order to capture non-linearities and interactions between variables, it should be trained on a lot of data. As I mentioned earlier, we have only 208 data points in total and 92 data points in the analysis window. We need some trade-off between generalizability and the capability of a model to learn.

After some experiments, I decided to use 3 cv-splits by allocating 20 weeks of data (about 10%) as a test set.

```
from sklearn.model_selection import TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=3, test_size = 20)
```

Each successive training set split is larger than the previous one.

```
tscv = TimeSeriesSplit(n_splits=3, test_size = 20)
for train_index, test_index in tscv.split(data):
    print(f"train size: {len(train_index)}, test size: {len(test_index)}")
```
```
#train size: 148, test size: 20
#train size: 168, test size: 20
#train size: 188, test size: 20
```

**Hyperparameter optimization using Optuna**

Hyperparameter optimization consists of a number of experiments or trials. Each trial can be roughly divided into three steps.

- Apply adstock transformation on media channels using a set of adstock parameters
```
for feature in adstock_features:
  adstock_param = f"{feature}_adstock"
  min_, max_ = adstock_features_params[adstock_param]
  adstock_alpha = trial.suggest_uniform(f"adstock_alpha_{feature}", min_, max_)
  adstock_alphas[feature] = adstock_alpha

  #adstock transformation
  x_feature = data[feature].values.reshape(-1, 1)
  temp_adstock = AdstockGeometric(alpha = adstock_alpha).fit_transform(x_feature)
  data_temp[feature] = temp_adstock
```
- Define a set of modeling parameters for **[Random Forest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html)**.
```
#Random Forest parameters
n_estimators = trial.suggest_int("n_estimators", 5, 100)
min_samples_leaf = trial.suggest_int('min_samples_leaf', 1, 20)
min_samples_split = trial.suggest_int('min_samples_split', 2, 20)
max_depth = trial.suggest_int("max_depth", 4,7)
ccp_alpha = trial.suggest_uniform("ccp_alpha", 0, 0.3)
bootstrap = trial.suggest_categorical("bootstrap", [False, True])
criterion = trial.suggest_categorical("criterion",["squared_error"])
```
- Cross-validate and measure the average error across all test sets
```
for train_index, test_index in tscv.split(data_temp):
 x_train = data_temp.iloc[train_index][features]
 y_train =  data_temp[target].values[train_index]

 x_test = data_temp.iloc[test_index][features]
 y_test = data_temp[target].values[test_index]

 #apply Random Forest
 params = {"n_estimators": n_estimators, 
           "min_samples_leaf":min_samples_leaf, 
           "min_samples_split" : min_samples_split,
           "max_depth" : max_depth, 
           "ccp_alpha" : ccp_alpha, 
           "bootstrap" : bootstrap, 
           "criterion" : criterion
           }

 #train a model      
 rf = RandomForestRegressor(random_state=0, **params)
 rf.fit(x_train, y_train)

 #predict test set
 prediction = rf.predict(x_test)

 #RMSE error metric       
 rmse = mean_squared_error(y_true = y_test, y_pred = prediction, squared = False)

 #collect errors for each fold
 scores.append(rmse)
```
```
#finally return the average of the cv error
return np.mean(scores)
```

Each trial returns the adstock, model parameters, and error metrics as a user attribute. This allows easy retrieval of the parameters in the best trial.

```
trial.set_user_attr("scores", scores)
trial.set_user_attr("params", params)
trial.set_user_attr("adstock_alphas", adstock_alphas)
```

The main function to start the optimization is \_optuna *optimize.* It returns the Optuna [Study](https://optuna.readthedocs.io/en/stable/reference/generated/optuna.study.Study.html) object with all trials including the best trial (having a minimal average RMSE error)

```
tscv = TimeSeriesSplit(n_splits=3, test_size = 20)
```
```
adstock_features_params = {}
adstock_features_params["tv_S_adstock"] = (0.3, 0.8)
adstock_features_params["ooh_S_adstock"] = (0.1, 0.4)
adstock_features_params["print_S_adstock"] = (0.1, 0.4)
adstock_features_params["facebook_S_adstock"] = (0.0, 0.4)
adstock_features_params["search_S_adstock"] = (0.0, 0.3)
adstock_features_params["newsletter_adstock"] = (0.1, 0.4)
```
```
OPTUNA_TRIALS = 2000
```
```
#experiment is an optuna study object
experiment = optuna_optimize(trials = OPTUNA_TRIALS, 
                             data = data, 
                             target = target, 
                             features = features, 
                             adstock_features = media_channels + organic_channels, 
                             adstock_features_params = adstock_features_params, 
                             media_features=media_channels, 
                             tscv = tscv, 
                             is_multiobjective=False)
```

RMSE score for each fold of the best trial:

```
experiment.best_trial.user_attrs["scores"]
```
```
#[162390.01010327024, 114089.35799374945, 79415.8649240292]
```

Adstock parameters corresponding to the best trial:

```
experiment.best_trial.user_attrs["adstock_alphas"]
```
```
#{'tv_S': 0.5343389820427953,
# 'ooh_S': 0.21179063584028718,
# 'print_S': 0.27877433150946473,
# 'facebook_S': 0.3447366707231967,
# 'search_S': 0.11609804659096469,
# 'newsletter': 0.2559060243894163}
```

Model parameters corresponding to the best trial:

```
experiment.best_trial.user_attrs["params"]
```
```
#{'n_estimators': 17,
# 'min_samples_leaf': 2,
# 'min_samples_split': 4,
# 'max_depth': 7,
# 'ccp_alpha': 0.19951653203058856,
# 'bootstrap': True,
# 'criterion': 'squared_error'}
```

**Final Model**

I build the final model using the optimized parameters by providing the start and end periods for analysis. The model is first built on all the data up to the end of the analysis period. The predictions and SHAP values are retrieved for the analysis period only.

```
best_params = experiment.best_trial.user_attrs["params"]
adstock_params = experiment.best_trial.user_attrs["adstock_alphas"]
result = model_refit(data = data, 
                     target = target,
                     features = features, 
                     media_channels = media_channels, 
                     organic_channels = organic_channels, 
                     model_params = best_params, 
                     adstock_params = adstock_params, 
                     start_index = START_ANALYSIS_INDEX, 
                     end_index = END_ANALYSIS_INDEX)
```

## Results

The first plot to check is how well the model fits the data for the analysis period of 92 weeks:

![Image by the author](https://towardsdatascience.com/wp-content/uploads/2022/06/1mj-rm_hDIsHujk5M8muHw.png)

Image by the author

MAPE improved by 40% and NRMSE by 17% compared to the [Bayesian approach](https://towardsdatascience.com/modeling-marketing-mix-using-pymc3-ba18dd9e6e68).

Next, let’s plot the share of spend vs. share of effect:

![Image by the author](https://towardsdatascience.com/wp-content/uploads/2022/06/1JS29PafhVEauZkzPAKjjuw.png)

Image by the author

The share of effect is calculated using the absolute sum of SHAP values for each media channel within the analysis interval and normalized by the total sum of SHAP values of all media channels.

The share of effect is almost consistent with the share of effect of the [previous article](https://towardsdatascience.com/modeling-marketing-mix-using-pymc3-ba18dd9e6e68). I observe only one inconsistency between the share of effect of the *search* channel.

**Diminishing return / Saturation effect**

I didn’t apply any non-linear transformations to explicitly model the diminishing returns. So let’s check if Random Forest could capture any non-linearities.

This is achieved by the scatter plot that shows the effect a single media channel has on the predictions made by the model where the x-axis is the media spend, the y-axis is the SHAP value for that media channel, which represents how much knowing a particular spend changes the output of the model for that particular prediction. The horizontal line corresponds to the SHAP value of 0. The vertical line corresponds to the average spend in the channel. The green line is a LOWESS smoothing curve.

![](https://towardsdatascience.com/wp-content/uploads/2022/06/17s0d4Huso_M_xPUr3ujIMw.png)

![](https://towardsdatascience.com/wp-content/uploads/2022/06/1Y7uBvAsBI6f_Skn3IUmYjQ.png)

![](https://towardsdatascience.com/wp-content/uploads/2022/06/1_CmjV3_cPdGcJ1QnP1DUlg.png)

![](https://towardsdatascience.com/wp-content/uploads/2022/06/1kq9ye-dFMPcHOSWze7TukQ.png)

![](https://towardsdatascience.com/wp-content/uploads/2022/06/1mxxKfkBFrO2Ytb4RFEMfEw.png)

Looking at all media channels, we can see that higher spend is associated with an increase in revenue. But the relations are not always linear.

Taking \_print *S* we can observe a slight decrease in revenue for spend up to 25K. Then it begins to increase up to about 90K where the increase in revenue is slowed down.

Taking \_facebook *S* we can observe almost no change in revenue for spend up to 90K and after 250K. Spends between 90K and 250K are probably the most optimal spending.

Some media channels like \_facebook\_S, print\_S, and search *S* have a high variance between SHAP values for the same spend. This can be explained by interaction with other media channels and should be further investigated.

## Multiobjective optimization

This solution can manage multiobjective optimization. The idea comes from Robyn by introducing a second optimization metric RSSD (decomposition root-sum-square distance)

> *The distance accounts for a relationship between spend share and a channel’s coefficient decomposition share. If the distance is too far, its result can be too unrealistic – e.g. media activity with the smallest spending gets the largest effect*

In the case of multiobjective optimization, the so-called Pareto Front, the set of all optimal solutions, will be determined by Optuna. The procedure will be the same as for a single optimization case: for each model belonging to the Pareto Front, we retrieve its parameters, build a final model and visualize the results. In the graph below all points with the reddish color belong to the optimal set.

![Image by the author](https://towardsdatascience.com/wp-content/uploads/2022/06/1DBKA1IvZPQcl1ISBcFkoKg.png)

Image by the author

## Conclusion

In this article, I continued exploring ways to improve models for Marketing Mix by using more complex algorithms that are able to capture non-linearities and variable interactions. As a result, the whole pipeline is simplified by omitting the non-linear transformation step, which is always applied when using linear regression. Usage of SHAP values allowed further analysis of effect share and response curves. My second goal was to reach consistent results between different approaches. The comparison between the results of the [previous article](https://towardsdatascience.com/modeling-marketing-mix-using-pymc3-ba18dd9e6e68) in which I used Bayesian modeling and the results of this article showed a high degree of consistency in the decomposed effects per media channel.

The complete code can be downloaded from my [Github repo](https://github.com/slavakx/medium_posts)

Thanks for reading!