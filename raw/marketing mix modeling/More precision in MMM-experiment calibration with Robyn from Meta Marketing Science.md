---
title: "More precision in MMM-experiment calibration with Robyn from Meta Marketing Science"
source: "https://medium.com/@gufengzhou/more-precision-in-mmm-experiment-calibration-with-robyn-from-meta-marketing-science-f608841fc6d4"
author:
  - "[[Gufeng Zhou]]"
published: 2022-11-24
created: 2026-04-17
description: "More precision in MMM-experiment calibration with Robyn from Meta Marketing Science Details of the new contextual calibration with immediate & carryover response in Robyn v3.8. TL,DR: Correlation ≠ …"
tags:
  - "clippings"
---
## Details of the new contextual calibration with immediate & carryover response in Robyn v3.8.

### TL,DR:

- **Correlation ≠ Causation.** Marketing Mix Models (MMM) should be calibrated with causal experiments given reasonable signal quality and study confidence.
- **MMM and experiments measure different things.** Experimental estimates are usually the short-term last dollar impact of ads on some match-able outcomes, while MMM measures the long(er) term average impact of ads on all outcomes. In most cases the former is a subset of the latter. The widely used “naïve calibrations” approach drives MMM’s total effect towards experimental results that’s a subset of MMM. This leads to underestimation of the calibrated channels and by extension also suboptimal budget allocations of the total media mix.
- **Contextual calibration with** [**Robyn v3.8**](https://www.facebook.com/groups/robynmmm/posts/1310953473006116/). The latest calibration feature in Robyn can isolate immediate effect from carryover. With this, we believe Robyn offers an edge over the naïve calibration. [An external study](https://www.analytic-edge.com/the-value-of-calibrating-mmm-with-lift-experiments/) has found out that the discrepancy of 25% between MMM & experiment.

### MMM is correlational and should be calibrated with causal experiments whenever appropriate

Marketing Mix Model (MMM) is a [decades-old measurement technique](https://en.wikipedia.org/wiki/Marketing_mix_modeling) commonly used to evaluate marketing effectiveness across ad publishers and allocate budget accordingly. It relies on the statistical relationship (e.g. regression) between media variables (e.g. spend, impressions) and outcomes (e.g. sales, conversions). While the modern and sophisticated machine-learning based techniques are evangelizing the performance of MMM, it remains correlational at its core.

On the other hand, experiments, or [randomized controlled trials (RCTs)](https://en.wikipedia.org/wiki/Randomized_controlled_trial), are scientific gold standard to infer causal results. In the field of Marketing, for example we have Facebook Conversion Lift, Brand Lift & GeoLift, among many other 3rd party solutions. That’s why experimental results are often considered “ground truth”. We know that [correlation doesn’t equal causation](https://en.wikipedia.org/wiki/Correlation_does_not_imply_causation). Ice cream sales don’t drive sunglass sales. Summer does. Therefore, it is important to validate and calibrate MMM with ground truth measures of causality.

### MMM and experiments measure different things

There are varying approaches to calibration. A common approach is to simply use causal estimates to hand-pick MMM candidates. A more rigorous approach, e.g. in the Bayesian framework, derives the prior distribution of beta coefficients from the causal estimates. As comparison, Robyn uses a multi-objective hyperparameter optimisation approach that implements the calibration between MMM & experiments as an additional objective function to be minimized.

These approaches, including Robyn prior to v3.8, can be seen as “naïve calibration”, because they aim to “simply” drive MMM’s total predicted effect for a given channel closer to the causal estimates. However, MMM and experiments measure different things. The following are three non-exhaustive differences in scope between MMM & experiments.

1. **Immediate vs. carryover effect**: [Carryover or adstock effect](https://en.wikipedia.org/wiki/Advertising_adstock) is defined as the lagged effect of advertising on consumer purchase behavior, while the dependent variable can be other business outcome metrics (e.g. conversion, lead generation). For example, a user sees an ad today and makes a purchase a week later. By nature, an experiment captures mostly immediate and short-term effects and has limited capacity for carryover. If a pre-study ad causes purchases during the study period, these purchases are excluded from study estimates because they would occur equally in both test & control groups due to the randomization. Similarly, if an ad during the study period results in post-study purchases, these are usually also excluded from study effects. MMM, on the other hand, can estimate carryover effects over time using adstocking & saturation transformation.
2. **Last dollar vs. average dollar**: In a typical experiment for an always-on channel, ads from this channel are running in the test group and not in the control group, while all other channels are broadcasting normally in both groups. If we consider a typical C-shape [saturation or diminishing return curve](https://en.wikipedia.org/wiki/Diminishing_returns) for a given consumer, the experiment creates a “lab environment” that doesn’t exist in reality: in the control group, the absence of the tested channel is filled by other channels, which “pushes” the tested channel’s effect to the upper part of a diminishing return curve. This is considered the “last-dollar” and thus the lower bound of channel A’s effect. If it’s a S-shape curve, then it won’t always be the lower bound due to the accelerating derivatives at the beginning of an S-curve. But nevertheless it remains the last-dollar effect. Compared to this, MMM usually measures the average effect within the modeling window.
3. **Some outcomes vs. all outcomes**: Some types of experiments, especially the ones relying on device or user level signals, cover a subset of outcomes that are matchable in the test and control group. These include typically products sold online, which are challenged by limited Visibility into customer activity due to ecosystem & policy changes, or are from a subset of users (e.g. loyalty card users / panels). MMM, on the other hand, aims to measure outcomes holistically across online & offline sales channels using aggregated media and outcome data.

In short,

- Experimental estimates are usually the short-term last dollar impact of ads on some match-able outcomes,
- while MMM measures the long(er) term average impact of ads on all outcomes.

Since the former is generally less than the latter, a naive calibration comparing MMM and experiment outputs directly is likely to underestimate the calibrated media. If this analysis is only conducted on some (testable) channels, then, over time, this could lead to a suboptimal budget allocation toward less effective channels.

While some marketers try to set up their studies accordingly to mitigate these discrepancies, they often face business constraints and trade-offs:

- Data availability: Marketers who wish to include omni-channel (or offline) outcome data may find that it is only available for a subset of users (e.g. loyalty card, panel).
- P&L considerations: Some businesses may constrain the use of experiments during sale periods (e.g. Black Friday, Christmas etc.) to minimize opportunity costs of a holdout.
- Org structure: It could be a tedious task to align testing agenda between different teams (e.g. brand, performance) and agencies in a timely manner, which often results in noise and competing ads during the study periods.
- Regulation: Regulation and policy may prevent the use of the same holdout group across different publishers, leading to different non-study ad exposure in the baseline.
- Statistical power: Experimental methods that require less signal such as Geo-based experiments (e.g. GeoLift) have lower power, because the sample size of any identity-based randomization (for example Facebook Conversion Lift) is far larger than geography-based randomization. There are just more people than cities and zip codes.

When putting the differences in scope and the business constraints together, the discrepancy between MMM and experimental estimates can be large. This [recent research](https://www.analytic-edge.com/the-value-of-calibrating-mmm-with-lift-experiments/) on calibration has observed a 25% difference in ROAS. Even though it’s nearly impossible to make them identical, there are approaches to close the gap between them.

### Robyn v3.8 Brings MMM and experiment Closer with Contextual Calibration

With the latest release ([Robyn v3.8](https://www.facebook.com/groups/robynmmm/posts/1310953473006116/)), we’re specifically tackling the difference #1 (immediate vs. carryover effect) by default with the new robyn\_calibrate function. This is done by separating the immediate effect from carryover effect for a given channel, and only “contextually” calibrating the appropriate subset (area B in figure 1) to experimental results:

- \[Area A\] If a pre-study ad causes purchases during the study period, these purchases are excluded from study estimates. With random assignment in RCT, we expect this to occur equally in the test and control group and therefore won’t be captured as the difference between both groups.
- \[Area B\] If an ad on study day 1 (e.g. period 5 in figure 1) causes lagged purchases during the study period, this is included in the study estimates, because the ad and its carryover only happens in the test group and not in the control group.
- \[Area C\] If an ad during the study causes outcomes after the study has ended, this is not included in the study estimates.
- Based on the above, the effect of an experiment is solely area B, while the effect of MMM includes area A + B during the experimental period. The mismatch of naive calibration happens when the area B in experiments is calibrated towards area A + B in MMM.
![](https://miro.medium.com/v2/resize:fit:1400/format:webp/0*ZAgZ-Ju8CD2mAb68)

Figure 1: Calibrating MMM with Lift in Robyn v3.8

Usually, adstocking transformation in MMM is applied on input media variables, meaning the immediate & carryover portion of the transformed variables are separable. However, we haven’t seen much effort in the industry to isolate immediate & carryover effects on the response. With Robyn v3.8, we can obtain the immediate, historical carryover & future carryover response separately.

In the example in figure 2, we assume the raw spend in a given period is 80$ and the carryover spend of historical campaigns is 60$. Robyn places the historical carryover spend on the lower part of the spend-response curve (aka. diminishing return curve), because it makes sense that historical ads have already built up some purchase propensity before the current ads. This mimics the context in an experimental setup, where the historical adstock is expected to occur in equal intensity in the test and control groups. As such, historical adstock contributes to outcomes first, with the experimental study estimating the incremental impact of the current period ads over and above this. In this example, if we would only calibrate period 5 with Robyn, then the green curve in figure 2 would be equal to area B in figure 1.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/0*34sOnvFtKKkrJSTC)

Figure 2: Isolating Immediate & Carryover response from Adstocking in Robyn v3.8

A separate, but important innovation we have also launched at the same time is the ability to calibrate multiple variables in MMM (e.g. Meta Brand campaigns, Meta Performance campaigns) with a single experiment (e.g. overall Lift from Brand + Performance ads). This provides further flexibility for analyses and calibration.

With our innovation in contextual calibration, we believe Robyn offers an edge over common naïve calibration methods today. Even though our current release only addresses one of the differences in scope discussed above, we believe it is a big step towards better comparability between the two major measurement techniques. By open-sourcing this solution, we also hope to further inspire the industry and advance this topic.

> **This article is co-authored with** [**Igor Skokan**](https://www.linkedin.com/in/igorskokan/), [**Mark Chen**](https://www.linkedin.com/in/markchen-sg/), [**Bernardo Lares**](https://www.linkedin.com/in/laresbernardo/) **and** [**myself**](https://www.linkedin.com/in/gufeng-zhou-96401721/)**.**

[![Gufeng Zhou](https://miro.medium.com/v2/resize:fill:96:96/0*pxqDNWTwFI3we1iO)](https://medium.com/@gufengzhou?source=post_page---post_author_info--f608841fc6d4---------------------------------------)[10 following](https://medium.com/@gufengzhou/following?source=post_page---post_author_info--f608841fc6d4---------------------------------------)

Meta Marketing Science. Author of "Robyn", the open source MMM package from Meta. [https://github.com/facebookexperimental/Robyn](https://github.com/facebookexperimental/Robyn)