---
title: "Marketing Measurement series: Marketing Mix Modeling at Qonto"
source: "https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-337b8af11471"
author:
  - "[[Louis Magowan]]"
published: 2024-05-21
created: 2026-04-17
description: "Marketing Measurement series: Marketing Mix Modeling at Qonto | Part I Getting started Hello and welcome to the inaugural article in Qonto’s Marketing Measurement series. This series will no doubt …"
tags:
  - "clippings"
---
## [The Qonto Way](https://medium.com/qonto-way?source=post_page---publication_nav-a9390fa3f292-337b8af11471---------------------------------------)

[![The Qonto Way](https://miro.medium.com/v2/resize:fill:38:38/1*62qiMixIqD-UODkXVUxPOA.png)](https://medium.com/qonto-way?source=post_page---post_publication_sidebar-a9390fa3f292-337b8af11471---------------------------------------)

Stories and learnings from the team behind Qonto

## Getting started

![An MMM whirlpool taking in various ad channels](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*Yxqt0kwxL63wJevHP3081A.png)

An MMM whirlpool taking in various ad channels

Hello and welcome to the inaugural article in Qonto’s **Marketing Measurement series**. This series will no doubt grow and change format over time, but generally it will be comprised of articles on popular marketing science topics, such as incrementality testing or Marketing Mix Modeling, written from a data science perspective.

While these articles will provide a somewhat technical treatment of the topics, they aim to contain information that is relevant and engaging to a broad audience of marketing professionals. These articles are not intended to be definitive ‘sources of truth’ on the topics, but rather an insight into how Qonto has chosen to approach them. Marketing science is an ambiguous, opinionated field and so we hope that this series will not only be educational, but that it will provoke discussion. In this spirit, please feel free to add your opinions, agreements, or disagreements to the comments on any article in the series.

**The Marketing Measurement series includes:**

**Marketing Mix Modeling at Qonto:**

- Part I: Getting started
- [Part II: Adstock and saturation](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-82e82c995b39)
- [Part III: Bayes’ Theorem & priors](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-05d28a2cfa18)
- [Part IV: Inputs for a Bayesian model](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-69bc3101d06d)
- [Part V: Specifying a Bayesian model with PyMC](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-f214ba550968)
- [Part VI: MLOps](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-part-vi-7bb9805076ba)

**Incrementality testing:**

- [How to invest better in acquisition channels? A $1 million question for Data Science](https://medium.com/qonto-way/how-to-invest-better-in-acquisition-channels-a-1-million-question-for-data-science-591c82b3e0e4)
- [Incrementality test scheduling: velocity vs. validity](https://medium.com/qonto-way/marketing-measurement-series-incrementality-test-scheduling-f7525b713b4a)
- [Getting the best of both worlds in marketing incrementality tests: rapid testing and trusted results](https://medium.com/qonto-way/getting-the-best-of-both-worlds-in-marketing-incrementality-tests-rapid-testing-and-trusted-58243204fc80)

**The outline for this article is as follows:**

- Introduction to Marketing Mix Modeling (MMM)
- MMM’s role in the marketing measurement stack
- MMM: the consultancy route  
	— Pros & cons  
	— Getting your money’s worth
- MMM: the in-house route  
	— Pros & cons  
	— Pre-requisites & upskilling
- The state of open source

## Introduction to Marketing Mix Modeling (MMM)

Marketing Mix Models (also called Media Mix Models, or MMMs) are holistic, econometric models that measure the incremental impact of marketing and non-marketing activities on a given KPI (Key Performance Indicator), such as Sales or Revenue. MMMs have existed [since the 1950s](https://www.guillaumenicaise.com/wp-content/uploads/2013/10/Borden-1984_The-concept-of-marketing-mix.pdf) but have been growing in popularity in recent years, due to their privacy-safe nature. MMMs rely on aggregated data rather than consumer-level data and so require no Personally Identifiable Information (PII) to be run. Crucially, these models can be used to give insights into the efficiencies of offline marketing channels (such as TV, Out-of-Home, or Radio) which are typically hard channels to measure, given their inherent lack of data.

**They can be used to answer questions like:**

- *What’s my overall ROI? What’s my ROI for a particular channel?*
- *How should I allocate budget across my different channels in order to maximize efficiency?*
- *What are the key drivers of my sales?*

MMM’s marketing input data can be whatever investment or exposure metrics you would like insights on, and the non-marketing input data can be whatever macro/control factors that you believe may impact your chosen KPI.

![Diagram showing the marketing inputs needed for MMM and how they are used to model a chosen target metric](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*-VrGjCjHeKd3G3nfyXMYTQ.png)

Diagram showing the marketing inputs needed for MMM and how they are used to model a chosen target metric

## MMM’s role in the marketing measurement stack

MMMs work best as a component of a broader marketing measurement stack, complementing attribution models and incrementality experiments. Each of these tools has its own strengths and weaknesses and will be more or less appropriate to use in certain contexts.

- **Incrementality experiments** measure the causal impact of specific marketing actions by comparing outcomes between a treated group exposed to the action and a control group that isn’t. They tend to give the most conservative estimates of the efficiency of a channel.
- **Attribution models** look at the customer journey, assigning credit to different touch-points that contributed to a conversion, offering a highly granular, real-time view of performance. They often give (depending on your choice of attribution model) the most generous estimates of the efficiency of a channel.
- **MMMs** give a macro-level view of marketing effectiveness over time. As a rule of thumb, its efficiency estimates should fall between the bounds provided by attribution models and incrementality experiments.

An abridged outline of how these tools can be used together is shown below:

![Flow diagram showing how attribution models, incrementality tests, and MMM all work together and combine](https://miro.medium.com/v2/resize:fit:2000/format:webp/1*I7oLncnvpxOfW3iQg3tStg.png)

Flow diagram showing how attribution models, incrementality tests, and MMM all work together and combine

## MMM: the consultancy route

### Pros & cons

MMMs are a complex topic requiring considerable technical and domain expertise to be implemented successfully. A large number of consultancies/vendors exist that can build and deliver MMMs for you. Depending on the needs and structure of your company, this may be the most appropriate option for you.

![Table weighing up the pros and cons of using a consultancy for MMM](https://miro.medium.com/v2/resize:fit:2000/format:webp/1*6GedUR6_Jko6lEgOECkpRw.png)

Table weighing up the pros and cons of using a consultancy for MMM

### Getting your money’s worth

If you do decide to go down the consultancy route, there are a few tips you can bear in mind to ensure you get your money’s worth from them and end up with an MMM that is as trustworthy as possible.

1. **Demand confidence intervals/credible intervals** for everything. You may not receive these by default, but they are an indispensable insight into the uncertainty of the model results your consultancy delivers.
2. **Demand out-of-sample/test validation.** Make sure the MMM you receive isn’t just evaluated on the data it was trained with. Given the ratio of features-to-data typically used in MMM, the risk of overfitting is high — test-set validation mitigates this risk and is a good way of evaluating how the MMM will generalize to new data.
3. **Don’t pay too much attention to R-Squared values.** The R-Squared metric indicates the proportion of variance of your KPI that is explained by the MMM. However, this can easily be increased by just adding more variables (in particular control variables) to the MMM. The R-Squared value is useful to know, but should definitely be viewed alongside genuine error metrics such as Root-Mean-Square-Error (RMSE) etc. It’s even better if these are test-set values. 😉
4. **Demand model evaluation on simulated data.** This [really interesting Google article](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/45998.pdf) outlines how you should consider asking your consultancy to do a parameter recovery exercise as part of your Statement of Work (SoW). In other words, you create a simulated dataset where you know the ground truth (perhaps using [this tool](https://github.com/google/amss) created by Google) and ask them to model over that dataset. You should then share your data generation process with them and invite them to explain why their model did or didn’t recover the ground truth well. Going through this process will help to keep your MMM vendor honest, build trust in their methods and prevent the delivery of black-box insights. It is an ambitious demand, however, and may incur additional costs to be met (or just be outright refused by your vendor). An alternative solution could be to provide them with your real data, but without the column names/telling them which data belongs to which channel and then share the names after they build their model.

## MMM: the in-house route

Using a consultancy is of course not the only option for producing MMMs for your company. Building them yourself is also possible.

### Pros & cons

![Table comparing the pros and cons of doing MMM in-house](https://miro.medium.com/v2/resize:fit:2000/format:webp/1*n7pIDO6QLACrZIE1P3MoAg.png)

Table comparing the pros and cons of doing MMM in-house

### Pre-requisites

MMM is a large and complex project. Doing it in-house may not be sensible for very young companies, or companies with nascent data teams.

Some pre-requisites you should try to satisfy before undertaking the project are provided below:

**Marketing measurement maturity**

- Be able to point to the data you want to model within a dashboard.  
	— *Data should be clean, ready to use, and well-understood in your company.*
- Be successfully leveraging at least one of the following:  
	*— Incrementality experiments → the more you’ve conducted, the more you’ll be able to check/calibrate your MMM with.  
	— Attribution model → multi-touch or data-driven if possible.*

**Data personnel/resources**

- Have 1–2 FTE data professionals available for the project.  
	*— These FTEs can be whatever combination of data scientists, data analysts, analytics engineers, etc. makes sense for your business.  
	— These FTEs will need to have some marketing experience/marketing science theory.  
	— The exact combination of resource requirements are likely to change over the project lifecycle as the project develops.*
- Be aware that once the project is undertaken, the resource requirements are likely to be somewhat permanent.  
	*— There are of course opportunities to scale the project and make its delivery more efficient.  
	— However, the benefits of scaling could be offset by the need to keep your MMM up to date with the latest research, by the need to build additional features/improvements to your MMM, or by the need to run MMM more frequently or in more markets.*

**Stakeholder buy-in**

- Ensure everyone involved understands what MMM is and isn’t and how it should be used.  
	\- *MMM is not a panacea — it won’t fix all of your marketing problems.*
- Ensure everyone involved is comfortable with ambiguity.  
	*\- You’ll never know with 100% certainty whether your model is correct.*

### Upskilling

Unless the data professionals you assign to your MMM project already have experience in the area and have been working closely with your marketing team, upskilling will most likely be required.

To be able to model a channel well in an MMM, your data professionals will have to have a good understanding of what it is, how it works and any business-specific context associated with it — like a miniature onboarding to that channel. Depending on how many channels your company advertises with, this step can be time-consuming.

Doing MMM well will also require considerable marketing science theory and MMM-specific technical knowledge.

Some of the best resources we’ve found for this are listed below:

- [MMM Slack Workspace](https://www.mmmhub.org/slack) — full of MMM enthusiasts and experts (many of whom also post interesting resources on LinkedIn).
- [An Analyst’s Guide to MMM](https://facebookexperimental.github.io/Robyn/docs/analysts-guide-to-MMM/) by Meta — the best entry-point document to MMM in our opinion.
- [Bayesian Methods for Media Mix Modeling with Carryover and Shape Effects](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/46001.pdf) by Google — the seminal paper for modern-day MMMs, cited by many other articles and repositories around MMM.
- We’ve also gathered some of our other favorite resources (with short descriptions for them) into this [Notion database](https://qonto.notion.site/MMM-Upskilling-f107b7d66c4f496dbb4676114a26e780)**.**

**One warning:** almost all of the content and research on MMM that is available online is produced by actors with powerful incentives to write about the topic in a certain way. Consider these incentives carefully when reading consultancy white papers or articles produced by Google/Meta. Little of this content has undergone broad peer-review. Even the authors of this article have incentives, which we leave as an exercise for the reader to guess at. 😉

## The state of open source

Open-source MMM is a rapidly developing field. You should carefully consider the needs of your stakeholders before committing to a solution. Bayesian flavors of MMMs are considered the state-of-the-art, but it’s also possible to do MMM with just a [simple linear regression](https://getrecast.com/bayesian-methods-for-mmm/) (though we wouldn’t recommend this). A list of other flavors of MMM can be found on [this page of Meta’s Blueprint course](https://www.facebookblueprint.com/student/path/253121/activity/469852#/page/633f6301422f820a22ceb359) on MMM (near the bottom of the page).

Indeed, Qonto has experimented with several solutions and a quick review (from our PoV, other businesses may have other needs and give different appraisals) of them can be found below.

![Table comparing various MMM open-source solutions across dimensions of Documentation , Community, Ease of Use, Breadth of Features and Repo Activity](https://miro.medium.com/v2/resize:fit:2000/format:webp/1*2GE7eV37NwCM0AwHYQUZ8A.png)

Table comparing various MMM open-source solutions across dimensions of Documentation, Community, Ease of Use, Breadth of Features and Repo Activity

Whatever option you decide to go with, it’ll be a real learning experience (for both marketing and data stakeholders). MMM is an exciting, rapidly developing field. Best of luck MMM-ing!

## About Qonto

Qonto makes it easy for SMEs and freelancers to manage day-to-day banking, thanks to an online business account that’s stacked with invoicing, bookkeeping and spend management tools.

Created in 2016 by Alexandre Prot and Steve Anavi, Qonto now operates in 4 European markets (France, Germany, Italy, and Spain) serving 450,000 customers, and employs more than 1,400 people.

Since its creation, Qonto has raised €622 million from well-established investors. Qonto is one of France’s most highly valued scale-ups and has been listed in the Next40 index, bringing together future global tech leaders, since 2021.

Interested in joining a challenging and game-changing company? Take a look at our [open positions](https://qonto.com/en/careers).

Illustration by Margaux Giron and Karina Pasechka.[Last published 2 days ago](https://medium.com/qonto-way/the-pmm-busywork-trap-and-the-ai-operating-system-i-built-to-escape-it-8e41a490da87?source=post_page---post_publication_info--337b8af11471---------------------------------------)

Stories and learnings from the team behind Qonto

[View list](https://medium.com/@kakasarnold/list/reading-list?source=post_page---list_recirc--337b8af11471-----------predefined%3A2571ed97cd46%3AREADING_LIST----------------------------)