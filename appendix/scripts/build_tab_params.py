#!/usr/bin/env python3
"""
Generate LaTeX tables of parameters from parameters.xlsx (constant sheet).

Two tables are produced:
- a longtable of general model parameters (parameter, definition, value/prior, unit);
- a compact table of screening-approach sensitivities (rows: screening approaches,
  columns: model compartments).

Usage:
    python3 scripts/build_tab_params.py \
        --xlsx parameters.xlsx \
        --out tab-params.tex \
        --out-sens tab-screening-sens.tex \
        --caption "Model parameters" \
        --label tab-params
"""

import argparse
import pandas as pd
from pathlib import Path


# Parameters matching this prefix go into the screening sensitivity table instead of the main one
SENS_PARAM_PREFIX = 'prev_se_'

# Screening tools that are defined in the spreadsheet but not used in the analysis
IGNORED_TOOLS = ('plts',)

# (spreadsheet key, column header)
SENS_COMPARTMENTS = [
    ('incipient',      r'Incipient\\infection'),
    ('contained',      r'Contained\\infection'),
    ('cleared',        r'Cleared\\or recovered'),
    ('subclin_lowinf', r'Subclinical\\low inf.'),
    ('clin_lowinf',    r'Clinical\\low inf.'),
    ('subclin_inf',    r'Subclinical\\high inf.'),
    ('clin_inf',       r'Clinical\\high inf.'),
]

SENS_TOOLS = [
    ('tst', 'Tuberculin skin test (TST)'),
    ('ssx', 'Symptom screening (SSx)'),
    ('cxr', 'Chest X-ray (CXR)'),
    ('pearl', 'Xpert + CXR'),
]

# Footnote markers attached to cells that carry no sensitivity parameter
SENS_EMPTY_NOTES = {
    (compartment, 'tst'): r'$^{*}$'
    for compartment in ('subclin_lowinf', 'clin_lowinf', 'subclin_inf', 'clin_inf')
}

SENS_TABLE_NOTES = (
    r'$^{*}$These states are not targeted by TST-guided preventive treatment, so no screening flow '
    r'originates from them. They are nevertheless assumed to be TST-positive with probability one when '
    r'computing the modelled TST positivity used as a calibration target.'
)

# Ordered grouping of the main table. Every non-sensitivity parameter must appear exactly once.
PARAM_CATEGORIES = [
    ('Transmission and mixing', [
        'raw_transmission_rate',
        'infection_pop_scale',
        'bg_mixing',
        'a_spread',
        'pc_strength',
        'rel_sus_children',
    ]),
    ('Infection and early progression', [
        'progression_rate_age0',
        'progression_rate_age5',
        'progression_rate_age15',
        'containment_rate_age0',
        'containment_rate_age5',
        'containment_rate_age15',
        'breakdown_rate',
        'clearance_rate',
        'rel_sus_contained',
        'rel_sus_cleared',
    ]),
    ('Active TB disease', [
        'clinical_progression_rate',
        'clinical_regression_rate',
        'infectiousness_gain_rate',
        'infectiousness_loss_rate',
        'rel_infectiousness_subclin',
        'rel_infectiousness_lowinf',
        'tb_mortality_rate_inf',
        'tb_mortality_rate_lowinf',
        'self_recovery_rate',
    ]),
    ('Passive detection and treatment', [
        'recent_detection_rate',
        'passive_detection_inflection',
        'passive_detection_shape',
        'passive_detection_past_frac',
        'tx_duration',
        'pct_neg_tx_death',
        'tpt_completion_perc',
    ]),
    ('Screening reachability', [
        'reachable_pop_frac',
        'rel_detection_unreachable',
        'rel_sus_unreachable',
    ]),
]

CALIBRATED = r'Calibrated'
EXPLORATION = r'Early model exploration'
ASSUMPTION = r'Assumption'
PEARL_OBSERVED = r'Observed during PEARL'

# Parameters whose value is varied, and the model recalibrated, in a sensitivity analysis
VARIED_IN_SENSITIVITY = {
    'clinical_regression_rate',
    'infectiousness_loss_rate',
    'tpt_completion_perc',
    'rel_sus_unreachable',
}

# Provenance of each value or prior, shown in the table's Source column.
PARAM_SOURCES = {
    'raw_transmission_rate': CALIBRATED,
    'infection_pop_scale': r'Full range of possible values',
    'bg_mixing': EXPLORATION,
    'a_spread': EXPLORATION,
    'pc_strength': EXPLORATION,
    'rel_sus_children': r'\cite{roy2014,pelzer2025,cai2025}',
    'progression_rate_age0': r'\cite{ragonnet2017}',
    'progression_rate_age5': r'\cite{ragonnet2017}',
    'progression_rate_age15': r'\cite{ragonnet2017}',
    'containment_rate_age0': r'\cite{ragonnet2017}',
    'containment_rate_age5': r'\cite{ragonnet2017}',
    'containment_rate_age15': r'\cite{ragonnet2017}',
    'breakdown_rate': CALIBRATED,
    'clearance_rate': r'\cite{emery2021,behr2019}',
    'rel_sus_contained': r'\cite{andrews2012}',
    'rel_sus_cleared': r'\cite{verver2005,interrante2015}',
    'clinical_progression_rate': CALIBRATED,
    'clinical_regression_rate': ASSUMPTION,
    'infectiousness_gain_rate': CALIBRATED,
    'infectiousness_loss_rate': ASSUMPTION,
    'rel_infectiousness_subclin': ASSUMPTION,
    'rel_infectiousness_lowinf': r'\cite{behr1999,asadi2022,yang2015}',
    'tb_mortality_rate_inf': r'\cite{ragonnet2021}',
    'tb_mortality_rate_lowinf': r'\cite{ragonnet2021}',
    'self_recovery_rate': r'\cite{ragonnet2021}',
    'recent_detection_rate': CALIBRATED,
    'passive_detection_inflection': CALIBRATED,
    'passive_detection_shape': EXPLORATION,
    'passive_detection_past_frac': CALIBRATED,
    'tx_duration': r'Standard six-month regimen',
    'pct_neg_tx_death': r'Treatment outcomes reported to WHO for Kiribati',
    'tpt_completion_perc': PEARL_OBSERVED,
    'reachable_pop_frac': PEARL_OBSERVED,
    'rel_detection_unreachable': ASSUMPTION,
    'rel_sus_unreachable': ASSUMPTION,
}


latex_escape_map = {
    '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
    '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'
}

def latex_escape(s):
    if pd.isna(s) or s == '':
        return ''
    s = str(s)
    for k,v in latex_escape_map.items():
        s = s.replace(k, v)
    return s


def build_value_or_prior(row) -> str:
    dist = row.get('distribution', '')
    p1   = row.get('distri_param1', '')
    p2   = row.get('distri_param2', '')
    val  = row.get('value', '')
    if pd.isna(dist) or str(dist).strip() == '':
        return format_number(val)
    if str(dist).strip().lower() == 'uniform':
        return rf"$\mathcal{{U}}({format_number(p1)},\,{format_number(p2)})$"
    inside = ', '.join([format_number(x) for x in (p1, p2) if pd.notna(x) and str(x) != ''])
    return f"{dist} ({inside})" if inside else f"{dist}"


def format_number(x) -> str:
    try:
        return f"{float(x):g}"
    except (TypeError, ValueError):
        return latex_escape(x)


def split_sens_param(name: str):
    """Split 'prev_se_<compartment>_<tool>' into its compartment and tool components."""
    compartment, _, tool = name[len(SENS_PARAM_PREFIX):].rpartition('_')
    return compartment, tool


def build_sens_cell(row) -> str:
    dist = str(row.get('distribution', '')).strip()
    if dist == '':
        return format_number(row.get('value', ''))
    p1, p2 = format_number(row.get('distri_param1', '')), format_number(row.get('distri_param2', ''))
    if dist.lower() == 'uniform':
        return rf"$\mathcal{{U}}({p1},\,{p2})$"
    return rf"{latex_escape(dist)} ({p1}, {p2})"


def df_to_sens_table(df, caption, label):
    cells = {}
    for _, r in df.iterrows():
        cells[split_sens_param(str(r['parameter']))] = build_sens_cell(r)

    expected = {(c, t) for c, _ in SENS_COMPARTMENTS for t, _ in SENS_TOOLS}
    unexpected = sorted(k for k in cells if k not in expected)
    if unexpected:
        raise ValueError(f"Unrecognised screening sensitivity parameters: {unexpected}")

    col_headers = [rf'\shortstack{{{header}}}' for _, header in SENS_COMPARTMENTS]
    header = ' & '.join([r'\textbf{Screening approach}'] + col_headers) + r' \\'
    rows = [
        ' & '.join(
            [tool_label]
            + [cells.get((c, tool), '--' + SENS_EMPTY_NOTES.get((c, tool), '')) for c, _ in SENS_COMPARTMENTS]
        ) + r' \\'
        for tool, tool_label in SENS_TOOLS
    ]

    return (
        r'\begin{table}[!ht]' + '\n' +
        r'\centering' + '\n' +
        r'\scriptsize' + '\n' +
        r'\setlength{\tabcolsep}{3pt}' + '\n' +
        r'\caption{' + caption + r'}\label{' + label + '}\n' +
        r'\begin{tabular}{l' + 'c' * len(SENS_COMPARTMENTS) + '}' + '\n' +
        r'\toprule' + '\n' +
        header + '\n' +
        r'\midrule' + '\n' +
        '\n'.join(rows) + '\n' +
        r'\bottomrule' + '\n' +
        r'\end{tabular}' + '\n' +
        r'\par\smallskip' + '\n' +
        r'\begin{minipage}{\textwidth}\raggedright\footnotesize' + '\n' +
        SENS_TABLE_NOTES + '\n' +
        r'\end{minipage}' + '\n' +
        r'\end{table}'
    )


def df_to_longtable(df, caption, label):
    cols = ['definition', 'value_or_prior', 'source']
    assert list(df.columns) == cols + ['parameter']

    align = r'p{0.45\textwidth} >{\centering\arraybackslash}p{0.15\textwidth} p{0.30\textwidth}'

    header = (
        r'\toprule' + '\n' +
        r'\textbf{Parameter} & \textbf{Value / Prior} & \textbf{Source} \\' + '\n' +
        r'\midrule'
    )
    continued = rf'\multicolumn{{3}}{{@{{}}l}}{{\textit{{Table~\ref{{{label}}} continued from previous page}}}} \\[2pt]'

    by_name = df.set_index('parameter')
    rows = []
    for i, (category, names) in enumerate(PARAM_CATEGORIES):
        if i:
            rows.append(r'\addlinespace')
        # The starred row terminator keeps a category heading with the row that follows it
        rows.append(rf'\multicolumn{{3}}{{@{{}}l}}{{\textbf{{{category}}}}} \\*')
        for name in names:
            r = by_name.loc[name]
            rows.append(' {} \\\\'.format(' & '.join(r[c] for c in cols)))
    body = '\n'.join(rows)

    table = (
        r'\begin{longtable}{' + align + '}' + '\n' +
        r'\caption{' + caption + r'}\label{' + label + r'}\\' + '\n' +
        header + '\n' +
        r'\endfirsthead' + '\n' +
        continued + '\n' +
        header + '\n' +
        r'\endhead' + '\n' +
        r'\midrule \multicolumn{3}{r}{\textit{Continues on next page}} \\' + '\n' +
        r'\endfoot' + '\n' +
        r'\bottomrule' + '\n' +
        r'\endlastfoot' + '\n' +
        body + '\n' +
        r'\end{longtable}'
    )
    return table

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--xlsx',   default='parameters.xlsx', help='Path to parameters.xlsx')
    ap.add_argument('--sheet',  default='constant',        help='Sheet name for constant params')
    ap.add_argument('--out',    default='tab-params.tex',  help='Output .tex file')
    ap.add_argument('--caption', default=(
        r'Model parameters. $\mathcal{U}(a,b)$ denotes a uniform prior estimated during calibration; '
        r'all other entries are fixed values. The Source column gives the origin of the value or of the '
        r'prior bounds, and the rationale for each is set out in Section~\ref{sec:params}.'
    ), help='LaTeX table caption')
    ap.add_argument('--label',  default='tab-params',      help='LaTeX table label')
    ap.add_argument('--out-sens',     default='tab-screening-sens.tex', help='Output .tex file for the screening sensitivity table')
    ap.add_argument('--caption-sens', default=(
        r'Sensitivity of each screening approach to the model states it can detect, i.e.\ the probability '
        r'that an individual occupying a given state and screened under that approach is correctly identified. '
        r'$\mathcal{U}(a,b)$ denotes a uniform prior estimated during calibration; dashes indicate states that '
        r'the approach does not target. Because operational constraints meant that frontline Xpert could be '
        r'applied to only 35\% of those screened, the PEARL algorithm is represented as the corresponding '
        r'weighted mixture of its two branches, '
        r'$s^{\mathrm{PEARL}}_k = 0.35\,s^{\mathrm{Xpert+CXR}}_k + 0.65\,s^{\mathrm{CXR}}_k$.'
    ), help='LaTeX caption for the screening sensitivity table')
    ap.add_argument('--label-sens',   default='tab-screening-sens', help='LaTeX label for the screening sensitivity table')
    args = ap.parse_args()

    xlsx_path = Path(args.xlsx)
    df = pd.read_excel(xlsx_path, sheet_name=args.sheet).fillna('')
    df['parameter'] = df['parameter'].astype(str)

    # Drop parameters relating to screening tools that are not part of the analysis
    df = df[~df['parameter'].str.endswith(tuple(f'_{tool}' for tool in IGNORED_TOOLS))].copy()

    # Drop parameters flagged as "Yes" in the optional 'skip' column
    if 'skip' in df.columns:
        df = df[df['skip'].astype(str).str.strip().str.lower() != 'yes'].copy()

    # Screening sensitivities get their own table
    is_sens = df['parameter'].str.startswith(SENS_PARAM_PREFIX)
    sens_df, df = df[is_sens].copy(), df[~is_sens].copy()
    Path(args.out_sens).write_text(
        df_to_sens_table(sens_df, args.caption_sens, args.label_sens) + '\n', encoding='utf-8'
    )
    print(f"Wrote {args.out_sens}")

    # Build value_or_prior
    df['value_or_prior'] = df.apply(build_value_or_prior, axis=1)

    # Map full_text -> definition
    if 'full_text' in df.columns:
        df = df.rename(columns={'full_text': 'definition'})
    elif 'definition' not in df.columns:
        df['definition'] = ''

    # Fail loudly if the spreadsheet and the hand-maintained groupings drift apart
    grouped = [name for _, names in PARAM_CATEGORIES for name in names]
    if len(grouped) != len(set(grouped)):
        raise ValueError('Duplicate parameter in PARAM_CATEGORIES')
    if set(grouped) != set(df['parameter']):
        raise ValueError(
            'PARAM_CATEGORIES does not match the spreadsheet.\n'
            f"  missing from PARAM_CATEGORIES: {sorted(set(df['parameter']) - set(grouped))}\n"
            f"  not in spreadsheet: {sorted(set(grouped) - set(df['parameter']))}"
        )
    if missing_sources := sorted(set(df['parameter']) - set(PARAM_SOURCES)):
        raise ValueError(f'No entry in PARAM_SOURCES for: {missing_sources}')

    # Select & order columns
    keep = ['definition', 'value_or_prior']
    if missing := [c for c in keep if c not in df.columns]:
        raise ValueError(f"Missing expected columns in Excel: {missing}")

    df = df[keep + ['parameter']].copy()

    # Escape LaTeX in cells holding plain text; values and sources already carry markup
    df['definition'] = df['definition'].map(latex_escape)
    df['source'] = df['parameter'].map(PARAM_SOURCES)
    varied = df['parameter'].isin(VARIED_IN_SENSITIVITY)
    df.loc[varied, 'source'] += r', varied in sensitivity analysis'
    df = df[['definition', 'value_or_prior', 'source', 'parameter']]

    # Build longtable
    tex = (
        '% NOTE: Requires \\usepackage{booktabs,longtable} in the preamble\n\n' +
        df_to_longtable(df, args.caption, args.label) + '\n'
    )

    Path(args.out).write_text(tex, encoding='utf-8')
    print(f"Wrote {args.out}")

if __name__ == '__main__':
    main()
