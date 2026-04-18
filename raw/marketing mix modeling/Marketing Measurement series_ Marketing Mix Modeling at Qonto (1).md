---
title: "Marketing Measurement series: Marketing Mix Modeling at Qonto"
source: "https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-82e82c995b39"
author:
  - "[[Louis Magowan]]"
published: 2024-05-22
created: 2026-04-17
description: "Marketing Measurement series: Marketing Mix Modeling at Qonto | Part II Adstock and saturation In this second article in Qonto’s Marketing Measurement series we’ll be diving into two interesting …"
tags:
  - "clippings"
---
## [The Qonto Way](https://medium.com/qonto-way?source=post_page---publication_nav-a9390fa3f292-82e82c995b39---------------------------------------)

[![The Qonto Way](https://miro.medium.com/v2/resize:fill:76:76/1*62qiMixIqD-UODkXVUxPOA.png)](https://medium.com/qonto-way?source=post_page---post_publication_sidebar-a9390fa3f292-82e82c995b39---------------------------------------)

Stories and learnings from the team behind Qonto

## Adstock and saturation

![A whirlpool of model inputs being sucked into an MMM, with MMM graphs around the outside](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*vcl_aqUYDNcOzznBcvUIEg.png)

A whirlpool of model inputs being sucked into an MMM, with MMM graphs around the outside

In this second article in Qonto’s **Marketing Measurement series** we’ll be diving into two interesting and important concepts in marketing science theory — adstock and saturation. These concepts help us link the psychology of advertising with the realities of media buying. They can be thought of as pre-processing functions or transformations that allow us to work with our marketing data in more sensible ways. They are fundamental to Marketing Mix Models. An example of how they’re applied in an MMM regression equation is given below (t=a time t; alpha=intercept):

![Regression equation for MMM, adstocking first and then saturating](https://miro.medium.com/v2/resize:fit:4800/format:webp/1*P-ubli5HVrLUq8w5CGUaeg.png)

MMM Regression Equation

If that opening paragraph was a bit highfalutin for your tastes, or you don’t want to have to read the full article, then feel free to just get stuck into these concepts by playing about with them in the [Streamlit demo app](https://mmm-variable-transformations.streamlit.app/) embedded below the article outline (or even better, open it in a new tab).

**The outline for this article is as follows:**

- Adstock overview:  
	\- Time delay  
	\- Time decay  
	\- Leveraging adstock
- Saturation overview:  
	\- Saturation in theory  
	\- Saturation in practice
- Bringing it all together
- Bonus section: dimension reduction

## Adstock overview

Adstock encapsulates two important marketing effects: time delay and time decay. These concepts can be quite abstract though, so the reader is strongly encouraged to play around with the functions and plots in the [Streamlit app](https://mmm-variable-transformations.streamlit.app/) to gain an intuitive sense of how adstock works.

![Calendar illustrating how investing in a channel can have a delayed and decaying effect on the ROI you get from that channel](https://miro.medium.com/v2/resize:fit:2000/format:webp/1*waiv2R7mF1nAGnECXA6OLQ.png)

Calendar illustrating how investing in a channel can have a delayed and decaying effect on the ROI you get from that channel

### Time delay

Also known as ***lag effect****,* this refers to the delay between investment on a channel or exposure (impressions, Gross Rating Points, clicks etc) gained from it and the resulting increase in your target KPI (sales/revenue/conversions etc.).

It’s not always the case that the largest increase in your target KPI coincides with the time of your investment. For example, if you happened to see an ad on TV for a new car, it’s unlikely you would immediately go out and buy that car as soon as the ad finishes. But, the ad may influence your decision to buy a new car at some point in the future.

Depending on your choice of adstock function, you will have to make a decision on when you think the **peak of your adstock** should be:

- **Immediate peak:** The effects of the ad are at their ***strongest*** the ***instant (relative to your unit of time)*** that it is being seen (e.g. a bottom-of-funnel, digital channel / last-click touchpoint that drives conversions directly).
- **Not immediate peak:** The effects of the ad are at their ***strongest*** ***some time*** (a day, a week, even months) ***after*** it has been seen (e.g. TV and radio ads).

![Geometric Adstock decayed over weeks, with no delay effect. Delayed Geometric Adstock decayed over weeks, with a delay effect](https://miro.medium.com/v2/resize:fit:4800/format:webp/1*8ctuGuVj5jOc7pHiF1sSyQ.png)

Geometric Adstock decayed over weeks, with no delay effect. Delayed Geometric Adstock decayed over weeks, with a delay effect

### Time decay

Also known as ***memory effect*** or ***carryover effect,*** this refers to the fact that once someone has seen an ad, they may not forget it immediately and may decide to buy/convert/sign up some time after having seen the ad. Similarly, people will not remember an ad perfectly forever — we expect their memory of an ad to decay and decay, until they’ve completely forgotten about it.

Depending on your choice of adstock function, you will have to make a decision on what **type of decay you think your adstock** should be:

- **Fixed-rate decay:** this assumes that for a cohort of people who were exposed to an ad, their aggregate ‘memory’ of it decays at the same rate each day — until they’ve completely forgotten about it.
- **Time-varying/flexible decay:** this assumes that for a cohort of people who were exposed to an ad, their aggregate ‘memory’ of it decays at a rate that changes depending on how long it’s been since they first saw the ad — until they’ve completely forgotten about it.

![Geometric Adstock decayed over weeks, with fixed decay. Weibull CDF Adstock decayed over weeks, with flexible decay.](https://miro.medium.com/v2/resize:fit:4800/format:webp/1*S_xQN_ImfZIKb--5kJFCIQ.png)

Geometric Adstock decayed over weeks, with fixed decay. Weibull CDF Adstock decayed over weeks, with flexible decay.

### Leveraging adstock

As the app demonstrates, a variety of functions exist for modeling adstock. The decision of which to use and what parameters to pass to it (or how you optimize its parameters) will likely be a combination of both statistical and business knowledge. On one hand, you may want to use in your MMM whichever adstock it is that produces the smallest model errors. However, you also don’t want to be producing models that make assumptions that are far removed from marketing science theory and common sense.

For example, with a channel such as TV it is reasonable to expect that there might be some delay between seeing an ad and converting/buying. Similarly, we might expect the memory of that TV ad to decay more slowly than, for example, a Facebook ad a person saw while idly scrolling through their newsfeed.

Indeed, there are no simple, one-size-fits-all answers here. Literature review and studying marketing science theory will help, but each business and how their ad channels work will be different. The best course is to work closely with your marketing stakeholders and ensure your adstock decisions align with both their understanding of the channels and marketing science theory. Importantly, it should also be appreciated that while these techniques will help you with modeling short- and medium-term advertising effects, they are most likely not able to capture long-term advertising effects. For this other MMM techniques would be required, such as the [nested model approach outlined by Google](https://www.thinkwithgoogle.com/_qs/documents/17950/The_MMM_Handbook.pdf).

**Hot Tip #1:** for first-time MMMers, you may want to consider using a simpler adstock function — like geometric adstock. It’s the easiest to understand and explain, and leaves you with the fewest parameters to optimize in your MMM. Weibull PDF adstock is probably the most versatile, being able to model both fixed delay and flexible decay, but it can be unintuitive and is trickier to optimize (more parameters). It may be able to produce stronger MMMs, but we wouldn’t recommend it for novice practitioners.

**Hot Tip #2:** when considering how to model adstock for your business, bear in mind the price/type of product that you are offering. Businesses that present a major commitment/cost to your customers (e.g. selling cars) may well have a more pronounced delay than businesses with minor commitments/costs (e.g. buying a t-shirt).

## Saturation overview

Saturation in marketing science refers to the fact that the relationship between investment on a particular ad channel and the target KPI (conversions/sales/revenue) it generates might not always be linear or straightforward. For example, we might see **diminishing returns on investment,** such that each additional unit of advertising increases the KPI, but at a declining rate.

Stated differently:

- an increase in advertising spend could lead to a proportional increase in the desired outcome (revenue, conversions, contracts signed),
- but, beyond a certain threshold, the effect saturates and further advertising investment might not yield significant additional benefits.

![A response curve showing saturation and optimal spend zones within a particular channel](https://miro.medium.com/v2/resize:fit:2000/format:webp/1*1MvpeIl3_zyPMxa9F_foeg.png)

A response curve showing saturation and optimal spend zones within a particular channel

### Saturation in theory

Broadly speaking, there are **4 types of saturation curve (see** [**here**](https://www.ashokcharan.com/Marketing-Analytics/~mx-mmm-sales-response-function.php#gsc.tab=0) **for a more in-depth discussion):**

![Graph showing the 4 most common shapes of response curve which are mentioned after](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*rLPVv7bDpEd4tqUejEP9ew.png)

🔗 Inspired by this article

**1\. Linear**

- A linear model of saturation represents **constant** **returns to scale**.
- This may not make sense though, as it suggests conversions/revenue/sales could increase infinitely.

**2\. Concave**

- A concave model of saturation represents **diminishing** **returns to scale**.
- This aligns well with marketing science theory and is one of the most common forms used in MMM.

**3\. Concave**

- A convex model of saturation represents **increasing** **returns to scale**.
- This is almost never used in MMM as it’s a poor fit with marketing science theory → it implies that returns increase exponentially as marketing activity increases.
- However, [some have suggested](https://getrecast.com/diminishing-returns/) it might be appropriate for a channel like SEO in which value could grow and compound over time.

**4\. S-shaped**

- An S-shaped model of saturation represents **variable returns to scale**, with increasing returns at low levels of marketing activity and diminishing returns at high levels.
- This is another popular form used in MMM, but [some have noted](https://sellforte.com/blog/advertising-response-curve/) that they can be hard to identify empirically — since they often require a lot of variance to be modeled.
- They do introduce an interesting concept that other forms don’t capture — **threshold**.
- This is the idea that you have to reach some minimum amount of marketing activity before you start to see ***any*** returns whatsoever.
- Depending on your business and channel, you may or may not consider this important.

### Saturation in practice

As was the case with adstock, the decision over which saturation type to employ won’t be easy. It, too, will likely have to be based on both statistical and business knowledge provided by your marketing stakeholders. Some highly efficient channels might appear to be linear at first, but this could be because you’ve never spent very much on them before.

Within the [app](https://mmm-variable-transformations.streamlit.app/Saturation) you can see several of the possible functions you can use to represent your saturation with. For example, the Hill function could be used if you believe your channel should have an S-shaped response, whereas a logistic function might be appropriate if you think it behaves in a concave way.

## Bringing it all together

One thing not discussed yet is the order in which to apply these transformations. You could saturate and then adstock your channel’s data, or do the reverse.

![Regression equation for MMM, saturating first and then adstocking](https://miro.medium.com/v2/resize:fit:4800/format:webp/1*J1i30X3p-3Kbtm1c5gJ37Q.png)

This time, the order of transformations is reversed: Saturate and then adstock.

This is another decision that isn’t straightforward. The [seminal Google MMM paper](https://research.google/pubs/bayesian-methods-for-media-mix-modeling-with-carryover-and-shape-effects/) *“Bayesian Methods for Media Mix Modeling with Carryover and Shape Effects”* outlines one approach though:

- For channels where the media spend is heavily concentrated in some single time periods with an on-and-off pattern — they recommend doing the **saturation transformation** and then **adstock transformation.**
- For channels where media spend in each period is small relative to cumulative spends, then they recommend doing **adstock transformation** and then **saturation transformation.**

## Bonus section: dimension reduction

While not an adstock or saturation concept, dimension reduction is a pre-processing technique that can be useful when building MMMs. MMM projects often have limited data, correlated variables, and datasets that are low signal-to-noise ([Google, 2017](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/45998.pdf)). They may also contain a large number of macro or control variables (e.g. to capture promotions, price increases, school holidays, COVID etc). Furthermore, many of these variables may be highly sparse, e.g. zeros for all the dates after COVID lockdowns ended.

Dimension reduction can help here. It can improve [model parsimony](https://www.statisticshowto.com/parsimonious-model/), by reducing the number of control features you feed into your MMM — while retaining as much of the information that the original variables contained as possible. Additionally, it might transform sparse/categorical features into continuous ones, which might be easier for your MMM to work with. The tradeoff, however, is that your dimension-reduced features will be harder to interpret results for — but most likely your stakeholders will only be interested in the marketing features/unreduced features anyway.

There are a multitude of techniques available for dimension reduction, each with their own advantages and disadvantages. You can experiment and see which one works best for you.

*Want to read more? Here’s the full Marketing Measurement series:*

**Marketing Mix Modeling:**

- [Part I: Getting started](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-337b8af11471) *(released 21 May 2024)*
- Part II: Adstock and saturation
- [Part III: Bayes’ Theorem & priors](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-05d28a2cfa18) *(released 23 May 2024)*
- [Part IV: Inputs for a Bayesian model](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-69bc3101d06d) *(released 27 May 2024)*
- [Part V: Specifying a Bayesian model with PyMC](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-f214ba550968) *(released 5 June 2024)*
- [Part VI: MLOps](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-part-vi-7bb9805076ba) *(released 14 June 2024)*

**Incrementality testing:**

- [How to invest better in acquisition channels? A $1 million question for Data Science](https://medium.com/qonto-way/how-to-invest-better-in-acquisition-channels-a-1-million-question-for-data-science-591c82b3e0e4) *(released 4 January 2023)*
- [Incrementality test scheduling: velocity vs. validity](https://medium.com/qonto-way/marketing-measurement-series-incrementality-test-scheduling-f7525b713b4a) (*released 19 June 2024)*
- [Getting the best of both worlds in marketing incrementality tests: rapid testing and trusted results](https://medium.com/qonto-way/getting-the-best-of-both-worlds-in-marketing-incrementality-tests-rapid-testing-and-trusted-58243204fc80) *(released 13 November 2024)*

**About Qonto**

Qonto makes it easy for SMEs and freelancers to manage day-to-day banking, thanks to an online business account that’s stacked with invoicing, bookkeeping and spend management tools.

Created in 2016 by Alexandre Prot and Steve Anavi, Qonto now operates in 4 European markets (France, Germany, Italy, and Spain) serving 450,000 customers, and employs more than 1,400 people.

Since its creation, Qonto has raised €622 million from well-established investors. Qonto is one of France’s most highly valued scale-ups and has been listed in the Next40 index, bringing together future global tech leaders, since 2021.

Interested in joining a challenging and game-changing company? Take a look at our [open positions](https://qonto.com/en/careers).

Illustration by Margaux Giron and Karina Pasechka.[Last published 2 days ago](https://medium.com/qonto-way/the-pmm-busywork-trap-and-the-ai-operating-system-i-built-to-escape-it-8e41a490da87?source=post_page---post_publication_info--82e82c995b39---------------------------------------)

Stories and learnings from the team behind Qonto