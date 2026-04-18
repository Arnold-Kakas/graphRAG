---
title: "Marketing Measurement series: Marketing Mix Modeling at Qonto"
source: "https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-69bc3101d06d"
author:
  - "[[Ruari Walker]]"
published: 2024-05-27
created: 2026-04-17
description: "Marketing Measurement series: Marketing Mix Modeling at Qonto | Part IV Inputs for a Bayesian model Welcome to article four in our MMM series. Before diving into this one, we advise you to first …"
tags:
  - "clippings"
---
## [The Qonto Way](https://medium.com/qonto-way?source=post_page---publication_nav-a9390fa3f292-69bc3101d06d---------------------------------------)

[![The Qonto Way](https://miro.medium.com/v2/resize:fill:76:76/1*62qiMixIqD-UODkXVUxPOA.png)](https://medium.com/qonto-way?source=post_page---post_publication_sidebar-a9390fa3f292-69bc3101d06d---------------------------------------)

Stories and learnings from the team behind Qonto

## Inputs for a Bayesian model

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*lMexgq-gxTvCpFU6D0dgTw.png)

*Welcome to article four in our MMM series. Before diving into this one, we advise you to first familiarize yourself with articles I-III. Links to each article in the series can be found at the end of this page.*

At Qonto we decided to build our MMM using [PyMC](https://www.pymc.io/welcome.html), a probabilistic programming language (PPL) for Python, designed to build and test Bayesian models. This article and the one after it will focus on specifying a model through the lens of PyMC. Here, we will focus on the inputs required to build a Bayesian MMM.

**The outline for this article is as follows:**

- Defining the required data
- Overview of PyMC  
	— Key PyMC concepts: models, data containers, and MCMC
- Specifying priors
- Defining the likelihood

## Defining the required data

One of the first concrete tasks when building an MMM is to define and gather the required data. There are several things to consider at this stage:

**Determine the dependent variable**. This is your target metric that will be modeled. Typically this will be something like Sales, Customer Sign-Ups, or Revenue, depending on your business and your objectives.

**Determine the independent variables**. Next, you need to determine the independent variables. Generally, they can be grouped into the following categories:

- **Paid media variables**. Any media variables with a clear marketing spend falls into this category. Examples include, LinkedIn, Branded Search, TV, and Print.
- **Organic**. Any marketing activities without a clear marketing spend fall into this category. Typically this may include newsletters, push notifications, and social media posts.
- **Control**. These include other variables that are not paid or organic media but that can help explain the dependent variable. The most common examples of control variables include competitor activity, price & promotional activity, macroeconomic factors like unemployment rate, etc. They can also include Google Trends data, and public and school holidays.

**Investment vs. exposure**. The metrics you use for the independent variables will depend on the media activity and will fall into the category of either exposure metrics (such as clicks, impressions, Gross Rating Points, etc) or investments. For organic channels there is no option but to use exposure metrics. More generally, this is a divided topic; using investments gives a direct cost-response relationship via the response curve, whereas using exposure metrics requires a translation to investment which introduces uncertainty (see the comment which Gufeng Zhou, the creator of Robyn, made [here](https://www.alpha.facebook.com/groups/robynmmm/posts/1234713643963433/?comment_id=1245438872890910&reply_comment_id=1245648736203257)). On the other hand, the [Robyn documentation](https://facebookexperimental.github.io/Robyn/docs/analysts-guide-to-MMM) states, “ *it is recommended to use media exposure metrics like impressions or GRPs for modeling* ”.

**Level of granularity**. You will need to decide how granular your input variables will be. For example, you may wish to consider Facebook, LinkedIn and Snapchat as individual channels, or you may want to group them together as a variable called Social.

We advise to first define a set of levels of channels, in collaboration with your stakeholders, in order to have an overview of the hierarchy of channels and how they could be aggregated in ways that are meaningful for your business:

![Table showing ways in which acquisition channels can be aggregated](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*66k9K7wrdzNcT6Jgyf3ZCA.png)

Table showing ways in which acquisition channels can be aggregated

Using a highly granular approach will likely result in having a large number of input variables and, depending on your business, may also lead to several channels being highly sparse — i.e. populated primarily with 0, reflecting the fact that channels are not always turned on. It may also lead to multicollinearity and so an unreliable model.

As a result, unless you are:

- a confident MMM practitioner,
- have a good amount of incrementality experiment results to calibrate your models,
- comfortable informing your priors,
- confident that the knowledge you are using to inform your priors is high quality and unbiased,

we advise erring on the side of ***less granularity***. In other words, aggregate your channels as much as you can — while still retaining insights and output that are actionable for your stakeholders and business.

![Visual representation of the balance between channel granularity and model stability](https://miro.medium.com/v2/resize:fit:2000/format:webp/1*KCLvFRl4HIJoK1Ru4falhg.png)

Visual representation of the balance between channel granularity and model stability

**Exploratory data analysis**. As in any data project, we advise exploratory data analysis once your input data has been collected.

Visualize your data — try to spot any outlying values or unusual periods in your dependent variable. Ask yourself if there is something which would explain them. It may be a good idea to ensure they’re included in the model. Similarly, check your independent variables are populated as expected and ask stakeholders to validate this input data. Data quality is key in MMM and the “ *garbage in, garbage out* ” principle holds especially true.

**Historical data**. It is generally recommended to use a minimum of 2–3 years of data, at a weekly level, with a column to row ratio of at most 1:10 (see [Robyn’s guide](https://facebookexperimental.github.io/Robyn/docs/analysts-guide-to-MMM) where this recommendation comes from and where they discuss the pros and cons of using weekly data) although Bayesian models can rely on less data when paired with informed priors (see the regularizing effect of priors in [Chapter 6](https://nbviewer.org/github/CamDavidsonPilon/Probabilistic-Programming-and-Bayesian-Methods-for-Hackers/blob/master/Chapter6_Priorities/Ch6_Priors_PyMC3.ipynb) of Bayesian Methods for Hackers).

## Overview of PyMC

PyMC is a probabilistic programming language (PPL) written in Python, designed to build and test Bayesian models. It is flexible and efficient in model construction and inference, making it ideal for MMM. It has a well-maintained library with an active community online. PyMC also provides comprehensive diagnostic tools to assess model convergence and performance. Additionally, its integration with [ArviZ](https://python.arviz.org/en/stable/), a library for exploratory analysis of Bayesian models, allows for in-depth visualization and analysis of model outputs. The code is fairly straightforward to read and the syntax is inline with NumPy.

In the context of marketing analytics, there is an excellent open-source package called [PyMC-Marketing](https://www.pymc-marketing.io/en/stable/), built on top of PyMC, allowing one to build Customer Lifetime Value (CLV) models and Marketing Mix Models. As outlined in [Marketing Mix Modeling at Qonto Part I: Getting Started](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-337b8af11471), PyMC-Marketing is very straightforward to use and has a growing set of relevant features — its popularity in the open-source community is rapidly increasing. We highly encourage you to take a look for yourself when working in this area.

All this is balanced by the fact that there is an active and responsive PyMC-based community who are very open and willing to discuss issues and questions when they arise. We highly recommend getting involved with and contributing to this community. Besides that, we also recommend reading [Bayesian Methods for Hackers](https://github.com/CamDavidsonPilon/Probabilistic-Programming-and-Bayesian-Methods-for-Hackers) which offers a great introduction to PyMC for beginners.

At Qonto, we decided to work directly in PyMC rather than PyMC-Marketing in order to build a better understanding of the machinery and more easily have the ability to build custom features when needed.

### Key PyMC Concepts: models, data containers and MCMC

Once PyMC has been successfully installed following the installation guide [here](https://www.pymc.io/projects/docs/en/stable/installation.html), you can open a notebook and import it:

```c
import pymc as pm
```

To create a model one creates a model object, within which all variables associated to that model are defined. Any changes or updates to the model must be defined within this context manager, either right after initialising the model or later on with a separate `with` statement.

```c
with pm.Model() as my_model:
  # define variables here
```

**Deterministic and stochastic variables**. The components of your model will be expressed as variables of which PyMC has two types — *deterministic* and *stochastic*. The first argument in these variables is a name which you assign to it. It’s important to choose clear, descriptive naming as we’ll need these when analyzing the model output. The convention is to give a variable the same name as what you call it in Python (see below).

- **Stochastic variables** can be thought of as random variables, and are typically various types of distributions such as `pm.HalfNormal` or `pm.Normal`. In the context of MMM they will be our prior distributions. For example, the prior for any given online channel coefficient will be represented as a stochastic variable. In the code below we have a stochastic variable `facebook_alpha` (which respects the naming convention) that is represented by a Half Normal distribution with standard deviation `sigma=1.5`
```c
facebook_alpha = pm.HalfNormal(name="facebook_alpha", sigma=1.5)
```
- **Deterministic variables** are dependent on other objects and can be defined using `pm.Deterministic`. Once the values from the dependent objects are known and fixed, the deterministic variable is fixed. In the code below, the variable `facebook_adstock` is fixed for a given value of `facebook_alpha`
```c
facebook_adstock = pm.Deterministic(name="facebook_adstock", var=geometric_adstock(x=your_data, alpha=facebook_alpha), dims=("date"))
```

**Data containers**. PyMC allows us to group and organize our input data into dimensions (groups of input columns) and coordinates (the unique values these dimensions can take, such as Snapchat), which allow us to create data containers. Data containers come with a range of benefits, including simplifying working with large datasets ([see here](https://www.pymc.io/projects/examples/en/latest/fundamentals/data_container.html) for more details). First, define your coordinates:

Next, create a model context within which you can define the data containers. Here, `FEATURES` is a dictionary of model inputs which makes accessing your co-ordinates easier.

**Markov Chain Monte Carlo (MCMC) sampling**. As already mentioned in [article III](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-05d28a2cfa18), you will need additional machinery to evaluate your posterior distribution. PyMC comes equipped with a variety of Markov Chain Monte Carlo (MCMC) sampling algorithms including the [No-U-Turn Sampler](https://jmlr.org/papers/volume15/hoffman14a/hoffman14a.pdf) (NUTS) and Metropolis sampling which explore the parameter space in an efficient way and focus on regions which return posterior samples with high probability. For additional details we recommend [PyMC’s overview](https://www.pymc.io/projects/docs/en/stable/learn/core_notebooks/pymc_overview.html).

## Specifying priors

In Bayesian inference, a prior is a probability distribution that represents our beliefs about a parameter before we have seen any data. Priors are crucial because they influence the posterior distribution — our updated beliefs about the model’s parameters after considering the data. Choosing appropriate priors can significantly affect the results and interpretations derived from a Bayesian analysis. See our previous article, [Marketing Mix Modeling at Qonto Part III: Bayes’ Theorem & priors](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-05d28a2cfa18), for an introduction to priors.

Below is an example of how priors could be specified in a PyMC MMM. Note that we are still within the `pm.Model` context as defined above in previous code snippets:

- **Baseline**. The intercept term represents the volume of our target metric attained without any marketing activity. It should therefore be non-negative. The Half Normal distribution may be an appropriate choice in this case.
- **Paid and organic channel coefficients**. You could begin with the assumption that paid and organic channels have a non-negative effect on the business, i.e. their coefficients are at least 0. Again, the Half Normal may be an appropriate family of distributions for these variables.
- **Competitor activity**. If you are using data relating to competitor activity in your model, you may assume that competitor activity has a negative effect on the target metric. One can ensure this is represented in your model by first scaling the data to the range 0–1, multiplying by -1 and then using a Half Normal distribution for the prior on the this variable’s coefficient.
- **Control variables**. It’s often not clear what direction or magnitude control variables have on the model. In this case one could use Normal distributions centered at 0 as the priors on control variable coefficients.
- **Adstock**. Your adstock parameters will depend upon the choice of adstock function you use (see [Marketing Mix Modeling at Qonto Part II: Adstock and saturation](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-82e82c995b39)). Geometric adstock is defined by a single parameter which should be between 0 and 1 and so the Beta distribution is an obvious choice here.
- **Saturation**. As with adstock, the parameters associated with saturation will depend on the choice of function you choose. Here we used Logistic Saturation which is defined by a single parameter, lambda. We advise using a Gamma distribution for the associated prior since lambda must be greater than 0.
- **Noise**. You can also set a likelihood on one or more of the defining parameters of your likelihood distribution. As you’ll see in the next section, this could be a Normal distribution. In the code above, a prior is defined for the standard deviation. It’s set to be Half Normal since we require it to be non-negative.

## Defining the likelihood

The likelihood represents the probability of the observed data given a set of parameters. It can be described as the bridge between theoretical models and reality, as described in [this article](https://medium.com/@nialloulton/choosing-the-likelihood-functions-in-bayesian-marketing-mix-modeling-18a1b18b7179). The likelihood function answers the question, “ *If the model parameters assumed a certain set of values, how probable would it be that I would have my actually observed data in front of me?*”

You may want to define the likelihood to be a Normal distribution with the mean being the predicted target given the aforementioned set of parameters. You can put a prior on the standard deviation of the likelihood, as defined in the section above. Normal distributions are chosen when the residuals are assumed to be evenly distributed about the mean. But they are not the only choice. As explained in [this article](https://medium.com/@nialloulton/choosing-the-likelihood-functions-in-bayesian-marketing-mix-modeling-18a1b18b7179), Student-T distribution may also be an appropriate choice.

For brevity, we omitted details on how trend and seasonality are defined. We followed Juan Orduz’s approach, detailed in his wonderful [article](https://juanitorduz.github.io/pymc_mmm/) which we recommend reading.

If you watched the learning phase in slow motion, to understand how the prior and the likelihood interact, it would look something like this:

1. **Sample from the joint prior**. Select a set of model parameters by sampling from the prior distributions.
2. **Build a model**. Insert the sampled parameters into your model to get a series of weekly predicted target metrics.
3. **Create likelihood distributions**. In our case, for each week of data we used a normal distribution with mean being the predicted target metric, and standard deviation coming from the sampling in (1).
4. **Compute the likelihood**. Calculate the probability of having our observed data given the parameters sampled from (1) by checking where the predicted data points lie on the respective normal distributions.
5. This process is repeated in the chosen MCMC algorithm (NUTS, Metropolis, etc).

It’s now clear that the likelihood and the priors are the protagonists in our model. However, before introducing observed data, we’re able to make a sanity check on our choice of priors. Since we know the structure of our regression equation, we can build models based entirely on our prior distributions via `pm.sample_prior_predictive` which samples parameters from their prior distributions. This is a good sense check to ensure your model is well-specified and that your parameters are somewhat sensible. This is important when you consider that you are likely working with scaled data and it’s therefore easy to define priors incorrectly or inaccurately.

```c
# Sample the prior
mmm_prior_predictive = pm.sample_prior_predictive(samples=1000, random_seed=rng)
```

The following plot shows the results of sampling from the prior. The black line represents the true target variable and is sitting on a prior density plot of the predicted values (darker colors representing a higher volume of samples).

![Plot showing the results of sampling from the prior](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*Ca0zIFrYl1wz4tR3wvBOJw.png)

Plot lifted directly from Juan Orduz’s article in which he also provides the code snippet which produces it

Stay tuned for the next article in the series, where we’ll bring these concepts together in a comprehensive end-to-end example, demonstrating how to build a Bayesian MMM using PyMC.

*Want to read more? Here’s the full Marketing Measurement series:*

**Marketing Mix Modeling:**

- [Part I: Getting started](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-337b8af11471) *(first released 21 May 2024)*
- [Part II: Adstock and saturation](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-82e82c995b39) *(first released 22 May 2024)*
- [Part III: Bayes’ Theorem & priors](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-05d28a2cfa18) (*first released 23 May 2024*)
- Part IV: Inputs for a Bayesian model
- [Part V: Specifying a Bayesian model with PyMC](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-f214ba550968) (*first released 5 June 2024*)
- [Part VI: MLOps](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-part-vi-7bb9805076ba) (*first released 14 June 2024*)

**Incrementality testing:**

- [How to invest better in acquisition channels? A $1 million question for Data Science](https://medium.com/qonto-way/how-to-invest-better-in-acquisition-channels-a-1-million-question-for-data-science-591c82b3e0e4) *(first released 4 January 2023)*
- [Incrementality test scheduling: velocity vs. validity](https://medium.com/qonto-way/marketing-measurement-series-incrementality-test-scheduling-f7525b713b4a) (*first released 19 June 2024)*
- [*Getting the best of both worlds in marketing incrementality tests: rapid testing and trusted results*](https://medium.com/qonto-way/getting-the-best-of-both-worlds-in-marketing-incrementality-tests-rapid-testing-and-trusted-58243204fc80) *(first released 13 November 2024)*

**About Qonto**

Qonto makes it easy for SMEs and freelancers to manage day-to-day banking, thanks to an online business account that’s stacked with invoicing, bookkeeping and spend management tools.

Created in 2016 by Alexandre Prot and Steve Anavi, Qonto now operates in 4 European markets (France, Germany, Italy, and Spain) serving 450,000 customers, and employs more than 1,400 people.

Since its creation, Qonto has raised €622 million from well-established investors. Qonto is one of France’s most highly valued scale-ups and has been listed in the Next40 index, bringing together future global tech leaders, since 2021.

Interested in joining a challenging and game-changing company? Take a look at our [open positions](https://qonto.com/en/careers).

Illustrations by [Eloïse Rulquin](https://www.linkedin.com/in/eloiserulquin/)