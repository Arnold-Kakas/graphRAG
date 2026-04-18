---
title: "Getting the best of both worlds in marketing incrementality tests: rapid testing and trusted…"
source: "https://medium.com/qonto-way/getting-the-best-of-both-worlds-in-marketing-incrementality-tests-rapid-testing-and-trusted-58243204fc80"
author:
  - "[[Anne-Claire Martial]]"
published: 2024-11-13
created: 2026-04-17
description: "Getting the best of both worlds in marketing incrementality tests: rapid testing and trusted results Marketing Measurement series: combining Meta Conversion Lift tests with in-house geo-based …"
tags:
  - "clippings"
---
## [The Qonto Way](https://medium.com/qonto-way?source=post_page---publication_nav-a9390fa3f292-58243204fc80---------------------------------------)

[![The Qonto Way](https://miro.medium.com/v2/resize:fill:38:38/1*62qiMixIqD-UODkXVUxPOA.png)](https://medium.com/qonto-way?source=post_page---post_publication_sidebar-a9390fa3f292-58243204fc80---------------------------------------)

Stories and learnings from the team behind Qonto

## Marketing Measurement series: combining Meta Conversion Lift tests with in-house geo-based tests

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*A9DznRDCKNETwzJD3hJnBA.png)

At Qonto, one mission of the Data Science Team is to support the Growth Department in efficiently allocating marketing budgets across channels. Our marketing measurement strategy includes several tools. These tools work together to provide insights.

- **The Attribution Model**: This model assigns each conversion to marketing touchpoints, usually based on the last-click principle. While it provides real-time descriptive information that’s easy to track, it has limitations as it doesn’t measure the incremental impact of ads. For instance, if a company had already decided to open a Qonto account when it saw an ad on channel A, the conversion would be attributed to channel A, although the client would have opened the account regardless of the ad.
- **The Marketing Mix Model (MMM)**: This holistic and econometric model provides a macro view of both marketing and non-marketing (such as holidays and Olympics) inputs. The other marketing tools help calibrate the MMM, which in turn is a valuable resource for identifying areas to test or explore in greater depth.
- **Incrementality tests**: These tests address the limitation of the Attribution Model by evaluating the **incremental** impact of a channel. In these tests, two groups are created: one exposed to the ads of the studied channel, and the other not. The causal impact of the channel is determined by comparing the number of conversions in the two groups. The groups can be created based on geography (geo-based experiments) or through randomization at the user level (Conversion Lift Tests — CLT). Until the end of 2023, Qonto only ran geo-based experiments.

Over the past two years, the number of incrementality experiments at Qonto has significantly increased for two main reasons. First, as a scale-up operating in a competitive environment, the context can change rapidly, necessitating the retesting of channels to ensure that budget allocation remains well-suited to the new conditions. Second, we require up-to-date data to continually refine our Marketing Mix Model (MMM).

> To manage the growing number of incrementality experiments, we sought a solution to accelerate our testing process while addressing the drawbacks identified with geo-based experiments, such as the challenge of finding an optimal regional split.

## Conversion Lift Tests in Meta

Advertisers like Meta offer to run incrementality tests, especially Conversion Lift Tests (CLT), directly on their platforms.

> ***By utilizing these platforms, the test management, monitoring, and post-test analysis are handled by the platform itself, significantly reducing the workload for the Data Science Team.***

### What is a CLT?

A CLT is a type of incrementality test where **randomization is based on individual users**.

In practice:

1. The intended audience is randomly split at the user level into control and treated groups.
2. During the experiment, the control group will be shown the ads, while the treated group will be intentionally withheld from seeing the ads.
3. Conversions in both groups are tracked. In [Meta CLT](https://www.facebook.com/business/m/one-sheeters/conversion-lift), this tracking can be done using [Meta Pixel](https://www.facebook.com/business/tools/meta-pixel).
4. The Conversion Lift is computed by comparing the number of conversions between the control and treated groups.
5. If the lift reaches a certain confidence or probability, it can be concluded that the channel provides an incremental increase in conversions. This allows for the computation of the Cost per Incremental Conversion, which is used to adjust marketing budget allocation.

The CLT process followed by Meta is illustrated below:

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*rgfcDYTtbcZE-RirQhC7NA.png)

Meta’s five-step process to measure ad effectiveness by comparing conversions between a group exposed to the ads and a group not exposed — source: Facebook

The setup described here is single-cell, meaning that it focuses on the incremental impact of one configuration. Multi-cell setups are also possible with the CLT platform, allowing for comparison of several distinct configurations (e.g. different frequencies), but these will not be covered in this article.

### CLT vs geo-based experiments

> ***The advertiser platform’s CLT is user-friendly and well-powered, but it lacks transparency and it also transfers ownership of data and results to Meta.***

The following table provides a comparison between CLT and geo-based experiments, highlighting their differences.

![](https://miro.medium.com/v2/resize:fit:2000/format:webp/1*KVysLryTwKT-SWIwX-iG3Q.png)

Comparison between CLT and geo-based experiments

## Our experience with Meta CLT

### Running Meta CLT

We conducted a CLT with Meta, tracking several metrics to gauge the ads’ impact at different stages of the acquisition funnel. We also developed a damage control dashboard to monitor the business impact of withholding ads from part of our audience and trigger alerts if it exceeded a predefined threshold based on the confidence interval.

At the end of the test, the CLT produced several results:

**Result 1:** There was a statistically significant positive impact of Meta ads on the success metrics.

**Result 2:** The value of the lift in conversion was high; this resulted in a low Cost per Incremental Acquisition.

These results were unexpected, as a geo-based experiment conducted a year and a half earlier on this channel had shown no statistically significant impact of Meta ads on acquisition, and our Attribution Model had attributed fewer conversions than the incremental conversions observed in the CLT. While there may be explanations for this change, we wanted to challenge the results due to the CLT’s ownership limitations. Therefore, we decided to run a second experiment using our in-house geo-based approach.

### Confirming the CLT results with our in-house geo-based experiment

We applied the methodology described [here](https://medium.com/qonto-way/how-to-invest-better-in-acquisition-channels-a-1-million-question-for-data-science-591c82b3e0e4), implementing a geographical split of France with treated regions (regions not exposed to the ads) and control regions (regions exposed to the ads). After several weeks of experimentation, we observed a statistically significant impact of Meta ads on conversions.

Several factors could explain why the results differed from the geo-based experiment conducted a year and a half before:

- **Higher volumes led to greater statistical significance:** In our initial geotest, we observed no statistically significant impact of Meta ads on the acquisition, meaning the impact was below the MDE and considered ‘noise’. Today, our acquisition is higher, which allows for a smaller MDE and enables us to distinguish an uplift from the noise more accurately.
- **Changes in the business environment can lead to changes in the incrementality tests results:** An incrementality test provides a causal relationship between ad exposure and conversion within the test context (internal validity). However, various factors, such as changes in the product or competitive environment, can limit the applicability of the results over an extended period (external validity). For example, if a new competitor enters the market and uses the same advertising channels, it could affect customer acquisition and decrease the relevance of the original test results. [This article](https://medium.com/qonto-way/marketing-measurement-series-incrementality-test-scheduling-f7525b713b4a) broadly details the concepts of internal and external validity.
- **Enhanced knowledge of the GeoLift package:** Our initial geo-based experiment with Meta was our first incrementality test using [GeoLift](https://facebookincubator.github.io/GeoLift/docs/intro/). Since then, we’ve conducted new tests on other channels, refining our understanding of the parameters needed to efficiently divide regions into treatment and control groups, achieving good statistical power while respecting budget constraints.

### Comparison with the Attribution Model

While the precise increment varied between the CLT and the geo-based experiment, both incrementality tests showed that the Attribution Model undervalued Meta ads’ performance. This isn’t surprising, as Attribution Models often overestimate the impact of certain channels, such as SEO and SEA Brand, while undervaluing others, like Push Ads. For instance, in a last-click Attribution Model, a conversion is attributed to the Google SEA brand channel under the following scenario:

1. A prospect sees an ad on Meta.
2. Later, wanting to open a professional bank account, the prospect recalls the Meta ad and searches Google for “Qonto,” clicking on the first link.

To mitigate this bias, Qonto has adjusted its Attribution Model by downplaying certain channels. To enhance accuracy further, we could apply coefficients derived from incrementality studies to the Attribution Model, thereby converting attributed conversions into incremental conversions.

> ***Overall, these findings emphasize the importance of using all measurement tools in conjunction to gain comprehensive insights and make informed decisions about budget allocation.***

## Next steps

Based on the CLT and the geo-based experiment results, we can adapt our strategy:

- **Budget adaptation**: Use the Cost per Incremental Conversion (CPIC) calculated in the geo-based experiment, along with the value from the CLT to establish a lower bound for the CPIC, and adjust our budget allocation for Meta accordingly.
- **Efficiency and speed**: Utilize mainly the CLT provided by advertisers to get directional insights with minimal workload thanks to the test management offered by the platform, and increase our velocity in conducting incrementality tests. Reserve in-house geo-based experiments for tests where we want full ownership and complete data visibility.
- **Ongoing validation**: Continue retesting our channels, as we have demonstrated that results can change over time.
- **Refinement of marketing measurement tools**: Leverage the new insights to refine our other marketing measurement tools (Attribution Model and MMM).

## Resources

If you want to read more about marketing measurement strategy, below is the full series of Qonto articles:

**Incrementality testing:**

- [*How to invest better in acquisition channels? A $1 million question for Data Science*](https://medium.com/qonto-way/how-to-invest-better-in-acquisition-channels-a-1-million-question-for-data-science-591c82b3e0e4)
- [*Incrementality test scheduling: velocity vs. validity*](https://medium.com/qonto-way/marketing-measurement-series-incrementality-test-scheduling-f7525b713b4a)
- *Getting the best of both worlds in marketing incrementality tests: rapid testing and trusted results (this article)*

**Marketing Mix Modeling:**

- [*Part I: Getting started*](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-337b8af11471)
- [*Part II: Adstock and saturation*](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-82e82c995b39)
- [*Part III: Bayes’ Theorem & priors*](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-05d28a2cfa18)
- [*Part IV: Inputs for a Bayesian model*](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-69bc3101d06d)
- [*Part V: Specifying a Bayesian model with PyMC*](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-f214ba550968)
- [*Part VI: MLOps*](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-part-vi-7bb9805076ba)

### About Qonto

Qonto makes day-to-day banking easier for SMEs and freelancers thanks to an online business account that’s combined with invoicing, bookkeeping and spend management tools.

Thanks to its innovative product, highly reactive 24/7 customer support, and clear pricing, Qonto has become the leader in its market with more than 500,000 customers.

Created in 2016 by Alexandre Prot and Steve Anavi, Qonto now operates in 8 European markets (France, Germany, Italy, Spain, Austria, Belgium, the Netherlands and Portugal), and employs more than 1,600 people.

Since its creation, Qonto has raised €622 million from well-established investors.

Interested in joining a challenging and game-changing company? Take a look at our [**open positions**](https://qonto.com/en/careers)**.**

Illustration by Océane Lanouet