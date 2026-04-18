---
title: "Marketing Measurement series: Marketing Mix Modeling at Qonto"
source: "https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-f214ba550968"
author:
  - "[[Ruari Walker]]"
published: 2024-06-05
created: 2026-04-17
description: "Marketing Measurement series: Marketing Mix Modeling at Qonto | Part V Specifying a Bayesian Model with PyMC Welcome to article five in our MMM series. In this article, we’ll detail how we …"
tags:
  - "clippings"
---
## [The Qonto Way](https://medium.com/qonto-way?source=post_page---publication_nav-a9390fa3f292-f214ba550968---------------------------------------)

[![The Qonto Way](https://miro.medium.com/v2/resize:fill:76:76/1*62qiMixIqD-UODkXVUxPOA.png)](https://medium.com/qonto-way?source=post_page---post_publication_sidebar-a9390fa3f292-f214ba550968---------------------------------------)

Stories and learnings from the team behind Qonto

## Specifying a Bayesian Model with PyMC

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*leYQKIRhRemJtNvj0wcUlA.png)

*Welcome to article five in our MMM series. In this article, we’ll detail how we specified a Bayesian MMM using PyMC. We’ll do so by going through a skeletal notebook, accessible* [*here*](https://github.com/iraur/MMM_PyMC_demo/blob/main/demo.ipynb)*, which builds an MMM using a fictitious dataset. We invite the reader to clone the repository and use the notebook in parallel with this article.*

**The structure of this article is as follows:**

- Data preparation
- Model specification overview
- Learning step
- Test set
- Words of warning

## Data preparation

In the notebook associated with this article, we use [the fictitious dataset](https://github.com/facebookexperimental/Robyn/tree/main/R/data) provided by Project Robyn. The target is revenue and there are 9 channels which we take as input variables.

**Categorize your input data**. After importing the required libraries and reading in the dataset, we first organize the columns into groups of features; paid, organic, competitor, and control. This keeps our code clean and allows us to easily log variables in MLflow as we’ll see in our next article in this series on MLOps.

**Scaling**. We then scale both the exogenous (input) and endogenous (output) variables. The `MinMaxScaler()` is used for the exogenous features and the `MaxAbsScaler()` is used for the endogenous variable.

Note that we want to avoid using `MinMaxScaler()` for the endogenous variable since we’ll eventually need to reverse the scaling process to interpret individual channel contributions in terms of original revenue values. As explained in [this article](https://juanitorduz.github.io/pymc_mmm/), employing `MinMaxScaler()` for the endogenous variable would lead to improper rescaling of individual channels, causing their values to be inflated relative to overall revenue scales. For example, if €13,000 represents the lowest total revenue value, weeks with zero investment in an individual channel would be mistakenly rescaled to €13,000.

Competitor data is non-negative after scaling. Multiplying by -1 and selecting an appropriate prior distribution such as the Half Normal ensures that this input has a negative effect on your target, as expected.

**Trend & seasonality**. For trend and seasonality components, we used a linear feature and Fourier modes, respectively, as Juan Orduz does in [this](https://juanitorduz.github.io/pymc_mmm/) highly instructive article.

## Model specification overview

Before diving into the details, let’s first take a bird’s-eye view of the main cell in this notebook in which we design the model. The following diagram gives an overview of our model specification. You can think of it as split into blocks which we describe below:

![Simplified overview of the model specification](https://miro.medium.com/v2/resize:fit:2000/format:webp/1*Sl4Mi39cYlcn8K_J0-ZUnw.png)

Simplified overview of the model specification

### Block #1 — create data containers for each group

All variables are defined and used within the `pm.Model()` object and are assigned to that model. Each variable is given a name which is specified in the first argument. It’s important to choose clear descriptive naming as we’ll need these when analyzing the model output. See our [previous article](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-69bc3101d06d) in which we introduced data containers.

Note that `date` is added as a mutable coordinate in order to have an out-of-sample test set. Similarly we create a container `y_obs_data`, via `pm.MutableData`, for our target variable since we’ll want use test data later.

### Block #2 — specify your prior distributions

Next, prior distribution families and parameters are defined for each unknown parameter in our model. This includes, the intercept, channel coefficients, as well as adstock and saturation parameters. See our [previous article](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-69bc3101d06d) on defining priors for a Bayesian model. Note that in the accompanying notebook the defining parameters for each prior distribution have been specified as the same values for respective input groups, e.g. for the `features_paid` group. But one may specify priors for each individual channel by passing a dictionary in place of a single value.

### Block #3 — transform variables

Adstock and saturation variable transformations are done in this block. Note that they are deterministic variables and so depend on parameters defined in the code block above. This is why we define them via `pm.Deterministic`. See our [previous article](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-69bc3101d06d) on deterministic and stochastic variables. In the notebook, geometric adstock and logistic saturation have been used, but one can use other functions already built in pymc-marketing ([here](https://github.com/pymc-labs/pymc-marketing/blob/main/pymc_marketing/mmm/transformers.py)), or you can custom build your own functions.

### Block #4 — introduce observed data

Here, the bridge is made between modeled data and true data via the likelihood. For each week of data there is a normal distribution with mean being the predicted target metric and standard deviation `sigma` coming from a previously defined prior.

## Learning step

Next, we come to what can be considered the learning step. This is where the power of PyMC comes into play, using Markov Chain Monte Carlo (MCMC) methods to sample from the posterior distribution. The `trace` variable below represents the collection of samples obtained for each parameter in your model.

Let’s explain the terms in the block above:

- **Draws**. Specifies the number of samples to draw from the posterior distribution. Each sample represents a set of parameter values for the model.
- **Tune**. Determines the number of samples to discard as tuning samples in as part of a “burn-in” or “warm-up” period. The samples collected during the tuning phase are not used for inference as they’re considered not to result in areas of high posterior probability.
- **Chains**. Specifies the number of independent Markov chains to run. Running multiple chains helps to diagnose convergence issues and ensures that the sampler explores the posterior distribution thoroughly.
- **Cores**. This parameter specifies the number of CPU cores to use for sampling. PyMC can parallelize sampling across multiple CPU cores to speed up the process.

## Test set

In the development of MMMs, it is advised to include out-of-sample predictions on which to evaluate the validity, accuracy, and generalizability of your models. Although metrics on the test data likely won’t be the primary way in which you’ll choose your final model, they can act as filters to remove unreliable models.

However, we have found that the concept of train and test datasets does not follow the usual conventions and remains a somewhat unsolved problem due to the effect of adstocking:

- Let’s suppose we have 3 years of data and we hold back the final 30 weeks as a test set.
- If we are adstocking our investment then the predicted target metric for any given week depends on the investment that week but also in previous weeks.
- But evaluating on our test set means we have a break in the adstock and the adstocked investment from previous weeks is not carried over. We essentially have to start adstocking from scratch which will likely result in poorer performance.

One solution to this issue was to first create the model and define the trace on the training set. Next, use this trace with the full dataset (train and test set together) and sample from the posterior. Although this creates weekly predictions for the entire dataset, we then evaluate only the test set, i.e. the final 30 weeks in the example give above.

We can use different datasets within the same model context using `pm.set_data`. Here, the `trace` was created with the train data but we now sample from the posterior using a different dataset:

## Words of warning

**Setting seeds**. Setting one seed at the top of your notebook and then re-running cells out of order as you use it will yield results that are not consistent. Be sure to set seeds in each cell in which sampling occurs in order to get reproducible results. Note that you’ll need to set a (different) seed per chain. Using `np.random.default_rng` instead of a regular seed allows you to do this. This is crucial given the sampling processes involved.

**Causal DAG issues**. Ensure that the input data used has a causal relationship with the target variable. For example, suppose your target variable is customer sign-ups and consider your referral program in which rewards are paid for referring a friend. Since the payout happens after the sign-up, we can’t use the spend on this channel to model sign-ups. A more appropriate option would be something like referral page views.

You should also be aware of your data generation process and the causal graph for your marketing mix — see [here](https://developers.google.com/meridian/docs/basics/causal-graph) for greater discussion.

**Overfitting**. Overfitting can be a risk particularly when you using too many input variables relative to the amount of historical data. Having a test set can help offset overfitting.

A simple demonstration of how a test set can filter out unwanted models is to build a simple linear regression model with your data. On training data you will likely have a very accurate model fit if you have a high number of regressors but a poor fit on test data.

There are more advanced techniques to prevent overfitting when using several inputs such as the RD-D2 shrinkage prior ([ref](https://arxiv.org/pdf/1609.00046.pdf)), which puts a prior on the coefficient of determination.

*Want to read more? Here’s the full Marketing Measurement series:*

**Marketing Mix Modeling:**

- [Part I: Getting started](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-337b8af11471) *(first released 21 May 2024)*
- [Part II: Adstock and saturation](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-82e82c995b39) *(first released 22 May 2024)*
- [Part III: Bayes’ Theorem & priors](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-05d28a2cfa18) (*first released 23 May 2024*)
- [Part IV: Inputs for a Bayesian model](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-69bc3101d06d) (*first released 27 May 2024*)
- Part V: Specifying a Bayesian model with PyMC
- [Part VI: MLOps](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-part-vi-7bb9805076ba) (*first released 14 June 2024*)

**Incrementality testing:**

- [How to invest better in acquisition channels? A $1 million question for Data Science](https://medium.com/qonto-way/how-to-invest-better-in-acquisition-channels-a-1-million-question-for-data-science-591c82b3e0e4) *(first released 4 January 2023)*
- [Incrementality test scheduling: velocity vs. validity](https://medium.com/qonto-way/marketing-measurement-series-incrementality-test-scheduling-f7525b713b4a) (*first released 19 June 2024)*
- [*Getting the best of both worlds in marketing incrementality tests: rapid testing and trusted results*](https://medium.com/qonto-way/getting-the-best-of-both-worlds-in-marketing-incrementality-tests-rapid-testing-and-trusted-58243204fc80) *(first released 13 November 2024)*

**About Qonto**

Qonto makes it easy for SMEs and freelancers to manage day-to-day banking, thanks to an online business account that’s stacked with invoicing, bookkeeping and spend management tools.

Created in 2016 by Alexandre Prot and Steve Anavi, Qonto now operates in 4 European markets (France, Germany, Italy, and Spain) serving 500,000 customers, and employs more than 1,600 people.

Since its creation, Qonto has raised €622 million from well-established investors. Qonto is one of France’s most highly valued scale-ups and has been listed in the Next40 index, bringing together future global tech leaders, since 2021.

Interested in joining a challenging and game-changing company? Take a look at our [open positions](https://qonto.com/en/careers).

Illustrations by [Pierre-Alain Dubois](https://www.linkedin.com/in/pierrealaindubois/)