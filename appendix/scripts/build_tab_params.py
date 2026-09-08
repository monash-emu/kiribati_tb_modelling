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
    if pd.notna(dist) and str(dist).strip() != '':
        # Render as: distribution (p1, p2) -- if p2 missing, still works
        inside = ', '.join([str(x) for x in (p1, p2) if pd.notna(x) and str(x)!=''])
        return f"{dist} ({inside})" if inside else f"{dist}"
    return str(val)


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
    # Expected columns
    cols = ['parameter','definition','value_or_prior','unit']
    assert list(df.columns) == cols

    # 2) Column alignment with monospaced for code-like columns
    #    - parameter (tt), definition (wrap), value_or_prior (tt), unit (l)
    #    Requires \usepackage{array}, \usepackage{booktabs,longtable} in preamble
    align = r'>{\ttfamily}p{0.28\textwidth} p{0.42\textwidth} >{\ttfamily}p{0.22\textwidth} l'

    header = (
        r'\toprule' + '\n' +
        r'\textbf{Parameter} & \textbf{Definition} & \textbf{Value / Prior} & \textbf{Unit} \\' + '\n' +
        r'\midrule'
    )

    rows = []
    for _, r in df.iterrows():
        row_cells = [r[c] for c in cols]
        rows.append(' {} \\\\'.format(' & '.join(row_cells)))
    body = '\n'.join(rows)

    footer = r'\bottomrule'

    table = (
        r'\begin{longtable}{' + align + '}' + '\n' +
        r'\caption{' + caption + r'}\label{' + label + r'}\\' + '\n' +
        header + '\n' +
        r'\endfirsthead' + '\n' +
        r'\caption[]{' + caption + r' (continued)}\\' + '\n' +
        header + '\n' +
        r'\endhead' + '\n' +
        r'\hline \multicolumn{4}{r}{\textit{Continues on next page}} \\' + '\n' +
        r'\endfoot' + '\n' +
        footer + '\n' +
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
    ap.add_argument('--caption',default='Model parameters',help='LaTeX table caption')
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

    # Select & order columns
    keep = ['parameter', 'definition', 'value_or_prior', 'unit']
    missing = [c for c in keep if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns in Excel: {missing}")

    df = df[keep].copy()

    # Escape LaTeX in all cells
    for col in keep:
        df[col] = df[col].map(latex_escape)

    # Build longtable
    tex = (
        '% NOTE: Requires \\usepackage{booktabs,longtable} in the preamble\n\n' +
        df_to_longtable(df, args.caption, args.label) + '\n'
    )

    Path(args.out).write_text(tex, encoding='utf-8')
    print(f"Wrote {args.out}")

if __name__ == '__main__':
    main()
