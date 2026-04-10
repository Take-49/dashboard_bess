"""
BESS Dashboard - Battery Energy Storage System Monitoring
Streamlit application with 5-page navigation.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from pathlib import Path

# Must be the first Streamlit command
st.set_page_config(
    page_title="BESS Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS
css_path = Path(__file__).parent / "assets" / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------
import sys
sys.path.insert(0, str(Path(__file__).parent))
from lib.data_loader import (
    load_perfmg_minute,
    load_grid_dispatch_log,
    load_historyalarm,
    load_soe_event,
    load_usrmg_user_log,
    get_perfmg_units,
)


@st.cache_data(ttl=600)
def load_all_data():
    return {
        "perf": load_perfmg_minute(),
        "dispatch": load_grid_dispatch_log(),
        "alarm": load_historyalarm(),
        "soe": load_soe_event(),
        "user_log": load_usrmg_user_log(),
        "units": get_perfmg_units(),
    }


data = load_all_data()

# Plotly theme defaults
PLOTLY_LAYOUT = dict(
    font=dict(family="Inter, Helvetica Neue, sans-serif", color="#1d1d1f"),
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    margin=dict(l=48, r=24, t=40, b=40),
    xaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
    yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
)
APPLE_BLUE = "#0071e3"
COLORS = ["#0071e3", "#34c759", "#ff9500", "#ff3b30", "#af52de", "#5ac8fa"]

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
st.sidebar.title("BESS Dashboard")
page = st.sidebar.radio(
    "Navigation",
    ["概要", "蓄電池モニタリング", "系統状況", "指令ログ", "アラーム・イベント"],
    label_visibility="collapsed",
)

# ---------------------------------------------------------------------------
# 1. Overview page
# ---------------------------------------------------------------------------
if page == "概要":
    st.title("概要")

    perf = data["perf"]
    alarm = data["alarm"]
    soe = data["soe"]

    # Latest values from performance data
    latest = perf.iloc[-1] if not perf.empty else pd.Series(dtype=float)
    prev = perf.iloc[-2] if len(perf) > 1 else pd.Series(dtype=float)

    def _delta(col):
        if col in latest and col in prev:
            d = latest[col] - prev[col]
            return f"{d:+.2f}"
        return None

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("SOC", f"{latest.get('ESS Average SOC', 0):.1f}%", _delta("ESS Average SOC"))
    col2.metric("SOH", f"{latest.get('Average ESS SOH', 0):.1f}%", _delta("Average ESS SOH"))
    col3.metric("有効電力", f"{latest.get('Active power', 0):.2f} kW", _delta("Active power"))
    col4.metric("周波数", f"{latest.get('Frequency', 0):.3f} Hz", _delta("Frequency"))
    col5.metric("未確認アラーム", f"{len(alarm[alarm['Acknowledged'] == 'Unacknowledged'])} 件")

    st.markdown("---")

    # Daily event summary timeline
    st.subheader("日別イベントサマリ")

    dispatch = data["dispatch"]
    dispatch_daily = dispatch.groupby(dispatch["Dispatch Time"].dt.date).size().reset_index()
    dispatch_daily.columns = ["date", "count"]
    dispatch_daily["type"] = "指令"

    soe_daily = soe.groupby(soe["Generation time"].dt.date).size().reset_index()
    soe_daily.columns = ["date", "count"]
    soe_daily["type"] = "SOE"

    alarm_daily = alarm.groupby(alarm["Generation time"].dt.date).size().reset_index()
    alarm_daily.columns = ["date", "count"]
    alarm_daily["type"] = "アラーム"

    combined = pd.concat([dispatch_daily, soe_daily, alarm_daily], ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"])

    fig = px.bar(
        combined, x="date", y="count", color="type",
        barmode="stack",
        color_discrete_sequence=COLORS,
        labels={"date": "日付", "count": "件数", "type": "種別"},
    )
    fig.update_layout(**PLOTLY_LAYOUT, height=350, legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig, use_container_width=True)

    # SOC trend (mini)
    st.subheader("SOC推移（直近）")
    if "ESS Average SOC" in perf.columns:
        fig_soc = go.Figure()
        fig_soc.add_trace(go.Scatter(
            x=perf.index, y=perf["ESS Average SOC"],
            mode="lines", name="SOC",
            line=dict(color=APPLE_BLUE, width=2),
            fill="tozeroy", fillcolor="rgba(0,113,227,0.08)",
        ))
        fig_soc.update_layout(**PLOTLY_LAYOUT, height=280, yaxis_title="%")
        st.plotly_chart(fig_soc, use_container_width=True)


# ---------------------------------------------------------------------------
# 2. ESS Monitor page
# ---------------------------------------------------------------------------
elif page == "蓄電池モニタリング":
    st.title("蓄電池モニタリング")

    perf = data["perf"]

    # Date range filter
    col_from, col_to = st.columns(2)
    date_min = perf.index.min().date()
    date_max = perf.index.max().date()
    with col_from:
        d_from = st.date_input("開始日", date_min, min_value=date_min, max_value=date_max)
    with col_to:
        d_to = st.date_input("終了日", date_max, min_value=date_min, max_value=date_max)
    filtered = perf.loc[str(d_from):str(d_to)]

    # SOC / SOH
    st.subheader("SOC・SOH 推移")
    fig = go.Figure()
    if "ESS Average SOC" in filtered.columns:
        fig.add_trace(go.Scatter(
            x=filtered.index, y=filtered["ESS Average SOC"],
            name="SOC (%)", line=dict(color=COLORS[0], width=2),
        ))
    if "Average ESS SOH" in filtered.columns:
        fig.add_trace(go.Scatter(
            x=filtered.index, y=filtered["Average ESS SOH"],
            name="SOH (%)", line=dict(color=COLORS[1], width=2),
        ))
    fig.update_layout(**PLOTLY_LAYOUT, height=400, yaxis_title="%",
                       legend=dict(orientation="h", y=1.08))
    st.plotly_chart(fig, use_container_width=True)

    # ESS power
    st.subheader("ESS 充放電電力")
    fig2 = go.Figure()
    if "Current total active ESS power" in filtered.columns:
        fig2.add_trace(go.Scatter(
            x=filtered.index, y=filtered["Current total active ESS power"],
            name="有効電力 (kW)", line=dict(color=COLORS[0], width=2),
            fill="tozeroy", fillcolor="rgba(0,113,227,0.06)",
        ))
    if "Current total reactive ESS power" in filtered.columns:
        fig2.add_trace(go.Scatter(
            x=filtered.index, y=filtered["Current total reactive ESS power"],
            name="無効電力 (kvar)", line=dict(color=COLORS[2], width=2),
        ))
    fig2.update_layout(**PLOTLY_LAYOUT, height=350, yaxis_title="kW / kvar",
                        legend=dict(orientation="h", y=1.08))
    st.plotly_chart(fig2, use_container_width=True)

    # PV power
    st.subheader("PV 発電量")
    fig3 = go.Figure()
    if "Total active PV power" in filtered.columns:
        fig3.add_trace(go.Scatter(
            x=filtered.index, y=filtered["Total active PV power"],
            name="PV有効電力 (kW)", line=dict(color=COLORS[1], width=2),
            fill="tozeroy", fillcolor="rgba(52,199,89,0.08)",
        ))
    fig3.update_layout(**PLOTLY_LAYOUT, height=300, yaxis_title="kW")
    st.plotly_chart(fig3, use_container_width=True)


# ---------------------------------------------------------------------------
# 3. Grid Status page
# ---------------------------------------------------------------------------
elif page == "系統状況":
    st.title("系統状況")

    perf = data["perf"]

    col_from, col_to = st.columns(2)
    date_min = perf.index.min().date()
    date_max = perf.index.max().date()
    with col_from:
        d_from = st.date_input("開始日", date_min, min_value=date_min, max_value=date_max)
    with col_to:
        d_to = st.date_input("終了日", date_max, min_value=date_min, max_value=date_max)
    filtered = perf.loc[str(d_from):str(d_to)]

    tab1, tab2, tab3 = st.tabs(["電圧・電流", "電力・力率", "周波数"])

    with tab1:
        # Phase voltages
        st.subheader("三相電圧")
        fig = go.Figure()
        for i, phase in enumerate(["Phase A voltage", "Phase B voltage", "Phase C voltage"]):
            if phase in filtered.columns:
                fig.add_trace(go.Scatter(
                    x=filtered.index, y=filtered[phase],
                    name=phase, line=dict(color=COLORS[i], width=1.5),
                ))
        fig.update_layout(**PLOTLY_LAYOUT, height=350, yaxis_title="kV",
                           legend=dict(orientation="h", y=1.08))
        st.plotly_chart(fig, use_container_width=True)

        # Line voltages
        st.subheader("線間電圧")
        fig2 = go.Figure()
        for i, line_v in enumerate(["A-B line voltage", "B-C line voltage", "C-A line voltage"]):
            if line_v in filtered.columns:
                fig2.add_trace(go.Scatter(
                    x=filtered.index, y=filtered[line_v],
                    name=line_v, line=dict(color=COLORS[i], width=1.5),
                ))
        fig2.update_layout(**PLOTLY_LAYOUT, height=350, yaxis_title="kV",
                            legend=dict(orientation="h", y=1.08))
        st.plotly_chart(fig2, use_container_width=True)

        # Phase currents
        st.subheader("三相電流")
        fig3 = go.Figure()
        for i, phase in enumerate(["Phase A current", "Phase B current", "Phase C current"]):
            if phase in filtered.columns:
                fig3.add_trace(go.Scatter(
                    x=filtered.index, y=filtered[phase],
                    name=phase, line=dict(color=COLORS[i], width=1.5),
                ))
        fig3.update_layout(**PLOTLY_LAYOUT, height=350, yaxis_title="A",
                            legend=dict(orientation="h", y=1.08))
        st.plotly_chart(fig3, use_container_width=True)

    with tab2:
        st.subheader("有効電力・無効電力")
        fig = go.Figure()
        if "Active power" in filtered.columns:
            fig.add_trace(go.Scatter(
                x=filtered.index, y=filtered["Active power"],
                name="有効電力 (kW)", line=dict(color=COLORS[0], width=2),
            ))
        if "Reactive power" in filtered.columns:
            fig.add_trace(go.Scatter(
                x=filtered.index, y=filtered["Reactive power"],
                name="無効電力 (kvar)", line=dict(color=COLORS[2], width=2),
            ))
        fig.update_layout(**PLOTLY_LAYOUT, height=400, yaxis_title="kW / kvar",
                           legend=dict(orientation="h", y=1.08))
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("力率")
        if "Power factor" in filtered.columns:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=filtered.index, y=filtered["Power factor"],
                name="力率", line=dict(color=COLORS[4], width=2),
            ))
            fig2.update_layout(**PLOTLY_LAYOUT, height=300, yaxis_title="Power Factor")
            st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader("系統周波数")
        if "Frequency" in filtered.columns:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=filtered.index, y=filtered["Frequency"],
                name="周波数 (Hz)", line=dict(color=COLORS[0], width=2),
            ))
            # Reference lines
            fig.add_hline(y=60, line_dash="dot", line_color=COLORS[1],
                          annotation_text="60 Hz")
            fig.update_layout(**PLOTLY_LAYOUT, height=400, yaxis_title="Hz")
            st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# 4. Dispatch Log page
# ---------------------------------------------------------------------------
elif page == "指令ログ":
    st.title("指令ログ")

    dispatch = data["dispatch"]

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        type_filter = st.multiselect(
            "Dispatch Type",
            dispatch["Dispatch Type"].unique().tolist(),
            default=dispatch["Dispatch Type"].unique().tolist(),
        )
    with col2:
        source_filter = st.multiselect(
            "Dispatch Source",
            dispatch["Dispatch Source"].unique().tolist(),
            default=dispatch["Dispatch Source"].unique().tolist(),
        )

    filtered = dispatch[
        dispatch["Dispatch Type"].isin(type_filter)
        & dispatch["Dispatch Source"].isin(source_filter)
    ]

    # Timeline chart
    st.subheader("指令タイムライン")
    type_colors = {"Active": COLORS[0], "Reactive": COLORS[2], "No": COLORS[5]}
    fig = go.Figure()
    for dtype in filtered["Dispatch Type"].unique():
        subset = filtered[filtered["Dispatch Type"] == dtype]
        daily = subset.groupby(subset["Dispatch Time"].dt.date).size().reset_index()
        daily.columns = ["date", "count"]
        fig.add_trace(go.Bar(
            x=daily["date"], y=daily["count"],
            name=dtype,
            marker_color=type_colors.get(dtype, COLORS[3]),
        ))
    fig.update_layout(**PLOTLY_LAYOUT, height=350, barmode="stack",
                       legend=dict(orientation="h", y=1.08),
                       xaxis_title="日付", yaxis_title="件数")
    st.plotly_chart(fig, use_container_width=True)

    # Summary stats
    col1, col2, col3 = st.columns(3)
    col1.metric("総件数", f"{len(filtered)}")
    col2.metric("Active指令", f"{len(filtered[filtered['Dispatch Type'] == 'Active'])}")
    col3.metric("Remote指令", f"{len(filtered[filtered['Dispatch Source'] == 'Remote'])}")

    # Data table
    st.subheader("指令一覧")
    st.dataframe(
        filtered[["Dispatch Time", "Dispatch Type", "Dispatch Mode",
                   "Dispatch Source", "Dispatch Content"]].sort_values(
            "Dispatch Time", ascending=False
        ),
        use_container_width=True,
        height=400,
    )


# ---------------------------------------------------------------------------
# 5. Alarms & Events page
# ---------------------------------------------------------------------------
elif page == "アラーム・イベント":
    st.title("アラーム・イベント")

    tab1, tab2, tab3 = st.tabs(["アラーム履歴", "SOEイベント", "ユーザ操作ログ"])

    with tab1:
        alarm = data["alarm"]
        st.subheader("アラーム一覧")

        # Summary
        col1, col2, col3 = st.columns(3)
        col1.metric("総アラーム", f"{len(alarm)} 件")
        col2.metric("Major", f"{len(alarm[alarm['Severity'] == 'Major'])} 件")
        col3.metric("未確認", f"{len(alarm[alarm['Acknowledged'] == 'Unacknowledged'])} 件")

        # Gantt-style timeline
        if not alarm.empty:
            st.subheader("アラームタイムライン")
            fig = go.Figure()
            for i, row in alarm.iterrows():
                color = "#ff3b30" if row["Severity"] == "Major" else "#ff9500"
                fig.add_trace(go.Scatter(
                    x=[row["Generation time"], row["End time"]],
                    y=[row["Alarm Name"], row["Alarm Name"]],
                    mode="lines",
                    line=dict(color=color, width=12),
                    name=row["Severity"],
                    showlegend=i == 0,
                    hovertext=f"{row['Alarm Name']}<br>{row['Generation time']} ~ {row['End time']}",
                ))
            layout_kwargs = {**PLOTLY_LAYOUT, "height": max(300, len(alarm) * 35)}
            layout_kwargs["yaxis"] = dict(
                gridcolor="rgba(0,0,0,0.06)", categoryorder="total ascending"
            )
            fig.update_layout(**layout_kwargs)
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            alarm[["SN", "Severity", "Alarm Name", "Generation time",
                    "End time", "Acknowledged"]].sort_values(
                "Generation time", ascending=False
            ),
            use_container_width=True,
        )

    with tab2:
        soe = data["soe"]
        st.subheader("SOEイベント一覧")

        # Event frequency
        if not soe.empty:
            freq = soe["SOE event Dscp"].value_counts().reset_index()
            freq.columns = ["イベント", "件数"]
            fig = px.bar(
                freq, x="件数", y="イベント", orientation="h",
                color_discrete_sequence=[APPLE_BLUE],
            )
            fig.update_layout(**PLOTLY_LAYOUT, height=max(300, len(freq) * 30))
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            soe[["Generation time", "SOE event ID", "SOE event Dscp"]].sort_values(
                "Generation time", ascending=False
            ),
            use_container_width=True,
            height=400,
        )

    with tab3:
        user_log = data["user_log"]
        st.subheader("ユーザ操作ログ")

        # Daily activity
        if not user_log.empty:
            daily = user_log.groupby(user_log["Operation Time"].dt.date).size().reset_index()
            daily.columns = ["date", "count"]
            fig = px.bar(
                daily, x="date", y="count",
                color_discrete_sequence=[APPLE_BLUE],
                labels={"date": "日付", "count": "操作数"},
            )
            fig.update_layout(**PLOTLY_LAYOUT, height=250)
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            user_log[["Operation Time", "User Name", "Operation Source",
                        "Parameters"]].sort_values(
                "Operation Time", ascending=False
            ),
            use_container_width=True,
            height=400,
        )
