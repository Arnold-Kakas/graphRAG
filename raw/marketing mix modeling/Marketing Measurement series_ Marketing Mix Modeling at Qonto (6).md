---
title: "Marketing Measurement series: Marketing Mix Modeling at Qonto"
source: "https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-part-vi-7bb9805076ba"
author:
  - "[[Louis Magowan]]"
published: 2024-06-14
created: 2026-04-17
description: "Marketing Measurement series: Marketing Mix Modeling at Qonto | Part VI MLOps Hello! In this latest article in Qonto’s six-part Marketing Mix Model (MMM) series we’ll be looking at MLOps and how …"
tags:
  - "clippings"
---
## [The Qonto Way](https://medium.com/qonto-way?source=post_page---publication_nav-a9390fa3f292-7bb9805076ba---------------------------------------)

[![The Qonto Way](https://miro.medium.com/v2/resize:fill:76:76/1*62qiMixIqD-UODkXVUxPOA.png)](https://medium.com/qonto-way?source=post_page---post_publication_sidebar-a9390fa3f292-7bb9805076ba---------------------------------------)

Stories and learnings from the team behind Qonto

## MLOps

![DVC and MLFlow feeding into an MMM machine](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*XNkwuu3dPeoBORI-782n6Q.png)

DVC and MLFlow feeding into an MMM machine

*Hello! In this latest article in Qonto’s six-part Marketing Mix Model (MMM) series we’ll be looking at MLOps and how this can be a boon to MMM projects. We’ll begin by discussing what MLOps is and why it’s important for MMM, then discuss some of the specific MLOps tools that Qonto uses (DVC and MLFlow). We’ll finish by sharing some tips and tricks for other MMM-ers.*

The structure of this article is as follows:

- **Introduction to MLOps**
- **DVC**
- **MLFlow**
- **Tips & tricks**

## Introduction to MLOps

### What is it?

“MLOps”, or “Machine Learning Operations”, refers to the set of practices, tools, and technologies that focus on integrating machine learning workflows into a broader software development and operations lifecycle. It combines the principles of DevOps, data engineering, and machine learning to ensure the efficient and reliable deployment of machine learning models in production environments.

MLOps encompasses a range of activities, including data management, model training and evaluation, model deployment, monitoring, and continuous improvement. It aims to establish a collaborative and automated environment where data scientists, machine learning engineers, and operations teams can work together seamlessly.

### Why does it matter for MMM?

MMMs are complex. They require a broad range of inputs, including macroeconomic indicators, seasonality data, and organic and paid marketing data — and often at quite a high level of granularity. Many of these inputs might also be highly sparse (contain a lot of zeros) and could require pre-processing or dimension reduction in some form. Additionally, in a Bayesian MMM context, there may be a considerable amount of prior beliefs to encode in your model — gathered from either a literature review, expert knowledge gained from your Growth/Marketing stakeholders, or hard business logic specific to your vertical.

Furthermore, if we appreciate that each feature in a model requires a choice of transformation function (for both adstock and saturation), a choice of prior distribution family, a choice of defining distribution parameters and/or bounds for your priors (how strongly to inform it), and also consider the many other parameter and hyperparameter options for MMM (noise priors, choice of likelihood etc.), the complexity of our modeling task quickly explodes. On top of this, the output generated from MMM is enormous — with diagnostics, model metrics and actual MMM results/output for each feature in your model.

In short, there are infinite ways in which you could build your MMM. Keeping track of the decisions you take and the models and outputs those models produce is a challenging task. This is exactly where MLOps can help.

![Table outlining the pain-points of MMM projects that justify the use of MLOps](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*XoDzOi5Fyft7bwNH38v8CQ.png)

Table outlining the pain-points of MMM projects that justify the use of MLOps

### What’s required to implement an MLOps framework?

Depending on the MLOps framework and tools you decide to use, it’s likely that some amount of dev time will be required to implement it. At Qonto, we chose to use a combination of MLFlow and DVC to meet our needs. Most data scientists would likely have the skillset and expertise required to get started with these tools locally (perhaps with some upskilling in MLOps theory/principles). Deploying them and leveraging them as hosted solutions might require some assistance from back-end / site reliability engineers (SRE), however. Indeed, a collaboration between data scientists and SRE was how Qonto’s solution was developed.

It should also be stated though that the benefits of having an MLOps framework in place extend well beyond MMM — **it can be relevant and helpful for any sizable Data Science project.**

As a reference and indicator for the technical knowledge required, the architecture for our MLFlow deployment is provided below. Logging is done in [Kibana](https://www.elastic.co/kibana) and monitoring in [Prometheus](https://prometheus.io/).

![Back-end architecture diagram for MLFlow deployment](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*dcAa87M2MsVUTRkWnXt0UA.png)

Back-end architecture diagram for MLFlow deployment

## DVC

### What is it?

[DVC](https://dvc.org/doc/start), or Data Version Control, is an open-source tool designed to make machine learning projects more manageable, efficient, and reproducible.

Similar to how software developers use Git to manage and track versions of their source code, DVC allows you to version control data, models, pipelines, and experiments (”experiments” in the [MLOps sens](https://dvc.org/doc/start/experiments/experiment-tracking) e — versioned iterations of ML model development).

Git + Gitlab/Github etc are not designed to track changes in data (or indeed in any object other than code) — so storing CSVs in Gitlab is not advised and isn’t scalable (though it’s perhaps acceptable if there’s only a few smaller CSVs). DVC works by storing changes to data / artifacts as metadata — which are themselves then tracked by Git. So Git doesn’t track the data/artifacts themselves — just the DVC metadata for these files. With this in mind, it’s recommended to be fully comfortable working with version control in Git before progressing to DVC.

- **Used locally**: DVC is useful for 1-person projects and for the development phase of modeling.
- **Used in conjunction with remote storage (S3, GCS etc)**: DVC is useful for multi-person projects, or projects that are large, or complex, or mature, or tend towards the side of production (are repeated often).

Initializing DVC is super simple, as the code below shows — but the [Get Started](https://dvc.org/doc/start) documentation for DVC can explain the process in more detail.

```c
# Assuming you've installed dvc already with
# \`pip install dvc\` or \`brew install dvc\`

# Navigate to the Git repository you want to use DVC in
cd path_to_repo
# Initialise the DVC project
dvc init

# Check the DVC config / ignore files that are created and are staged
git status
# Commit the changes
git commit -m "Initialize DVC"
```

### Why does it matter for MMM?

As mentioned previously, MMMs often require a broad range of inputs — many of which, often, may not be available online. For example, the Gross Rating Points or Net Costs from your TV ads will generally not be accessible via an API and may be provided manually by your saleshouse/media agency. Similarly, certain macroeconomic or seasonal data you want to include in your MMM might not live in your data warehouse. Additionally, some of this data may get overwritten and so couldn’t be re-obtained in the future easily, e.g. as negotiated advertising costs for TV might be slightly different to final advertising costs. Ensuring reproducibility and persistence in this context can be difficult.

For pure API/online data — the process is simpler. You could just pull your data, then in 6 months time you could git checkout the version of your pipeline you used for the original data pull, re-run it and get the exact same data as your original pull (*inb4 data engineers yelling at me about what a gross over-simplification this is* 😉). However, with the stakeholder-provided data/manual data that MMMs require, we need some extra help. Enter DVC.

DVC lets you combine your macro, online and offline data into a CSV and track any changes that are made to it. At Qonto, for each iteration of an MMM we deliver, we have our input data versioned right beside the code we used to model it with. Furthermore, by configuring DVC to work with an AWS S3 remote, we can make changes to the data locally, commit, and push those changes, and then other data scientists on the project can run a `dvc pull` to download the latest version of the MMM dataset we’re working with. If ever we’re asked to remodel or reproduce an MMM we previously delivered, we just have to go back in time in Git then use DVC to download the version of the input data from that time. A big headache relief for MMM!

## MLFlow

### What is it?

[MLFlow](https://mlflow.org/docs/latest/index.html) is a versatile, expandable, open-source platform for managing workflows and artifacts across the machine learning lifecycle. It has built-in integrations with many popular ML libraries, but can be used with any library, algorithm, or deployment tool. Some of the [more popular libraries](https://mlflow.org/docs/latest/tracking/autolog.html) even have an `autolog` command such that by adding a single line of code to your workflow/notebook much of your MLOps will automatically be taken care of.

Two of the most important components of MLFlow are its **Experiment Tracking** and its **Model Registry**.

### Experiment Tracking

MLFlow allows you to log and track experiments, including metrics, parameters, artifacts (objects produced by the ML process, e.g. like a saved model) and model environment dependencies.

It helps you keep track of different runs and compare the performance of various models and hyperparameters. All accessible in a neat, polished UI that can be run locally or via a deployment.

For example, this image of the MLFlow Tracking UI shows a chart linking metrics (learning rate and momentum) to a loss metric:

![Example screenshot of MLFlow UI](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*eistfOukhuxCAZyTWhjIgg.png)

🔗 Credit: MLFlow Docs

### Model Registry

The MLFlow Model Registry facilitates collaborative model development by providing a central repository for managing and versioning models. It enables teams to track model lineage, share models, and control access to different versions.

Models can be registered easily via the UI.

![Example screenshot of MLFlow Model Registry UI](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*aHYfIDUscdYcNf9_bIuC0A.png)

🔗 Credit: MLFlow Docs

### MLFlow vs DVC

> But hold on… isn’t a lot of this stuff exactly what DVC does too?

Yes! There is a lot of overlap between DVC’s and MLFlow’s capabilities. However, the two tools have slightly different strengths and weaknesses — and at Qonto we prefer to use them together.

There is of course no 100% accepted answer for how to do MLOps — but we find that:

- MLFlow suits our needs better for Experiment Tracking, Model Versioning, and Model Registering.
- DVC suits our needs better for Data Versioning and Data Storage Management.

### Why does it matter for MMM?

Keeping track of the innumerable ways you could build your MMM and the output it produces is challenging. MLFlow helps out massively here.

It allows us to painlessly keep track of:

- The features we included or excluded from our data and the pre-processing steps we took on them.
- The parameters we used e.g. for our Bayesian priors.
- The hyperparameters we used, e.g. [PyMC sample methods](https://www.pymc.io/projects/docs/en/v4.4.0/api/generated/pymc.sample.html) like `tune`, `chains`, `draws` or test set proportion.
- The model output, diagnostics and evaluation metrics produced for the selection above, e.g. “Dimension reduction via TruncatedSVD produced a test RMSE that was XYZ lower than when I used Linear PCA for the reduction.”
- The Git commit hash for the version of your code/notebook that you ran your model with, e.g. rather than saving 100s of notebooks with names like `Model.ipynb`, `Model2.ipynb`, `Model2_serious.ipynb`, `Model2_super_serious.ipynb`.

For Jupyter fans, the following function might be helpful when trying to get the Git hash directly in the notebook.

```c
import subprocess
def get_git_revision_hash() -> str:
    """
    Retrieve the current Git commit hash of the HEAD revision.

    This function runs the command \`git rev-parse HEAD\` to obtain the commit hash of the HEAD revision
    in the current Git repository. It requires that the command is run within a Git repository and that
    the Git executable is available in the system's PATH.
    Credit to: https://stackoverflow.com/questions/14989858/get-the-current-git-hash-in-a-python-script

    Returns:
        str: A string representing the current Git commit hash, if successfully retrieved.
             If the command fails (e.g., not run within a Git repository or Git is not installed),
             a CalledProcessError will be raised by subprocess.check_output.

    Raises:
        subprocess.CalledProcessError: An error occurred while trying to execute the git command.
    """
    return subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()
```

All of this can then be brought together neatly into something that resembles the code below. All of the logged information can then be easily viewed and compared across models via the MLFlow UI.

## Tips & tricks

There are some minor tips & tricks that we’ve observed which others might find useful in their MMM MLOps as well.

### Give your stakeholders access to the MLFlow deployment

- Create a dedicated experiment (MLFlow folder for storing model runs) and put your best models in there, or whatever models and output you would like your stakeholder to see. Keep this separate from the junk models you produce during development / tuning.
- It’s a low-effort way of ensuring transparency — it gives output directly to stakeholders and helps keep them involved and up-to-date on the model development process.

### Give your models memorable names

- There’s a lot of terminology in MMM and it can often become quite confusing.
- e.g. Marketing Mix Models vs “ *models* ” in MLFlow; incrementality experiments vs “ *experiments* ” in MLFlow.
- Something that started out as a lame joke but actually turned out to be quite useful was naming our model runs using memorable character names in MLFlow (we went for Harry Potter characters in our most recent MMM).
- It sounds silly, but when it comes to discussing the various model candidates you produce and keeping everyone clear what *exactly* you are talking about — it helps!
![Screenshot of MLFlow UI containing memorably-named experiments](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*3lz-nYwnmBLDTPIH_copIg.png)

Screenshot of MLFlow UI containing memorably-named experiments

**Remember**: MLOps is a rapidly evolving and highly opinionated topic — there’s no 100% correct answer, and likely any framework you employ will need to be adapted over time. Some helpful resources for diving into the topic are listed below:

**Recommended resources:**

- [MLOps Concepts course on DataCamp](https://app.datacamp.com/learn/courses/mlops-concepts) — a very short, condensed introduction to the topic.
- [MLOps: Continuous delivery and automation pipelines in machine learning](https://cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning) — nice article from Google.
- [A Gentle Introduction to MLOps](https://towardsdatascience.com/a-gentle-introduction-to-mlops-7d64a3e890ff) — a quality Medium article.
- [Machine Learning Operations (MLOps): Getting Started](https://www.coursera.org/learn/mlops-fundamentals) on Coursera.
- [Detailed description of MLOps and why it’s useful from Databricks (creators of MLFlow)](https://www.databricks.com/glossary/mlops).
- [MLOps specialisation on DeepLearning.AI](https://www.coursera.org/specializations/machine-learning-engineering-for-production-mlops#howItWorks).

*Want to read more? Here’s the full Marketing Measurement series:*

**Marketing Mix Modeling:**

- [Part I: Getting started](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-337b8af11471) *(released 21 May 2024)*
- [Part II: Adstock and saturation](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-82e82c995b39) *(released 22 May 2024)*
- [Part III: Bayes’ Theorem & priors](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-05d28a2cfa18) *(released 23 May 2024)*
- [Part IV: Inputs for a Bayesian model](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-69bc3101d06d) *(released 27 May 2024)*
- [Part V: Specifying a Bayesian model with PyMC](https://medium.com/qonto-way/marketing-measurement-series-marketing-mix-modeling-at-qonto-f214ba550968) *(released 5 June 2024)*
- Part VI: MLOps

**Incrementality testing:**

- [How to invest better in acquisition channels? A $1 million question for Data Science](https://medium.com/qonto-way/how-to-invest-better-in-acquisition-channels-a-1-million-question-for-data-science-591c82b3e0e4) *(released 4 January 2023)*
- [Incrementality test scheduling: velocity vs. validity](https://medium.com/qonto-way/marketing-measurement-series-incrementality-test-scheduling-f7525b713b4a) *(released 19 June 2024)*
- [Getting the best of both worlds in marketing incrementality tests: rapid testing and trusted results](https://medium.com/qonto-way/getting-the-best-of-both-worlds-in-marketing-incrementality-tests-rapid-testing-and-trusted-58243204fc80) *(released 13 November 2024)*

### About Qonto

Qonto makes it easy for SMEs and freelancers to manage day-to-day banking, thanks to an online business account that’s stacked with invoicing, bookkeeping and spend management tools.

Created in 2016 by Alexandre Prot and Steve Anavi, Qonto now operates in 4 European markets (France, Germany, Italy, and Spain) serving 500,000 customers, and employs more than 1,600 people.

Since its creation, Qonto has raised €622 million from well-established investors. Qonto is one of France’s most highly valued scale-ups and has been listed in the Next40 index, bringing together future global tech leaders, since 2021.

Interested in joining a challenging and game-changing company? Take a look at our [open positions](https://qonto.com/en/careers).

Illustrations by Pierre-Alain Dubois[Last published 2 days ago](https://medium.com/qonto-way/the-pmm-busywork-trap-and-the-ai-operating-system-i-built-to-escape-it-8e41a490da87?source=post_page---post_publication_info--7bb9805076ba---------------------------------------)

Stories and learnings from the team behind Qonto