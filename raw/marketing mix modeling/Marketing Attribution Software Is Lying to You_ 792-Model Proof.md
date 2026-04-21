---
title: "Marketing Attribution Software Is Lying to You: 792-Model Proof"
source: "https://cassandra.app/blog/marketing-attribution-software-analysis"
author:
published:
created: 2026-04-20
description: "Cassandra is the Marketing Measurement platform that incorporates Marketing Mix Modeling, Incrementality testing and Always on Incrementality to measure and allocate your Marketing Mix scientifically."
tags:
  - "clippings"
---
##### Marketing attribution software over-reports by 1.2x to 2.3x. We analyzed 792 MMMs across 194 advertisers. See which channels actually deliver — and which produce nothing.

![](https://framerusercontent.com/images/qmjvevr0HtNoHehjLDn4CorkLQ.png?width=1024&height=1024) ![](https://framerusercontent.com/images/kLC502NjSM6rjTG35dRQOqfqKw.jpg?width=2912&height=1632)

#### Get a weekly dose of insightful people strategy content

### The Short Version

If you are evaluating marketing attribution software, read this first. We compared platform-reported channel performance against incrementality-measured values across 792 Marketing Mix Models spanning 194 advertisers and multiple markets (2023-2025). The finding: every marketing attribution platform over-reports its own performance — by 1.2x to 2.3x on average, and up to 4-6x in extreme cases. But inflated credit is not the real damage. The real damage is that attribution cannot tell you which channels produce zero incremental return — and in a typical portfolio, 20-35% of budget flows to exactly those channels. In one case, we found 35% of a EUR 16.7M budget going to channels with near-zero measured incrementality. Attribution is not a measurement system. It is an accounting ledger. The marketing measurement platform you actually need is one built on incrementality and portfolio theory — not click tracking.

## Attribution Is Accounting, Not Measurement

There is a distinction in finance between bookkeeping and valuation. Bookkeeping records what happened. Valuation determines what something is worth. These are fundamentally different activities, and confusing them leads to bad capital allocation.

Attribution is bookkeeping. Every marketing attribution software on the market records which touchpoints a user interacted with before converting, then distributes credit according to a predetermined rule — last-click, first-click, linear, time-decay, or some algorithmic variant. The output is a ledger: Channel A gets 40% credit, Channel B gets 35%, Channel C gets 25%.

This ledger answers one question: "Who touched the ball?" It does not answer the question that actually matters for budget decisions: "Who created the scoring opportunity?"

A midfielder who delivers 50 key passes per season but rarely scores will show up poorly in a goals-only attribution model. A striker who taps in from two yards out will look like the most valuable player on the pitch. Any football analyst knows this is nonsense. Yet this is exactly how most marketing organizations allocate hundreds of millions of dollars.

The distinction matters because [attribution systematically misleads budget decisions](https://cassandra.app/learn/why-attribution-misleads-budget-decisions). When you use an accounting ledger to make investment decisions, you are not measuring. You are rearranging receipts.

## The Ledger Fallacy: What Attribution Actually Measures

To understand why attribution fails as a measurement tool, you need to understand what it actually captures.

Attribution tracks observable user-level interactions: clicks, impressions, site visits. It then applies a deterministic or probabilistic rule to assign conversion credit. The implicit assumption is that the touchpoints recorded in the attribution window are the touchpoints that caused the conversion.

This assumption is wrong in three specific ways.

**1\. Selection bias.** Users who click on branded search ads were already looking for your brand. They had already been influenced by something else — a TV spot, a social ad, a podcast mention, a friend's recommendation. Attribution gives 100% of the credit to the last observable click and 0% to the thing that actually created the demand. This is not a minor distortion. In our data, platforms over-report branded search performance by a median of 1.2x — but with extreme variance. Some models show overestimation exceeding 3x.

**2\. Unobservable touchpoints.** Attribution cannot track what it cannot see. A user hears your brand mentioned on a podcast, thinks about it for three days, then types your URL directly into their browser. Attribution records this as "direct traffic" — the channel that, by definition, means "we have no idea what caused this." Across our dataset, attribution cannot account for the majority of demand-generation signals that precede a conversion. It simply ignores them.

**3\. Correlation masquerading as causation.** If you increase Meta spend and see more branded search conversions the following week, attribution credits the conversions to branded search. The causal chain — Meta created awareness, awareness drove search behavior, search captured the conversion — is invisible to the attribution model. The channel that harvested demand gets the credit. The channel that created the demand gets nothing.

These are not edge cases. They are structural features of how attribution works. And they lead directly to a predictable pattern of misallocation that we can now quantify.

## What 792 Models Reveal About Marketing Attribution Software

We ran a systematic comparison across 792 MMMs, matching platform-reported channel performance against incrementality-measured values for the same advertisers and time periods. The methodology: for each advertiser, we took the channel-level ROAS as reported by their marketing attribution software (Google Analytics, various MMPs, platform-reported metrics) and compared it against the incremental ROAS estimated by our Bayesian Marketing Mix Models.

The results were consistent enough to call structural.

### Every Platform Inflates Its Own Numbers

Across 62 models where we had both platform-reported and MMM-attributed metrics for the same channels, every major platform over-reported its performance.

| Platform | Models | Median Overestimation | IQR (Interquartile Range) |
| --- | --- | --- | --- |
| Meta | 32 | 2.34x | 0.67 - 4.66x |
| Google | 33 | 1.18x | 0.80 - 2.17x |
| Other Platforms | 12 | 1.9x | 0.75 - 3.03x |

Meta over-reports by a median of 134%. Google is closer to reality at 18% median overestimation. Other platforms — DSPs, niche ad networks, affiliate platforms — over-report by nearly 2x.

The financial parallel is instructive. Imagine asking three fund managers how their portfolios performed, knowing each one inflates returns by 18-134%. No serious investor would make capital allocation decisions based on self-reported returns. Yet this is exactly what marketing attribution software asks you to do.

### The Variance Is the Point

The median overestimation tells part of the story. The interquartile range tells the rest.

Meta's IQR spans 0.67x to 4.66x. That means some advertisers see Meta under-report its contribution (the platform claims less than the MMM measures) while others see Meta over-report by nearly 5x. You cannot predict where your business falls on this spectrum without measuring incrementality directly.

Google's IQR spans 0.80x to 2.17x — a 2.7x spread between the bottom and top quartile. The same marketing attribution platform, applied to two different advertisers, produces estimates that diverge by nearly 3x.

This variance is not noise. It reflects real differences in channel mix, measurement windows, audience overlap, and baseline organic demand across advertisers. The point is that no single overestimation factor applies to everyone — and any marketing attribution solution that claims otherwise is misleading you.

### What Channels Actually Deliver: Incremental ROAS Across 792 Models

Setting aside what platforms report, here is what channels actually deliver when measured incrementally:

| Channel | Models | Median Incremental ROAS | 95% CI |
| --- | --- | --- | --- |
| Search Non-Brand | 60 | 5.21x | 2.29 - 9.89 |
| Performance Max | 48 | 4.64x | 3.11 - 6.41 |
| Search Brand | 85 | 4.14x | 1.95 - 7.78 |
| Programmatic Display | 128 | 4.09x | 0.00 - 59.99 |
| Meta Retargeting | 72 | 3.64x | 0.00 - 32.72 |
| YouTube | 14 | 2.70x | 1.50 - 4.20 |
| Connected TV | 16 | ~2.3x | 0.00 - 3.9x |
| Meta Prospecting | 59 | 1.90x | — |

Two patterns emerge. First, the confidence intervals vary dramatically by channel. Performance Max shows a tight CI of \[3.11 - 6.41\] — you can bet on it with reasonable certainty. Programmatic Display and Meta Retargeting show extreme ranges spanning from 0 to 30-60x — execution quality, creative, and targeting determine where you land.

Second, the channels with the widest CIs are often the ones where marketing attribution software struggles most. Programmatic Display, Meta Retargeting, and Meta Prospecting all show extreme variance — precisely because platform attribution cannot separate their incremental contribution from organic baseline and cross-channel effects. Meta Prospecting, notably, delivers the lowest median incremental ROAS (1.90x) despite often being one of the highest-spend channels.

### Prospecting vs Retargeting: The Double Penalty

Our dataset reveals a pattern that contradicts what most marketing attribution platforms report. Across the full dataset (59 prospecting models, 72 retargeting models), retargeting delivers a median incremental ROAS of 3.64x — nearly twice that of prospecting at 1.90x.

Yet platforms report the opposite. In a directional subset (n=3 per bucket — treat as directional, not definitive), prospecting shows a platform-reported ROAS of 15.65x while retargeting shows 13.40x. The overestimation ratios tell the real story: platforms inflate prospecting by 4.3x and retargeting by 2.67x.

This creates a double penalty for prospecting budgets:

- **Lower incremental return** — prospecting delivers 1.90x vs retargeting's 3.64x
- **Higher overestimation** — platforms inflate prospecting more aggressively, making it look like the better bet when it is actually the worse one

The implication is that retargeting, despite appearing less impressive in platform dashboards, delivers nearly twice the incremental value. Meanwhile, prospecting is the most over-reported channel type in our dataset — the widest gap between what platforms claim and what incrementality measurement reveals. This is the exact distortion that marketing attribution software, by design, cannot detect.

**Want to see how much your platforms are over-reporting?** Cassandra measures incremental ROAS per channel using Bayesian MMM and geo-experiments — not click tracking.

## Portfolio Theory: A Different Question Entirely

Attribution asks: "Which channel gets credit for this conversion?"

Portfolio theory asks a fundamentally different question: "What is the optimal allocation across channels given their expected returns, correlations, and risk profiles?"

This is not a subtle distinction. It changes everything about how you approach budget decisions.

In 1952, Harry Markowitz demonstrated that evaluating investments individually by their returns is inferior to evaluating them as a portfolio. The reason: correlations between assets matter as much as individual asset returns. A combination of moderately returning assets with low correlation to each other will outperform a concentrated position in the highest-returning asset — at lower risk.

We detailed the mechanics of this framework in our analysis of the [marketing efficient frontier](https://cassandra.app/blog/marketing-efficient-frontier). The core principle translates directly to marketing channels:

- Each channel has an **expected incremental return** (measured by MMM, not attribution)
- Each channel has a **risk profile** — how much its performance varies across time, creative cycles, and market conditions (what we formalized as [risk-adjusted ROAS](https://cassandra.app/blog/risk-adjusted-roas))
- Channels have **correlations** with each other — some move together, some move independently, some are inversely correlated

The portfolio approach considers all three dimensions simultaneously. Attribution considers none of them.

### Why Correlations Change Everything

Here is a concrete example from our dataset. Consider two channels:

- **Meta Prospecting:** Median incremental ROAS of 1.90x, with high variance across 59 models — moderate return, high uncertainty
- **YouTube:** Median incremental ROAS of 2.70x, with a confidence interval spanning 1.50x to 4.20x — higher return and much tighter variance

An attribution-minded allocator would look at platform-reported numbers and say: "Meta shows higher ROAS, so allocate more to Meta." But incrementally, YouTube delivers 2.70x vs Meta Prospecting's 1.90x — the opposite of what the platform dashboards suggest.

A portfolio-minded allocator asks: "What is the correlation between these two channels?" and "What combination minimizes risk while preserving return?"

If the correlation is +0.85 (both rise and fall together), combining them does little to reduce portfolio risk. If the correlation is +0.15 (largely independent), combining them in the right proportion dramatically reduces total portfolio variance while preserving most of the expected return.

In our dataset, channels that appear similar under attribution often show very different incremental profiles and interaction patterns — dynamics that only a [portfolio-level construction](https://cassandra.app/blog/marketing-budget-portfolio-construction) can capture.

Attribution cannot see this. It does not model correlations. It does not model risk. It simply assigns credit to whoever touched the conversion last and calls it a day.

## From Credit Assignment to Capital Allocation

The shift from attribution thinking to portfolio thinking requires changing the fundamental question your measurement system answers.

**Attribution question:** "How should we distribute credit for conversions that already happened?"

**Portfolio question:** "How should we distribute capital to maximize future incremental returns at an acceptable level of risk?"

One looks backward. The other looks forward. One is accounting. The other is investment management.

The practical difference shows up in budget decisions. An attribution-guided team sees a channel delivering a platform-reported ROAS of 8x and increases its budget. A portfolio-guided team runs an MMM and discovers the incremental ROAS is 4.14x — strong, but roughly half what the platform claims. And more importantly, the portfolio-guided team discovers that 35% of its budget is flowing to channels with near-zero incremental return — a reallocation opportunity that attribution makes completely invisible.

We have seen this play out dozens of times. The initial reaction from performance marketing teams is resistance: "You want us to reduce spend on our highest-ROAS channel?" Yes. Because the "highest-ROAS channel" under attribution is often not the highest-incrementality channel under causal measurement.

This is why the finance analogy matters. No portfolio manager would say "Our Treasury bond returned 4% with certainty — let's put everything there." They understand that a diversified portfolio with a mix of risk profiles produces better risk-adjusted returns than a concentrated position in the safest asset. Marketing teams need to internalize the same logic.

## The Correlation Problem Attribution Cannot See

Beyond the credit-assignment failure, attribution has a second structural blind spot: it cannot detect or model cross-channel effects.

Marketing channels do not operate independently. When you run a TV campaign, branded search volume increases. When you run Meta prospecting campaigns, direct traffic increases. When you pause YouTube, Meta ROAS declines because the two channels were working in concert — YouTube was warming audiences that Meta was converting.

These interaction effects are invisible to attribution because attribution models each conversion as a linear sequence of touchpoints within a single user journey. The user who saw your YouTube ad, did not click, then three days later saw your Meta ad and converted gets attributed to Meta. YouTube gets nothing.

In our models, cross-channel interaction effects are a meaningful component of total marketing impact — dynamics that attribution, by design, cannot detect. A Marketing Mix Model captures these effects structurally; a marketing attribution platform ignores them entirely.

The portfolio framework handles this naturally. Channel correlations — the core of portfolio construction — are precisely a measure of how channels interact. Negatively correlated channels (one goes up when the other goes down) provide natural hedging. Positively correlated channels amplify both upside and downside. The [optimal portfolio construction](https://cassandra.app/blog/marketing-budget-portfolio-construction) accounts for all of these dynamics simultaneously.

## Case Study: Where 35% of a EUR 16.7M Budget Produces Zero Incremental Return

A home improvement retailer spending EUR 16.7M annually across 19 channels asked us to measure the incremental contribution of each channel using Cassandra. Their attribution platform reported positive ROAS across every channel. The MMM told a fundamentally different story.

### The highest-performing channels (by incremental ROAS)

| Channel | Incremental ROAS | Annual Spend | % of Budget |
| --- | --- | --- | --- |
| Google Ads Pure Brand | 62.16x | EUR 37,715 | 0.2% |
| Display Consideration | 37.72x | EUR 186,839 | 1.1% |
| Local Services | 23.07x | EUR 254,733 | 1.5% |
| Google Ads Kitchen | 23.01x | EUR 774,923 | 4.6% |
| Google Ads Garden | 19.24x | EUR 1,598,325 | 9.6% |

These five channels — delivering 19x to 62x incremental ROAS — received only **17% of the total budget**.

### The lowest-performing channels (by incremental ROAS)

| Channel | Incremental ROAS | Annual Spend | % of Budget |
| --- | --- | --- | --- |
| Google Ads Stoves | 0.00x | EUR 535,556 | 3.2% |
| Google Ads DY | 0.00x | EUR 1,381,158 | 8.3% |
| Google Ads Bathroom | 0.00x | EUR 363,830 | 2.2% |
| TikTok | 0.19x | EUR 380,591 | 2.3% |
| Radio | 0.40x | EUR 3,254,035 | 19.5% |

These five channels — delivering zero to near-zero incremental ROAS — absorbed **35.5% of the total budget (EUR 5.9M)**.

Attribution reported positive ROAS on every one of these channels. The platform dashboards showed green across the board. There was no signal, anywhere in the attribution data, that EUR 5.9M per year was producing effectively nothing.

This is the core failure of marketing attribution software. It does not just inflate numbers. It hides waste. It makes every channel look like it is working, and in doing so, it makes it impossible to identify the channels that are not.

The gap between the best channels (62x) and the worst (0x) in this portfolio spans the entire possible range. No marketing attribution platform can reveal this gap because it does not measure incrementality. It measures touchpoints.

**Cassandra automates this entire analysis** — from incremental ROAS measurement to portfolio-optimized budget allocation. No data science team required.

## Why Marketing Attribution Software Persists Despite Its Failures

If marketing attribution software is this flawed, why does it dominate marketing measurement? Three reasons.

**1\. Operational convenience.** Attribution is real-time, user-level, and integrated into every ad platform. Portfolio-based measurement requires statistical modeling, longer time horizons, and a willingness to accept uncertainty ranges rather than point estimates. Most marketing teams prefer a wrong but precise number over a right but probabilistic one.

**2\. Platform incentives.** Google, Meta, and every ad platform report their own attribution. The platform that captures the last click gets the credit — and the budget increase. Platforms have no incentive to tell you that their attributed conversions are not incremental. This is the marketing equivalent of asking a broker whether you should sell your position with them.

**3\. Organizational inertia.** Performance marketing teams are structured around attribution metrics. KPIs, compensation, and career advancement are tied to attributed ROAS. Switching to incrementality-based measurement threatens existing power structures. The channel manager whose channel looks best under attribution has a personal incentive to resist the switch.

None of these are good reasons to continue making bad decisions. But they explain why the industry has been slow to change.

## How to Move Beyond Your Marketing Attribution Platform

Moving from attribution-guided to portfolio-guided allocation is not an overnight process — and no marketing attribution platform will guide you through it, because the transition renders their core product obsolete. Here is the sequence we have seen work across dozens of implementations.

### Step 1: Establish an Incrementality Baseline

You cannot build a portfolio without accurate expected returns. Attribution-reported ROAS is not an accurate expected return. You need incremental ROAS from a properly calibrated MMM or, better, from geo-based experiments that establish causal ground truth.

This is the measurement foundation. Without it, you are building a portfolio on bad inputs, which is worse than not building one at all. We detailed the full approach to [risk-adjusted return measurement](https://cassandra.app/blog/beyond-roi-risk-adjusted-returns) in a prior analysis.

### Step 2: Measure Channel Risk and Correlations

For each channel, calculate:

- **Expected incremental return** (median iROAS from your MMM)
- **Return variance** (the width of the credible interval or standard deviation across time periods)
- **Pairwise correlations** (how each channel's performance co-moves with every other channel)

This gives you the three inputs required for portfolio optimization: returns, risk, and correlations.

### Step 3: Construct the Efficient Frontier

Using the inputs from Step 2, compute the set of portfolio allocations that maximize return at each level of risk. Every allocation that falls on this curve is efficient — no reallocation can improve return without increasing risk, or decrease risk without reducing return.

Your current allocation almost certainly falls below this frontier. The gap between where you are and the frontier represents recoverable value.

### Step 4: Select Your Target Portfolio

The right portfolio depends on your organization's risk tolerance. A venture-backed startup burning toward product-market fit will tolerate higher variance for higher expected returns. A public company with quarterly earnings pressure will prefer lower variance even at the cost of some expected return.

This is the conversation attribution can never facilitate. Attribution has no concept of risk tolerance. Portfolio theory makes it the central decision variable.

### Step 5: Implement Gradually, Measure Continuously

Shift allocation toward the target portfolio in increments — we recommend 15-20% of the delta per quarter. Measure incremental outcomes at each stage. Re-estimate the model quarterly to update expected returns, risk, and correlations as market conditions change.

This is not a one-time optimization. It is a continuous capital allocation process — the same process that drives every serious investment firm.

## Known Limitations

We are rigorous about stating what this framework does not solve.

**1\. Portfolio theory requires accurate inputs.** If your MMM is poorly specified — wrong adstocks, missing confounders, insufficient data — the portfolio built on its outputs will be wrong. Garbage in, garbage out applies to portfolio optimization as much as it applies to attribution.

**2\. Correlations are not stationary.** Channel correlations shift as market conditions change, as you enter new markets, and as platforms alter their algorithms. The portfolio that was optimal last quarter may not be optimal next quarter. Continuous re-estimation is not optional.

**3\. Small-budget brands may lack sufficient data.** Portfolio optimization requires enough data to estimate channel-level returns and correlations with reasonable precision. Brands spending less than $200K/month across fewer than four channels may not generate enough signal for reliable portfolio construction.

**4\. Organizational change is harder than model change.** The statistical framework is straightforward. Getting a performance marketing organization to stop optimizing against attributed ROAS and start optimizing against incremental portfolio returns is a change management challenge that no model can solve by itself.

## Frequently Asked Questions

### What is wrong with marketing attribution software?

Marketing attribution software assigns conversion credit based on observable touchpoints (clicks, impressions) using rules like last-click or time-decay. The fundamental problem: it measures who touched the ball, not who created the scoring opportunity. Our analysis of 792 models across 194 advertisers shows that platforms over-report their own performance by 1.2x to 2.3x on average, with extreme cases exceeding 4x. Worse, attribution cannot identify channels with zero incremental return — and in a typical portfolio, 20-35% of budget flows to those channels. Attribution is an accounting ledger, not a measurement system.

### Is marketing attribution software the same as incrementality testing?

No. Attribution distributes credit for conversions that already happened. Incrementality testing measures the causal impact of marketing — what would have happened without the spend. These produce fundamentally different answers. In our data, Meta platforms report an average ROAS of 8x, but incremental measurement reveals 1.90x for prospecting and 3.64x for retargeting. Retargeting delivers nearly twice the incremental value of prospecting — yet platforms overestimate prospecting by a wider margin, making it look like the better bet. A marketing measurement platform built on incrementality provides the accurate expected returns needed for budget optimization.

### What should I use instead of a marketing attribution platform?

The alternative is a portfolio-based measurement approach combining Marketing Mix Modeling (MMM) for incremental return estimation, geo-experiments for causal calibration, and portfolio optimization for budget allocation. This framework treats your channel mix as an investment portfolio — optimizing for risk-adjusted incremental returns rather than attributed credit. Companies that made this transition saw significant improvement in incremental outcomes by reallocating budget from zero-return channels to high-performing ones.

### Can marketing attribution software and MMM work together?

Attribution provides useful operational data — which creatives are getting clicks, which audiences are engaging, which landing pages convert. That operational signal has value for day-to-day campaign management. But it should not drive budget allocation decisions. MMM provides the strategic layer: accurate incremental returns, channel correlations, and risk profiles needed for portfolio-level optimization. The two systems answer different questions at different time horizons.

### How much budget do I need for portfolio-based measurement?

Portfolio optimization requires enough data to estimate channel-level returns and correlations with reasonable precision. Brands spending less than $200K/month across fewer than four channels may not generate enough signal for reliable portfolio construction. For smaller budgets, start with a properly calibrated MMM to establish incremental baselines before attempting full portfolio optimization.

## Conclusion

Marketing attribution software does not measure. It is an accounting ledger that records who touched the conversion last. It does not measure incrementality, it does not model risk, and it cannot see cross-channel effects. Using attribution to guide budget decisions is the equivalent of using bookkeeping entries to make investment decisions — you are looking at the right numbers in the wrong framework.

Portfolio theory offers a fundamentally better alternative. By treating your channel mix as a portfolio and optimizing for risk-adjusted incremental returns rather than attributed credit, you can recover the value that attribution-guided allocation leaves on the table. In one case, we identified EUR 5.9M — 35% of a EUR 16.7M budget — flowing to channels with zero measured incrementality. That is not an edge case. It is a pattern we see repeatedly across advertisers who have never measured incrementality.

The finance industry abandoned individual-stock picking in favor of portfolio construction decades ago. Marketing is overdue for the same transition. The tools exist. The data exists. The framework exists. What remains is the willingness to measure what matters instead of what is convenient.

**Ready to see what portfolio-optimized allocation looks like for your budget?** Cassandra measures your channels' incremental returns and shows you exactly where attribution is misleading your spend. [Try it free or book a demo](https://cassandra.app/platform).

**Methodology:** This analysis is based on 792 Marketing Mix Models across 194 advertisers, multi-market, multi-currency (2023-2025). Platform overestimation analysis based on 62 models with paired platform-reported and MMM-attributed metrics. Incremental ROAS estimated using Bayesian MMMs with geo-level calibration where available.

**Author:** [Gabriele Franco](https://www.linkedin.com/in/gabriele-francoo/), Founder & CEO of Cassandra

<iframe src="https://app-eu1.hubspot.com/conversations-visitor/143285527/threads/utk/c0e067a899b64f08a23cdaa158a85443?uuid=a9ec1881af224a0a9baf5ca5cce186d2&amp;mobile=false&amp;mobileSafari=false&amp;hideWelcomeMessage=false&amp;hstc=76869066.d974ffe754974a65696aae488e4b5bc2.1776668081107.1776668081107.1776668081107.1&amp;domain=cassandra.app&amp;inApp53=false&amp;messagesUtk=c0e067a899b64f08a23cdaa158a85443&amp;url=https%3A%2F%2Fcassandra.app%2Fblog%2Fmarketing-attribution-software-analysis&amp;inline=false&amp;isFullscreen=false&amp;globalCookieOptOut=&amp;isFirstVisitorSession=false&amp;isAttachmentDisabled=false&amp;isInitialInputFocusDisabled=false&amp;enableWidgetCookieBanner=false&amp;isInCMS=false&amp;hideScrollToButton=true&amp;isIOSMobile=false&amp;hubspotUtk=d974ffe754974a65696aae488e4b5bc2" title="Widget četu" allowfullscreen=""></iframe>