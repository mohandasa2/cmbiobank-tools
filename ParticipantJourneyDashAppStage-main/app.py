# app.py
import os
import re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, dcc, html, Input, Output, State, ctx

# ---------- CONFIG ----------
CSV_TIMELINE = "timeline 10-21-26.csv"
CSV_THERAPY = "RespTargetedTherapy23.csv"
CSV_NONTHERAPY = "new_Nondata25.csv"
CHUNK_SIZE = 40

SELECT_ALL = "Select All"
DESELECT_ALL = "Deselect All"
CONTROL_VALUES = {SELECT_ALL, DESELECT_ALL}

# --- Mappings ---
timepoint_marker = {
    "Archival": "circle",
    "Baseline": "square",
    "On Treatment": "triangle-up",
    "On Treatment (Fresh)": "triangle-up",
    "Progression": "triangle-down",
    "Post-Treatment (No progression)": "diamond",
}
specimen_colors = {
    "Bone Marrow": "grey",
    "Formalin Fixed Paraffin Embedded Tissue": "blue",
    "Blood": "green",
    "Fresh Tissue": "purple",
    "Frozen Tissue": "pink",
    "Formalin Fixed Tissue": "orange",
}

# ---------- Helpers ----------
def numeric_sort(participant_ids):
    def get_number_after_dash(pid):
        m = re.search(r"-(\d+)", str(pid))
        return int(m.group(1)) if m else float("inf")

    return sorted(participant_ids, key=get_number_after_dash)


def load_data():
    df_ = pd.read_csv(CSV_TIMELINE)
    df2_ = pd.read_csv(CSV_THERAPY)
    df3_ = pd.read_csv(CSV_NONTHERAPY)
    return df_, df2_, df3_


def make_dropdown_options(values):
    return (
        [
            {"label": SELECT_ALL, "value": SELECT_ALL},
            {"label": DESELECT_ALL, "value": DESELECT_ALL},
        ]
        + [{"label": v, "value": v} for v in values]
    )


def normalize_dropdown_value(values):
    if values is None:
        return [SELECT_ALL]

    sel = list(values) if isinstance(values, (list, tuple)) else [values]

    if DESELECT_ALL in sel:
        return []

    if SELECT_ALL in sel and len(sel) > 1:
        sel = [v for v in sel if v != SELECT_ALL]

    return sel


def selection_state(values, all_values):
    """
    Returns:
      state = 'off' | 'all' | 'selected'
      effective_values = list of values to use when needed
    """
    values = normalize_dropdown_value(values)

    if not values:
        return "off", []

    if SELECT_ALL in values:
        return "all", list(all_values)

    return "selected", [v for v in values if v not in CONTROL_VALUES]


def apply_assessment_filter(df_in, selected_timepoints, mode="any"):
    """
    Any selected:
        - keep only rows whose Assessment timepoint is selected
    Must have all selected:
        - keep only participants who have all selected timepoints
        - then show only the selected rows for those participants
    """
    if selected_timepoints is None:
        return df_in

    if DESELECT_ALL in selected_timepoints:
        return df_in.iloc[0:0].copy()

    if not selected_timepoints or SELECT_ALL in selected_timepoints:
        return df_in

    selected_set = set(map(str, selected_timepoints))
    df_selected = df_in[df_in["Assessment timepoint"].astype(str).isin(selected_set)].copy()

    if mode == "any":
        return df_selected

    participant_tp = (
        df_in[["participant ID", "Assessment timepoint"]]
        .dropna()
        .assign(**{"Assessment timepoint": lambda x: x["Assessment timepoint"].astype(str)})
        .groupby("participant ID")["Assessment timepoint"]
        .apply(set)
    )

    keep_ids = participant_tp[
        participant_tp.apply(lambda s: selected_set.issubset(s))
    ].index

    return df_selected[df_selected["participant ID"].isin(keep_ids)]


def apply_base_filters(disease_values, specimen_values, assessment_values, assessment_mode):
    disease_state, disease_vals = selection_state(disease_values, all_diseases)
    specimen_state, specimen_vals = selection_state(specimen_values, all_specimens)
    assessment_state, assessment_vals = selection_state(assessment_values, all_assessments)

    if disease_state == "off" or specimen_state == "off" or assessment_state == "off":
        return df.iloc[0:0].copy(), disease_vals, specimen_vals, assessment_vals

    filtered = df[df["Disease type"].isin(disease_vals)]
    filtered = filtered[filtered["Specimen category"].isin(specimen_vals)]
    filtered = apply_assessment_filter(filtered, assessment_vals, assessment_mode)
    filtered = filtered[filtered[SPEC_DAYS_COL].notna()]
    return filtered, disease_vals, specimen_vals, assessment_vals


def matching_participant_ids_from_therapy(df_source, subject_col, therapy_col, selected_values):
    if not selected_values:
        return set()
    return set(
        df_source[df_source[therapy_col].isin(selected_values)][subject_col]
        .astype(str)
        .str.strip()
        .unique()
    )


# ---------- Build app ----------
app = Dash(__name__, title="Participant Timeline Viewer")
server = app.server

df, df_second, df_nontherapy = load_data()

# ---------- Normalize / clean ----------
df = df.copy()
df_second = df_second.copy()
df_nontherapy = df_nontherapy.copy()

df.columns = (
    df.columns.astype(str)
    .str.replace("\ufeff", "", regex=False)
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)
)
df_second.columns = (
    df_second.columns.astype(str)
    .str.replace("\ufeff", "", regex=False)
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)
)
df_nontherapy.columns = (
    df_nontherapy.columns.astype(str)
    .str.replace("\ufeff", "", regex=False)
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)
)

# IDs
df["participant ID"] = df["participant ID"].astype(str).str.strip()
df_second["Subject"] = df_second["Subject"].astype(str).str.strip()
df_nontherapy["Subject"] = df_nontherapy["Subject"].astype(str).str.strip()

# Strings
for col in ["Disease type", "Specimen category", "Assessment timepoint"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()

if "Targeted Therapy" in df_second.columns:
    df_second["Targeted Therapy"] = df_second["Targeted Therapy"].astype(str).str.strip()

# Standardize non-targeted therapy column name once
NONTHERAPY_COL = next(
    (c for c in df_nontherapy.columns if c.lower().strip() == "non targeted therapy"),
    None,
)
if NONTHERAPY_COL is None:
    raise ValueError(f"Couldn't find 'Non Targeted Therapy'. Columns: {list(df_nontherapy.columns)}")

df_nontherapy = df_nontherapy.rename(columns={NONTHERAPY_COL: "Non Targeted Therapy"})
NONTHERAPY_COL = "Non Targeted Therapy"
df_nontherapy[NONTHERAPY_COL] = df_nontherapy[NONTHERAPY_COL].astype(str).str.strip()

# Numeric x axis
SPEC_DAYS_COL = "Specimen collection event (days from enrollment)"
df[SPEC_DAYS_COL] = pd.to_numeric(df[SPEC_DAYS_COL], errors="coerce")

# Targeted therapy numeric dates
T_START = "Start Date from Enrollment"
T_END = "End Date from Enrollment"
if T_START in df_second.columns:
    df_second[T_START] = pd.to_numeric(df_second[T_START], errors="coerce")
if T_END in df_second.columns:
    df_second[T_END] = pd.to_numeric(df_second[T_END], errors="coerce")

# Non-targeted therapy numeric dates
NS_COL = "N-startDate from enrollment"
NE_COL = "N-endDate from enrollment"
if NS_COL in df_nontherapy.columns:
    df_nontherapy[NS_COL] = pd.to_numeric(df_nontherapy[NS_COL], errors="coerce")
if NE_COL in df_nontherapy.columns:
    df_nontherapy[NE_COL] = pd.to_numeric(df_nontherapy[NE_COL], errors="coerce")

# ---------- Dropdown options ----------
all_diseases = sorted(df["Disease type"].dropna().unique())
all_specimens = sorted(df["Specimen category"].dropna().unique())
all_assessments = sorted(df["Assessment timepoint"].dropna().unique())
all_targeted = sorted(df_second["Targeted Therapy"].dropna().unique())
all_nontargeted = sorted(df_nontherapy[NONTHERAPY_COL].dropna().unique())

disease_options = make_dropdown_options(all_diseases)
specimen_options = make_dropdown_options(all_specimens)
assessment_options = make_dropdown_options(all_assessments)
targeted_options_all = make_dropdown_options(all_targeted)
nontargeted_options_all = make_dropdown_options(all_nontargeted)

# ---------- Layout ----------
app.layout = html.Div(
    [
        html.H2("Participant Timeline Viewer"),
        html.H4("updated as on: 10/21/2026"),

        html.Div(
            [
                html.Div(
                    [
                        html.Label("Disease Types"),
                        dcc.Dropdown(
                            id="disease-dropdown",
                            options=disease_options,
                            value=[SELECT_ALL],
                            multi=True,
                            clearable=False,
                        ),
                    ],
                    style={"flex": "1"},
                ),
                html.Div(
                    [
                        html.Label("Targeted Therapy"),
                        dcc.Dropdown(
                            id="therapy-dropdown",
                            options=targeted_options_all,
                            value=[SELECT_ALL],
                            multi=True,
                            clearable=False,
                        ),
                    ],
                    style={"flex": "1"},
                ),
                html.Div(
                    [
                        html.Label("Non Targeted Therapy (Misc)"),
                        dcc.Dropdown(
                            id="nontherapy-dropdown",
                            options=nontargeted_options_all,
                            value=[SELECT_ALL],
                            multi=True,
                            clearable=False,
                        ),
                    ],
                    style={"flex": "1"},
                ),
                html.Div(
                    [
                        html.Label("Specimen Category"),
                        dcc.Dropdown(
                            id="specimen-dropdown",
                            options=specimen_options,
                            value=[SELECT_ALL],
                            multi=True,
                            clearable=False,
                        ),
                    ],
                    style={"flex": "1"},
                ),
                html.Div(
                    [
                        html.Label("Assessment Timepoint"),
                        dcc.Dropdown(
                            id="assessment-dropdown",
                            options=assessment_options,
                            value=[SELECT_ALL],
                            multi=True,
                            clearable=False,
                        ),
                    ],
                    style={"flex": "1"},
                ),
            ],
            style={"display": "flex", "gap": "12px", "marginBottom": "12px"},
        ),

        html.Div(
            [
                html.Div(
                    [
                        html.Label("Assessment Match Mode"),
                        dcc.RadioItems(
                            id="assessment-mode",
                            options=[
                                {"label": "Any selected", "value": "any"},
                                {"label": "Must have all selected", "value": "all"},
                            ],
                            value="any",
                            inline=True,
                        ),
                    ],
                    style={"flex": "1", "paddingLeft": "12px", "paddingTop": "22px"},
                ),
            ],
            style={"display": "flex", "gap": "12px", "marginBottom": "12px"},
        ),

        html.Div(
            [
                html.Button(
                    "⬇ Download Specimen + Assessment",
                    id="download-specimen-btn",
                    n_clicks=0,
                    style={"marginRight": "8px"},
                ),
                html.Button(
                    "⬇ Download Therapy Data",
                    id="download-therapy-btn",
                    n_clicks=0,
                    style={"marginRight": "8px"},
                ),
                html.Span(id="info-text"),
            ],
            style={"marginBottom": "12px"},
        ),

        dcc.Download(id="download-specimen-data"),
        dcc.Download(id="download-therapy-data"),

        dcc.Slider(
            id="page-slider",
            min=0,
            step=1,
            value=0,
            tooltip={"placement": "bottom", "always_visible": False},
        ),
        dcc.Graph(id="timeline-graph", config={"displayModeBar": True, "scrollZoom": True}),
        html.Div(
            id="debug",
            style={"whiteSpace": "pre-wrap", "fontFamily": "monospace", "marginTop": "12px"},
        ),
    ],
    style={"width": "98%", "margin": "auto", "fontFamily": "Arial"},
)

# ---------- Dropdown option callbacks ----------
@app.callback(
    Output("therapy-dropdown", "options"),
    Output("therapy-dropdown", "value"),
    Input("disease-dropdown", "value"),
)
def update_therapy_options(selected_diseases):
    state, disease_vals = selection_state(selected_diseases, all_diseases)
    if state == "off":
        return targeted_options_all, [SELECT_ALL]

    participants = df[df["Disease type"].isin(disease_vals)]["participant ID"].unique()
    therapies = sorted(
        df_second[df_second["Subject"].isin(participants)]["Targeted Therapy"]
        .dropna()
        .unique()
    )
    return make_dropdown_options(therapies), [SELECT_ALL]


@app.callback(
    Output("nontherapy-dropdown", "options"),
    Output("nontherapy-dropdown", "value"),
    Input("disease-dropdown", "value"),
)
def update_nontherapy_options(selected_diseases):
    state, disease_vals = selection_state(selected_diseases, all_diseases)
    if state == "off":
        return nontargeted_options_all, [SELECT_ALL]

    participants = df[df["Disease type"].isin(disease_vals)]["participant ID"].unique()
    therapies = sorted(
        df_nontherapy[df_nontherapy["Subject"].isin(participants)][NONTHERAPY_COL]
        .dropna()
        .unique()
    )
    return make_dropdown_options(therapies), [SELECT_ALL]


# ---------- Normalize dropdown selections ----------
@app.callback(Output("disease-dropdown", "value"), Input("disease-dropdown", "value"), prevent_initial_call=True)
def norm_disease(sel):
    return normalize_dropdown_value(sel)


@app.callback(Output("specimen-dropdown", "value"), Input("specimen-dropdown", "value"), prevent_initial_call=True)
def norm_specimen(sel):
    return normalize_dropdown_value(sel)


@app.callback(Output("assessment-dropdown", "value"), Input("assessment-dropdown", "value"), prevent_initial_call=True)
def norm_assessment(sel):
    return normalize_dropdown_value(sel)


@app.callback(Output("therapy-dropdown", "value"), Input("therapy-dropdown", "value"), prevent_initial_call=True)
def norm_therapy(sel):
    return normalize_dropdown_value(sel)


@app.callback(Output("nontherapy-dropdown", "value"), Input("nontherapy-dropdown", "value"), prevent_initial_call=True)
def norm_nontherapy(sel):
    return normalize_dropdown_value(sel)


# ---------- Main plot callback ----------
@app.callback(
    Output("timeline-graph", "figure"),
    Output("page-slider", "max"),
    Output("page-slider", "marks"),
    Output("page-slider", "value"),
    Output("info-text", "children"),
    Input("disease-dropdown", "value"),
    Input("therapy-dropdown", "value"),
    Input("nontherapy-dropdown", "value"),
    Input("specimen-dropdown", "value"),
    Input("assessment-dropdown", "value"),
    Input("assessment-mode", "value"),
    Input("page-slider", "value"),
)
def update_plot(
    disease_values,
    therapy_values,
    nontherapy_values,
    specimen_values,
    assessment_values,
    assessment_mode,
    page_idx,
):
    disease_state, disease_vals = selection_state(disease_values, all_diseases)
    specimen_state, specimen_vals = selection_state(specimen_values, all_specimens)
    assessment_state, assessment_vals = selection_state(assessment_values, all_assessments)
    targeted_state, targeted_vals = selection_state(therapy_values, all_targeted)
    nontherapy_state, nontherapy_vals = selection_state(nontherapy_values, all_nontargeted)

    if disease_state == "off" or specimen_state == "off" or assessment_state == "off":
        fig = go.Figure()
        fig.update_layout(title="No participants found for selected filters.")
        return fig, 0, {}, 0, "No participants found."

    filtered, _, _, _ = apply_base_filters(disease_values, specimen_values, assessment_values, assessment_mode)

    if filtered.empty:
        fig = go.Figure()
        fig.update_layout(title="No participants found for selected filters.")
        return fig, 0, {}, 0, "No participants found."

    # AND logic across active therapy filters:
    # - selected therapy values restrict participants
    # - Select All or Deselect All do not restrict participants
    final_pids = set(filtered["participant ID"].astype(str).str.strip().unique())

    if targeted_state == "selected":
        targeted_pids = matching_participant_ids_from_therapy(
            df_second, "Subject", "Targeted Therapy", targeted_vals
        )
        final_pids &= targeted_pids

    if nontherapy_state == "selected":
        nontherapy_pids = matching_participant_ids_from_therapy(
            df_nontherapy, "Subject", NONTHERAPY_COL, nontherapy_vals
        )
        final_pids &= nontherapy_pids

    filtered = filtered[filtered["participant ID"].astype(str).str.strip().isin(final_pids)]

    participants = numeric_sort(filtered["participant ID"].unique())
    total = len(participants)

    if total == 0:
        fig = go.Figure()
        fig.update_layout(title="No participants found for selected filters.")
        return fig, 0, {}, 0, "No participants found."

    chunks = [participants[i:i + CHUNK_SIZE] for i in range(0, total, CHUNK_SIZE)]
    max_page = len(chunks) - 1

    triggered = ctx.triggered_id
    if triggered == "page-slider":
        page_idx = max(0, min(page_idx or 0, max_page))
    else:
        page_idx = 0

    current_chunk = chunks[page_idx]
    marks = {i: {"label": str(i + 1)} for i in range(len(chunks))}
    participant_y = {pid: i for i, pid in enumerate(current_chunk[::-1])}

    height_px = max(600, len(current_chunk) * 20)
    fig = make_subplots(rows=1, cols=1)

    # specimen connecting lines
    for pid in current_chunk:
        p_df = filtered[filtered["participant ID"] == pid].sort_values(SPEC_DAYS_COL)
        if p_df.empty:
            continue
        xs = p_df[SPEC_DAYS_COL].tolist()
        ys = [participant_y[pid]] * len(xs)
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line=dict(color="black", width=0.2),
                showlegend=False,
            )
        )

    # specimen scatter points
    added_legend = set()
    for tp, marker in timepoint_marker.items():
        tp_df = filtered[filtered["Assessment timepoint"].astype(str) == str(tp)]
        for cat, color in specimen_colors.items():
            subset = tp_df[
                (tp_df["Specimen category"] == cat)
                & (tp_df["participant ID"].isin(current_chunk))
            ]
            if subset.empty:
                continue

            xs = subset[SPEC_DAYS_COL]
            ys = subset["participant ID"].map(participant_y)
            name = f"{tp} | {cat}"
            show_legend = name not in added_legend
            added_legend.add(name)

            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="markers",
                    marker=dict(symbol=marker, size=12, color=color),
                    name=name,
                    showlegend=show_legend,
                    hovertemplate=(
                        "Participant: %{text}<br>"
                        "Day: %{x}<br>"
                        f"Timepoint: {tp}<br>"
                        f"Category: {cat}<extra></extra>"
                    ),
                    text=subset["participant ID"],
                )
            )

    # ---------- Therapy overlays ----------
    START_END_MARKER_SIZE = 9
    START_END_MARKER_LINE_WIDTH = 1

    TARGETED_LINE_COLOR = "#B22222"
    TARGETED_START_COLOR = "#3CB371"
    TARGETED_END_COLOR = "#B22222"

    NON_TARGETED_LINE_COLOR = "#4682B4"
    NON_TARGETED_START_COLOR = "#A0DEA0"
    NON_TARGETED_END_COLOR = "#D18F8F"

    # Targeted therapy overlay
    if targeted_state != "off":
        therapy_subset = df_second[df_second["Subject"].isin(current_chunk)].copy()
        if targeted_state == "selected":
            therapy_subset = therapy_subset[therapy_subset["Targeted Therapy"].isin(targeted_vals)]
        therapy_subset = therapy_subset[therapy_subset[T_START].notna()]

        def _collapse_targeted(g: pd.DataFrame) -> pd.Series:
            g = g.copy().sort_values(T_START)
            start = g[T_START].min()
            last = g.iloc[-1]

            if pd.notna(last[T_END]):
                end = last[T_END]
                ongoing = False
            else:
                end = last[T_START]
                ongoing = True

            if pd.notna(start) and pd.notna(end) and end < start:
                end = start

            return pd.Series({"Start": start, "End": end, "Ongoing": ongoing})

        if not therapy_subset.empty and "Targeted Therapy" in therapy_subset.columns:
            by_tx = (
                therapy_subset.groupby(["Subject", "Targeted Therapy"], dropna=False)
                .apply(_collapse_targeted)
                .reset_index()
            )

            by_win = (
                by_tx.groupby(["Subject", "Start", "End", "Ongoing"], dropna=False)["Targeted Therapy"]
                .apply(lambda s: "; ".join(sorted({str(x).strip() for x in s if pd.notna(x) and str(x).strip()})))
                .reset_index(name="Therapies")
            )

            line_key = "Therapy Period"
            start_key = "Targeted Therapy Start"
            end_key = "Targeted Therapy End"

            for _, row in by_win.iterrows():
                pid = row["Subject"]
                y = participant_y.get(pid)
                if y is None or pd.isna(row["Start"]) or pd.isna(row["End"]):
                    continue

                start, end, ongoing = row["Start"], row["End"], bool(row["Ongoing"])
                therapies_str = row["Therapies"] if row["Therapies"] else "(unknown)"

                show_line_leg = line_key not in added_legend
                hover = (
                    "Participant: %{text}<br>"
                    f"Targeted Therapy: {therapies_str}<br>"
                    f"Start: {start}<br>"
                    f"End: {end if not ongoing else 'Ongoing'}<extra></extra>"
                )

                fig.add_trace(
                    go.Scatter(
                        x=[start, end],
                        y=[y, y],
                        mode="lines",
                        line=dict(color=TARGETED_LINE_COLOR, width=2),
                        name=line_key,
                        legendgroup="TG_LINE",
                        showlegend=show_line_leg,
                        hovertemplate=hover,
                        text=[pid, pid],
                    )
                )
                if show_line_leg:
                    added_legend.add(line_key)

                fig.add_trace(
                    go.Scatter(
                        x=[start],
                        y=[y],
                        mode="markers",
                        marker=dict(
                            symbol="x",
                            size=START_END_MARKER_SIZE,
                            color=TARGETED_START_COLOR,
                            line=dict(width=START_END_MARKER_LINE_WIDTH, color=TARGETED_START_COLOR),
                        ),
                        name=start_key,
                        legendgroup="TG_START",
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )

                if not ongoing:
                    fig.add_trace(
                        go.Scatter(
                            x=[end],
                            y=[y],
                            mode="markers",
                            marker=dict(
                                symbol="x",
                                size=START_END_MARKER_SIZE,
                                color=TARGETED_END_COLOR,
                                line=dict(width=START_END_MARKER_LINE_WIDTH, color=TARGETED_END_COLOR),
                            ),
                            name=end_key,
                            legendgroup="TG_END",
                            showlegend=False,
                            hoverinfo="skip",
                        )
                    )

            if start_key not in added_legend:
                fig.add_trace(
                    go.Scatter(
                        x=[None],
                        y=[None],
                        mode="markers",
                        marker=dict(symbol="x", size=START_END_MARKER_SIZE, color=TARGETED_START_COLOR),
                        name=start_key,
                        legendgroup="TG_START",
                        showlegend=True,
                    )
                )
                added_legend.add(start_key)

            if end_key not in added_legend:
                fig.add_trace(
                    go.Scatter(
                        x=[None],
                        y=[None],
                        mode="markers",
                        marker=dict(symbol="x", size=START_END_MARKER_SIZE, color=TARGETED_END_COLOR),
                        name=end_key,
                        legendgroup="TG_END",
                        showlegend=True,
                    )
                )
                added_legend.add(end_key)

    # Non-targeted therapy overlay
    if nontherapy_state != "off":
        nt_subset = df_nontherapy[df_nontherapy["Subject"].isin(current_chunk)].copy()
        if nontherapy_state == "selected":
            nt_subset = nt_subset[nt_subset[NONTHERAPY_COL].isin(nontherapy_vals)]
        nt_subset = nt_subset[nt_subset[NS_COL].notna()]

        if not nt_subset.empty:
            nt_subset["_therapy_clean"] = nt_subset[NONTHERAPY_COL].astype(str).str.strip()
            nt_subset["_is_surgery"] = nt_subset["_therapy_clean"].str.lower().eq("surgery")

            def _collapse_nontargeted(g: pd.DataFrame) -> pd.Series:
                g = g.copy().sort_values(NS_COL)

                start = g[NS_COL].min()
                is_surgery = bool(g["_is_surgery"].any())

                if is_surgery:
                    return pd.Series({
                        "Start": start,
                        "End": np.nan,
                        "Ongoing": False,
                        "NoEnd": True,
                    })

                if g[NE_COL].notna().any():
                    end = g.loc[g[NE_COL].notna(), NE_COL].max()
                    ongoing = False
                else:
                    end = g[NS_COL].max()
                    ongoing = True

                if pd.notna(start) and pd.notna(end) and end < start:
                    end = start

                return pd.Series({
                    "Start": start,
                    "End": end,
                    "Ongoing": ongoing,
                    "NoEnd": False,
                })

            by_tx = (
                nt_subset.groupby(["Subject", NONTHERAPY_COL], dropna=False)
                .apply(_collapse_nontargeted)
                .reset_index()
            )

            by_win = (
                by_tx.groupby(["Subject", "Start", "End", "Ongoing", "NoEnd"], dropna=False)[NONTHERAPY_COL]
                .apply(lambda s: "; ".join(sorted({str(x).strip() for x in s if pd.notna(x) and str(x).strip()})))
                .reset_index(name="Therapies")
            )

            line_key = "Non-Targeted Therapy Period"
            start_key = "Non-Targeted Therapy Start"
            end_key = "Non-Targeted Therapy End"

            for _, row in by_win.iterrows():
                pid = row["Subject"]
                y = participant_y.get(pid)
                if y is None or pd.isna(row["Start"]):
                    continue

                start = row["Start"]
                end = row["End"]
                ongoing = bool(row["Ongoing"])
                no_end = bool(row.get("NoEnd", False))
                therapies_str = row["Therapies"] if row["Therapies"] else "(unknown)"

                if no_end or pd.isna(end):
                    continue

                show_line_leg = line_key not in added_legend
                hover = (
                    "Participant: %{text}<br>"
                    f"Non-Targeted Therapy: {therapies_str}<br>"
                    f"Start: {start}<br>"
                    f"End: {end if not ongoing else 'Ongoing'}<extra></extra>"
                )

                fig.add_trace(
                    go.Scatter(
                        x=[start, end],
                        y=[y, y],
                        mode="lines",
                        line=dict(color=NON_TARGETED_LINE_COLOR, width=1, dash="dash"),
                        name=line_key,
                        legendgroup="NT_LINE",
                        showlegend=show_line_leg,
                        hovertemplate=hover,
                        text=[pid, pid],
                    )
                )
                if show_line_leg:
                    added_legend.add(line_key)

                fig.add_trace(
                    go.Scatter(
                        x=[start],
                        y=[y],
                        mode="markers",
                        marker=dict(
                            symbol="x",
                            size=START_END_MARKER_SIZE,
                            color=NON_TARGETED_START_COLOR,
                            line=dict(width=START_END_MARKER_LINE_WIDTH, color=NON_TARGETED_START_COLOR),
                        ),
                        name=start_key,
                        legendgroup="NT_START",
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )

                if not ongoing:
                    fig.add_trace(
                        go.Scatter(
                            x=[end],
                            y=[y],
                            mode="markers",
                            marker=dict(
                                symbol="x",
                                size=START_END_MARKER_SIZE,
                                color=NON_TARGETED_END_COLOR,
                                line=dict(width=START_END_MARKER_LINE_WIDTH, color=NON_TARGETED_END_COLOR),
                            ),
                            name=end_key,
                            legendgroup="NT_END",
                            showlegend=False,
                            hoverinfo="skip",
                        )
                    )

            if start_key not in added_legend:
                fig.add_trace(
                    go.Scatter(
                        x=[None],
                        y=[None],
                        mode="markers",
                        marker=dict(symbol="x", size=START_END_MARKER_SIZE, color=NON_TARGETED_START_COLOR),
                        name=start_key,
                        legendgroup="NT_START",
                        showlegend=True,
                    )
                )
                added_legend.add(start_key)

            if end_key not in added_legend:
                fig.add_trace(
                    go.Scatter(
                        x=[None],
                        y=[None],
                        mode="markers",
                        marker=dict(symbol="x", size=START_END_MARKER_SIZE, color=NON_TARGETED_END_COLOR),
                        name=end_key,
                        legendgroup="NT_END",
                        showlegend=True,
                    )
                )
                added_legend.add(end_key)

    # layout
    fig.update_yaxes(
        tickmode="array",
        tickvals=list(participant_y.values()),
        ticktext=list(participant_y.keys()),
        automargin=True,
    )
    fig.update_xaxes(title_text="Days from Enrollment")
    fig.update_layout(
        height=height_px,
        margin=dict(l=200, r=320, t=60, b=60),
        legend=dict(orientation="v", x=1.02, y=1),
        title=(
            f"Participant timelines — Page {page_idx + 1} of {len(chunks)} "
            f"(showing {len(current_chunk)} participants)"
        ),
    )

    info = (
        f"Disease: {len(disease_vals)} selected | "
        f"Targeted:{len(targeted_vals)} selected | "
        f"Non-targeted:{len(nontherapy_vals)} selected | "
        f"Specimen: {len(specimen_vals)} selected | "
        f"Assessment: {len(assessment_vals)} selected | "
        f"Participants shown: {total}"
    )

    return fig, max_page, marks, page_idx, info


# ---------- Download 1: specimen + assessment ----------
@app.callback(
    Output("download-specimen-data", "data"),
    Input("download-specimen-btn", "n_clicks"),
    State("disease-dropdown", "value"),
    State("specimen-dropdown", "value"),
    State("assessment-dropdown", "value"),
    State("assessment-mode", "value"),
    prevent_initial_call=True,
)
def download_specimen_data(n_clicks, disease_values, specimen_values, assessment_values, assessment_mode):
    disease_state, disease_vals = selection_state(disease_values, all_diseases)
    specimen_state, specimen_vals = selection_state(specimen_values, all_specimens)
    assessment_state, assessment_vals = selection_state(assessment_values, all_assessments)

    if disease_state == "off" or specimen_state == "off" or assessment_state == "off":
        out = pd.DataFrame({"message": ["No participants (Disease/Specimen/Assessment selection is empty)."]})
        return dcc.send_data_frame(out.to_csv, "specimen_assessment_empty.csv", index=False)

    specimen_filtered = df.copy()
    specimen_filtered = specimen_filtered[specimen_filtered["Disease type"].isin(disease_vals)]
    specimen_filtered = specimen_filtered[specimen_filtered["Specimen category"].isin(specimen_vals)]
    specimen_filtered = apply_assessment_filter(specimen_filtered, assessment_vals, assessment_mode)
    specimen_filtered = specimen_filtered[specimen_filtered[SPEC_DAYS_COL].notna()]

    if specimen_filtered.empty:
        out = pd.DataFrame({"message": ["No specimen rows match the current filters."]})
        return dcc.send_data_frame(out.to_csv, "specimen_assessment_empty.csv", index=False)

    return dcc.send_data_frame(
        specimen_filtered.to_csv,
        "specimen_assessment_data.csv",
        index=False,
    )


# ---------- Download 2: therapy data (all matching participants across all pages) ----------
@app.callback(
    Output("download-therapy-data", "data"),
    Input("download-therapy-btn", "n_clicks"),
    State("disease-dropdown", "value"),
    State("therapy-dropdown", "value"),
    State("nontherapy-dropdown", "value"),
    State("specimen-dropdown", "value"),
    State("assessment-dropdown", "value"),
    State("assessment-mode", "value"),
    prevent_initial_call=True,
)
def download_therapy_data(
    n_clicks,
    disease_values,
    therapy_values,
    nontherapy_values,
    specimen_values,
    assessment_values,
    assessment_mode,
):
    disease_state, disease_vals = selection_state(disease_values, all_diseases)
    specimen_state, specimen_vals = selection_state(specimen_values, all_specimens)
    assessment_state, assessment_vals = selection_state(assessment_values, all_assessments)
    targeted_state, targeted_vals = selection_state(therapy_values, all_targeted)
    nontherapy_state, nontherapy_vals = selection_state(nontherapy_values, all_nontargeted)

    if disease_state == "off" or specimen_state == "off" or assessment_state == "off":
        out = pd.DataFrame({"message": ["No participants (Disease/Specimen/Assessment selection is empty)."]})
        return dcc.send_data_frame(out.to_csv, "therapy_empty.csv", index=False)

    # Match the graph filters across all pages
    timeline_filtered = df.copy()
    timeline_filtered = timeline_filtered[timeline_filtered["Disease type"].isin(disease_vals)]
    timeline_filtered = timeline_filtered[timeline_filtered["Specimen category"].isin(specimen_vals)]
    timeline_filtered = apply_assessment_filter(timeline_filtered, assessment_vals, assessment_mode)
    timeline_filtered = timeline_filtered[timeline_filtered[SPEC_DAYS_COL].notna()]

    final_pids = set(timeline_filtered["participant ID"].astype(str).str.strip().unique())

    # AND logic for active therapy filters
    if targeted_state == "selected":
        targeted_pids = matching_participant_ids_from_therapy(
            df_second, "Subject", "Targeted Therapy", targeted_vals
        )
        final_pids &= targeted_pids

    if nontherapy_state == "selected":
        nontherapy_pids = matching_participant_ids_from_therapy(
            df_nontherapy, "Subject", NONTHERAPY_COL, nontherapy_vals
        )
        final_pids &= nontherapy_pids

    if not final_pids:
        out = pd.DataFrame({"message": ["No participants for current filters."]})
        return dcc.send_data_frame(out.to_csv, "therapy_empty.csv", index=False)

    # Export therapy rows for ALL matching participants, across all pages
    t_out = df_second[df_second["Subject"].isin(final_pids)].copy()
    if targeted_state == "off":
        t_out = t_out.iloc[0:0].copy()
    elif targeted_state == "selected":
        t_out = t_out[t_out["Targeted Therapy"].isin(targeted_vals)]
    t_out["Forms"] = "Targeted therapy"

    nt_out = df_nontherapy[df_nontherapy["Subject"].isin(final_pids)].copy()
    if nontherapy_state == "off":
        nt_out = nt_out.iloc[0:0].copy()
    elif nontherapy_state == "selected":
        nt_out = nt_out[nt_out[NONTHERAPY_COL].isin(nontherapy_vals)]
    nt_out["Forms"] = "Non targeted therapy"

    out = pd.concat([t_out, nt_out], ignore_index=True, sort=False)

    if out.empty:
        out = pd.DataFrame({"message": ["No therapy rows match the current graph filters."]})
        return dcc.send_data_frame(out.to_csv, "therapy_empty.csv", index=False)

    return dcc.send_data_frame(out.to_csv, "therapy_data.csv", index=False)


# ---------- Run ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(debug=True, host="0.0.0.0", port=port)