---
title: "Hitting ROAS target using Robyn’s budget allocator"
source: "https://medium.com/@gufengzhou/hitting-roas-target-using-robyns-budget-allocator-274ace3add4f"
author:
  - "[[Gufeng Zhou]]"
published: 2023-03-22
created: 2026-04-17
description: "Hitting ROAS target using Robyn’s budget allocator Details of the new “Target Efficiency” scenario in Robyn’s new budget allocator v3.10.1 TLDR A new scenario “target efficiency” is added …"
tags:
  - "clippings"
---
## Details of the new “Target Efficiency” scenario in Robyn’s new budget allocator v3.10.1

## TLDR

A new scenario “target efficiency” is added to the budget allocator in Robyn’s dev version v3.10.1, one month after [the latest allocator update](https://medium.com/@gufengzhou/the-convergence-of-marginal-roas-in-the-budget-allocation-in-robyn-5d407aebf021). Users can now **set ROAS or CPA targets** in the budget allocation. This is especially interesting for **growth advertisers** who ask questions like **“how much can I spend without budget limit until marketing hits break-even?”**

I’d like to introduce the details of the new allocator scenario, which requires revisiting some basics. In this note, we’ll be handling the following topics:

- Interpreting the result of `scenario = "target_efficiency"`
- Understanding saturation, the foundation of budget allocation
- How does budget allocation work technically
- The technical difference between `"target_efficiency"` & `"max_response"`

**DISCLAIMER**: This analysis uses a simulated data set that has no real life interpretation.

## Interpreting the result of “target\_efficiency”

First of all, please check out [the previous note](https://medium.com/@gufengzhou/the-convergence-of-marginal-roas-in-the-budget-allocation-in-robyn-5d407aebf021) about the scenario `"max_response"` first to better understand the design of the one-pager as well as the principle of budget allocation. This knowledge will help when understanding the new scenario.

Let’s look at an example in script 1 below of how to use the new scenario. Simply set `scenario = "target_efficiency"` to use it. When the main model has revenue as dependent variable, the metric for target\_efficiency is ROAS. For conversion, it's CPA. If `target_value = NULL`, it'll be set to default value that is 80% of initial ROAS or 120% of initial CPA. In this example, we're setting `target_value = 1.5`, which is a target ROAS of 1.5.

```c
# Script 1
AllocatorCollect <- robyn_allocator( 
 InputCollect = InputCollect,   
 OutputCollect = OutputCollect,   
 select_model = "1_123_2",   
 # date_range = NULL, # Default last month as initial period   
 scenario = "target_efficiency",   
 target_value = 1.5, # Customize target ROAS or CPA value   
 export = TRUE )
```

Please note that this example uses another selected model (ID 1\_123\_2) than the previous note. Therefore, the initial performance is different. Below in figure 1 is the one-pager result.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*ejZqlp4bLsTNrRtSxY8_lg.jpeg)

Figure 1: The new Robyn budget allocator scenario “target\_efficiency” for ROAS in v3.10.1

### 1st section — total budget optimization

1. The total initial spend of 932k is the same as in the last note, even though a different model is selected. Raw spend for the same period doesn’t change regardless of model selection. The initial total marketing ROAS in the first block is 1.64 that is simply the total response of 1.53M divided by the total spend of 932k in the last 4 weeks.
2. The desired ROAS of `target_value = 1.5` is shown in the title of the second block (blue). This can be also translated into " **How much can I spend without any budget limit until ROAS hits 1.5** ", given the initial ROAS of 1.64. We can see that it's achieved when increasing total spend by 22.3% to 1.14M. The total response also increased by 12.2% to 1.71M. Due to the law of diminishing return, it's generally true that the efficiency metric will decrease on a higher spend level, with an exception of the beginning part of the S shape saturation curves.
3. The third block (gold) is hard-coded to be `ROAS = 1` as a reference target. Similar to the "unbounded allocation" in max\_response, we believe that providing a further target can better showcase the potential of budget allocation and thus better assist budget decision making. For ROAS, the target of 1 is a significant threshold often used to evaluate the break-even point. In other words, " **How much can I spend without any budget limit until marketing break-even** "? We can observe that this imaginary advertiser can spend 3.31M until the total response equals to total spend.

### 2nd & 3rd sections — Budget allocation & saturation curve per media

These two sections show the media-level comparison between the three pillars with spend share, response share, ROAS, mROAS as well as the respective saturation curves. More details these and the calculation can be found in the [previous note](https://fb.workplace.com/notes/897004158170692).

In the example in figure 1, we can observe the following:

- **No budget upper limit**: All channels increase budget in both targets of 1.5 and 1. The reason is that “target\_efficiency” doesn’t have upper budget limit, because this scenario has a strong explorative character and is especially designed for growth advertiser use cases. The guiding question is “ **How much can I spend without any budget limit until marketing break-even?”** On the saturation curve plots, we can see that the budget upper bounds per media is set to infinite, while all blue & gold dots have higher spend level than the initial grey dots. In comparison, when “max\_response” from the previous note uses the same initial total budget for allocation, the budget allocation is rather a zero-sum game, with some channels increased and the others decreased.
- **mROAS convergence when ROAS = 1**: Similar to the previous note, we can observe the channel level mROAS convergence with the total marketing ROAS = 1 target in the 2nd section and 3rd block (gold) in figure 1, when 4 out of 5 channels are approaching mROAS of about 0.2. The convergence of ROAS to the equilibrium state is often achieved when there’s less constraints or more freedom in the optimisation.

**Targeting CPA** in the allocator works very similarly as with ROAS. When setting `dep_var_type = "conversion"` in the model input, the target efficiency metric is automatically changed to CPA instead. For CPA, the question can be formulated as " **how much can I spend without any budget limit until CPA hits X?**" As in script 2 shown below, all arguments remain the same as for ROAS. The only difference is the target\_value that is adapted to a meaningful level for CPA for this specific selected model.

```c
# Script 2

> InputCollect$dep_var_type 
[1] "conversion"

AllocatorCollect <- robyn_allocator( 
 InputCollect = InputCollect,   
 OutputCollect = OutputCollect,   
 select_model = select_model,   
 # date_range = "last_4", # Default last month as initial period   
 scenario = "target_efficiency",   
 target_value = 40, # Customize target ROAS or CPA value   
 export = create_files 
)
```

As in figure 2 below, we can see the allocation result for target\_value = 40 in the blue block in the middle. As for the right block in gold, the extended target CPA level is set to be 1.5x of the target\_value, which is 40 \* 1.5 = 60 in this example. Interestingly, however expected, we can also observe the the convergence of mCPA when having a larger freedom of optimisation, as highlighted in the red circle in the channel level insights.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*pisLeS0dxhOyGt7DABG4Xg.jpeg)

Figure 2: The new Robyn budget allocator scenario “target\_efficiency” for CPA in v3.10.1

## Understanding saturation, the foundation of budget allocation

To better understand the allocator under the hood, let’s first look at the saturation transformation that is the foundation for budget allocation. In Robyn, we use the two-parametric Hill function to derive the nonlinear saturation curve. Below is an example of how the Hill function is implemented in Robyn, with alpha and gamma as the parameters.

```c
# Script 3

# x_adstockediis a vector s a adstocked media spend variableocked media. Alpha & gamma are the parameters for the Hill function

# calculate inflexion point from gamma
inflexion <- c(range(x_adstocked) %*% c(1 - gamma, gamma))

# Hill transformation -> derive saturation curve
x_saturated <- x_adstocked ^ alpha / (x_adstocked ^ alpha + inflexion ^ alpha)
```

Hill is a flexible function that is able to output wide range of curves from C- to S-shapes. In figure 3 below, we can see that alpha controls the shape, and gamma the inflexion point of the curve. The x-axis represents spend and y-axis the response. When alpha < 1, the curve has a C shape. When alpha > 1, the curve has an S shape. The larger the gamma, the higher the inflexion point and thus the later the media starts to saturate.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*jVkJCuCWMgIouWb1QbN9NA.jpeg)

Figure 3: This visualisation can be generated with plot\_saturation(plot = TRUE)

Now, figure 4 below is the zoom-in of figure 1 and shows the saturation curves for all channels from the selected model. The shapes of the curves are determined by the alpha and gamma in the table below. For example, we can see that the C-shape from ooh\_S is induced by the alpha of 0.54 while the S-shape of facebook\_S is has alpha of 2.86.

```c
channel     alphas     gammas
facebook_S  2.859418   0.3082975
ooh_S       0.544481   0.7115405
print_S     0.854705   0.7753609
search_S    2.931675   0.9202952
tv_S        1.39326    0.9229643
```
![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*olT_PzVp9rhJY_N0yVpPIQ.jpeg)

Figure 4: Saturation curve zoom-in from figure 1

It’s a very powerful knowledge to understand how alpha and gamma influence the saturation curve. We’ve seen users with very strong domain knowledge about their media saturation, for example saying “We believe that channel A much has a minimum reach of x to have measurable effect. We’ve also been overspending on channel A up to 150k recently and thus expect the saturation happens at around 120k.” This assumption can be implemented as followed:

- No effect without minimum reach means that there’s a “build-up” phase of this channel, where lower spend level has limited effect. This indicates a typical S curve that can be enforced by setting alpha to >1. By default, we recommend an alpha range of 0.5–3. This knowledge can narrows it down to 1–3.
- Saturation at 120k out of 150k indicates a higher saturation position closer to the maximum spend level, meaning the inflexion point of the S curve, or the point of highest marginal response, should not happen too late. By default, we recommend a gamma range of 0.3–1. With this knowledge, we can set a mid-range gamma of 0.3–0.7 to induce an earlier inflexion range, so that the saturation happens at the higher end of the spend range.

## How does budget allocation work technically

The goal of budget allocation is maximising the response given a certain spend level. Looking at figure 4 above, this goal can be rewritten as the following:

**Identifying a point on each saturation curve so that**

- **the sum of values from all points on the y axis is maximised and**
- **the sum of values from all points on the x axis is equal to a certain spend level.**

In Robyn, the saturation curve is induced by the Hill function as specified in script 3 above. In the field of optimisation, this is a gradient-based nonlinear optimisation problem with equality constraint. Again, we can rewrite the goal above as pseudo code:

- **Objective function (pseudo code)**:
```c
maximise(sum(optimum_spend_per_channel ^ alpha / 
      (optimum_spend_per_channel ^ alpha + inflexion ^ alpha)))
```
- **Equality constraint (pseudo code)**:
```c
sum(optimum_spend_per_channel) == certain_budget
```

Robyn uses SLSQP, or Sequential Least Square Quadratic Programming, from the [library ‘nloptr’](https://nlopt.readthedocs.io/en/latest/NLopt_Algorithms/#slsqp) to solve this problem. To quote the documentation, SLSQP uses “successive second-order approximations of the objective function with first-order approximations of the constraints”. We can see Robyn’s implementation of the objective function and equality constraint in script 4.

```c
# Script 4

fx_objective <- function(x, coeff, alpha, inflexion, x_hist_carryover) {
  
  # Adstock scales
  xAdstocked <- x + mean(x_hist_carryover)
  
  # Hill transformation
  xOut <- coeff * ((1 + inflexion ^ alpha / xAdstocked ^ alpha) ^ -1)
  
  return(xOut)
 }
 
eval_g_eq <- function(X) {

  # get function input
  eval_list <- getOption("ROBYN_TEMP")
  
  # equality constraint
  constr <- sum(X) - eval_list$total_budget_unit
  
  # gradient
  grad <- rep(1, length(X))
  
  return(list("constraints" = constr, "jacobian" = grad))
 }
```

## The technical difference between “target\_efficiency” & “max\_response”

The section above explained the details of the scenario “ `max_response` " in Robyn. The new scenario " `target_efficiency` " uses the same objective function, because the task of maximising response is common for all. The difference lies in the constraints.

- In `scenario = "max_response"`, the equality constraint requires the sum of spend to be equal to a given spend level that is a constant. In other words, " **what the maximum response given a total budget level** ".
- In `scenario = "target_efficiency"`, the sum of spend needs to be equal to the proportion of the sum of response that is a variable. In other words, " **what the maximum response when the total budget equals response times a constant x** ", while x is either the desired ROAS or CPA.

The script 5 below shows the implementation of the equality constraint function for `target_efficiency`. We can see that, compared to a rather simple linear constraint in script 4, we use the objective function `fx_objective()` itself to obtain the variable sum of response. Finally, the constraint function is equaling sum of spend to the sum of response, with ROAS or CPA as the desirable multiplier.

```c
# Script 5

eval_g_eq_effi <- function(X, target_value) {

  # get function input
  eval_list <- getOption("ROBYN_TEMP")
 
  # get total response
  sum_response <- sum(mapply(
   fx_objective,
   x = X,
   coeff = eval_list$coefs_eval,
   alpha = eval_list$alphas_eval,
   inflexion = eval_list$inflexions_eval,
   x_hist_carryover = eval_list$hist_carryover_eval,
   SIMPLIFY = TRUE
  ))
  
  # constraint with target_value as ROAS / CPA tuner
  if (eval_list$dep_var_type == "conversion") {
    
    # For CPA target
    constr <- sum(X) - sum_response * target_value
    
  } else {
     
   # For ROAS target
   constr <- sum(X) - sum_response / target_value
    
  }
```

> ***This article is co-authored with*** [***Bernardo Lares***](https://www.linkedin.com/in/laresbernardo/) ***and*** [***myself***](https://www.linkedin.com/in/gufeng-zhou-96401721/)***.***

[![Gufeng Zhou](https://miro.medium.com/v2/resize:fill:96:96/0*pxqDNWTwFI3we1iO)](https://medium.com/@gufengzhou?source=post_page---post_author_info--274ace3add4f---------------------------------------)[10 following](https://medium.com/@gufengzhou/following?source=post_page---post_author_info--274ace3add4f---------------------------------------)

Meta Marketing Science. Author of "Robyn", the open source MMM package from Meta. [https://github.com/facebookexperimental/Robyn](https://github.com/facebookexperimental/Robyn)

## Responses (2)

Kakasarnold

```ts
Thank you Gufeng for a really nice walkthrough! One thing I don't get is why in this example you are targeting to decrease the ROAS and increase the CPA. Shouldn't it be the other way around? Marketers are normally trying to achieve higher returns and lower costs
```

1

```ts
Can you implement same functionality in Python?
```