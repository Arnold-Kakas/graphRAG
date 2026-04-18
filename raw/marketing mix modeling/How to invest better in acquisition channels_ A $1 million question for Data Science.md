---
title: "How to invest better in acquisition channels? A $1 million question for Data Science"
source: "https://medium.com/qonto-way/how-to-invest-better-in-acquisition-channels-a-1-million-question-for-data-science-591c82b3e0e4"
author:
  - "[[Marianne Borzic Ducournau]]"
published: 2023-01-04
created: 2026-04-17
description: "How to invest better in acquisition channels? A $1 million question for Data Science Qonto’s Data Science and Growth teams recently collaborated on a project to measure the impact of one of our …"
tags:
  - "clippings"
---
## [The Qonto Way](https://medium.com/qonto-way?source=post_page---publication_nav-a9390fa3f292-591c82b3e0e4---------------------------------------)

[![The Qonto Way](https://miro.medium.com/v2/resize:fill:76:76/1*62qiMixIqD-UODkXVUxPOA.png)](https://medium.com/qonto-way?source=post_page---post_publication_sidebar-a9390fa3f292-591c82b3e0e4---------------------------------------)

Stories and learnings from the team behind Qonto

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*zKDqZKR92WfCe7-ejarnJQ.png)

Qonto’s Data Science and Growth teams recently collaborated on a project to measure the impact of one of our acquisition channels. In this post we will explain the methodology we used, some of the problems we encountered, and what we learnt along the way.

**Authors:** [Ruari Walker](https://www.linkedin.com/in/ruariwalker/), [Marianne Borzic Ducournau](https://www.linkedin.com/in/mborzic/?locale=en_US)

## The $1 million question

As a fast-growing scale-up in a competitive industry, one of our biggest challenges at Qonto is to maintain the strong growth of our customer base.

The acquisition of new clients comes from three categories:

- **Organic.** This covers all free marketing channels such as SEO (Google Search), physical conferences or word of mouth.
- **Offline** **media marketing.** This relates to everything non-digital that we pay for directly in order to increase awareness and trust in Qonto. Typical examples would be billboards on bus stops and TV commercials.
- **Online paid acquisition.** This consists mainly of the clickable ads that anyone who scrolls through LinkedIn, Instagram or YouTube will be familiar with.

Qonto’s marketing model relies heavily on the latter category, with investments that are counted in millions of euros per year. It’s therefore crucial that we can measure the ROI of each channel as precisely as possible.

**Attribution models** go a long way towards giving us this measurement but their usefulness remains **limited by their purely descriptive nature**: they tell the last touchpoint of a customer who signed up but they can’t explain the role each prior touchpoint had in the acquisition. To give you a footballing analogy, attribution models would tell you which player scored a goal, but can’t tell you which teammates provided all the passes in the build-up to that goal. They tell you the end result but not the full story about how that result was achieved.

In addition, attribution models have technical limitations:

- Offline channels are hard to track: it is almost impossible to know whether a prospect watched a Qonto ad on TV or not.
- Prospects can opt out of being tracked online by declining cookies.
- It’s not always clear what exact trigger prompted any given customer to sign up, even when we ask them explicitly.

Our Data Science team was tasked with measuring — as rigorously as possible — the contribution of several important acquisition channels in our French market. For the sake of confidentiality, we’ll focus here on what we’ll call ***Channel X,*** which accounts for a significant fraction of our paid online acquisition budget.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*5scLfTyHenLcl3rNQxRh7Q.png)

Tracking issues

We wanted to use a framework that **does not rely on attribution models** and concepts such as first click or last click; these describe only the current state of affairs without showing the bigger picture by assessing [incrementality or causality](https://medium.com/asos-techblog/accelerating-geo-testing-at-asos-edbdf123a98b) following a change in marketing strategy.

We decided to pursue what we thought to be the simplest approach: cutting the budget to €0 on *Channel X* and measuring the impact this has on customer sign-ups. Of course, we would need to *control for everything else* in order to attribute the impact solely to *Channel X.*

## Shoot, we can’t go with A/B testing…

The natural approach to solving such problems is to set up an experiment protocol. This ensures that in the sentence “if we cut *Channel X* **then** we lose N sign ups”, the ‘ **then** ’ is a causal relationship: the action *caused* the result; it is not a simple correlation.

Ideally, we would carry out an A/B test, often seen as the gold standard of experimental research. Yet in this case, when prospects come to `qonto.com` it is already too late: we don’t know if they’ve seen the ad on *Channel X* or not. Yet this is the earliest point in the funnel where we have any control.

A ‘Before’ vs ‘After’ analysis would not be suitable in our case as it would not *isolate* the change in budget reduction that we wanted to measure. Instead, the change could be explained by seasonality or market fluctuations, for example. We **would not be able to conclude with any certainty** that an observed impact on sign-ups was due exclusively to the budget reduction.

## Let’s use another strategy

We decided to turn to a different type of test, namely a **geographical test**.

Typically, in our case, a geographical test would split France into 2 groups of regions, A and B. We would maintain the budget for *Channel X* in Group A and reduce it in Group B. The problem? Sign-ups in **groups A and B are not directly comparable**: the grouped regions might not have the same population or same demographic, making it very **rare to find two perfectly comparable groups**.

To solve that, we created a **synthetic version** of Group B (let’s call it Group B\*). This was our **counterfactual, our control group,** whose purpose was to inform us what the performance of Group B would have been during the test period under the “business as usual” configuration. Group B\* was calibrated on pre-test data using the Group A regions, which experienced no budget change. In particular, it was a **weighted average of those regions** which mimicked the behaviour in the treatment regions as accurately as possible in the pre-test period. During the test, we could compare Group B to its counterfactual Group B\*.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*vbNZ3sXAvcantZ6qenh_yQ.png)

We divided France by regions and the intervention was applied in 7 regions

Once the test had started, the treatment and control groups would begin to deviate if the intervention was having an impact and we would run a statistical test to determine if the difference is significant.

To implement this solution we had to:

- determine the treatment regions
- construct a synthetic control group
- determine an appropriate experiment design (duration, minimum detectable effect, etc.)

In order to do so, we used Meta’s [GeoLift](https://facebookincubator.github.io/GeoLift/) library in R which leverages Synthetic Control Methods. This methodology was popularized in the early 2000s by [Abadie et al](https://www.tandfonline.com/doi/abs/10.1198/jasa.2009.ap08746). They measured the impact of a large-scale tobacco control program in California by comparing the consumption of cigarettes in the state after the policy intervention with a synthetic control group for California, built from other states where there was no such policy.

## Some challenges we faced along the way

Along the way, we encountered several challenges:

**Finer geo granularity and treatment exposure**. A model’s performance increases with the degrees of freedom and the number of treated parts; splitting France into smaller areas (the country’s ~100 administrative *départements,* for example) would have been ideal. However, this was not possible in our case and we instead divided the country into its 22 former administrative regions. Also, since cutting the *Channel X* budget would be potentially detrimental to the business, we limited to 7 the number of treated regions.

**User contamination**. A fair experiment requires that prospective customers in the treatment region do not see ads on *Channel X*. We went some way to ensuring this was the case by targeting ads based on home location, although we were unable to guarantee it for everyone: some people may split their time between regions, for instance.

**Blocking local campaigns**. In order to have an unbiased experiment, the change in *Channel X* must be **the only variable** between treatment and non-treatment regions — any planned local marketing campaigns would have to be postponed until the end of the test.

## We have lift-off! Experiment launch and monitoring

We launched the test directly from the *Channel X* ads platform by reducing the budget to €0 in the 7 Group B regions. The experiment lasted for 6 weeks and we confirmed the launch was successful by checking daily spend at a regional level.

We decided to monitor a variety of metrics in 3 ways:

- **In-test monitoring**. We built a Metabase dashboard tracking key metrics such as sign-ups on a daily and cumulative level. This gave us confidence that (a) the experiment was progressing as expected and that (b) the experiment was not detrimental to the business.
- **Stopping mechanisms.** There is, as mentioned, the risk that suspending the budget in certain regions would damage the business financially if it turns out that customer sign-up volumes are overly dependent on *Channel X*. So we built **damage control metrics** — together with thresholds based on confidence intervals — which would trigger alerts for us via Slack and email if our chosen metrics on any given day were particularly unusual.
- **Post-test analysis**. We defined several secondary metrics that we wanted to analyze at the end of the test, such as the price plan mix and the type of customers opening accounts. Our hypothesis was that the **type** of customer signing up might change as a result of this experiment since customers’ profiles are channel-dependant.
![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*zN9bSXqQ7LVwyehiC-0X7g.png)

Daily sign ups over time (left) and cumulative since launch (right)

## Mission accomplished: the results and what we learnt

The results were both surprising and counterintuitive.

**Result #1**. We did not detect any change in customer sign-ups aggregated from all channels. Moreover, we did not see any overall changes in metrics further up the sign-up funnel, like `qonto.com` visits.

**Result #2**. Customer sign-ups from paid acquisition channels also remained constant, despite a drop in website visits that typically came from these channels.

**Result #3.** We observed a spike in the number of sign-ups attributed to other channels (*non-Channel X*). This suggests we have “channel overlap”. A prospective customer is exposed to Qonto adverts on multiple channels, so removing one from this mix has little or no impact.

A happy side-effect of running this experiment was that we saved a considerable sum of money that we would have otherwise spent on *Channel X* during that period.

**The Action Plan**. The learnings from this experiment will lead to several actions and future projects:

- We will reduce the amount we spend on *Channel X.*
- We will work to better understand the overlap in our channel mix and explore tools which can help keep our channel mix efficient.
- We will dive into the world of marketing mix modelling to assign spend in the most impactful way.
- We will run geo testing on other channels using synthetic control methods to better understand the impact those channels have.

This geo test is one of many examples of what the Data Science team does at **Qonto**. If you’re keen to use your modelling skills to make a monetary impact, consider [**joining us**](https://jobs.lever.co/qonto?department=Tech+%26+Data&team=Data+Science%2FAnalytics), we are hiring!

**About Qonto** [Qonto](https://qonto.com/en) is a finance solution designed for SMEs and freelancers founded in 2016 by Steve Anavi and Alexandre Prot. Since our launch in July 2017, Qonto has made business financing easy for more than 250,000 companies.

Business owners save time thanks to Qonto’s streamlined account set-up, an intuitive day-to-day user experience with unlimited transaction history, accounting exports, and a practical expense management feature.

They stay in control while being able to give their teams more autonomy via real-time notifications and a user-rights management system.

They benefit from improved cash-flow visibility by means of smart dashboards, transaction auto-tagging, and cash-flow monitoring tools.

They also enjoy stellar customer support at a fair and transparent price.

Interested in joining a challenging and game-changing company? Consult our [job offers](https://qonto.com/en/careers)![Data](https://medium.com/tag/data?source=post_page-----591c82b3e0e4---------------------------------------)[Data Science](https://medium.com/tag/data-science?source=post_page-----591c82b3e0e4---------------------------------------)[Last published 2 days ago](https://medium.com/qonto-way/the-pmm-busywork-trap-and-the-ai-operating-system-i-built-to-escape-it-8e41a490da87?source=post_page---post_publication_info--591c82b3e0e4---------------------------------------)

Stories and learnings from the team behind Qonto