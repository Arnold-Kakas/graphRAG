---
title: "Understanding Bayesian Marketing Mix Modeling: A Deep Dive into Prior Specifications"
source: "https://medium.com/data-science/understanding-bayesian-marketing-mix-modeling-a-deep-dive-into-prior-specifications-af400adb836e"
author:
  - "[[Slava Kisilevich]]"
published: 2023-06-24
created: 2026-04-20
description: "Understanding Bayesian Marketing Mix Modeling: A Deep Dive into Prior Specifications Exploring model specification with Google’s LightweightMMM Bayesian marketing mix modeling has been receiving …"
tags:
  - "clippings"
---
## [TDS Archive](https://medium.com/data-science?source=post_page---publication_nav-7f60cf5620c9-af400adb836e---------------------------------------)

[![TDS Archive](https://miro.medium.com/v2/resize:fill:76:76/1*JEuS4KBdakUcjg9sC7Wo4A.png)](https://medium.com/data-science?source=post_page---post_publication_sidebar-7f60cf5620c9-af400adb836e---------------------------------------)

An archive of data science, data analytics, data engineering, machine learning, and artificial intelligence writing from the former Towards Data Science Medium publication.

## Exploring model specification with Google’s LightweightMMM

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/0*3MvDq6OytH5-VZRX)

Photo by Pawel Czerwinski on Unsplash

Bayesian marketing mix modeling has been receiving more and more attention, especially with the recent releases of open source tools like [LightweightMMM](https://lightweight-mmm.readthedocs.io/en/latest/index.html) (Google) or [PyMC Marketing](https://www.pymc-marketing.io/) (PyMC Labs). Although these frameworks simplify the complexities of Bayesian modeling, it is still crucial for the user to have an understanding of fundamental Bayesian concepts and be able to understand the model specification.

In this article, I take Google’s LightweightMMM as a practical example and show the intuition and meaning of the prior specifications of this framework. I demonstrate the simulation of prior samples using Python and the scipy library.

## Data

I use the data made available by [Robyn](https://github.com/facebookexperimental/Robyn) under MIT Licence.

The dataset consists of 208 weeks of revenue (from 2015–11–23 to 2019–11–11) having:

- 5 media spend channels: **tv\_S, ooh\_S, print\_S, facebook\_S, search\_S**
- 2 media channels that have also the exposure information (Impression, Clicks): facebook\_I, search\_clicks\_P
- Organic media without spend: **newsletter**
- Control variables: **events, holidays**, competitor sales (**competitor\_sales\_B)**

## LightweightMMM Model Specification

The specification of the [LightweightMMM model](https://lightweight-mmm.readthedocs.io/en/latest/models.html#) is defined as follows:

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*ZJv9qeZtqTUf_T5YXznMQg.png)

LMMM Model Specification (image by the author)

This specification represents an additive linear regression model that explains the value of a response (target variable) at a specific time point *t.*

Let’s break down each component in the equation:

- **α**: This component represents the intercept or the baseline value of the response. It is the expected value of the response when all other factors are zero.
- ***trend***: This component captures the increasing or decreasing trend of the response over time.
- ***seasonality***: This component represents periodic fluctuations in the response.
- ***media\_channels***: This component accounts for the influence of media channels (tv, radio, online ads) on the response.
- ***other\_factors***: This component encompasses any other variables that have influence on the response such as weather, economic indicators or competitor activities.

Below, I go through each of the components in detail and explain how to interpret the prior specifications. As a reminder, a prior distribution is an assumed distribution of some parameter without any knowledge of the underlying data.

### Intercept

![](https://miro.medium.com/v2/resize:fit:1100/format:webp/1*TPjO8rYg41Z5CL7Z_Y5McQ.png)

Intercept prior specification (image by the author)

The intercept is defined to follow a half-normal distribution with a standard deviation of 2. A half-normal distribution is a continuous probability distribution that resembles a normal distribution but is restricted to positive values only. The distribution is characterized by a single parameter, the standard deviation (scale). Half-normal distribution implies that the intercept can get only positive values.

The following code generates samples from the prior distribution of the intercept and visualizes the probability density function (PDF) for a half-normal distribution with a scale of 2. For visualizations of other components, please refer to the accompanying source code in the [Github repo](https://github.com/slavakx/medium_posts).

```c
from scipy import stats

scale = 2
halfnormal_dist = stats.halfnorm(scale=scale)
samples = halfnormal_dist.rvs(size=1000)

plt.figure(figsize=(20, 6))
sns.histplot(samples, bins=50, kde=False, stat='density', alpha=0.5)
sns.lineplot(x=np.linspace(0, 6, 100), 
      y=halfnormal_dist.pdf(np.linspace(0, 6, 100)), color='r')

plt.title(f"Half-Normal Distribution with scale={scale}")
plt.xlabel('x')
plt.ylabel('P(X=x)')
plt.show()
```
![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*qMUbVf2JWsCynjB_I6zZ1g.png)

Half Normal Distribution (image by the author)

### Trend

![](https://miro.medium.com/v2/resize:fit:1100/format:webp/1*dDI7QisSpWqC6PQx4urvLg.png)

Trend specification (image by the author)

The trend is defined as a power-law relationship between time *t* and the trend value. The parameter *μ* represents the amplitude or magnitude of the trend, while *k* controls the steepness or curvature of the trend.

The parameter *μ* is drawn from a normal distribution with a mean of 0 and a standard deviation of 1. This implies that *μ* follows a standard normal distribution, centered around 0, with standard deviation of 1. The normal distribution allows for positive and negative values of *μ*, representing upward or downward trends, respectively.

The parameter *k* is drawn from a uniform distribution between 0.5 and 1.5. The uniform distribution ensures that *k* takes values that result in a reasonable and meaningful curvature for the trend.

The plot below depicts separate components obtained from the prior distributions: a sample of the intercept and trend, each represented individually.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*X-M1sjoZfeNRVA_2d7AKlQ.png)

Trend and Intercept (image by the author)

### Seasonality

![](https://miro.medium.com/v2/resize:fit:1100/format:webp/1*1uPIr56H9KcwpF8cmZcv_w.png)

Seasonality specification (image by the author)

Each component γ is drawn from a normal distribution with a mean of 0 and a standard deviation of 1.

By combining the cosine and sine functions with different γ, cyclic patterns can modeled to capture the [seasonality](https://en.wikipedia.org/wiki/Seasonality) present in the data. The cosine and sine functions represent the oscillating behavior observed over the period of 52 units (weeks).

The plot below illustrates a sample of the seasonality, intercept and trend obtained from the prior distributions.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*R3Qqr-dYLbbwR7pD5moJbA.png)

Seasonality, Trend and Intercept (image by the author)

### Other factors (control variables)

![](https://miro.medium.com/v2/resize:fit:1100/format:webp/1*nnOYWlRcrQbIPS5wv5ikTg.png)

Other Factors specification (image by the author)

Each factor coefficient *λ* is drawn from a normal distribution with a mean of 0 and a standard deviation of 1, which means that *λ* can take positive or negative values, representing the direction and magnitude of the influence each factor has on the outcome.

The plot below depicts separate components obtained from the prior distributions: a sample of the intercept, trend, seasonality and control variables (*competitor\_sales\_B, newsletter, holidays and events*) each represented individually.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*lyJX95ib9TANrAQ-do6QjQ.png)

Other factors (combined) (image by the author)

### Media Channels

![](https://miro.medium.com/v2/resize:fit:1100/format:webp/1*cTEPLm9Y4rYxZ_6ce_6fiw.png)

Media Channels prior specification (image by the author)

The distribution for *β* coefficient of a media channel *m* is specified as a half-normal distribution, where the standard deviation parameter *v* is determined by the sum of the total cost associated with media channel *m*. The total cost reflects the investment or resources allocated to that particular media channel.

### Media Transformations

![](https://miro.medium.com/v2/resize:fit:1100/format:webp/1*aY8o1cd3ES4VpqUNOUtkCg.png)

Adstock and Hill Saturation Specification (image by the author)

In these equations, we are modeling the media channels’ behavior using a series of transformations, such as adstock and Hill saturation.

## [Modeling Marketing Mix using PyMC3](https://towardsdatascience.com/modeling-marketing-mix-using-pymc3-ba18dd9e6e68?source=post_page-----af400adb836e---------------------------------------)

### Experimenting with priors, data normalization, and comparing Bayesian modeling with Robyn, Facebook’s open-source MMM…

towardsdatascience.com

The variable *media channels* represents the transformed media channels at time point *t*. It is obtained by applying a transformation to the raw media channel value *x*. The Hill transformation is controlled by the parameters *K* a half saturation point (0 < k ≤ 1), and shape *S* controlling the steepness of the curve (s > 0).

The variable *x* ∗ represents the transformed media channels value at time *t* after undergoing the adstock transformation. It is calculated by adding the current raw media channel value to the product of the previous transformed value and the adstock decay parameter *λ*.

Parameters *K* and *S* follow gamma distributions with shape and scale parameters both set to 1, while *λ* follows a beta distribution with shape parameters 2 and 1.

The probability density function of the Hill Saturation parameters *K* and *S* are illustrated in the plot below:

```c
shape = 1
scale = 1

gamma_dist = stats.gamma(a=shape, scale=scale)
samples = gamma_dist.rvs(size=1000)

plt.figure(figsize=(20, 6))
sns.histplot(samples, bins=50, kde=False, stat='density', alpha=0.5)
sns.lineplot(x=np.linspace(0, 6, 100), y=gamma_dist.pdf(np.linspace(0, 6, 100)), color='r')

plt.title(f"Gamma Distribution for $K_m$ and $S_m$ with shape={shape} and scale={scale}")
plt.xlabel('x')
plt.ylabel('P(X=x)')

# Show the plot
plt.show()python
```
![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*ODLin-3hMFJM05rcCmViGg.png)

Gamma distribution (image by the author)

The probability density function of the adstock parameter λ is shown in the plot below:

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*axCGt-ZHl5F6fwlIqcytBQ.png)

Beta distribution (image by the author)

**A Note on the specification of the adstock parameter *λ*:**

The probability density function of the Beta(α = 2, β = 1) distribution exhibits a positive trend, indicating that higher values have a higher probability density. In media analysis, different industries and media activities may demonstrate varying decay rates, with most media channels typically exhibiting small decay rates. For instance, Robyn suggests the following ranges of λ decay for common media channels: TV (0.3–0.8), OOH/Print/Radio (0.1–0.4), and digital (0–0.3).

In the context of the Beta(α = 2, β = 1) distribution, higher probabilities are assigned to λ values closer to 1, while lower probabilities are assigned to values closer to 0. Consequently, outcomes or observations near the upper end of the interval \[0, 1\] are more likely to occur compared to outcomes near the lower end.

Alternatively, in the [Bayesian Methods for Media Mix Modeling with Carryover and Shape Effects](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/46001.pdf), the decay parameter is defined as Beta(α = 3, β = 3), whose probability density function is illustrated below. This distribution is symmetric around 0.5, indicating an equal likelihood of observing outcomes at both extremes and near the center of the interval \[0, 1\].

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*Eez_CcieS9l26rgffPyhCA.png)

Beta(3,3) (image by the author)

The plot below depicts separate components obtained from the prior distributions: a sample of the intercept, trend, seasonality, control variables and media channels, each represented individually.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*z712e_cCHOspIWH46pfh2A.png)

All model components (image by the author)

### Combining all components

As mentioned earlier, LightweightMMM models an additive linear regression by combining various components such as intercept, trend, seasonality, media channels, and other factors sampled from their prior distributions to obtain the predictive response. The plot below visualizes the true response and the expected response sampled from the prior predictive distribution.

Visualizing a single sample against the true response value allows us to observe how the model’s prediction compares to the actual outcome for a specific set of parameter values. It can provide an intuitive understanding of how the model performs in that particular instance.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*B1x1xbNEZ36VqmLnLjjiLw.png)

Revenue: True vs. Prior (image by the author)

### Prior predictive check

In order get more robust insights, it is generally recommended to sample multiple times from the prior predictive distribution and measure the uncertainty. The prior predictive check helps assess the adequacy of the chosen model and evaluate whether the model’s predictions align with our expectations, before observing any actual data.

The plot depicted below visualizes the prior predictive distribution by showing the expected revenue (mean) at each point, along with measures of uncertainty. We can see that the true revenue falls within the range of the standard deviation, indicating that the model specification is suitable for the observed data.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*-pQn0IluTdQ1ttBt7SfLTw.png)

Prior predictive check (image by the author)

## Conclusion

Bayesian marketing mix modeling may take considerable time to master. I hope that this article helped you to enhance your understanding of prior distributions and Bayesian marketing model specifications.

The complete code can be downloaded from my [Github repo](https://github.com/slavakx/medium_posts)

Thanks for reading![Last published Feb 3, 2025](https://medium.com/data-science/diy-ai-how-to-build-a-linear-regression-model-from-scratch-7b4cc0efd235?source=post_page---post_publication_info--af400adb836e---------------------------------------)

An archive of data science, data analytics, data engineering, machine learning, and artificial intelligence writing from the former Towards Data Science Medium publication.

## Responses (1)

Kakasarnold

```c
Hello! First of all, thank you very much for your enlightening article. I am a beginner in the field of MMM and I am using lightweight_mmm. I have a few questions about choosing priors:- Is using costs as media channel prior mandatory, or can it…
```