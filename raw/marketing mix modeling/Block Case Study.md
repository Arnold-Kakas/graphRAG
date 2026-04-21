---
title: "Block Case Study"
source: "https://getrecast.com/block-case-study/"
author:
published: 2025-12-10
created: 2026-04-20
description: "How Block transformed marketing measurement and planning across Square, Cash App, and Afterpay with Recast MMM."
tags:
  - "clippings"
---
**Case Studies > Block**

For Block — the parent company of Square, Cash App, and Afterpay — marketing measurement presented a uniquely complex challenge. They have multiple business units, customer journeys ranging from instant mobile payments to enterprise B2B sales cycles, and international operations with fundamentally different market dynamics.

In 2023, Block began transitioning to Recast. What started as an engagement with Square US has since expanded across more of the organization — transforming how Block measures, plans, and optimizes marketing spend across its portfolio of businesses.

---

![](https://getrecast.com/wp-content/uploads/2025/12/block-recast-v5-scaled.png%20,https://getrecast.com/wp-content/uploads/2025/12/block-recast-v5-scaled.png)

### Contents:

- [Block’s Enterprise Challenge](#block-enterprise-challenge)
- [Square US: The Pioneer Implementation](#square-us)
- [Square International: Scaling Across Markets](#square-int)
- [Cash App: A Data Scientist’s Approach to MMM Validation](#cash-app)
- [Block’s Unified Platform Advantage](#block-unified-platform)

---

When [Michael Wexler](https://www.linkedin.com/in/michaelwexler/), Head of Global Go To Market (GTM) Data at Square, evaluated his company’s marketing measurement capabilities in 2023, he faced a challenge familiar to many enterprise organizations: multiple business units using different vendors and approaches, producing insights that were both expensive and too outdated to be actionable.

[Block](https://block.xyz/) – the parent company of [Square](https://squareup.com/us/en), [Cash App](https://cash.app/), and [Afterpay](https://www.afterpay.com/en-US) (along with [Tidal](https://tidal.com/), [Proto](https://proto.xyz/), and [Bitkey](https://bitkey.world/)) – presents an extremely complex marketing measurement challenge. They have multiple customer journeys ranging from consumer instant mobile payments to enterprise B2B sales cycles, international operations, and both self-serve and sales-led go to market motions, across offline, web, and mobile approaches. This meant Block needed a measurement approach that could handle this complexity while remaining dynamic enough to guide in-flight media optimization decisions.

“I want to focus on (marketing levers) that we have control over, which is the media spend and the targeting and the choices there,” Wexler reflected on the vendor evaluation process. “Measuring other things is great, but they’re not necessarily things we’re going to take action on.”

This philosophy would help guide Block’s transition from legacy media mix modeling (MMM) vendors to Recast, ultimately transforming how the company measures, plans, and optimizes marketing spend across its portfolio of businesses.

### Block’s Enterprise Challenge

Block’s measurement challenges stem from both the company’s scale and its structure. Square US had been using a traditional enterprise MMM vendor, while Afterpay brought their own legacy vendor from before their acquisition by Block. Further complicating things, Square’s international markets were forced to rely on learnings from US models despite fundamental differences in their business dynamics.

The limitations of using disparate, traditional MMM approaches became increasingly apparent. Square’s legacy vendor operated on a biannual refresh cycle, meaning marketing investments made in January wouldn’t yield measurement insights until much later in the year.

“A lot of times we weren’t seeing the results of our January investment reflected in the MMM system until September or October,” explained [Ling Chiao](https://www.linkedin.com/in/lingchiao/), who has led marketing analytics at Square US for almost seven years. “So (the refresh cadence) was something that was really important to us as we onboarded with Recast.”

![](https://getrecast.com/wp-content/uploads/2025/12/image.png)

Square’s international markets faced their own challenges. [Andy Crowe](https://www.linkedin.com/in/andrewjohncrowe/), Square’s International GTM Insights Lead, described this in saying: “We’ve wanted MMM for years, and outside the US, we’d been somewhat at a disadvantage by not having that, both in terms of optimizing our investment, but also advocating for additional spend and defending the efficiency of that spend.”

The cost of expanding traditional MMM to each international market was prohibitively expensive. Teams were forced to use US models as rough proxies, despite knowing that markets like the UK and Australia had different local media landscapes, consumer behaviors, and even product offerings.

Beyond speed and cost, there was also a philosophical disconnect. Traditional MMM vendors focused heavily on decomposing baseline conversions – using econometric models to explain why organic demand fluctuated based on factors like competitor spending or macroeconomic conditions. While intellectually interesting, these insights didn’t help marketing teams decide where to allocate next quarter’s budget.

Recast offered a fundamentally different approach: a forward-looking, time-varying Bayesian model that focused on the levers marketing teams could actually control and how they change over time. Instead of just explaining what happened, Recast made weekly forecasts that could be validated against actual results – proving the model truly understood the causal relationships driving each of Block’s businesses with a rapid feedback loop. Critically, this allowed the team to focus on making changes that would improve performance in the future, not just attempt to explain what happened in the past.

### Why Recast: Speed, Transparency, and Focus on What Matters

When Block began evaluating alternatives, three key differentiators set Recast apart from other vendors: the speed at which insights could be retrieved, ongoing transparency into model performance, and a focus on actionable marketing levers.

“Recast’s weekly refresh is far faster than any of the other players, but can also be faster than we might be able to react to it,” Michael Wexler noted. “But what it does allow is for us to see a problem forming and immediately start taking action.”

The switch to Recast was about more than getting insights faster – it was about fundamentally changing how marketing teams operate. Instead of waiting months to understand incremental media performance, teams could spot trends within weeks, run different scenario analyses and evaluate potential optimization flights, then adjust accordingly. Mid-month course corrections became possible. Quarterly planning could incorporate the latest business results rather than data from two quarters ago.

Another key differentiator was Recast’s transparency into model assumptions and diagnostics. Where traditional vendors operated as black boxes, providing outputs with little visibility into the underlying methodology, Recast exposed everything – model diagnostics, [model methodology](https://docs.getrecast.com/docs/?l=en), uncertainty intervals, and model performance metrics like weekly [out-of-sample forecast accuracy checks](https://getrecast.com/recast-model-configuration-process/).

“Our other vendor would give us a set of metrics that they thought we should see but they kind of buried the real details beneath a wrapper,” Wexler explained. “Part of (our trust-building) was leveraging all the work Recast does with model diagnostics.”

![](https://getrecast.com/wp-content/uploads/2025/12/image-3.png)

A third differentiator was Recast’s focus on controllable marketing factors. While Recast does estimate baseline conversions and incorporate external factors as context variables, the platform’s suite of forward-looking tools are focused on helping marketers optimize what they can actually influence: their media spend and targeting decisions such as their mix of platform placement, audience targeting, and creative delivery.

## Square US: The Pioneer Implementation

Square US became the first Block entity to transition to Recast, but the move required careful navigation. With over a decade of marketing measurement maturity, Square had developed sophisticated approaches focused on triangulation – combining MMM, multi-touch attribution (MTA), and incrementality testing to get a complete picture of marketing performance.

“We know that no measurement system is perfect,” Ling Chiao explained. “And in order to really understand the results of your channels and your incremental impact, you really have to triangulate through these different approaches.”

The challenge was maintaining stakeholder trust while switching a core piece of measurement infrastructure. Square approached this systematically, using their incrementality test results as validation points for their new Recast models. [Peter Zhou](https://www.linkedin.com/in/peter-haochen-zhou-b1a381a4/), who led much of the technical transition, described the process: “It was key that we could incorporate our incrementality test results to achieve model calibration with our previous lift tests.”

Square then took an iterative approach to building confidence. They worked closely with Recast through multiple model iterations, each time refining based on business feedback and new model performance test results including out-of-sample forecast accuracy checks.

When marketing teams raised concerns about specific channels, it triggered deeper investigation rather than immediate acceptance. This wasn’t about making Recast match other tools, but rather, was about ensuring the model reflected real business dynamics.

The collaborative process paid off. As model iterations advanced, backtesting metrics improved and, more importantly, when teams acted on the model’s recommendations, they began observing the model’s expected business outcomes firsthand.

“For the old MMM, there was no way to see ongoing backtesting results,” Zhou noted. “Recognizing that the fundamental methodology is different, we feel like the Recast models align better with our other data points and are proven with the (visible) backtesting results.”

![](https://getrecast.com/wp-content/uploads/2025/12/image-4.png)

### Operational Excellence at Scale

With trust established, Square US integrated Recast deeply into their operations. Weekly data refreshes became automated through robust data pipelines. Marketing stakeholders began gathering for monthly MMM reviews, examining performance trends and discussing optimization opportunities based on the latest insights.

Finance teams at Square have also gained self-service access through custom Looker dashboards that leverage data pulled directly from Recast’s API, allowing them to explore MMM outputs alongside their other metrics and tools they’re already familiar with. And, perhaps most significantly, quarterly and annual planning cycles shifted from exercises based on old data to dynamic processes that incorporate recent MMM insights, fundamentally changing how Square approaches budget allocation and forecasting.

“We’re trying to get into an environment where we feel better about making changes within the quarter, as fast as we can,” Chiao explained. “With our other MMM vendor, we didn’t even have this (recent) data available, so there weren’t these types of conversations happening between the quarterly cycles.”

The results at Square US have been transformative. Marketing teams can now respond to performance changes in their MMM within weeks rather than months, and Finance teams have built confidence in Marketing’s plans because they’re backed by transparent, validated forecasts.

## Square International: Scaling Across Markets

While Square US pioneered the Recast implementation, their international markets presented a different opportunity and challenge. These younger markets had always wanted MMM but couldn’t justify the cost with traditional vendors. “We’ve long wanted to have individual media mix models for these markets,” explained Andy Crowe. “It’s fantastic to finally be at that stage now.”

These international teams benefited enormously from the bedrock laid by Square US. Data pipelines had been built, methodologies were proven, and internal education materials existed. All of this allowed Square’s international markets to move much faster than would have been possible if they had started from scratch.

But they also needed modeling flexibility. UK and Australian markets had different media landscapes than the US, and marketing teams are structured differently. This meant that any new media mix models would need to reflect these realities on the ground.

[Durugshan Wijayakumar](https://www.linkedin.com/in/durugshan/), who works alongside Andy Crowe on the international data science team, emphasized the collaborative nature of the rollout: “The open lines of communication with the Recast team were really helpful. Recast always volunteered to help us with information about the US rollout and provided slides that we could circulate internally.”

### Defending the “Hard to Track” Spend

One of the most immediate benefits for international markets has been the ability to prove the efficiency of marketing spend that had historically been challenging to measure. Upper funnel spend, significant in certain Square markets, had at times been difficult to justify without clear incrementality measurement.

“If you think about a financial leader at Block who’s looking at moving budgets, the US was always a more attractive place to put that because there was actual (modeling) evidence of what their channels were delivering,” Crowe explained. “While we strongly believed in the strategic value of upper-funnel activity, we didn’t have the same rigor of evidence to show incrementality, which left those allocations more vulnerable to budget shifts.”

With Recast, international teams can finally demonstrate and quantify the incremental value of upper-funnel channels. They now have apples-to-apples measurement that could prove the incremental efficiency of channels during organization-wide efficiency pushes.

## Cash App: A Data Scientist’s Approach to MMM Validation

When [Matt Patton](https://www.linkedin.com/in/mattpatton1/) joined Cash App’s data science team in late 2024, he found a marketing measurement transformation already in motion. Cash App was onboarding with Recast after deciding to transition from a partnership with a legacy MMM solution. What Patton brought to the team was a rigorous, technical approach to validating the output of Recast’s models and a philosophical conviction that would align perfectly with Recast’s forward-looking methodology.

Before Recast, Cash App’s measurement framework relied heavily on AppsFlyer attribution data, reflecting their mobile-focused consumer marketing. Their previous MMM played a supporting measurement role while lift tests were “tertiary”because a rapid experimentation process was still nascent. The strategic decision to make MMM more foundational had already been made, but execution required building organizational trust in a new platform.

Patton immediately contributed to this shift by translating complex statistical concepts for stakeholders throughout the business. “That’s something I was able to contribute almost immediately,” he recalls, “being able to explain what a backtest is (for example)… I was literally explaining this timeline thing like it was time travel.”

Cash App’s organizational shift was aided by other factors. For one, the outputs of Recast’s initial models largely aligned with internally-trusted attribution data. “The MMM didn’t tell us one channel was awesome, that the attribution told us was not,” Patton notes. There was also a philosophical component to trust-building. Discussing his vision for validation, Patton says, “If we can predict the future well, then we know our measurement is working.” He would go on to call prediction accuracy “the white whale of digital measurement.” because such accuracy is something that will always be actively pursued even if never fully achieved.

![](https://getrecast.com/wp-content/uploads/2025/12/image-1.png)

This forward-looking approach aligned perfectly with Recast’s platform methodology and validation techniques. As with Square US, reviewing the results of out-of-sample forecast accuracy checks and other model diagnostic tests would be key factors in Cash App building trust in Recast.

### Leveraging Advanced Features for Decision-Making

Cash App quickly adopted the Recast platform’s advanced capabilities for practical marketing decision making. A few of their key platform use cases include:

**Saturation Curves:** Recast’s estimation of saturation for every media channel plays a key role in guiding investment recommendations. Rather than simply saying a channel can handle more spend, Patton can advise things like: “It would be less risky to increase budgets 50% higher than you would have and see how performance data comes back.”

**Time Shift:** Another common use case is viewing Recast’s time shift analysis, which estimates the length of time that marketing activities can have an incremental impact on a given KPI. In addition to optimization, viewing time shifts has helped Cash App determine appropriate measurement windows for their complex user journey when designing holdout tests.

**Uncertainty:** Uncertainty boundaries are exposed throughout the Recast platform and helps drive testing priorities at Cash App. “We’re doing a test right now,” Patton mentions of a geo-lift test for a channel that shows strong ROI in Recast but with high uncertainty.

**Multi-Stage Modeling:** Cash App makes use of Recast’s [unique multi-stage modeling techniques](https://getrecast.com/multi-stage-models/) to understand the incremental impact of their paid media on multiple steps in their conversion funnel. This technique is critical when optimizing budgets to drive the KPIs the business cares about most.

Use cases like these have helped Recast become Cash App’s go-to platform for answering questions about marketing performance at Cash App. Patton explains that where those answers once came from attribution data, they now come from Recast.

But more broadly, Recast is helping Cash App achieve a new marketing measurement state, where prediction accuracy is used to validate measurement truth. “My goal is to get to a point where we can make predictions and then see how they land,” Patton explains. Recast will be a critical lever in Cash App’s pursuit of measurement’s white whale: proving causality by making accurate predictions, one forecast at a time.

### Block’s Unified Platform Advantage

As Recast rolled out across Block entities, an unexpected benefit emerged: the power of standardization. For the first time, leadership could discuss marketing performance across different businesses using the same vocabulary and framework.

“Now there’s a standardized (marketing measurement) tool that different parts of the business can look at,” Crowe notes. “Leaders are familiar with it, and it’s speaking the same language.”

![](https://getrecast.com/wp-content/uploads/2025/12/image-2.png)

This standardization occurred alongside a broader organizational shift at Block toward “functionalization” – bringing together previously distributed functions like engineering, data, and design across the entire company. Having a unified measurement platform perfectly supported this strategic direction.

Yet standardization didn’t mean rigidity. With Recast, each business maintained the modeling flexibility needed to meet their unique dynamics:

- Square US leverages sophisticated modeling to track customer cohorts with different values to the business.
- Square International focuses on market-specific nuances and measuring upper-funnel media spend.
- Cash App concentrates solely on performance media measurement.
- Afterpay is preparing to tackle their own unique two-sided marketplace dynamics.

Stepping back, Block’s measurement philosophy – treating MMM, incrementality testing, and attribution as three legs of a stool – finally found a platform that felt purpose-built. Recast’s transparency about uncertainty has helped teams prioritize which channels to test next, and incrementality results can be incorporated directly into the models and used to calibrate the measurement of subsequent weekly refreshes.

This systematic approach to managing uncertainty transformed it from a weakness into a tool for experiment prioritization. Channels with high uncertainty and high spend become prime candidates for incrementality testing within Block’s businesses. And as test results come in, they get incorporated into their Recast models, reducing uncertainty and enabling more confident optimization.

### Results and the Path Forward

The impact of Block’s transition to Recast extends far beyond faster data refreshes. Marketing teams now operate with fundamentally different cadences and confidence levels.

- **Speed to Insight:** The shift from biannual to weekly updates didn’t just provide fresher data, it changed how teams think about optimization. “Even by mid-month, we could start to get a sense of where things are starting to move,” Wexler notes.
- **Cross-Functional Alignment:** Finance teams are more closely entwined with marketing via shared dashboards. “They appreciate (Recast) because it speaks more to their language,” Chiao explained, referring to concepts like ROI, marginal ROI, and diminishing returns curves that Recast surfaces prominently.
- **Securing Budget:** International markets could finally defend their investments in hard-to-track channels. “It’s very good for defensibility of budget,” Crowe emphasized. “We can show additional evidence that our upper-funnel marketing activities are working and adding incremental value.”
- **Cultural Transformation:** Perhaps most significantly, Block’s marketing organization shifted from backward-looking MMM measurement to forward-looking planning. Instead of using MMM primarily to justify past spending, teams now use it to optimize future allocation.

Looking ahead, Block continues to expand their relationship with Recast across multiple dimensions. Sub-channel optimization capabilities are being developed to help channel managers allocate budgets within their portfolios, providing granular insights beyond parent channel performance. Square’s geographic expansion continues with Canada and Japan implementations underway, and the US team has deployed an MQL (Marketing Qualified Lead) model to understand the full customer journey beyond initial conversion.

### Lessons for Complex Enterprises

Block’s successful transformation offers several lessons for other complex organizations considering modern incrementality platforms:

1. **Transparency builds trust.** Black box models create skepticism. Exposing uncertainty, model diagnostics and model forecast accuracy helps stakeholders understand and believe the results.
2. **Focus on what you can control.** Be cognizant of external factors that influence marketing, but build forecasts based on the levers that your team controls.
3. **Standardization enables scale.** A unified platform across business units creates common language and shared learnings while maintaining flexibility for unique needs.
4. **Observe uncertainty, then manage it.** High uncertainty signals opportunity for testing and learning, not model failure.
5. **The importance of forecast accuracy.** Making accurate, validated forecasts over an extended period of time is a key lever to building organizational trust in measurement tooling.

For Block, Recast has become more than a measurement vendor – it’s a strategic partner in building what Ling Chiao calls “a continuous process” of testing, forecasting, learning, and optimizing. In a world where marketing conditions change rapidly and every dollar counts, that continuous process isn’t just nice to have. It’s essential for enterprise survival and growth.