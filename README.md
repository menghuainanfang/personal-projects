# Python Data Science Projects

This repository is an evolving portfolio of end-to-end Python data science case studies. It begins as an independent study inspired by Leonard Apeltsin's *Data Science Bookcamp* and will grow into a collection of reproducible, original projects.

The goal is not to copy the official source code verbatim, but to:

1. Understand the methods.
2. Reimplement the workflows independently.
3. Reproduce and verify results.
4. Modify data, parameters, and methods.
5. Turn selected case studies into original portfolio projects.

## Project roadmap

|  # | Case study                | Core topics                                                   | Status  |
| -: | ------------------------- | ------------------------------------------------------------- | ------- |
| 01 | Probability simulations   | Probability, Monte Carlo simulation, NumPy                    | Planned |
| 02 | Ad-click statistics       | Statistical inference, hypothesis testing, A/B testing        | Planned |
| 03 | Outbreak detection        | Clustering, geospatial analysis, visualization                | Planned |
| 04 | Job-market NLP            | Text processing, TF-IDF, dimensionality reduction, clustering | Planned |
| 05 | Social-network prediction | Graph analysis, feature engineering, machine learning         | Planned |

## Working method

Each case study will progress through the same sequence:

**Implementation → Reproduction → Extension → Independent project**

- **Implementation:** Build the core workflow independently to understand each technique.
- **Reproduction:** Check whether the implementation reproduces the expected behavior and conclusions.
- **Extension:** Change data, parameters, features, or methods and examine the consequences.
- **Independent project:** Develop selected ideas into self-contained portfolio case studies with original framing and analysis.

## Repository structure

```text
.
├── 01-probability-simulations/
├── 02-ad-click-statistics/
├── 03-outbreak-detection/
├── 04-job-market-nlp/
├── 05-social-network-prediction/
└── docs/
    └── PROJECT_README_TEMPLATE.md
```

Each project directory starts with a scoped README. Code, notebooks, tests, figures, and data directories will be added only when the corresponding project begins.

## Reproducibility

Python versions, dependencies, data-acquisition instructions, and execution commands will be documented as each project begins. Random seeds and relevant environment details will be recorded where they affect results.

Datasets will only be redistributed when their licenses permit it. Otherwise, each project will provide instructions for obtaining the data from its original source.

## Progress philosophy

The repository favors clear reasoning and verifiable progress over polished but unexplained output. Project claims will be supported by code, documented assumptions, and reproducible evidence; planned work will remain clearly distinguished from completed work.

## Acknowledgment

The initial study path is inspired by Leonard Apeltsin's *Data Science Bookcamp*. The book provides learning context and case-study inspiration; the implementations and portfolio extensions in this repository are developed independently.

## License

The code and original documentation in this repository are available under the [MIT License](LICENSE). Third-party datasets and other external materials remain subject to their respective licenses and terms.
