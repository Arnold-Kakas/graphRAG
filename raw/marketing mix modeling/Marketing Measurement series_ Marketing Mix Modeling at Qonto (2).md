---
title: "Marketing Measurement series: Marketing Mix Modeling at Qonto"
source: "https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-05d28a2cfa18"
author:
  - "[[Ruari Walker]]"
published: 2024-05-23
created: 2026-04-17
description: "Marketing Measurement series: Marketing Mix Modeling at Qonto | Part III Bayes’ Theorem & priors Welcome to article three in our Marketing Mix Modeling series. In this article, we’ll begin to …"
tags:
  - "clippings"
---
## [The Qonto Way](https://medium.com/qonto-way?source=post_page---publication_nav-a9390fa3f292-05d28a2cfa18---------------------------------------)

[![The Qonto Way](https://miro.medium.com/v2/resize:fill:76:76/1*62qiMixIqD-UODkXVUxPOA.png)](https://medium.com/qonto-way?source=post_page---post_publication_sidebar-a9390fa3f292-05d28a2cfa18---------------------------------------)

Stories and learnings from the team behind Qonto

## Bayes’ Theorem & priors

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*mCC8M1Sdxv4f_3iuUf7wkQ.png)

*Welcome to article three in our Marketing Mix Modeling series. In this article, we’ll begin to focus on the Bayesian approach to MMM and discuss the role of the famous prior in this framework. The approach will be high-level and theoretical with practical applications and examples to follow later in the series.*

**The outline for this article is as follows:**

- Thinking like a Bayesian  
	— From probabilities to probability distributions
- Uncertainty is the game, quantifying it is the aim  
	— Conjugate pairs  
	— Sampling from the posterior
- Specifying priors in MMM  
	— Further tips and tricks
- Some challenges when selecting priors  
	— Advice to mitigate some of these challenges

Before diving in to this article, we invite you to take advantage of our [Streamlit app](https://mmm-prior-elicitation.streamlit.app/), embedded below, which allows you to play around and get to grips with different types of distributions and the parameters which define them. As you’ll discover in this article, understanding the distributions on offer and their defining parameters plays a central role in Bayesian statistics.

## Thinking like a Bayesian

It’s Saturday night and you’re deciding which restaurant to go to. You assume you’ll choose your favorite one as usual but, when browsing the website, you notice some negative reviews they’ve been receiving lately. Would this lead to you reconsidering where to eat? If the answer to this question is “ *yes* ”, then you are thinking like a Bayesian.

There are many everyday examples like this, in which we update our views and opinions based on new or additional information which is presented to us. These analogies are perhaps the simplest way to describe the basis of Bayesian statistics — a statistical philosophy in which probability expresses a degree of belief in an event (this is at odds with how the Frequentist philosophy would describe the concept of probability — which is based on the *frequency* of the events in question). This belief may change as new evidence is presented.

Bayesian statistics and inference is based on Bayes’ Theorem, a fundamental theorem that describes how to update the probabilities of hypotheses when given evidence. It’s stated mathematically as follows:

![Annotated image of Bayes’ Theorem](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*bHnl_YPJCn4m884OSXyw3A.png)

Annotated image of Bayes’ Theorem

In the context of the first example above:

- P(B|A): is called the **likelihood**. It represents the probability of negative restaurant reviews, given that the restaurant is your favorite.
- P(A): is called the **prior** and is analogous to the probability that you will go to eat at your favorite restaurant.
- P(A|B): is called the **posterior**. It represents the *updated probability* that you go to eat at your favorite restaurant, given that it’s recently received bad reviews.

The denominator is called the **marginal likelihood** and represents the probability of any restaurant receiving a bad review. It is a normalizing factor to ensure the final result is a valid probability and so can be largely ignored.

### From probabilities to probability distributions

In many real-world applications, we’re not just interested in the probability of a single event, but in the range of possible outcomes and their associated probabilities. Bayes’ Theorem can be extended to probability distributions, enabling us to describe an unknown parameter (or a set of unknown parameters) based on some observed data and our prior beliefs.

Our priors should now take the form of *probability distributions* which are used to express the uncertainty and variability in our initial assumptions. As we’ll see in the next section, we will think of ‘uncertainty’ in terms of distributions.

Since we’re now in the world of distributions, the posterior distribution — the probability distribution of our parameters given the data in front of us — can be thought of as an averaging of the likelihood and the prior in some sense.

![Visual representation of the posterior distribution as an average of the prior and the likelihood](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*_RKfw-C7n97KErIy1D6CHw.png)

Visual representation of the posterior distribution as an average of the prior and the likelihood

As we saw in our second article of this series [Marketing Mix Modeling at Qonto Part II: Adstock and saturation](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-82e82c995b39), our MMM regression equation has the form (t = time period; alpha = intercept):

![MMM regression equation](https://miro.medium.com/v2/resize:fit:2000/format:webp/1*ifiWBeJJltl2xYRJXRxNYw.png)

MMM regression equation

So, in the context of MMM, our unknown parameters include (but are not limited to):

- Paid channel, organic, and control coefficients.
- Adstock parameters for each channel.
- Saturation parameters for each channel.

“ *Selecting priors* ” in the context of MMM entails selecting prior probability distributions for each one.

## Uncertainty is the game, quantifying it is the aim

### Conjugate pairs

So far, so good. But how can we determine the resulting posterior distribution based on the likelihood and the prior? Sometimes this is fairly straightforward. Let’s think about estimating click-through rates in a new page on your e-commerce website:

- The prior represents the probability distribution of the true conversion rate. Since we’re talking about conversion rates, the range of values should be bounded between 0 and 1. In this case, the Beta distribution might be a suitable choice of prior distribution since it satisfies this criteria and is fairly flexible (see the Streamlit app above!).
- The binomial distribution is a natural choice for the likelihood distribution as it represents the probability of *k* successes from *n* trials (here, *k* clicks from *n* page visits).

But in fact we’re now in a very particular setting because these two distributions neatly combine to return a Beta distribution again! In this case, we say that we have a **conjugate pair**, or that the beta distribution is a **conjugate prior** for the binomial distribution. Another example of this would be choosing a normal distribution for both the likelihood and the prior, resulting again in a normal distribution for the posterior. See [here](https://en.wikipedia.org/wiki/Conjugate_prior#Table_of_conjugate_distributions) for further examples of conjugate pairs.

### Sampling from the posterior

However this is often not the case in practice. Particularly for something as complex as MMM, which is a multi-dimensional problem to solve (more than one unknown parameter to estimate) and several distributions which likely don’t fit together in the neat way seen in the example above. In these cases, there is no closed formula for the posterior, or finding it boils down to solving an obscure multi-dimensional integral. So we have to find an alternative approach.

This is where PyMC comes in. PyMC employs a machinery called *Markov Chain Monte Carlo (MCMC)* which are a family of sampling algorithms in which the next sample depends on the current one. These algorithms enable us to sample from the prior distribution(s) in an intelligent way, allowing us to focus on the most important areas of the prior distributions. The term “ *most important* ” means the regions of the parameter space which result in peaks in the posterior space. In short, instead of computing the posterior analytically, we sample thousands of data points to build an accurate estimate of it.

## Specifying priors in MMM

Specifying a prior probability distribution encodes various information into your model, including:

- **Our uncertainty.** How certain we are about the possible values of our parameter. A large standard deviation indicates a higher degree of uncertainty (known as a **weakly-informed prior**), while a smaller one indicates more confidence (known as an **informed prior**).
- **The range of possible values.** The range of values which our parameter can take. Values with 0 probability in our distribution are not possible. For example, Half Normal distributions assign 0 probability to values less than 0. Similarly, Uniform distributions are defined by upper and lower bounds.
- **The type of data.** We are also specifying whether the parameter takes on discrete or continuous data types based on the distribution family selected. It’s important to understand the context and the data well to know what values your unknowns can take.

In a Bayesian MMM, priors are crucial because they influence the posterior distribution — our updated beliefs about the model’s parameters after considering the data. Choosing appropriate priors can significantly affect the results and interpretations derived from a Bayesian model. Here are some suggestions for the kind of things to consider when setting priors in your MMM.

**Example #1: priors for paid and organic channel coefficients**

- It’s reasonable to believe that paid channels like Facebook, Snapchat, and LinkedIn do not have a negative effect on your target metric, meaning you may want to bound the channel coefficient below by 0.
- In this case, a Half Normal distribution might be an appropriate family of distributions to select. The choice of standard deviation needed in order to fix a particular distribution from this family will depend on how confident we are in this channel’s efficiency.
![Half Normal distribution](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*9zv_gqpbPowtrCZkiq67qQ.png)

Half Normal distribution

**Example #2: priors for competitor marketing investment**

- Suppose we have data relating to the marketing investments which our competitors make. We could argue that these investments could be unintentionally beneficial to our business — *a lead views a competitor ad on social media but is redirected to Qonto after making a Google search*. On the other hand, competitor ad investment could result in Qonto losing business — *leads view and click on these ads.*
- Suppose we simply can’t decide between these two outcomes. In this case our unwillingness to commit one way or another could be modeled by a Uniform distribution centered at 0, with appropriate bounds.
![Uniform distribution](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*BvQnLRIVgMzvBpF5HBl9XA.png)

Uniform distribution

**Example #3: referral coefficients**

- Qonto operates a successful [referral program](https://qonto.com/en/referral) in which, at the time of writing, the referrer and the referee each earn €80. This means the cost of acquiring a new customer (CAC) associated to this channel is at least €160. We write “ *at least* ” here because it may be possible that the referee would have opened a Qonto account regardless of the referral program. We want to capture this hard business logic in the model and so we want to select a prior which insists on a CAC ≥ €160.

**Example #4: control variables**

- You may often find that you are unsure of the direction or magnitude of the effect of your Control variables. In these cases, you may want to use a Normal distribution centered at 0 with an appropriate standard deviation based on the variable and the context.

### Further tips and tricks

**Experimentation**. As already mentioned in [Part I](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-337b8af11471) of this series, experiments and attribution models should work in close collaboration with MMM. Experiments are considered the gold standard of marketing measurement — they are the closest we can come to understanding the true efficiency of a marketing channel. We can encode the results of experiments ([geo tests](https://medium.com/qonto-way/how-to-invest-better-in-acquisition-channels-a-1-million-question-for-data-science-591c82b3e0e4), lift tests) into our model via informed prior distributions.

**Attribution & surveys**. Similarly, but resulting in priors which are not as informed when used in isolation, we can use customer survey results and attribution models (both in-house and platform-based) to give clues on the ranges of channel efficiencies we can expect.

**Leverage your team**. More generally, we advise working closely with your stakeholders to understand their prior beliefs and to use them when building your MMM. They are the business experts and will have their own insights, analysis, and experience which you can draw on. The Delphi Method is a technique which can be used to leverage the marketing expertise within your broader team for your MMM — we recommend [this article](https://medium.com/@nialloulton/the-delphi-method-for-bayesian-marketing-mix-modelling-efc5fb4640e) for an overview.

**Sampling from the prior**. Once we have fixed all prior distributions required for our model we can sample from them, insert those values into our known MMM regression equation, and check the result against our observed data. In fact this is advised as a sanity check on your model specification and on your chosen priors.

If in doubt, it’s best to select priors that are uninformative, or only weakly informative so as to give your model as much freedom as possible.

## Some challenges when selecting priors

**Scaled data**. If you are taking a Bayesian approach to MMM, it’s likely that you have scaled your data at some point. This makes it difficult to think about the likely values of parameters such as channel coefficients, even when you have strong convictions about those values.

**Transformed data**. As seen in [Part II](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-82e82c995b39), the channel coefficients are actually coefficients to data which has been transformed by adstock and saturation functions. This adds another layer of complexity when defining appropriate prior values.

**Complex transformations**. Defining priors for parameters in transformation functions is particularly difficult as we don’t think about the effects of marketing in terms of equations. These functions seem abstract and far away from the world of marketing.

**Practical constraints**. You may work in a large company, or a fast-growing company, with multiple stakeholders and an ever-changing team. Explaining the model and the concept of priors to stakeholders can be time-consuming and some stakeholders may not feel at ease with providing priors, particularly if they are new to the team, for example.

**Target metric**. Stakeholders usually have an idea of channel efficiency, not of channel contributions. This results in some numerical gymnastics for the stakeholders in order to translate their knowledge into the format you require.

**Offline channels**. It’s likely that you won’t have lots of reliable performance-related data points for Offline channels since they don’t have touch points like Online channels do. It’s also unlikely you would be able to run incrementality experiments on these channels, given that they arguably have more long-term impact than short-term impact (and you won’t be able to run an incrementality test for months and months).

### Advice to mitigate some of these challenges

**Employ the Delphi Method**. We would strongly encourage anyone working on a Bayesian MMM to define priors using the Delphi Method. This mitigates bias, provides a structured and well-documented framework, and breaks down siloes between stakeholders and teams.

**Transparency and documentation**. The best way to answer the criticism of Bayesian approaches is via transparency. We think it’s important that stakeholders and MMM builders are fully transparent about how the model was built and what assumptions have been made. That means documenting how priors were collected and why those priors were chosen.

**Err on the side of uncertainty**. We believe being overly cautious and giving the model more freedom to explore parameter spaces is the preferred approach versus being overly-confident and too restrictive.

**Try, fail, repeat**. Often there are many channels and parameters in the make-up of your model, and therefore many priors to select. There is very often no right answer on which family of distribution to select and, once selected, the parameters which fix a specific distribution. For now our advice is to accept that and to not be afraid of playing around with different choices in your model. Tracking the results of this “playing around” may be difficult, but look out for Part VI in this series on MLOps which can make this process much easier!

**Visualizations**. Visualizations beat numbers and raw data, for stakeholders and data people alike. We advise using visualizations, like the Streamlit app above, to help guide you when selecting and defining a distribution.

**Holistic view**. Use all data points at your disposal to build up a holistic view of your channels, including attribution models (in-house and platform-based), past experiments, customer surveys, and any relevant past analyses which have been done.

Further, more concrete, examples together with a practical implementation of these priors in PyMC will follow in an upcoming article. There are many aspects to consider when selecting prior distributions and there are often no clear right or wrong choices.

*Want to read more? Here’s the full Marketing Measurement series:*

**Marketing Mix Modeling:**

- [Part I: Getting started](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-337b8af11471) *(first released 21 May 2024)*
- [Part II: Adstock and saturation](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-82e82c995b39) *(first released 22 May 2024)*
- Part III: Bayes’ Theorem & priors
- [Part IV: Inputs for a Bayesian model](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-69bc3101d06d) (*first released 27 May 2024*)
- [Part V: Specifying a Bayesian model with PyMC](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-f214ba550968) (*first released 5 June 2024*)
- [Part VI: MLOps](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-part-vi-7bb9805076ba) (*first released 14 June 2024*)

**Incrementality testing:**

- [How to invest better in acquisition channels? A $1 million question for Data Science](https://medium.com/qonto-way/how-to-invest-better-in-acquisition-channels-a-1-million-question-for-data-science-591c82b3e0e4) *(first released 4 January 2023)*
- [Incrementality test scheduling: velocity vs. validity](https://medium.com/qonto-way/marketing-measurement-series-incrementality-test-scheduling-f7525b713b4a) (*first released 19 June 2024)*
- [*Getting the best of both worlds in marketing incrementality tests: rapid testing and trusted results*](https://medium.com/qonto-way/getting-the-best-of-both-worlds-in-marketing-incrementality-tests-rapid-testing-and-trusted-58243204fc80) *(first released 13 November 2024)*

### About Qonto

Qonto makes it easy for SMEs and freelancers to manage day-to-day banking, thanks to an online business account that’s stacked with invoicing, bookkeeping and spend management tools.

Created in 2016 by Alexandre Prot and Steve Anavi, Qonto now operates in 4 European markets (France, Germany, Italy, and Spain) serving 450,000 customers, and employs more than 1,400 people.

Since its creation, Qonto has raised €622 million from well-established investors. Qonto is one of France’s most highly valued scale-ups and has been listed in the Next40 index, bringing together future global tech leaders, since 2021.

Interested in joining a challenging and game-changing company? Take a look at our [open positions](https://qonto.com/en/careers).

Illustrations by [Estelle Pannier](https://www.linkedin.com/in/estelle-pannier-senior-brand-designer/)