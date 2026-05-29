"""
Gerador de gráficos IBGE/SIDRA no estilo Mapeou.
Retorna PDF em BytesIO.
"""
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ── Paleta ────────────────────────────────────────────────────────────────────
BG        = "#1A1A1A"
SURFACE   = "#242424"
ACCENT    = "#00C47A"
ACCENT2   = "#007A4D"
TEXT      = "#E0E0E0"
MUTED     = "#888888"
GRID      = "#2E2E2E"
BORDER    = "#333333"


def _fmt_value(v: float, unidade: str) -> str:
    """Formata valor com sufixo legível."""
    u = unidade.lower()
    if "tonelada" in u or "cabeça" in u or "litro" in u or "quilograma" in u or "dúzia" in u:
        if v >= 1_000_000:
            return f"{v/1_000_000:.1f} M"
        if v >= 1_000:
            return f"{v/1_000:.1f} mil"
    return f"{v:,.0f}"


def generate_ranking_chart(data: dict) -> bytes:
    """
    Gera gráfico de barras horizontais para rankings (top culturas ou top estados).
    data: dict com 'tipo', 'titulo', 'subtitulo', 'itens', 'unidade', e opcionalmente 'total_nacional'.
    """
    itens   = data["itens"]
    titulo  = data["titulo"]
    subtit  = data["subtitulo"]
    unidade = data["unidade"]
    tipo    = data["tipo"]
    total_nacional = data.get("total_nacional", 0)

    n = len(itens)
    fig_h = max(5.5, 1.0 + n * 0.52)
    fig = plt.figure(figsize=(11, fig_h), facecolor=BG)

    ax = fig.add_axes([0.32, 0.12, 0.58, 0.72])
    ax.set_facecolor(SURFACE)
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER)

    nomes  = [it["nome"] for it in reversed(itens)]
    values = [it["valor"] for it in reversed(itens)]
    y      = np.arange(n)

    # Gradiente de cor: mais escuro para menor valor
    max_val = max(values)
    colors  = [
        ACCENT if v == max_val else
        "#006B44" if v >= max_val * 0.5 else
        "#004D31"
        for v in values
    ]

    bars = ax.barh(y, values, color=colors, height=0.62, zorder=3)

    # Rótulos de valor dentro/fora da barra
    for i, (bar, val) in enumerate(zip(bars, values)):
        pct = val / max_val * 100
        label = _fmt_value(val, unidade)
        if tipo == "ranking_states" and total_nacional:
            label += f"  ({val/total_nacional*100:.1f}%)"
        x_pos = bar.get_width()
        ax.text(
            x_pos + max_val * 0.01, bar.get_y() + bar.get_height() / 2,
            label, va="center", ha="left",
            color=TEXT, fontsize=7.5, fontweight="500"
        )

    # Linha vertical para total nacional
    if tipo == "ranking_states" and total_nacional:
        ax.axvline(total_nacional, color=ACCENT, linewidth=1,
                   linestyle="--", alpha=0.4, zorder=2)
        ax.text(total_nacional, n - 0.1,
                f"Total BR: {_fmt_value(total_nacional, unidade)}",
                color=ACCENT, fontsize=7, ha="center", va="bottom", alpha=0.7)

    ax.set_yticks(y)
    ax.set_yticklabels(nomes, color=TEXT, fontsize=8.5)
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: _fmt_value(v, unidade))
    )
    ax.tick_params(axis="x", colors=MUTED, labelsize=7.5)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.yaxis.grid(False)
    ax.set_xlim(0, max_val * 1.35)
    ax.set_ylim(-0.5, n - 0.5)

    # Números de posição
    for i, nome in enumerate(reversed(range(1, n + 1))):
        ax.text(-max_val * 0.015, i, f"{nome}°",
                va="center", ha="right", color=MUTED, fontsize=7.5)

    # Header
    fig.text(0.06, 0.94, titulo,
             color=TEXT, fontsize=12, fontweight="bold", va="top")
    fig.text(0.06, 0.88, subtit,
             color=MUTED, fontsize=7.5, va="top")

    # Rodapé
    fig.text(0.06, 0.03,
             "Dados: IBGE · Sistema IBGE de Recuperação Automática (SIDRA)",
             color=MUTED, fontsize=7)
    fig.text(0.94, 0.03, "Mapeou",
             color=ACCENT, fontsize=7, ha="right", fontweight="bold")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_chart(series: dict) -> bytes:
    """
    Recebe dict {'anos', 'valores', 'unidade', 'titulo', 'tipo'}
    e retorna PDF como bytes.
    """
    anos    = series["anos"]
    valores = series["valores"]
    unidade = series["unidade"]
    titulo  = series["titulo"]
    tipo    = series.get("tipo", "bar")

    fig_w, fig_h = 11, 6.5
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor=BG)

    # ── Área do gráfico ───────────────────────────────────────────────────
    ax = fig.add_axes([0.10, 0.18, 0.82, 0.60])
    ax.set_facecolor(SURFACE)
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER)

    x = np.arange(len(anos))

    if tipo == "bar":
        bars = ax.bar(x, valores, color=ACCENT, width=0.72, zorder=3)
        # Destaca o maior valor
        max_idx = int(np.argmax(valores))
        bars[max_idx].set_color(ACCENT2)
        bars[max_idx].set_edgecolor(ACCENT)
        bars[max_idx].set_linewidth(1.5)
    else:
        ax.fill_between(x, valores, alpha=0.18, color=ACCENT, zorder=2)
        ax.plot(x, valores, color=ACCENT, linewidth=2, zorder=3)
        ax.scatter(x, valores, color=ACCENT, s=28, zorder=4)

    # Grid horizontal
    ax.yaxis.grid(True, color=GRID, linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.xaxis.grid(False)

    # Eixo X — anos
    step = max(1, len(anos) // 12)
    ticks_idx = list(range(0, len(anos), step))
    ax.set_xticks([x[i] for i in ticks_idx])
    ax.set_xticklabels([str(anos[i]) for i in ticks_idx],
                       color=MUTED, fontsize=8, rotation=45, ha="right")

    # Eixo Y — valores formatados
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: _fmt_value(v, unidade))
    )
    ax.tick_params(axis="y", colors=MUTED, labelsize=8)
    ax.tick_params(axis="x", colors=MUTED, labelsize=8)

    # Limites com margem
    ymax = max(valores) * 1.12
    ax.set_ylim(0, ymax)
    ax.set_xlim(-0.6, len(anos) - 0.4)

    # ── Linha de tendência ────────────────────────────────────────────────
    if len(valores) > 4:
        coef = np.polyfit(x, valores, 1)
        trend = np.poly1d(coef)(x)
        ax.plot(x, trend, color=TEXT, linewidth=1, linestyle="--",
                alpha=0.35, zorder=5, label="Tendência")

    # ── Anotação do valor máximo ──────────────────────────────────────────
    max_idx  = int(np.argmax(valores))
    max_val  = valores[max_idx]
    max_year = anos[max_idx]
    ax.annotate(
        f"Máx: {_fmt_value(max_val, unidade)}\n({max_year})",
        xy=(x[max_idx], max_val),
        xytext=(8, 6), textcoords="offset points",
        color=TEXT, fontsize=7.5,
        bbox=dict(boxstyle="round,pad=0.3", facecolor=BG, edgecolor=BORDER, alpha=0.9),
    )

    # ── Header (título + subtítulo) ───────────────────────────────────────
    fig.text(0.10, 0.90, titulo,
             color=TEXT, fontsize=13, fontweight="bold", va="bottom")
    fig.text(0.10, 0.86,
             f"Fonte: IBGE — SIDRA  ·  Unidade: {unidade}  ·  Período: {anos[0]}–{anos[-1]}",
             color=MUTED, fontsize=8, va="bottom")
    nota = series.get("nota_metodologia")
    if nota:
        fig.text(0.10, 0.83, f"* {nota}",
                 color="#BB8800", fontsize=7, va="bottom", style="italic")

    # ── Rodapé ───────────────────────────────────────────────────────────
    fig.text(0.10, 0.04,
             "Dados: IBGE · Sistema IBGE de Recuperação Automática (SIDRA)",
             color=MUTED, fontsize=7)
    fig.text(0.90, 0.04, "Mapeou",
             color=ACCENT, fontsize=7, ha="right", fontweight="bold")

    # ── Exporta PDF ───────────────────────────────────────────────────────
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=180,
                bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    buf.seek(0)
    return buf.read()
