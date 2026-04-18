---
title: "The convergence of marginal ROAS in the budget allocation in Robyn"
source: "https://medium.com/@gufengzhou/the-convergence-of-marginal-roas-in-the-budget-allocation-in-robyn-5d407aebf021"
author:
  - "[[Gufeng Zhou]]"
published: 2023-03-02
created: 2026-04-17
description: "The convergence of marginal ROAS in the budget allocation in Robyn Details of the new budget allocator in Robyn v3.10.0 TLDR With the latest release of the Robyn dev version v3.10.0, we’ve upgraded …"
tags:
  - "clippings"
---
## Details of the new budget allocator in Robyn v3.10.0

### TLDR

With the latest release of the [Robyn dev version v3.10.0](https://github.com/facebookexperimental/Robyn), we’ve upgraded the budget allocator to provide more precision and better visualisation support (with the new allocator one-pager) for decision making. In this article, I’d like to introduce the details and interpretation of the new allocator one-pager as well as to discuss the following aspects of budget allocation in MMM:

- ROAS, mROAS and how budget allocation works
- The risk of being conservative in budget constraints
- The convergence of mROAS to equilibrium state

NOTE: This analysis uses a simulated data set that has no real life interpretation.

### Intro of the new Robyn budget allocator one-pager

First of all, let’s have a look at the new allocator one-pager in figure 1.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*hiAioWKWWoatHmxNFGEp5A.png)

Figure 1: The new Robyn budget allocator one-pager in v3.10.0

It contains three major sections:

**1st section — total budget optimisation**: Compare total performance improvement of two different allocation constraints conditions to the initial performance. A quick summary: with the same spend level as last 4 weeks and the benchmark ROAS of 1.46, bounded budget allocation delivers +11.0% more media response with ROAS of 1.62, while the 3x larger bound delivers +15.2% media response growth with 1.68 ROAS.

1. The “initial” pillar refers to the total spend and response from the last 4 weeks of the modelling window. The simulation period can be customised.
2. The “bounded” pillar refers to the optimised total response with the same spend under the user-defined channel-level constraints. The code snippet below shows how the constraints are defined for 5 example channels: 0.7–1.2 as lower and upper constraint means the first channel’s budget is allowed to vary between 70% and 120% of it’s selected mean (last 4 weeks) during the allocation.
3. Finally, the “bounded x3” pillar refers to the optimised total response with the same spend under the 3x wider constraints. With 0.7–1.2 as user-defined constraints, we allow -30% and +20% budget shift from the mean. 3x wider constraints means -90% and +60% range, which results in a new bound of 0.1–1.6.
```c
> InputCollect$paid_media_spends
[1] "tv_S"       "ooh_S"      "print_S"    "facebook_S" "search_S"  

# Case 1: use default total budget and date range
AllocatorCollect1 <- robyn_allocator(
  InputCollect = InputCollect,
  OutputCollect = OutputCollect,
  select_model = select_model,
  date_range = NULL, # When NULL, will set last month (30 days, 4 weeks, or 1 month)
  total_budget = NULL, # When NULL, use total spend of date_range
  channel_constr_low = c(0.7, 0.7, 0.7, 0.7, 0.7),
  channel_constr_up = c(1.2, 1.5, 1.5, 1.5, 1.5),
  channel_constr_multiplier = 3,
  scenario = "max_historical_response",
  export = TRUE
)
# Figure 2
```

**2nd section — Budget allocation per media:** This section shows the media-level comparison between the three pillars in spend share, response share, ROAS and mROAS. We want to specify how ROAS and mROAS are calculated.

- **ROAS = total response / raw spend**. Robyn performs adstocking on the raw spend and obtains the total response. In other words, the total response includes the effect from adstock & raw spend. However, while calculating ROAS, we only consider the “real money”, or raw spend as the denominator, because it’s misleading to consider “theoretical money” as part of the real cost.
- **mROAS = marginal response / marginal spend.** When it comes to marginal ROAS, we refer to the response of the “next dollar spend”. For example, for the spend level of 10$, the marginal response is the response of the 11th dollar. It also represents the slope at the 10$ point on the saturation curve. More details below.

**3rd section — Saturation curve per media:** The saturation curve of each media variable is visualised separately. The curve is transformed using the two-parametric Hill function, which is flexible enough to provide the C- & S-shape of the saturation. The x-axis refers to spend & y-axis the response (revenue, in this case). There’re four points on each curve:

1. **Carryover (white point)**: This point depicts the historical carryover level in the selected simulation period (last 4 weeks in this example) obtained from adstocking from preceding historical spend for this media. It can be understood as “lagged purchase from previous campaigns” and won’t change regardless of your current spend level. Raw spend will always “sits above” this point. If spending 0 within the selected simulation period, this point is the minimum response this variable will get. The grey area reinforce visualisation the adstock.
2. ==**Initial (grey point)**==: This point shows the mean (raw) spend of the selected simulation period and serve as benchmark for the optimised results. Again, note that the mean spend (or any spend) always start from the carryover point as described above.
3. **Bounded (blue point):** This point shows the optimised spend point and its response. It also starts from the carryover point as described above. It’s restricted by the user-defined spend bounds (lower & upper constraints) for this channel, which is shown in the first \[\] square bracket besides the channel name. The dotted line on the blue point visualises the user-defined bounds. Use the ooh\_S example, the dotted line on the blue point is th ==e 70%-150% range of the mean== spend that is the x-axis location of the grey point.
4. **Bounded x3 (gold point):** Similar to the blue point, this point shows the optimised spend point with 3 ==x wider range of the user-defined spend bounds. T== he purpose of this point is to showcase the potential of optimisation with wider bounds and mitigates the risk of subpar optimisation result due to too conservative constraints.

### ROAS, mROAS and how budget allocation works

Figure 3 below is the zoom-in of figure 1. Let’s look at the initial & bounded tables for facebook\_S & ooh\_S. At a first glance, it’s counterintuitive to see that ooh\_S get budget decrease and facebook\_S increase, even though ooh\_S has higher total initial ROAS of 3.78, while facebook\_S has ROAS of 0.94.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*ehSZkFDZhxMmaz0KLpXORQ.png)

Figure 3: Comparing spend share & ROAS of ooh\_S & facebook\_S

The reason for the higher total ROAS lies in ROAS calculation that includes the response of adstocking: **ROAS = total response / raw spend**. In Figure 4 below, this example model finds higher carryover effect (grey area and white dot) for ooh\_S. We can eyeball the following values:

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*qmSTOvipIDubKZk19-fJBw.png)

Figure 4: Comparing saturation points of ooh\_S & facebook\_S. ROAS = total response / raw spend

- ooh\_S carryover spend 17k (x on white dot)
- ooh\_S initial raw spend 11k (28k–17k, x on grey dot minus x on white dot)
- ooh\_S initial total response 42k (y on grey dot)
- **ooh\_S initial ROAS = 42k / 11k ≈ 3.78**
- facebook\_S carryover spend 2k (x on white dot)
- facebook\_S initial raw spend 6k (8k–2k, x on grey dot minus x on white dot)
- facebook\_S initial total response 6k (y on grey dot)
- **facebook\_S initial ROAS = 6k+ / 6k ≈ 0.94**

However, budget allocation doesn’t care about the total ROAS, but rather the **“next dollar response”**. In other words, “I’ll invest in whichever media that returns more revenue on the next dollar spend”. In Robyn, we call it **mROAS** (marginal return on ads spend). It’s the slope or first-order derivative of the current spend point on each curve.

In figure 5 below, despite the difference in axis scale, we can observe that both initial grey and blue points on facebook\_S have steeper slope than ooh\_S. In general, **mROAS = marginal response / marginal spend**. But in this case, we define the marginal spend as the “next dollar”, so we can simplify it as **mROAS = marginal response / 1.**

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*x3A7IDc-yKKGiUmF7iy1yw.png)

Figure 5: Slopes on initial & bounded optimised points

Eyeballing mROAS is difficult, but Robyn’s new allocator one-pager provides this information. In figure 6 below, we can clearly see that facebook\_S has higher mROAS. This is the reason why the allocator “decides” to increase spend on facebook\_S and decrease on ooh\_S.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*c6jQZdqBM0KIdYCXHSHqTQ.png)

Figure 6: mROAS of facebook\_S is higher than ooh\_S

### The risk of being conservative in budget constraints

Some attentive readers might have noticed an interesting phenomenon for ooh\_S: In figure 7 below, the allocator recommends to decrease ooh\_S spend from 5% to 3.5% in the bounded allocation (user-defined lower & upper constraints), but increase to 12.4% in the bounded x3 allocation (3x as wide constraints).

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*9wnq4-tws7z0WEguvy0k7g.png)

Figure 7: tv\_S decease “freed-up” optimization potential

The same pattern can be observed on the saturation curve. Looking at ooh\_S in figure 8 below, the user-defined budget bound of 0.7–1.5 for ooh\_S suggests a budget decrease (blue dot) compared to the initial point (grey dot), while the 3x wider bound of 0.1–2.5 results in budget increase (gold dot).

The reason behind the direction change lies in the “saving potential” of tv\_S. As the largest spending media, tv\_S delivers rather mediocre to low ROAS in general. With a narrow bound, tv\_S optimisation is restricted within a relative “linear” part of the curve, marked green. But with larger range, the allocator is able to enter the orange part where the slope is slowing down and mROAS is smaller. This “frees up” a large part of the budget that has more potential on other curves.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*WbxJa-hcFCmGTol_Ytz0AA.png)

Figure 8: Saturation curves with allocation points

This is the reason why we’ve introduced the “unbounded allocation”, in this case the 3x wider bound, as a default information in the allocation one-pager. Especially for very conservative bounds settings, this feature shows the potential of optimisation if widen up. Of course we’re aware that not every media can be flexibily increased or decreased by large amount. However, we believe this information is still valuable for decision making.

### The convergence of mROAS to equilibrium state

Another interesting phenomenon is that mROAS seems to be converging when further freedom is given to the allocator. In figure 9 below, we can clearly see that the mROAS of four media are approaching the homogeneous value between 0.4–0.5. If we would unify the scale of x- and y-axis in figure 8, these four media’s “bounded x3” points (gold) will show similar slope. Looking back at the definition of mROAS as “next dollar response”, it makes sense: the optimisation system is constantly trading off the mROAS of each channel until they all converges to a stable value, or the equilibrium state.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*TGP7ErH4AzxgV1CZey2eZA.png)

Figure 9: Convergence of mROAS given more freedom in optimization

Lastly, even though it’s interesting to observe the convergence of mROAS and helpful to understand how budget allocation works under the hood, what advertisers really care about is maximising the total marketing ROAS. Especially when interpreting the result to senior business leaders, the presenter shouldn’t stick to too much technical details that will cause confusion.

### Apendix

Robyn uses the optimisation package “nloptr” to perform the gradient-based nonlinear optimisation with bounds and equality constraints. Augmented Lagrangian (AUGLAG) is used for global optimisation and Sequential Least Square Quadratic Programming (SLSQP) for local optimisation. For algorithmic details please see [nloptr’s documentation](https://nlopt.readthedocs.io/en/latest/NLopt_Algorithms/#slsqp).

> ***This article is co-authored with*** [***Bernardo Lares***](https://www.linkedin.com/in/laresbernardo/) ***and*** [***myself***](https://www.linkedin.com/in/gufeng-zhou-96401721/)***.***

[![Gufeng Zhou](https://miro.medium.com/v2/resize:fill:96:96/0*pxqDNWTwFI3we1iO)](https://medium.com/@gufengzhou?source=post_page---post_author_info--5d407aebf021---------------------------------------)[10 following](https://medium.com/@gufengzhou/following?source=post_page---post_author_info--5d407aebf021---------------------------------------)

Meta Marketing Science. Author of "Robyn", the open source MMM package from Meta. [https://github.com/facebookexperimental/Robyn](https://github.com/facebookexperimental/Robyn)

## Responses (2)

Kakasarnold

==Initial (grey point)==

```c
the spend corresponding to this point is equal to the value of the carryover + average spend
```

```c
may i know which data set is used for this budget allocation. when i am experiment with demo code and given demo dataset in budget allocation the spending budget is different in initial, bounded, boundedx3 but in this blog the spend amount in initial , Bounded, Bounded x3 are 932k dollars
```