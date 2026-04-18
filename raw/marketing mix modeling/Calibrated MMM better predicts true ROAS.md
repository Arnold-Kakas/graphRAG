---
title: "Calibrated MMM better predicts true ROAS"
source: "https://medium.com/@gufengzhou/calibrated-mmm-better-predicts-true-roas-d5adfc8abdc4"
author:
  - "[[Gufeng Zhou]]"
published: 2023-03-23
created: 2026-04-17
description: "Calibrated MMM better predicts true ROAS A simulation-based calibration experiment from the Robyn Public Hackathon 2022 This article is co-authored with David Choe, Pratt Hetrakul and myself. Key …"
tags:
  - "clippings"
---
## Key findings

- **Calibrated models are better**: All calibrated models show predicted ROAS closer to true ROAS with smaller MAPE than uncalibrated models.
- **Good for one, good for all**: When only calibrating one from both simulated channels (TV & FB), the other channel also predicts better towards true ROAS than uncalibrated.
- **The more calibrated channels, the better:** Calibrating both simulated channels (TV & FB) shows the lowest error to true ROAS. This is expected, because Robyn’s calibration is designed to recover the true ROAS by having the [calibration error](https://l.workplace.com/l.php?u=https%3A%2F%2Ffacebookexperimental.github.io%2FRobyn%2Fdocs%2Ffeatures%2F%23calibration-with-experiments&h=AT1MyuOvdAmymVE2lUY_gO28c3d1GNvqdyPbrCf9sWwIBnnan7XuArnFh57nU-1o734yCZ5uTmzjok4S5iE1BPo-6FeDNd82GSFmRXlgJKvEewEdhQblKwSvkxgBL7CLOnSpHxI9so_PSjvMtsZm6Q) (MAPE.LIFT) as an objective function within Robyn’s multi-objective optimisation capacity.
- **The more studies to calibrate, the better:** The true ROAS prediction improves strongly with up-to 10 studies per channel.
- This is the **winner project** of the [ROBYN HACKATHON 2022](https://apac-robyn2022.devpost.com/). **Congrats** to [**Yuta Hayakawa**](https://devpost.com/qiringji) and [**Ryosuke Hyodo**](https://devpost.com/hyodo_ryosuke) from Cyber Agent from Japan! Thanks for providing this brilliant proof-of-concept for MMM calibration.
- **Disclaimer**: All datasets are simulated by the hackathon team. The channel naming is random. The results don’t reflect real life channel performance.

## Data simulation setup

Last year, the Meta Marketing Science team hosted [the first ever public hackathon](https://l.workplace.com/l.php?u=https%3A%2F%2Fapac-robyn2022.devpost.com%2F&h=AT1MyuOvdAmymVE2lUY_gO28c3d1GNvqdyPbrCf9sWwIBnnan7XuArnFh57nU-1o734yCZ5uTmzjok4S5iE1BPo-6FeDNd82GSFmRXlgJKvEewEdhQblKwSvkxgBL7CLOnSpHxI9so_PSjvMtsZm6Q) for [Robyn](https://l.workplace.com/l.php?u=https%3A%2F%2Ffacebookexperimental.github.io%2FRobyn%2F&h=AT1MyuOvdAmymVE2lUY_gO28c3d1GNvqdyPbrCf9sWwIBnnan7XuArnFh57nU-1o734yCZ5uTmzjok4S5iE1BPo-6FeDNd82GSFmRXlgJKvEewEdhQblKwSvkxgBL7CLOnSpHxI9so_PSjvMtsZm6Q), the open-sourced package for machine-learning based Marketing Mix Model. Yuta Hayakawa and Ryosuke Hyodo from Cyber Agent, Japan have won the Best Overall and Best Innovation prizes with their [calibration simulation project](https://github.com/qiringji/robyn_hackathon_2022_autumn).

The idea aimed to answer the following questions:

- Does a calibrated MMM better estimate true ROAS?
- If only one channel has experimental result, is it still recommended to calibrate?
- How many experiments are recommended for calibration?

The data simulation package “ [siMMMulator](https://facebookexperimental.github.io/siMMMulator/) ”, another open source project from Meta, is used to generate the simulated MMM datasets. This package allows the users to define true ROAS values for the beta estimates.

The simulation setting:

- 5 years of weekly data
- A revenue with trend and seasonal pattern as dependent variables as well as two media channels (TV & Facebook) are created.
- The parameter `true_cvr` in siMMMulator is the average causal effect of a unit impression of each media.
- The variable `noisy_cvr` in siMMMulator is the causal effect of a unit impression of each media on each campaign.
- On top of siMMMulator’s native capacity, the team has added multicollinearity as well as seasonal pattern into the media variables to better mimic real life situations
- Moreover, the team has also generated RCT (randomized controlled trials) data points based on the simulated true lift for the calibration use cases.
![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*2f-oYDIMCDVjPSsN0JLvhw.jpeg)

Figure 1. Ad spend on each channel by campaign

![](https://miro.medium.com/v2/resize:fit:1130/format:webp/1*jSNT_B43SU_LY1gdQuBdeg.jpeg)

Figure 2. Baseline sales by week

## Experiment design #1：Comparison between 0, 1 & 2 calibrated channels

The goal of this experiment is to prove that models with more calibrated channels can better predict true ROAS. The setting is the following:

**Simulated media**: TV and Facebook

**8 scenarios**:

- No calibration, with or without trend & seasonality (2 scenarios)
- Calibrated only TV, with or without trend & seasonality (2 scenarios)
- Calibrated only FB, with or without trend & seasonality (2 scenarios)
- Calibrated both channels, with or without trend & seasonality (2 scenarios)

**Total iteration**: 3000 per scenario (1000 iterations x 3 trials)

**Evaluation metrics**: MAPE (Mean absolute percentage error) is computed between the true ROAS from the simulation and the estimated ROAS from Robyn

**Assumption**: The team assumes that RCT results reflect the true effect from the simulation. This is achieved by creating RCT results using true conversions directly.

**Result**:

- **Calibrated models are better:** Figure 3 below shows that uncalibrated model results have the largest MAPE of ROAS. All calibrated models show predicted ROAS closer to true ROAS.
- **Good for one, good for all**: When only calibrating TV, FB’s predicted ROAS has MAPE of 1.28, smaller than the uncalibrated MAPE of 1.56. When only calibrating FB, TV’s predicted ROAS has MAPE of 1.72, smaller than the uncalibrated MAPE of 1.82.
- **The more calibrated channels, the better**: In figure 3, calibrating both simulated channels (TV & FB) shows the lowest MAPE of 0.08 for Facebook. While this doesn’t hold true for TV (0.17), we strongly believe that it’s due to the lack of convergence for calibrated models with 3k iterations. It’s to be expected that the MAPE will further decrease if running more iterations to pursue better model convergence.
- **More uncertainty with uncalibrated models**: Looking at the standard deviation in figure 3 & 4 as well as the error bar in figure 5, uncalibrated models have the largest uncertainty, which makes sense considering the nature of calibration is to constrain the predicted response to be closer to the RCT results.
![](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*16QLDmy9gFDO9ZOYS2SpyA.jpeg)

Figure 3. Result table on experiment #1

![](https://miro.medium.com/v2/resize:fit:1360/format:webp/1*OcCXlkcnWWQBU8o9ZMTNVg.jpeg)

Figure 4. MAPE trend by calibration by number of channels calibrated

## Experiment design #2：Number of experiments in each media

The second experiment is to prove that models with more RCT results per channel will predict more accurately toward true ROAS. The setting is the following.

- **Simulated media**: TV and Facebook
- **11 scenarios**: Comparing ROAS prediction error between models with different numbers of RCT studies for each channel for calibration (2, 3, 4, 5, 7, 8, 10, 50, 150, 200 & 260 RCT studies).
- **Total iteration**: 3000 per scenario (1000 iterations x 3 trials)
- **Evaluation metrics**: MAPE (Mean absolute percentage error) is computed between the true ROAS from the simulation and the estimated ROAS from Robyn
- **Assumption**: The team assumes that RCT results reflect the true effect from the simulation. This is achieved by creating RCT results using true conversions directly.

**Result**

- **The more studies to calibrate, the better**: As shown below, it’s obvious that ROAS prediction benefits from more RCT studies for calibration.
- **Sweet spot at 10 studies per channel**: We can observe the MAPE remains stable at the lowest level after >10 RCT studies for calibration, indicating a potential sweet spot of 10 studies per channel. However, we believe this finding needs further confirmation.
![](https://miro.medium.com/v2/resize:fit:1220/format:webp/1*lml4qF49gl_yPqh_L4MDBA.jpeg)

Figure 5. Figure 4. MAPE trend by number of experiments

## Open questions

While we’re excited about the positive confirmation from this experiment, there’re many questions left unanswered.

- Does the number of calibration points needed depend on the overall size of the investments into the channel? (e.g. need more for larger budgets or more varying budgets)
- Would the improvement scale beyond two channels? If there were 5 channels, and we calibrated one, would we see improvement in each of or just the sum of the remaining 4?
- It’s observable in this experiment that when calibrating FB only, TV’s predicted ROAS tends to get closer to FB’s true ROAS and vice versa. Further experiments are needed to deepdive on this.
- How strongly does calibration reduce the predictive power of the model?
- With the latest versions of Robyn, the [contextual calibration](https://fb.workplace.com/notes/1282592612527233) will enable the true ROAS to be calibrated against the immediate effect instead of total. An extra experiment is needed to investigate the performance.

Lastly, we would like to refer to our open source package [GeoLift](https://facebookincubator.github.io/GeoLift/) as a great option to conduct geo-experiments.

[![Gufeng Zhou](https://miro.medium.com/v2/resize:fill:96:96/0*pxqDNWTwFI3we1iO)](https://medium.com/@gufengzhou?source=post_page---post_author_info--d5adfc8abdc4---------------------------------------)[10 following](https://medium.com/@gufengzhou/following?source=post_page---post_author_info--d5adfc8abdc4---------------------------------------)

Meta Marketing Science. Author of "Robyn", the open source MMM package from Meta. [https://github.com/facebookexperimental/Robyn](https://github.com/facebookexperimental/Robyn)

## Responses (3)

Kakasarnold

```c
Hi what do you mean by ‘calibration’ and ‘studies conducted’ in this context?
```

3

```c
Very interesting read Gufeng! Thanks for creating Robyn!

Question: In scenarios where calibration isn’t doable, would you still recommend leveraging MMM? I know the analysis says that increases uncertainty. Curious if the pro still outweighs the con.
```

1

```c
Amazing !
```

1