---
title: "Cost-per-Unit: Model What Drives Revenue, Report What You Spend"
source: "https://www.pymc-marketing.io/en/stable/notebooks/mmm/mmm_cost_per_unit.html"
author:
published:
created: 2026-04-20
description: "Imagine you are a marketing analyst at an e-commerce company. You run two advertising channels — say a social-media channel (measured in impressions) and a TV channel (measured in dollars). Your da..."
tags:
  - "clippings"
---
Imagine you are a marketing analyst at an e-commerce company. You run two advertising channels — say a social-media channel (measured in **impressions**) and a TV channel (measured in **dollars**).

Your data scientist fits a Media Mix Model on this data. The model learns how each channel’s *input* drives *revenue*. But there is a catch: **the two channels are measured in completely different units.** Comparing their returns side-by-side is meaningless unless we first bring them onto a common scale.

## When does this matter?

The impressions-vs-dollars scenario above is just one example. In practice, channels can differ in unit for many reasons:

- **Impressions, clicks, or other engagement metrics** — any non-monetary media input whose price fluctuates over time.
- **Different currencies** — e.g. one channel invoiced in USD and another in EUR. Exchange rates move, so pre-converting to a single currency before fitting bakes FX noise into the predictor.
- **Any heterogeneous unit** — the core idea is the same whenever the raw media input is not directly in the currency you use for reporting.

## Why not just convert everything to dollars upfront?

One obvious solution is to convert every channel to a common dollar unit before fitting — multiply impressions by the cost-per-impression, convert EUR to USD, etc. Simple enough.

But this approach has a serious flaw: **cost-per-unit conversions are not fixed.** The price of an impression fluctuates with auction dynamics, seasonality, competitor activity, and platform pricing changes. Exchange rates move daily. Converting before modelling bakes those price fluctuations directly into the predictor variable, adding noise that has nothing to do with the media’s actual effect on consumers.

When impressions are the causal driver — a consumer *sees* an ad — modelling on impressions keeps the signal clean and separates the *media effect* from the *media cost*.

## The approach: model in native units, convert at reporting time

This is exactly what **`cost_per_unit`** enables. We fit the model on whatever unit best represents each channel’s causal input (impressions, clicks, local currency, etc.) and supply the cost-per-unit separately as a post-fit parameter. This means:

- The model estimates the effect in the channel’s native unit — preserving the true causal relationship.
- At reporting and optimisation time, we apply the cost-per-unit to translate everything into a common currency for fair channel comparison.
- We can update the cost-per-unit assumption without re-fitting the model, making it easy to explore how pricing or exchange-rate changes affect budget recommendations.

In this notebook we will:

1. **Fit** an MMM on the raw data (impressions + dollars)
2. **Inspect** ROAS and saturation curves *before* any unit conversion — and see how misleading they can be
3. **Set `cost_per_unit`** for the social-media channel ($0.10/impression) and watch the story change dramatically
4. **Run budget optimization** under different cost-per-impression assumptions ($0.05, $0.10, $0.15) to see how pricing affects allocation

## A note on choosing the right unit

That said, **there is no universal rule that impressions are always better than spend.** The right choice depends on data quality and the modelling context. If your impression data is unreliable or noisy (e.g. inconsistent tracking across platforms), modelling on spend may actually produce a cleaner signal. It is up to the modeller to decide which unit best represents the true causal input for each channel. `cost_per_unit` supports either direction — you can model on impressions and convert to dollars, or model on spend and convert back.

## Step 1: Load Data and Fit the Model

We use a two-channel dataset from `multidimensional_mock_data.csv`, filtered to `geo_a`. The model is built from a YAML config with `GeometricAdstock` and `MichaelisMentenSaturation`.

```
%load_ext autoreload
%autoreload 2

import warnings

import numpy as np
import pandas as pd
import plotly.io as pio

from pymc_marketing.mmm.builders.yaml import build_mmm_from_yaml
from pymc_marketing.mmm.multidimensional import (
    MultiDimensionalBudgetOptimizerWrapper,
)
from pymc_marketing.paths import data_dir

warnings.filterwarnings("ignore")
pio.renderers.default = "notebook_connected"

df = pd.read_csv(data_dir / "multidimensional_mock_data.csv", parse_dates=["date"])
df_geo_a = df.loc[df["geo"] == "geo_a"].reset_index(drop=True)
x_train = df_geo_a[["date", "x1", "x2"]].rename(columns={"x1": "Social", "x2": "TV"})
# Scale Social to simulate impression-level values (the raw mock data uses a
# smaller scale; multiplying by 10 gives realistic impression counts).
x_train["Social"] = x_train["Social"] * 10
y_train = df_geo_a["y"]
x_train.head()
```

|  | date | Social | TV |
| --- | --- | --- | --- |
| 0 | 2018-04-02 | 1592.900090 | 0.0 |
| 1 | 2018-04-09 | 561.942382 | 0.0 |
| 2 | 2018-04-16 | 1462.001331 | 0.0 |
| 3 | 2018-04-23 | 356.992763 | 0.0 |
| 4 | 2018-04-30 | 1933.725768 | 0.0 |

```
# We use only 2 chains for speed — divergences and convergence warnings
# are expected and harmless for the purposes of this demo.
seed: int = sum(map(ord, "cost_per_unit"))
mmm = build_mmm_from_yaml(
    X=x_train,
    y=y_train,
    config_path=data_dir / "config_files" / "cost_per_unit_example.yml",
    model_kwargs={
        "sampler_config": {
            "chains": 2,
            "tune": 1000,
            "draws": 1000,
            "random_seed": seed,
        }
    },
)
_ = mmm.fit(x_train, y_train)
```

```
Initializing NUTS using jitter+adapt_diag...
Multiprocess sampling (2 chains in 2 jobs)
NUTS: [intercept_contribution, adstock_alpha, saturation_alpha, saturation_lam, y_sigma]
```

```
Sampling 2 chains for 1_000 tune and 1_000 draw iterations (2_000 + 2_000 draws total) took 8 seconds.
There was 1 divergence after tuning. Increase \`target_accept\` or reparameterize.
We recommend running at least 4 chains for robust computation of convergence diagnostics
```

## Step 2: The Misleading Picture — ROAS Without Unit Conversion

Let’s look at the fitted ROAS and saturation curves *as-is*, without any cost-per-unit adjustment. Remember:

- **Social** is in **impressions**
- **TV** is in **dollars**

So the “ROAS” for Social is really *revenue per impression*, while TV’s ROAS is a proper *revenue per dollar*. Comparing them side-by-side is like comparing apples and oranges. Without cost-per-unit adjustment, Social’s apparent ROAS will appear roughly **10x smaller** than TV’s — not because Social is less effective, but because it is being measured in impressions rather than dollars.

```
fig_roas_before = mmm.plot_interactive.roas()
fig_roas_before
```

**Notice how TV dominates.** Its ROAS is expressed in $/$ and looks roughly **10x larger** than Social’s revenue-per-impression metric — exactly as expected when one channel is measured in impressions and the other in dollars.

A naive reading of this chart would suggest: *“TV is far more efficient — pour all the money there.”*

Let’s look at the saturation curves next. The x-axis for each channel is in its *native unit*, so the scales are not comparable.

```
mmm.plot_interactive.saturation_curves()
```

```
Sampling: []
```

The saturation curves above look reasonable individually, but they are **not comparable** — Social Media’s x-axis is *impressions* while TV’s is *dollars*. We cannot visually judge which channel gives more bang for the buck.

---

## Step 3: Setting cost\_per\_unit — Leveling the Playing Field

Now we tell the model what Social Media impressions actually *cost*. By setting `cost_per_unit = \$0.10` for Social Media, we bridge the gap from impressions back to dollars. The model can then express everything in consistent **$/$** terms.

- **`channel_1` (Social Media):** `cost_per_unit = 0.1` ($0.10 per impression)
- **`channel_2` (TV):** `cost_per_unit = 1.0` (already in dollars — this is the default when omitted)

There are **two ways** to attach `cost_per_unit` to a model:

1. **At initialization** — pass the DataFrame directly to the `MMM()` constructor via the `cost_per_unit` parameter. The conversion factors are then applied automatically after `fit()`.
2. **Post-hoc** — call `mmm.set_cost_per_unit(df)` on an already-fitted model, which is what we do below. This is useful when you want to experiment with different cost assumptions without refitting.

```
dates = mmm.data.dates
cost_per_unit_df = pd.DataFrame(
    {
        "date": dates,
        "Social": np.ones(len(dates)) * 0.1,
    }
)
cost_per_unit_df.head(10)
```

|  | date | Social |
| --- | --- | --- |
| 0 | 2018-04-02 | 0.1 |
| 1 | 2018-04-09 | 0.1 |
| 2 | 2018-04-16 | 0.1 |
| 3 | 2018-04-23 | 0.1 |
| 4 | 2018-04-30 | 0.1 |
| 5 | 2018-05-07 | 0.1 |
| 6 | 2018-05-14 | 0.1 |
| 7 | 2018-05-21 | 0.1 |
| 8 | 2018-05-28 | 0.1 |
| 9 | 2018-06-04 | 0.1 |

```
# and now let's set it
mmm.set_cost_per_unit(cost_per_unit_df)
```

### Verifying the Conversion

`get_channel_data()` returns the **raw** values (impressions for Social Media, dollars for TV). `get_channel_spend()` multiplies by `cost_per_unit`, so now **both** columns are in dollars.

```
raw = mmm.data.get_channel_data()
spend = mmm.data.get_channel_spend()
raw_df = (
    raw.isel(date=slice(0, 10)).to_dataframe().unstack("channel").add_suffix("_raw")
)
spend_df = (
    spend.isel(date=slice(0, 10))
    .to_dataframe()
    .unstack("channel")
    .add_suffix("_spend($)")
)
comparison = pd.concat([raw_df, spend_df], axis=1)
comparison
```

<table><thead><tr><th></th><th colspan="2">channel_data_raw</th><th colspan="2">channel_spend_spend($)</th></tr><tr><th>channel</th><th>Social_raw</th><th>TV_raw</th><th>Social_spend($)</th><th>TV_spend($)</th></tr><tr><th>date</th><th></th><th></th><th></th><th></th></tr></thead><tbody><tr><th>2018-04-02</th><td>1592.900090</td><td>0.000000</td><td>159.290009</td><td>0.000000</td></tr><tr><th>2018-04-09</th><td>561.942382</td><td>0.000000</td><td>56.194238</td><td>0.000000</td></tr><tr><th>2018-04-16</th><td>1462.001331</td><td>0.000000</td><td>146.200133</td><td>0.000000</td></tr><tr><th>2018-04-23</th><td>356.992763</td><td>0.000000</td><td>35.699276</td><td>0.000000</td></tr><tr><th>2018-04-30</th><td>1933.725768</td><td>0.000000</td><td>193.372577</td><td>0.000000</td></tr><tr><th>2018-05-07</th><td>235.854931</td><td>0.000000</td><td>23.585493</td><td>0.000000</td></tr><tr><th>2018-05-14</th><td>2121.245524</td><td>0.000000</td><td>212.124552</td><td>0.000000</td></tr><tr><th>2018-05-21</th><td>1669.600873</td><td>439.890918</td><td>166.960087</td><td>439.890918</td></tr><tr><th>2018-05-28</th><td>1265.351424</td><td>0.000000</td><td>126.535142</td><td>0.000000</td></tr><tr><th>2018-06-04</th><td>4690.272079</td><td>0.000000</td><td>469.027208</td><td>0.000000</td></tr></tbody></table>

## Step 4: The True Picture — ROAS After Cost-per-Unit

Now that both channels are in consistent dollar terms, let’s revisit the ROAS chart.

```
fig_roas_after = mmm.plot_interactive.roas()
fig_roas_after
```

**The story has changed dramatically.** Social Media’s ROAS has jumped — because dividing revenue by *actual dollar spend* (impressions × $0.10) instead of raw impression counts gives a much larger number. The two channels are now **much more comparable**.

The takeaway: TV is *not* overwhelmingly better. Social Media delivers competitive returns when measured properly.

Let’s confirm this with the saturation curves, now plotted with a consistent **dollar (Spend)** x-axis.

```
mmm.plot_interactive.saturation_curves(max_value=3)
```

```
Sampling: []
```

Now both saturation curves share the same unit on the x-axis — **dollars spent**. You can directly compare the marginal return of an extra dollar on Social Media vs. TV, which is exactly what you need for budget planning.

---

## Step 5: Budget Optimization with cost\_per\_unit

For budget optimization, we provide a *future* `cost_per_unit` for the planning window. This is independent of the historical values — impression prices may change over time.

The optimizer:

1. Takes a **total dollar budget**
2. Allocates dollars across channels and time periods
3. Converts Social Media’s dollar allocation to *impressions* using `cost_per_unit` before evaluating the response function
4. Returns optimal budgets **in dollars**

```
num_periods = 4
freq = pd.infer_freq(mmm.data.dates)
future_dates = pd.date_range(
    start=mmm.data.dates[-1] + pd.tseries.frequencies.to_offset(freq),
    periods=num_periods,
    freq=freq,
)
budget_wrapper = MultiDimensionalBudgetOptimizerWrapper(
    model=mmm,
    start_date=future_dates[0],
    end_date=future_dates[-1],
)
```

### Sensitivity Analysis: How Impression Price Affects Allocation

The cost per impression is not fixed — it varies with market conditions, bidding strategy, and seasonality. Let’s see how the optimal budget allocation shifts when Social Media impressions cost **$0.05**, **$0.10**, or **$0.15** each.

- **Cheaper impressions ($0.05)** → more impressions per dollar → Social Media becomes more attractive
- **Baseline ($0.10)** → our best estimate of current pricing
- **Expensive impressions ($0.15)** → fewer impressions per dollar → budget shifts toward TV

```
def compare_budgets_optimization_for_different_cpus(budget):
    rates = [0.05, 0.1, 0.15]
    results_list = []
    for rate in rates:
        cpu_df = pd.DataFrame(
            {
                "date": future_dates,
                "Social": [rate] * num_periods,
            }
        )
        budgets, _ = budget_wrapper.optimize_budget(
            budget=budget,
            cost_per_unit=cpu_df,
        )
        row = budgets.to_dataframe(name="budget").reset_index()
        row["cost_per_impression"] = f"${rate:.2f}"
        results_list.append(row)

    comparison_df = pd.concat(results_list)
    return comparison_df.pivot_table(
        index="cost_per_impression",
        columns="channel",
        values="budget",
        aggfunc="sum",
    )

compare_budgets_optimization_for_different_cpus(1000)
```

| channel | Social | TV |
| --- | --- | --- |
| cost\_per\_impression |  |  |
| $0.05 | 470.958946 | 529.041054 |
| $0.10 | 448.043782 | 551.956218 |
| $0.15 | 407.744872 | 592.255128 |

### Reading the Results (Small Budget)

At $1,000 total budget, the optimizer behaves intuitively: as the cost per impression **decreases** (from $0.15 → $0.05), each dollar buys more Social Media impressions, making that channel more efficient. The optimizer responds by shifting more budget toward Social Media.

But does this pattern hold at every budget level? Let’s run the same comparison with **10× the budget** to see:

```
compare_budgets_optimization_for_different_cpus(10_000)
```

| channel | Social | TV |
| --- | --- | --- |
| cost\_per\_impression |  |  |
| $0.05 | 3930.414318 | 6069.585682 |
| $0.10 | 4161.406550 | 5838.593450 |
| $0.15 | 4302.888274 | 5697.111726 |

### Why the Pattern Reverses at Higher Budgets

The $10,000 result is **the opposite** of the $1,000 case: as impressions get *cheaper*, Social actually receives *less* dollar budget. This is counter-intuitive but mathematically correct — it is driven by **saturation**.

At a $1,000 budget the channels still have room to grow: cheaper impressions mean more impressions per dollar, so the channel with the lower cost-per-unit is genuinely more *efficient*. The optimizer rewards that efficiency by shifting budget toward Social.

At $10,000, both channels are deep into their saturation curves. Once a channel is saturated, additional spend yields almost no incremental response. The optimizer’s job reduces to distributing dollars so that each channel *just* reaches its plateau. When impressions are cheap, fewer dollars are needed to buy enough impressions to saturate Social — so the remaining dollars spill over to TV. When impressions are expensive, the optimizer must allocate *more* dollars to Social to purchase the same number of impressions.

In short, at low budgets we are in the **efficiency regime** (cheaper = higher return per dollar → more Social), while at high budgets we enter the **saturation regime** (cheaper = Social saturates with fewer dollars → surplus flows elsewhere).

> **Practical note:** A scenario where *every* channel is deeply saturated is a signal that your budget exceeds the capacity of your current media mix. In practice, rather than pouring money into channels that have already plateaued, this is the point where you should consider **developing new channels** — finding untapped audiences or formats that still offer meaningful marginal returns.

This is exactly the kind of scenario analysis that `cost_per_unit` enables: same model, same posterior — but different economic assumptions about media pricing lead to different optimal strategies.

---

## Key Takeaways

1. **Choose the unit that best represents the causal input** — impressions, clicks, GRPs, or even spend — depending on data quality and modelling context. There is no one-size-fits-all rule; it is the modeller’s call.
2. **Set `cost_per_unit`** to bring every channel onto a common currency (dollars, euros, etc.) for fair ROAS comparisons and budget planning. This also handles cross-currency channels (e.g. USD vs EUR).
3. **Raw ROAS can be misleading** when channels use different units — always check whether you’re comparing apples to apples
4. **Budget optimization respects `cost_per_unit`** — the optimizer works in the common currency internally and converts to channel-native units before evaluating the response function
5. **Sensitivity analysis** with different rates lets you plan for changing media prices or exchange rates without refitting the model

```
%load_ext watermark
%watermark -n -u -v -iv -w
```

```
Last updated: Tue, 10 Mar 2026

Python implementation: CPython
Python version       : 3.12.12
IPython version      : 9.10.0

numpy         : 2.3.5
pandas        : 2.3.3
plotly        : 6.5.2
pymc_marketing: 0.18.2

Watermark: 2.6.0
```