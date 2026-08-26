# Kiribati Tuberculosis Screening Model

## Overview

This repository contains the transmission model and analysis code for the study **"From rollout to refinement: using early screening data to model the next phase of population-wide tuberculosis screening in Kiribati"**. The analysis supports the PEARL Study's population-wide TB screening program in South Tarawa, Kiribati.

## Study Purpose

The PEARL Study is implementing population-wide screening for tuberculosis (TB) disease and infection in South Tarawa, Kiribati. This modeling project evaluates the potential impact of different screening strategies and coverage levels to guide the design of the program's next phase (2026–2035).

### Key Research Questions

- How much TB burden (incidence and deaths) could be averted through different screening algorithms at varying coverage levels?
- What is the role of preventive therapy guided by tuberculin skin testing (TST)?
- How important is frontline Xpert MTB/RIF testing compared to alternative diagnostic pathways?
- What is the epidemiological impact of people who are not reached by screening programs?
- Are screening impact projections sensitive to assumptions about transition rates across the TB spectrum?

## Methodology

### Model Framework

The model is a dynamic compartmental transmission model that captures heterogeneity across the TB infection-disease spectrum, including:

- **TB Susceptibility**: Uninfected individuals
- **TB Infection**: Viable *Mycobacterium tuberculosis* infection (including latent TB infection)
- **Active TB Disease**: Undiagnosed and diagnosed disease with treatment pathways
- **Recovery and Immunity**: Post-treatment states

The model incorporates:
- Age-structured demography based on UN data for Kiribati
- Contact patterns derived from empirical contact matrices
- Screening and diagnostic algorithms with realistic sensitivity/specificity
- Preventive therapy effectiveness
- Treatment outcomes and relapse risks

### Model Calibration

The model was calibrated to:
- Epidemiological observations from the PEARL Study screening phase (2024–2025)
- Historical TB notifications in Kiribati
- Demographic data (population, fertility, mortality rates)
- Contact patterns specific to Kiribati

### Screening Algorithms Evaluated

1. **PEARL Algorithm** (baseline): Symptom screening → CXR → frontline Xpert → TST (with preventive therapy)
2. **PEARL without frontline Xpert**: Symptom screening → CXR → TST (with preventive therapy)
3. **Disease screening only**: Symptom screening → CXR → Xpert (no TST-guided preventive therapy)

Coverage levels tested: 65%, 75%, and 85%

## Repository Structure

```
├── code/                          # Main analysis code
│   ├── pyproject.toml            # Python project configuration
│   └── tbh/                      # Main Python package (TB Heterogeneity model)
│       ├── model.py              # Core transmission model
│       ├── age_mixing.py          # Age-structured mixing patterns
│       ├── demographic_tools.py   # Demographic data processing
│       ├── interventions.py       # Screening and treatment interventions
│       ├── runner_tools.py        # Simulation execution utilities
│       ├── outputs.py             # Output generation and aggregation
│       └── plotting.py            # Visualization functions
│
├── data/                          # Input data
│   ├── scenarios.py              # Scenario definitions
│   ├── un_population.csv         # UN population estimates (Kiribati)
│   ├── un_fertility_rates_KIR.csv # UN fertility rates
│   ├── un_mortality.csv          # UN mortality rates
│   └── Rscript/                  # Contact matrices
│       ├── conmat_matrix.R       # R script for contact matrix generation
│       ├── conmat_all_KIR.csv    # Contact matrix for Kiribati
│       └── KIR_pop_2025.csv      # Population structure
│
├── notebooks/                     # Analysis and visualization notebooks
│   ├── manuscript_results.ipynb   # Main results summary
│   ├── manuscript_figs.ipynb      # Manuscript figures
│   ├── full_analysis.ipynb        # Complete analysis workflow
│   ├── mixing_model.ipynb         # Contact pattern analysis
│   ├── sa_outputs.ipynb           # Sensitivity analysis results
│   ├── data_processing.ipynb      # Data preparation and validation
│   ├── check_demographics.ipynb   # Demographic data verification
│   └── test_outputs/              # Test results and diagnostics
│
├── remote_cluster/                # Results from high-performance computing runs
│   ├── outputs/                   # Simulation output directories
│   │   ├── 59094989_new_priors/   # Main posterior samples
│   │   ├── 59223189_sas/          # Sensitivity analysis results
│   │   └── 59293003_longer_runs/  # Extended simulation runs
│   └── scripts/                   # HPC submission scripts
│
├── appendix/                      # Supplementary materials
│   ├── appendix.tex              # Appendix LaTeX document
│   ├── parameterisation.tex       # Model parameterization details
│   ├── tab-params.tex             # Parameter tables
│   └── scripts/                   # Appendix generation scripts
│
├── pixi.toml                      # Project configuration (Pixi package manager)
├── LICENSE                        # License information
└── README.md                      # This file
```

## Installation and Setup

### Prerequisites

- Python 3.9+
- Pixi (package management) or Conda/Mamba
- Jupyter notebook (for running analysis notebooks)
- R (for contact matrix generation, optional)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd kiribati_tb_modelling
   ```

2. **Set up the environment using Pixi**:
   ```bash
   pixi install
   ```
   
   Or using Conda/Mamba:
   ```bash
   conda create -n kiribati_tb python=3.10
   conda activate kiribati_tb
   cd code && pip install -e .
   ```

3. **Install the main package**:
   ```bash
   cd code
   pip install -e .
   ```

## Usage

### Running Analyses

#### 1. View Main Results
```bash
jupyter notebook notebooks/manuscript_results.ipynb
```

#### 2. Generate Manuscript Figures
```bash
jupyter notebook notebooks/manuscript_figs.ipynb
```

#### 3. Run Full Analysis Pipeline
```bash
jupyter notebook notebooks/full_analysis.ipynb
```

#### 4. Examine Sensitivity Analyses
```bash
jupyter notebook notebooks/sa_outputs.ipynb
```

### Running Simulations

The model can be run directly using the `tbh` package:

```python
from tbh.model import TransmissionModel
from tbh.runner_tools import run_simulation

# Create and configure model
model = TransmissionModel(population_size=50000, time_steps=120)

# Add screening intervention
model.add_intervention(coverage=0.85, algorithm='PEARL')

# Run simulation
results = run_simulation(model, num_particles=1000)
```

## Data Sources

- **Demographic data**: UN World Population Prospects
- **TB epidemiology**: PEARL Study observations and historical Kiribati TB notifications
- **Contact patterns**: Empirically derived contact matrices for Kiribati
- **Contact matrix generation**: R scripts in `data/Rscript/`

## Citation

If you use this model or code in your work, please cite:

> [To be updated with published article citation]
> 
> From rollout to refinement: using early screening data to model the next phase of population-wide tuberculosis screening in Kiribati. *The Lancet* (2026).

## Key Files for Reviewers

- **Model implementation**: [code/tbh/model.py](code/tbh/model.py)
- **Main results**: [notebooks/manuscript_results.ipynb](notebooks/manuscript_results.ipynb)
- **Figures**: [notebooks/manuscript_figs.ipynb](notebooks/manuscript_figs.ipynb)
- **Sensitivity analyses**: [notebooks/sa_outputs.ipynb](notebooks/sa_outputs.ipynb)
- **Parameterization**: [appendix/parameterisation.tex](appendix/parameterisation.tex)

See [LICENSE](LICENSE) file for details.

## Contact

For questions about this analysis, please contact the corresponding author.

---
