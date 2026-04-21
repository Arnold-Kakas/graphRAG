---
title: "Bayesian Media Mix Modeling using PyMC3, for Fun and Profit"
source: "https://engineering.hellofresh.com/bayesian-media-mix-modeling-using-pymc3-for-fun-and-profit-2bd4667504e6"
author:
  - "[[Luca Fiaschi]]"
published: 2020-08-24
created: 2026-04-20
description: "Bayesian Media Mix Modeling using PyMC3, for Fun and Profit Michael Johns, Zhenyu Wang, Bruno Dupont, and Luca Fiaschi “If you can’t measure it, you can’t manage it, or fix it” –Mike …"
tags:
  - "clippings"
---
## [HelloTech](https://engineering.hellofresh.com/?source=post_page---publication_nav-ac51da0a699a-2bd4667504e6---------------------------------------)

[![HelloTech](https://miro.medium.com/v2/resize:fill:76:76/1*21bfFIjN4ybVTEpqQURdiw.png)](https://engineering.hellofresh.com/?source=post_page---post_publication_sidebar-ac51da0a699a-2bd4667504e6---------------------------------------)

The HelloFresh engineering blog

*Michael Johns, Zhenyu Wang, Bruno Dupont, and Luca Fiaschi*

> *“If you can’t measure it, you can’t manage it, or fix it”*
> 
> *–Mike Bloomberg*

Knowing where to allocate marketing dollars and how much to spend is a perennial business problem. The complexity of modern marketing only adds to this challenge. Contemporary measurement methods rely heavily on data from online web-tracking (cookies) that provide only a limited view of advertising touchpoints in the customer journey and could be further jeopardized by new privacy regulations [(Juneau, 2020)](https://www.forbes.com/sites/forbesagencycouncil/2020/05/18/digital-marketing-in-a-cookie-less-internet/#3517153b21e2%5C). To get a comprehensive picture of how well marketing budgets are working requires an approach that can account for online (e.g. search, social media, etc.) and offline (TV, radio, etc.) marketing activities with both direct and indirect effects. Media Mix Modeling (MMM) provides one solution to this problem.

This post describes how we built a Media Mix Model of customer acquisition to optimize a yearly budget in the hundreds of millions of dollars. We describe the model, some of the challenges we faced when building it, and discuss how it is used to guide marketing strategy.

## What is a Marketing Mix Model (MMM)?

Media mix modeling is a statistical modeling technique for quantifying the effectiveness of advertising on business metrics like new customer acquisitions. MMMs have been in use since the 1960’s (e.g., Borden, 1964) and are common in many industries.

Our MMM is designed to estimate the incremental impact of a marketing channel (think Facebook, podcasting, online display ads) on the number of new subscribers. These estimates can be used to better understand and optimize the efficiency of different allocations of our marketing budget (media mix). The MMM is especially helpful in quantifying the impact of offline channels like television, billboards, or radio advertising, which are difficult to assess using digital measurement solutions.

## How we built our MMM

We developed our model based on the approach described in [Jin et al. (2017)](https://research.google/pubs/pub46001/). They propose using Bayesian methods to build a multivariable regression model with transformations on marketing activity variables (e.g., spending) which account for diminishing returns and lagged effects of impressions. Using Bayesian methods gives us the ability to incorporate our prior knowledge about marketing effects into the model and produce results that are easier to use in practice while being consistent with field experiments such as lift tests.

In the core modeling framework, marketing dollars spent each week in specific channels (e.g., Hulu, Facebook, direct mail, banner ads, etc.) are used to predict the total number of new customers acquired that week. Spend per channel is transformed using a saturation function to capture diminishing returns on advertising. Channels that can have decaying effects over time, like TV, are further transformed with a function to capture such lagged effects. Control variables are included to account for external factors that can also influence the number of customers signing up each week, such as seasonal variation and discount offers in circulation.

In statistical terms, the model has the following form:

![](https://miro.medium.com/v2/resize:fit:1200/format:webp/1*mRuochvtE63792bgyL4RZw@2x.png)

where ***x\_mt*** is the spend value for a marketing channel ***m*** in week ***t***. Spend is transformed using a saturation and decay function ***f( )***; ***β\_m*** is the effect of channel ***m*** on customer acquisition; ***z\_ct*** is the value of control variable *c* in week *t*; ***β\_c*** is the effect of control variable ***c***; ***e\_t*** is a Normal error term with mean 0 and constant variance.

This means that the number of new customers acquired each week (***y\_t***) is modeled using weekly marketing spend for the different channels while controlling for factors external to marketing. The model produces a coefficient (*β\_m*) for each channel that represents the number of customers that are acquired for each dollar spent, holding all other spending constant. These coefficients are transformed into the total number of new customers that a channel produces. We can then divide the amount spent on the channel by the estimate of customers acquired to get the *incremental customer acquisition cost* (*iCAC*), a standard measure of marketing efficiency.

Traditional statistical models would assume that the relationship between marketing and customer acquisition follows a straight line. This assumption is often too simplistic. The yield from marketing dollars will tend to approach a point of saturation as spending increases. That is, marketing dollars will start to show diminishing returns after reaching a certain spend level. To account for this saturation, marketing spend is transformed using a nonlinear function that can capture the diminishing returns on advertising:

![](https://miro.medium.com/v2/resize:fit:1100/format:webp/1*uHCWkXj84W_-Ih_BxxoHSw@2x.png)

where *μ* is the half-saturation point and *xₘₜ* is the spend value. The shape of this curve, which is determined by the parameter *μ*, is learned for each channel as part of the model fitting process. **Figure 1** illustrates the shape of the logistic function for values of *μ*, ranging from 1 to 7.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/0*hMtlwBj4Cab0C9g6)

Figure (1): logistic saturation function for different parametrizations.

The ability to learn this curve for each input channel while fitting the model is yet another advantage of Bayesian methods.

From a marketing perspective, the channel saturation curve allows us to identify the range of spend where we will get the most “bang” for our marketing dollars. The curve can also be plotted against the estimated CAC,(*x* ₘₜ / β *ₘ* *f(xₘₜ)*), to help understand how quickly efficiency will decrease as spending increases. This pattern can be seen in **Figure 2**: the CAC generally increases — an indicator of lower efficiency — as spending increases.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/0*P5oBLI-42COiqw-6)

Figure (2): CAC function for different parameterizations and levels of weekly marketing spend.

In addition to saturation effects, the impact of offline marketing is often distributed over time. Marketing channels with these sorts of decaying effects are further transformed using an adstock function. Advertising adstock is the idea that the impact of advertising peaks at a certain point and continues to have a successively weaker effect for some time period after that peak. We use a geometric decay weight that assumes the effect of advertising peaks at the time of exposure and then decreases over time. The weight function controls the rate of decay through the *ɑlpha* parameter.

![](https://miro.medium.com/v2/resize:fit:1100/format:webp/1*-ktWMJzu2IhlMfLI4eI90w@2x.png)

**Figure 3** below illustrates the shape of the adstock function with different assumptions about how slowly the impact of media exposure can decay.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/0*iDA1YEC_t3abpUZI)

Figure (3): Adstock function for different levels of parameter alpha.

A longer adstock means that the effect of advertising persists longer. The length of the adstock is also learned during the model fitting process. Adstock decay is typical for channels like television or radio — the type of advertising that produces multiple impressions over time. The length of the adstock decay gives us additional insight into how a channel functions. A short decay can suggest a short product consideration time; a long decay suggests that it takes some time before prospective customers decide to adopt the product.

## Accounting for the Marketing Funnel

The mixture of marketing channels is often organized into a funnel. **Figure 4** illustrates how we might organize offline and online marketing channels based on our knowledge of the way different types of advertising can influence the customer journey.

![](https://miro.medium.com/v2/resize:fit:1200/format:webp/1*gD84zpNkUUN3U2jC9HFMVQ.png)

Figure (4): Schematic representation of the marketing funnel.

Offline, brand channels are typically placed at the top of the funnel; online, direct response channels tend to fall at the bottom. The idea is that channels at the top of the funnel create awareness and interest that drives prospective customers to online channels at the bottom of the funnel before converting.

One implication of the funnel structure is that offline marketing can have a significant downstream effect on certain online channels, a phenomenon referred to as a “funnel effect”. For example, after hearing a podcast ad, a prospective customer would need to go online, where they might encounter search engine marketing. Including channels in the model from all levels of the funnel implies that the amount spent in each channel can be equally impactful in driving conversions. In reality, the amount spent on channels like Search Engine Marketing is more often a product of spending on brand marketing higher up in the funnel (e.g. on TV). Failing to consider these hierarchical relationships in the model could produce misleading results.

==To deal with these potential funnel effects we estimate the efficiency of marketing spend in two steps. In the first step we fit the core MMM (described above and depicted in== ==**Figure 5**====) while excluding spend from a set of== ==***mediating***== ==channels at the bottom of the funnel:== ==*search engine marketing*====,== ==*affiliate marketing,*== ==and== ==*online leads*====. Leaving these downstream channels out of the model gives channels further up in the funnel the opportunity to get credit for the downstream impacts that would otherwise be obscured. We call this the== ==**direct model**====.==

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/0*7CHmObTBXGG1wXGT)

Figure (5): Schematic representation of the direct model.

In the second step, we then use the same set of marketing channels to model the amount of weekly *spend* (not conversions)for *search engine marketing, affiliate marketing,* and *online leads*. The coefficients from this ***lower-funnel*** model tell us how much marketing spend in the “top” of the funnel is absorbed by these channels at the “bottom” of the funnel. We call this the **undirect model** and is depicted in **Figure 6.**

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/0*gva9PHW3aAp8ufYj)

Figure (6): Schematic representation of the undirect model.

Spend estimates from the directed model are then corrected using the undirected one, producing a funnel-adjusted CAC. Calculating the CAC using the adjusted spend provides a more accurate picture of each channel’s marketing efficiency. **Figure 6** shows how the CACs can shift following adjustment for lower-funnel impacts.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*nbWMEK5suVXPv_zGeGbg_Q.png)

Figure (6): Comparison between adjusted and un-adjusted CAC for multiple channels.

The mathematical formulation of our fully adjusted *CAC\** for each time-step *t* and upper-funnel channel *m* is:

![](https://miro.medium.com/v2/resize:fit:1200/format:webp/1*KioZ3XSIIYPGieR6Sj_Nww@2x.png)

Where *η\_mt* is a spend adjustment obtained by calculating the effect of the upper funnel channel on the lower funnel spend. And *ξ\_mt* is a seasonal adjustment to conversions obtained by redistributing the extra conversions from seasonal variables. These coefficients are derived from the models for total conversions (*y\_t***,** direct model**)** and total lower funnel spend (undirect model) as follows:

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*X5gmcWPTfsWV-o_0Px9shw@2x.png)

## Making the Model Interpretable and Actionable

A major goal that guided our approach was ensuring that the results would be *plausible, interpretable, and actionable*. Outputs from inferential models — models that describe relationships — can be difficult to understand and apply in practice. Using a Bayesian modeling approach provides several advantages in accomplishing this goal.

Fitting a Bayesian model requires first specifying a *prior* on the model coefficient being estimated. The prior defines a range of possible values for the channel estimate and a proposal for how likely those values are to occur. It is essentially an educated guess about how much a particular channel influences conversions. The model then uses the observed marketing data to update the proposal encoded in the prior. The most likely value after updating the priors is our best estimate for the marketing channel coefficient.

Specifying a prior for each channel estimate makes it possible to set constraints on the results to ensure they fall within a sensible range. For example, it is highly unlikely that marketing would ever have a negative impact on customer acquisition. We, therefore, constrain all channel estimates to be non-negative.

With the prior, we can also use information from lift tests or incrementality analyses to tune model estimates and make them consistent with external benchmarks. Once built, the model is then continually evaluated and adjusted as we conduct tests and get new information about the effectiveness of our marketing. This makes the MMM extremely adaptable to changes in the marketing landscape. We can also incorporate feedback from channel managers to adjust estimates that are unrealistically large or small. As a result, we can provide outputs that are consistent with existing knowledge and responsive to stakeholder needs.

## Building a Bayesian MMM in PyMC3

The sample code below illustrates how to implement a simple MMM with priors and transformation functions using PyMC3. For this toy example, we assume that there are three marketing channels *(X1, X2, X3)* and one control variable (*Z1*). ==Each marketing channel is transformed using a saturation function to model diminishing returns.==

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/0*SfcvSVra4GE5d3xt)

Building a model requires first defining priors on the unknown parameters to be estimated: *intercept*; marketing channel, *beta*; control variable, *c\_beta*; saturation curve shape parameter, *half\_sat*; likelihood noise, *sigma*. **Figure 7** shows the shape of key prior distributions, which are based on the recommendations of Jin et al. (2017).

![](https://miro.medium.com/v2/resize:fit:1100/format:webp/0*sEiWLj6ZLpojrlQt)

Figure (7): Shape of the prior distribution for the parameters beta (Half Normal).

We next define the model of the expected number of activations, *mu*, as a linear combination of baseline conversions, the spend in the marketing channels, and the impact of the control variable. This model defines the mean of the likelihood function for the outcome, *y\_obs*, which is represented as a normal distribution with mean *μ* and variance *σ* in a linear regression model. Once the model is defined, we sample from the resulting probability space to produce the posterior distributions of the model parameters. **Figure 8** shows a sample trace plot that displays the history of the sampling process for a model parameter.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/0*P2pMM61-aqEwh3sd)

Figure (8): Traceplot from a fit of the directed model.

The inspection of the trace plot is used to confirm that the sampling process was able to effectively explore the probability space and converge on a valid distribution. Additionally, it is typical to check model performance by conducting a *posterior predictive check* (PPC). Data are simulated from the fitted model and compared to the observed data. Variation in the simulated data can be used to build plausibility intervals that are similar in spirit to a confidence interval. **Figure 9** shows a sample PPC with a 95% plausibility interval for predicted and observed data.

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*QmzsHvlclLDMg41DgEcLlg.png)

Figure (9): Prediction sampled by the directed model with actual data.

Inferences for the target variable and the parameters can then be extracted using the mean (or median) and area of highest probability density of the posterior distributions.

## Putting the MMM to Use

MMMs have several applications. As noted, a common use is quantifying the effectiveness and efficiency of marketing. This is particularly important for monitoring offline channels that are difficult to measure on a continuous basis. It also helps us identify lower funnel online channels that tend to absorb some of the influence of upper funnel channels. Taken as a whole, the model gives us an integrated view of channel performance and inter-channel dynamics.

While an MMM can help fill knowledge gaps, the overarching purpose of the model is to provide insights that can inform strategic planning. We use *iCAC* estimates from the model to identify channels that are underperforming, as well as those that are highly efficient. Spend can then be shifted between channels to produce an overall mix that maximizes the total efficiency of our marketing.

To do this, we plug model coefficients into a *constrained optimization algorithm* to generate recommendations for how to distribute our marketing budget, *B*, to maximize the number of conversions in a certain period of time:

![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*AA-Rc7lsshBuV8MrNfDQcQ@2x.png)

The optimization routine uses a nonlinear gradient method to find the spend levels for our channels that will produce the lowest *blended* CAC (i.e., *total spend / total conversion*), given constraints on overall and channel-level budgets (defined by the two *b\_mt* constants and the value of *B*). Constraints are discussed with marketing stakeholders to ensure optimization is performed under realistic conditions and results are actionable. By comparing the algorithmic recommendations to historical spending patterns we can identify new channel development opportunities that might go unnoticed when looking at a single channel in isolation.

## Conclusion

Media mix modeling is a powerful tool for measuring and managing a complex marketing mix. By accounting for marketing spend saturation, advertising decay, and the marketing funnel hierarchy, the MMM offers a flexible tool for evaluating the performance of both online and offline marketing channels. Moreover, using a Bayesian framework provides us with the ability to incorporate existing marketing knowledge into the model. The MMM will continue to evolve in form and function as it is calibrated based on lift tests of various marketing channels. In the meantime, we will also keep exploring other areas where this model can be helpful, such as demand forecasting and business planning.

## References

\[1\] Borden, N. H. (1964). [The concept of the marketing mix](https://motamem.org/wp-content/uploads/2019/07/Borden-1984_The-concept-of-marketing-mix.pdf). *Journal of advertising research, 4, 2–7*.

\[2\] Jin, Y., Wang, W., Sun, Y., Chan, D., & Koehler, J. (2017). [*Bayesian methods for media mix modeling with carryover and shape effects*](https://research.google/pubs/pub46001/)*.* Google Research.

\[3\] Juneau, T. (2020). [*Digital Marketing In a Cookie Less Internet*](https://www.forbes.com/sites/forbesagencycouncil/2020/05/18/digital-marketing-in-a-cookie-less-internet/#56aa295921e2). Forbes.

\[4\] Chan, D., Perry, M. (2017) [*Challenges And Opportunities In Media Mix Modeling*](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/45998.pdf), Google Research.

[![Luca Fiaschi](https://miro.medium.com/v2/resize:fill:96:96/0*72KFRrAa0vLIWk2d.)](https://medium.com/@lucafiaschi?source=post_page---post_author_info--2bd4667504e6---------------------------------------)[149 following](https://medium.com/@lucafiaschi/following?source=post_page---post_author_info--2bd4667504e6---------------------------------------)

CDAO @ Mistplay | ex-HelloFresh | ex-Rocket Internet. Tech executive with more than 15 years of driving business growth through AI, ML Ops and Data Science.

## Responses (7)

Kakasarnold