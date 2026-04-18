---
title: "Marketing Measurement series: Incrementality test scheduling"
source: "https://medium.com/qonto-way/marketing-measurement-series-incrementality-test-scheduling-f7525b713b4a"
author:
  - "[[Louis Magowan]]"
published: 2024-06-19
created: 2026-04-17
description: "Marketing Measurement series: Incrementality test scheduling Velocity vs. validity Today’s addition to the Qonto Marketing Measurement series will be broaching the topic of incrementality …"
tags:
  - "clippings"
---
## [The Qonto Way](https://medium.com/qonto-way?source=post_page---publication_nav-a9390fa3f292-f7525b713b4a---------------------------------------)

[![The Qonto Way](https://miro.medium.com/v2/resize:fill:76:76/1*62qiMixIqD-UODkXVUxPOA.png)](https://medium.com/qonto-way?source=post_page---post_publication_sidebar-a9390fa3f292-f7525b713b4a---------------------------------------)

Stories and learnings from the team behind Qonto

## Velocity vs. validity

![Three plants: A short, leafy one for validity; a tall but not leafy one for velocity; a tall and leafy one for the plant that has both velocity and validity](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*B01mj-ASa2p0SDlinTfLgA.png)

Three plants: A short, leafy one for validity; a tall but not leafy one for velocity; a tall and leafy one for the plant that has both velocity and validity

*Today’s addition to the Qonto* ***Marketing Measurement series*** *will be broaching the topic of incrementality experimentation (XPs). A TL;DR for the article is given below.*

⚡ **TL;DR:** **Experiment (XP) scheduling is a trade-off between velocity (number of XPs in a given time) and (external) validity of those XPs.**

- All marketing XPs are flawed and our ability to generalize causal claims about them is limited.
- Isolated incrementality XP results should be considered as *directional,* not *definitive* (unless there is strong, supporting evidence to complement them). They shouldn’t be regarded as an outright source of truth — but as a hint that should be re-verified regularly (and perhaps used to calibrate a Marketing Mix Model with).
- A pragmatic approach could be to reserve isolated, cooled-down geo tests for the most business-critical questions and maintain a good level of XP velocity otherwise (incl. simultaneous XPs if needed).
- Let’s not sweat the small stuff: [“Do you care more about the precision of the outcome, or making money?”](https://cxl.com/blog/can-you-run-multiple-ab-tests-at-the-same-time/)

**The outline for this article is as follows:**

- Internal vs. external validity
- Threats to external validity in marketing experiments
- Let’s not sweat the small stuff
- A pragmatic approach to marketing experimentation

## Internal vs. external validity

Before getting stuck into the discussion around causal inference in marketing XPs, let’s take some time to clarify the distinction between **internal** and **external validity.** These two causal inference concepts are useful to bear in mind when considering marketing XPs. Often in marketing science articles the term “causal” is used quite liberally, even imprecisely. A one-off [Conversion Lift test on Meta](https://www.facebook.com/business/m/one-sheeters/conversion-lift) might give you internally valid results for the incrementality of that channel during your XP — but it’s insufficient as evidence to use when making “causal” claims about that channel’s incrementality outside of your XP. This is where the subtleties of internal and external validity come to the fore.

The sections below will be lightweight refreshers on them, but, for more detail, please feel free to dig into the indicative references below.

🔗 **Indicative references:**

- [Experimental and Quasi-Experimental Designs for Generalized Causal Inference](https://iaes.cgiar.org/sites/default/files/pdf/147.pdf)
- [Cambridge Handbook of Experimental Political Science (Chapter 3)](https://www.cambridge.org/core/books/cambridge-handbook-of-experimental-political-science/CCEA698DB2EB4FF270D988F84EA90377)

### Internal validity

**Internal validity** refers to the degree to which a study accurately establishes a cause-effect relationship. It’s about the integrity of the experimental design and whether the results of the study truly demonstrate the effect of the treatment or intervention. A study with high internal validity lets you be reasonably confident that the outcomes were caused by the independent variable and not by other confounding variables. Having a robust assignment mechanism (randomization) to treatment and control groups (or holdout groups if using synthetic controls) and proper experimental design can increase internal validity.

### External validity

**External validity** refers to the degree to which the results of a study can be generalized to other situations, populations, or settings. In other words, it’s about the applicability of the study’s findings beyond the specific context in which the research was conducted. External validity is often addressed by comparing the results of several internally valid studies that were conducted in different circumstances at different times. It requires good substantive/theoretical support as well. Factors that influence external validity include sample representativeness, realism of the experimental conditions, and the similarity between the experimental setting and the setting to which the results will be applied.

### Relating them to marketing experiments

To summarize: internal validity is about the validity of conclusions drawn *within the context* of the study; external validity is their validity *outside the context* of the study.

- If a Data Science team do their job well, the marketing XPs they run should be **internally valid** — *but their external validity is by no means guaranteed.*
- If a Data Science team **consistently** do their job well, then they may **move towards external validity** — *for any ad channels that are frequently re-tested.*

## Threats to external validity in marketing experiments

Marketing experimentation is not medicine/biostatistics — the external validity of our tests will never be excellent. XPs on their own might be internally valid for the specific time-period, (sub-)population and context we consider — but generalizing their results is trickier.

### Threats to external validity — all marketing experiments

There are many factors which could limit the external validity of your marketing XPs. Some are listed below:

- **Product/offering changes.** Your company, brand and offering/product will change considerably over time. The product that that you advertised in the e.g. 2022 Instagram ads is different to the product you’re advertising now.
- **Marketing mix changes.** The combination of channels that your company markets with and their respective budgets may have changed considerably over time. Often incrementality tests are run on lower- or mid-funnel channels (since testing upper-funnel channels like TV or radio isn’t straightforward), which in theory would be affected by the marketing mix of channels above them in the funnel.  
	*\- Additionally — the marketing mix within the channel you’re testing could change. You could spend a greater proportion of the budget for that channel on retargeting, instead of prospecting — or on any number of targeted ad groups within the channel (incl. by demographic or device).*
- **Creatives and messaging change.** The creative and copy used in your ads may have changed over time, e.g. your 2022 Instagram ads might look very different to your 2024 ones.
- **Unknown unknowns.** There could be any number of confounding variables introducing heterogeneous treatment effects which you have no knowledge of. This could be true for users of either a particular platform (lift tests) or to regions (geo tests).
- **Competitor activity.** You have no control over what your competitors do. The effects you see in your incrementality tests could be entirely determined by the actions of your competitors and it would be hard for you to know. Let’s illustrate this with a thought experiment, shown in the image below:  
	*\- Imagine you run a go-dark (turn off spend) geo-based XP on SEA (Search Engine Advertising) Brand in certain treatment regions (yellow).  
	\- Imagine also a key competitor of yours also happens to run a go-dark (turn off spend) geo-based XP on SEA — but on SEA Competitor, with keywords based around your company’s name (blue).  
	\- Imagine finally that you both (through some very bad luck) happen to have selected many of the same treatment regions for your tests (green, treatment region for both your company and your competitor).  
	\- At the end of your test you see 0% incrementality for SEA Brand. 🥂  
	\- But how do we know that the 0% incrementality isn’t just because your key competitor stopped stealing sales from you with their own SEA ads?*
![Map of France, with geographic departments colored according to treatment group status for you or an imaginary competitor](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*JBwnpIcz8pD6tHqxoVBv1Q.png)

Map of France, with geographic departments colored according to treatment group status for you or an imaginary competitor

### Threats to external validity — simultaneous marketing experiments

In order to increase the number of XPs you can run, you may consider running multiple experiments in parallel. In this case, there are some specific threats to external validity to bear in mind.

**Lift x lift tests — cookie contamination**

Two of the most popular solutions for incrementality testing are the Conversion Lift Tests (CLTs) that [Google](https://support.google.com/google-ads/answer/12003020?hl=en) and [Meta](https://www.notion.so/148bf4cdee2944f78296514c7525f563?pvs=21) provide. The external validity of XP results obtained from running simultaneous Google and Meta CLTs could be threatened via Cookie Contamination as outlined below, however:

- Channels such as YouTube and Meta use cookies and other tracking methods to identify users and track their interactions with ads.
- When a user visits a website or uses an app that uses these platforms’ services, a cookie is placed on their device. These cookies contain unique identifiers that enable the platforms to recognize the user across different websites and sessions.
- Now, imagine you have a user who is included in both your YouTube and Meta tests. This user sees and interacts with ads on both platforms. If this user then makes a purchase, both platforms would attribute the conversion to their respective ads. This is because each platform does its own conversion tracking and doesn’t know what ads the user has seen on other platforms.
- This overlap in audience (and hence in conversions) can lead to *overestimation of the incremental impact of each platform.*
- When interpreting the results of your tests, it’s important to take this potential contamination into account and treat the results as directional (or at least fallible) rather than absolute.
![Diagram outlining the potential double-counting of conversions when using platform-based cookie data](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*7hTJeCjg-jMy3ZU69SyYkA.png)

Cookie Contamination: Double-counted Conversions

### Lift x geo tests — insufficient randomization

Alongside CLTs, one of the most popular solutions for incrementality testing is geo testing — e.g. using the [GeoLift package](https://facebookincubator.github.io/GeoLift/) from Meta. However, running CLTs at the same time as a geo test could also threaten external validity:

- Geo tests test over a population of ***everyone who could potentially sign up/generate revenue/generate sales for your business****.*
- Lift tests test over a sample of ***everyone who is a user of a given platform (e.g. Meta) that could potentially sign up/generate revenue/generate sales for your business****.*
- So, the tests are assigning treatments to groups of subjects that are not necessarily the same.
- E.g. there may be a much higher proportion of people using Meta in metropolitan regions of your market than in more rural regions.
- So, if a geo test and a CLT are run simultaneously, there may be contamination introduced.
![Diagram outlining the potential differences in randomization between conversion lift tests and geo tests](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*33VQkfvEnvYIHhGaaZgMNg.png)

Randomising over different groups of subjects

### Geo x geo tests — insufficient volume?

In theory, simultaneous geo tests are possible to run without introducing contamination or threats to external validity — e.g. via a [multi-cell test.](https://facebookincubator.github.io/GeoLift/docs/GettingStarted/MultiCellWalkthrough) In practice, this might be tricky as the volume of data you would require for your target metric would be large (unless you’re willing to greatly relax your requirements for a [Minimum Detectable Effect](https://facebookincubator.github.io/GeoLift/docs/GettingStarted/Walkthrough)). Some businesses, particularly larger ones that operate in a B2C context, might find this to be a viable approach however.

## Let’s not sweat the small stuff

In the end, the scheduling of incrementality XPs can be thought of as a **trade-off** **between** **velocity** (how many XPs you’re able to run in a given time) and (external) **validity**. There is likely to be *some* contamination of results introduced when running XPs simultaneously — but the contamination you know about might be a drop in the ocean compared to the contamination you don’t know about.

There does not seem to be a universally accepted approach regarding this trade-off. Some companies do ([Booking.com](https://partner.booking.com/en-gb/click-magazine/industry-perspectives/role-experimentation-bookingcom), [Netflix](https://netflixtechblog.com/its-all-a-bout-testing-the-netflix-experimentation-platform-4e1ca458c15) (albeit with stratified sampling)) simultaneous/high velocity XP scheduling; [some companies](https://posthog.com/product-engineers/ab-testing-examples) don’t.

### Validity/velocity tradeoff

At Qonto, we think that the benefits of velocity often outweigh the contamination that it might introduce:

- Especially, if results are viewed **directionally** rather than **definitively**.
- e.g. “ *Let’s* ***decrease budget*** *on Instagram ads as the geo test showed no more than 4% incrementality (4% Minimum Detectable Effect) ”* instead of “ *Let’s* ***cut budget*** *on Instagram completely as the geo test’s incrementality point-estimate was 0%”*

For business-critical/extremely important XPs, velocity can always be reduced:

- Such as by running an single isolated geo test which is well “cooled-down” (i.e., it hasn’t been run straight after a previous geo test which could have introduced heterogenous treatment effects across geo units).

> ***“The world is full of noise. Stop worrying about it and start running as fast as you can to outpace the rest!”*** — [Source](https://cxl.com/blog/can-you-run-multiple-ab-tests-at-the-same-time/)

## A pragmatic approach to marketing experimentation

1. **Acknowledge that all marketing XPs are flawed with limited external validity. We can only do the best we can  
	\-** Admit the flaws, but commit to making the XPs are internally valid as possible.
2. **View XP results as directional not definitive (unless there is also strong, supporting evidence)  
	\-** Re-test as much as possible.  
	\- Verify results by incorporating them into a (Bayesian) MMM: Moderately inform the priors — don’t fix them; Leave room for the model to disagree.
3. **Schedule XPs at a velocity that is palatable  
	\-** Introducing some noise/contamination into the results.  
	\- In exchange for having a much greater quantity of (directional) results.
4. **Don’t sweat the small stuff  
	\-** The contamination you may introduce from simultaneous XPs is probably a drop in the ocean compared to the contamination you don’t control.  
	\- The substantive effect of this contamination you introduce may be small anyway — unless you have reason to believe one/all of the channels in the simultaneous XPs are hugely incremental/have a massive impact.
5. **Consider how your Growth/Marketing team will leverage XP results in practical terms  
	\-** They will need ongoing, repeated sources of evidence anyway (re-tests).  
	\- They might not trust results of a single XP, no matter how internally valid it is — *and they’re probably right not to do so.  
	\-* They will (generally) use results of an XP directionally too.
6. **Reserve isolated, cooled-down XPs for business-critical questions  
	\-** Such as testing a particularly important or new channel.  
	\- Or perhaps by testing the combined results of multiple previous XPs (or validating an MMM’s overall recommendations with).
7. **Be on the lookout for new confounders, new information  
	\-** Nothing above is certain.  
	\- Be prepared to completely change your approach if new information comes to light.

*Want to read more? Here’s the full Marketing Measurement series:*

**Marketing Mix Modeling:**

- [Part I: Getting started](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-337b8af11471) *(released 21 May 2024)*
- [Part II: Adstock and saturation](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-82e82c995b39) *(released 22 May 2024)*
- [Part III: Bayes’ Theorem & priors](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-05d28a2cfa18) *(released 23 May 2024)*
- [Part IV: Inputs for a Bayesian model](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-69bc3101d06d) *(released 27 May 2024)*
- [Part V: Specifying a Bayesian model with PyMC](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-f214ba550968) *(released 5 June 2024)*
- [Part VI: MLOps](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-part-vi-7bb9805076ba) *(released 14 June 2024)*

**Incrementality testing:**

- [How to invest better in acquisition channels? A $1 million question for Data Science](https://medium.com/qonto-way/how-to-invest-better-in-acquisition-channels-a-1-million-question-for-data-science-591c82b3e0e4) *(released 4 January 2023)*
- [Getting the best of both worlds in marketing incrementality tests: rapid testing and trusted results](https://medium.com/qonto-way/getting-the-best-of-both-worlds-in-marketing-incrementality-tests-rapid-testing-and-trusted-58243204fc80) *(released 13 November 2024)*
- Incrementality test scheduling: velocity vs. validity

## 🔗 References

- [Comprehensive Guide on XP Scheduling, Prioritising and Implementing](https://support.optimizely.com/hc/en-us/categories/4410287901197-Experimentation)
- [Can You Run Multiple A/B Tests at the Same Time?](https://cxl.com/blog/can-you-run-multiple-ab-tests-at-the-same-time/)
- [AB Testing: When Tests Collide](https://blog.conductrics.com/ab-testing-when-tests-collide-2/)
- [Experimentation at Netflix](https://netflixtechblog.com/its-all-a-bout-testing-the-netflix-experimentation-platform-4e1ca458c15)
- [Experimentation at Booking.com](https://partner.booking.com/en-gb/click-magazine/industry-perspectives/role-experimentation-bookingcom)
- [Experimentation at Uber](https://www.uber.com/en-FR/blog/supercharging-a-b-testing-at-uber/)
- [Experimentation at Monzo](https://monzo.com/blog/2019/07/31/how-we-experiment-at-monzo)
- [How YC’s biggest startups run A/B tests (with examples)](https://posthog.com/product-engineers/ab-testing-examples)
- [Double counting + attribution windows: Some problems with conversion lift testing](https://mackgrenfell.com/facebook-ads/conversion-lift-testing)

## About Qonto

Qonto makes it easy for SMEs and freelancers to manage day-to-day banking, thanks to an online business account that’s stacked with invoicing, bookkeeping and spend management tools.

Created in 2016 by Alexandre Prot and Steve Anavi, Qonto now operates in 4 European markets (France, Germany, Italy, and Spain) serving 500,000 customers, and employs more than 1,600 people.

Since its creation, Qonto has raised €622 million from well-established investors. Qonto is one of France’s most highly valued scale-ups and has been listed in the Next40 index, bringing together future global tech leaders, since 2021.

Interested in joining a challenging and game-changing company? Take a look at our [open positions](https://qonto.com/en/careers).

Illustrations by Pierre-Alain Dubois[Last published 2 days ago](https://medium.com/qonto-way/the-pmm-busywork-trap-and-the-ai-operating-system-i-built-to-escape-it-8e41a490da87?source=post_page---post_publication_info--f7525b713b4a---------------------------------------)

Stories and learnings from the team behind Qonto