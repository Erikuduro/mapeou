"""
Cartographic map generator — IBGE style, high fidelity.
Produces A3-landscape PDF matching the reference layout:
  ┌──────────────────────────────────┬──────────────────┐
  │  title centered at top           │                  │
  ├──────────────────────────────────┤  Brazil inset    │
  │                                  │                  │
  │  MAIN MAP                        ├──────────────────┤
  │  municipality + neighbours       │  State inset     │
  │  graticule · N-arrow · scalebar  ├──────────────────┤
  │                                  │  Legend          │
  │                                  ├──────────────────┤
  └──────────────────────────────────┤  Metadata        │
                                     └──────────────────┘
"""
import math
import os
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.patches import Polygon as MplPolygon
import geopandas as gpd
import numpy as np
from shapely.geometry import box, MultiPolygon, Polygon

# ── colour palette ────────────────────────────────────────────────────────────
C_BG       = "#C8C8C8"   # map background (ocean / void)
C_COUNTRY  = "#D0C8C0"   # warm grey – neighbouring countries
C_MUNI     = "#F5DEB3"   # cream – target municipality
C_NEIGHBOR = "#A8C4D4"   # muted blue – direct neighbours
C_OTHER    = "#DEDEDE"   # light grey – other visible municipalities
C_URBAN    = "#C9A8DC"   # lavender – Sítio Urbano
C_HVY      = "#111111"   # heavy border (target municipality)
C_MED      = "#333333"   # medium border (neighbours)
C_THIN     = "#999999"   # thin border (distant municipalities)
C_GRID     = "#AAAAAA"   # graticule lines
C_INSET_BG = "#F0F0F0"   # inset background
C_NE_RED   = "#CC0000"   # Northeast outline in Brazil inset
C_FRAME    = "#111111"   # panel frame

FONT = "DejaVu Sans"

REGIAO_STATES = {
    'N':  frozenset({'AC','AM','AP','PA','RO','RR','TO'}),
    'NE': frozenset({'AL','BA','CE','MA','PB','PE','PI','RN','SE'}),
    'CO': frozenset({'DF','GO','MS','MT'}),
    'SE': frozenset({'ES','MG','RJ','SP'}),
    'S':  frozenset({'PR','RS','SC'}),
}
REGIAO_NOME = {
    'N': 'Norte', 'NE': 'Nordeste', 'CO': 'Centro-Oeste',
    'SE': 'Sudeste', 'S': 'Sul',
}


# ── UTM zone helpers ──────────────────────────────────────────────────────────

def _utm_zone_epsg(lon: float) -> int:
    """EPSG code for SIRGAS 2000 UTM zone at given longitude (Southern Hemisphere)."""
    zone = int((lon + 180) / 6) + 1
    return 31954 + zone   # Zone 18S=31972 … Zone 25S=31979


def _utm_zone_name(lon: float) -> str:
    zone = int((lon + 180) / 6) + 1
    return f"{zone}S"


def _setup_utm_graticule(ax, xmin, xmax, ymin, ymax, label_size=5.5,
                         top=True, bottom=True, left=True, right=True):
    """UTM grid in km (Easting / Northing)."""
    span_x, span_y = xmax - xmin, ymax - ymin
    steps = [500, 1000, 2000, 5000, 10000, 20000, 50000, 100000]
    step_x = min(steps, key=lambda s: abs(s - span_x / 5))
    step_y = min(steps, key=lambda s: abs(s - span_y / 5))

    xt = np.arange(math.ceil(xmin / step_x) * step_x, xmax + step_x * 0.01, step_x)
    yt = np.arange(math.ceil(ymin / step_y) * step_y, ymax + step_y * 0.01, step_y)
    xt = xt[(xt >= xmin) & (xt <= xmax)]
    yt = yt[(yt >= ymin) & (yt <= ymax)]

    ax.set_xticks(xt)
    ax.set_yticks(yt)
    ax.set_xticklabels([f"{x/1000:.0f} E" for x in xt],
                       fontsize=label_size, fontfamily=FONT, rotation=90)
    ax.set_yticklabels([f"{y/1000:.0f} N" for y in yt],
                       fontsize=label_size, fontfamily=FONT)
    ax.tick_params(top=top, labeltop=top, bottom=bottom, labelbottom=bottom,
                   left=left, labelleft=left, right=right, labelright=right,
                   length=3, width=0.5, color=C_FRAME)
    ax.grid(True, linestyle='--', linewidth=0.4, color=C_GRID, alpha=0.7, zorder=1)
    for sp in ax.spines.values():
        sp.set_edgecolor(C_FRAME)
        sp.set_linewidth(0.8)


def _scale_bar_utm(ax, xmin, xmax, ymin, ymax):
    """Accurate scale bar: data units are metres in UTM."""
    span_m = xmax - xmin
    nice_km = [0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500]
    total_km = min(nice_km, key=lambda k: abs(k - span_m / 4000))
    seg_m = total_km * 500  # two segments = total_km km total

    bx = xmax - (xmax - xmin) * 0.05 - seg_m * 2
    by = ymin + (ymax - ymin) * 0.04
    bh = (ymax - ymin) * 0.013

    for i, fc in enumerate(['black', 'white']):
        ax.add_patch(mpatches.Rectangle(
            (bx + i * seg_m, by), seg_m, bh,
            facecolor=fc, edgecolor='black', lw=0.6, zorder=7))

    fs = 5.5
    for pos, label in [
        (bx,             "0"),
        (bx + seg_m,     f"{total_km/2:.4g}"),
        (bx + seg_m * 2, f"{total_km:.4g} km"),
    ]:
        ax.text(pos, by + bh * 2.4, label, ha='center', va='bottom',
                fontsize=fs, fontfamily=FONT, zorder=8)


# ── helpers ───────────────────────────────────────────────────────────────────

def _dms(val: float, is_lat: bool) -> str:
    """Format decimal degrees as D°MM'0\"Dir."""
    direction = ("N" if val >= 0 else "S") if is_lat else ("L" if val >= 0 else "W")
    v = abs(val)
    deg = int(v)
    min_f = (v - deg) * 60
    mins = int(round(min_f))
    if mins == 60:
        deg += 1
        mins = 0
    return f"{deg}°{mins:02d}'0\"{direction}"


def _graticule_ticks(lo: float, hi: float, span: float) -> np.ndarray:
    """Return clean graticule tick positions for an axis span."""
    # Use minute-based intervals
    minute_opts = [1, 2, 5, 10, 15, 20, 30, 60, 120, 300, 600]
    target_n = 5
    target_min = span * 60 / target_n
    step_min = min(minute_opts, key=lambda m: abs(m - target_min))
    step_deg = step_min / 60.0
    start = math.ceil(lo / step_deg) * step_deg
    ticks = np.arange(start, hi + step_deg * 0.01, step_deg)
    return ticks[(ticks >= lo) & (ticks <= hi)]


def _setup_graticule(ax, xmin, xmax, ymin, ymax, label_size=5.5,
                     top=True, bottom=True, left=True, right=True):
    """Add graticule lines + DMS tick labels on all requested sides."""
    lon_ticks = _graticule_ticks(xmin, xmax, xmax - xmin)
    lat_ticks = _graticule_ticks(ymin, ymax, ymax - ymin)

    ax.set_xticks(lon_ticks)
    ax.set_yticks(lat_ticks)

    lon_labels = [_dms(x, False) for x in lon_ticks]
    lat_labels = [_dms(y, True)  for y in lat_ticks]

    ax.set_xticklabels(lon_labels, fontsize=label_size, fontfamily=FONT, rotation=90)
    ax.set_yticklabels(lat_labels, fontsize=label_size, fontfamily=FONT)

    ax.tick_params(top=top, labeltop=top,
                   bottom=bottom, labelbottom=bottom,
                   left=left, labelleft=left,
                   right=right, labelright=right,
                   length=3, width=0.5, color=C_FRAME)

    ax.grid(True, linestyle='--', linewidth=0.4, color=C_GRID, alpha=0.7, zorder=1)
    for sp in ax.spines.values():
        sp.set_edgecolor(C_FRAME)
        sp.set_linewidth(0.8)


def _north_arrow(ax, x, y, size):
    """Traditional cartographic N-arrow at data coords (x,y), half-black half-white."""
    half = size * 0.45
    tip  = y + size * 1.2
    base = y - size * 0.4

    ax.add_patch(MplPolygon(
        [[x, tip], [x, y], [x - half, base]],
        closed=True, facecolor='black', edgecolor='black', lw=0.6, zorder=9
    ))
    ax.add_patch(MplPolygon(
        [[x, tip], [x, y], [x + half, base]],
        closed=True, facecolor='white', edgecolor='black', lw=0.6, zorder=9
    ))
    ax.text(x, base - size * 0.25, 'N', ha='center', va='top',
            fontsize=7, fontweight='bold', fontfamily=FONT, zorder=9)


def _scale_bar(ax, xmin, xmax, ymin, ymax):
    """Alternating B/W scale bar with km labels."""
    lat_rad = math.radians((ymin + ymax) / 2)
    km_per_deg = 111.32 * math.cos(lat_rad)
    x_span_km  = (xmax - xmin) * km_per_deg

    nice_km = [0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500]
    total_km = min(nice_km, key=lambda k: abs(k - x_span_km * 0.25))
    seg_km   = total_km / 2          # two segments
    seg_deg  = seg_km / km_per_deg

    bx = xmax - (xmax - xmin) * 0.05 - seg_deg * 2
    by = ymin + (ymax - ymin) * 0.04
    bh = (ymax - ymin) * 0.013

    for i, fc in enumerate(['black', 'white']):
        ax.add_patch(mpatches.Rectangle(
            (bx + i * seg_deg, by), seg_deg, bh,
            facecolor=fc, edgecolor='black', lw=0.6, zorder=7
        ))

    fs = 5.5
    for pos, label in [
        (bx,              "0"),
        (bx + seg_deg,    f"{seg_km:.4g}"),
        (bx + seg_deg*2,  f"{total_km:.4g} km"),
    ]:
        ax.text(pos, by + bh * 2.4, label, ha='center', va='bottom',
                fontsize=fs, fontfamily=FONT, zorder=8)


# ── panel drawing ─────────────────────────────────────────────────────────────


def _draw_main(ax, state_munis: gpd.GeoDataFrame, muni_id: int,
               muni_nome: str, sitio_urbano=None) -> str:
    """Returns the UTM zone name (e.g. '21S') for use in metadata."""
    from ibge_api import get_water_bodies

    target_mask = state_munis['codarea'].astype(str) == str(muni_id)
    target      = state_munis[target_mask]

    if target.empty:
        raise ValueError(f"Municipality id={muni_id} not found in state mesh.")

    target_geom = target.geometry.iloc[0]
    buf         = target_geom.buffer(0.001)
    nbr_mask    = state_munis.geometry.intersects(buf) & ~target_mask
    neighbors   = state_munis[nbr_mask]

    # Geographic extent (EPSG:4326) used for Overpass query
    show = gpd.GeoDataFrame(
        geometry=gpd.GeoSeries([target_geom] + list(neighbors.geometry)),
        crs=state_munis.crs)
    b    = show.total_bounds
    pad  = 0.28
    geo_xmin = b[0] - (b[2]-b[0])*pad
    geo_ymin = b[1] - (b[3]-b[1])*pad
    geo_xmax = b[2] + (b[2]-b[0])*pad
    geo_ymax = b[3] + (b[3]-b[1])*pad

    # ── CRS transform: determine UTM zone from bounding-box centroid ──────────
    center_lon = (geo_xmin + geo_xmax) / 2
    utm_epsg   = _utm_zone_epsg(center_lon)
    utm_zone   = _utm_zone_name(center_lon)

    def _to_utm(gdf):
        return gdf.to_crs(epsg=utm_epsg)

    target_u    = _to_utm(target)
    neighbors_u = _to_utm(neighbors)
    state_u     = _to_utm(state_munis)

    # UTM bounding box with padding
    bb = np.array(
        list(target_u.total_bounds) if neighbors_u.empty
        else [
            min(target_u.total_bounds[0], neighbors_u.total_bounds[0]),
            min(target_u.total_bounds[1], neighbors_u.total_bounds[1]),
            max(target_u.total_bounds[2], neighbors_u.total_bounds[2]),
            max(target_u.total_bounds[3], neighbors_u.total_bounds[3]),
        ])
    px = (bb[2]-bb[0]) * 0.28
    py = (bb[3]-bb[1]) * 0.28
    xmin, ymin = bb[0]-px, bb[1]-py
    xmax, ymax = bb[2]+px, bb[3]+py

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_facecolor(C_BG)

    clip_box_u = box(xmin, ymin, xmax, ymax)

    # ── 1. Neighbouring countries (Natural Earth, z=1) ─────────────────────
    from ibge_api import get_water_bodies, get_countries
    countries = get_countries()
    if countries is not None and not countries.empty:
        try:
            iso_col = 'iso_a2' if 'iso_a2' in countries.columns else None
            if iso_col:
                foreign = countries[countries[iso_col] != 'BR']
            else:
                foreign = countries
            foreign_u = foreign.to_crs(epsg=utm_epsg)
            foreign_vis = foreign_u[foreign_u.geometry.intersects(clip_box_u)]
            if not foreign_vis.empty:
                foreign_clip = gpd.clip(foreign_vis, clip_box_u)
                foreign_clip.plot(ax=ax, facecolor=C_COUNTRY, edgecolor='#555555',
                                  linewidth=0.7, linestyle='--', zorder=1)
                # Country name labels
                name_col = next((c for c in ['name', 'admin'] if c in foreign_clip.columns), None)
                if name_col:
                    for _, row in foreign_clip.iterrows():
                        if row.geometry.is_empty:
                            continue
                        cx, cy = row.geometry.centroid.x, row.geometry.centroid.y
                        if xmin < cx < xmax and ymin < cy < ymax:
                            ax.text(cx, cy, str(row[name_col]).upper(),
                                    ha='center', va='center', fontsize=6,
                                    fontfamily=FONT, color='#333333', fontweight='bold',
                                    zorder=2,
                                    bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                                              alpha=0.65, edgecolor='none'))
        except Exception:
            pass

    # ── 2. Water bodies: clip → buffer(0) fix → dissolve (z=3) ────────────
    water = get_water_bodies(muni_id, geo_xmin, geo_ymin, geo_xmax, geo_ymax)
    if water is not None and not water.empty:
        try:
            water_u = _to_utm(water)
            water_vis = water_u[water_u.geometry.intersects(clip_box_u)]
            if not water_vis.empty:
                water_clip = gpd.clip(water_vis, clip_box_u)
                water_clip = water_clip.copy()
                water_clip['geometry'] = water_clip.geometry.buffer(0)
                water_clip = water_clip[
                    water_clip.geometry.is_valid & ~water_clip.geometry.is_empty]
                if not water_clip.empty:
                    water_diss = water_clip.dissolve()[['geometry']]
                    water_diss.plot(ax=ax, facecolor='#A8D4E8', edgecolor='#4A90C8',
                                    linewidth=0.5, zorder=3)
        except Exception:
            pass

    # ── 3. Municipality layers (z=4-6) ────────────────────────────────────
    visible_u = state_u[state_u.geometry.intersects(clip_box_u)].copy()

    tgt_ids = set(target_u['codarea'].astype(str))
    nbr_ids = set(neighbors_u['codarea'].astype(str))
    others_u = visible_u[~visible_u['codarea'].astype(str).isin(tgt_ids | nbr_ids)]

    if not others_u.empty:
        others_u.plot(ax=ax, facecolor=C_OTHER, edgecolor=C_THIN, linewidth=0.3, zorder=4)
    if not neighbors_u.empty:
        neighbors_u.plot(ax=ax, facecolor=C_NEIGHBOR, edgecolor=C_MED, linewidth=0.65, zorder=5)
    target_u.plot(ax=ax, facecolor=C_MUNI, edgecolor=C_HVY, linewidth=1.6, zorder=6)

    # ── Sítio Urbano (z=7) ────────────────────────────────────────────────────
    if sitio_urbano is not None and not sitio_urbano.empty:
        sitio_u = _to_utm(sitio_urbano)
        sitio_u.plot(ax=ax, facecolor=C_URBAN, edgecolor="#7A5C9A",
                     linewidth=0.7, zorder=7)
        su_c = sitio_u.geometry.union_all().centroid
        ax.annotate("Sítio Urbano",
                    xy=(su_c.x, su_c.y),
                    xytext=(su_c.x + (xmax-xmin)*0.08, su_c.y - (ymax-ymin)*0.06),
                    fontsize=5.5, fontfamily=FONT, color="#333333", zorder=9,
                    arrowprops=dict(arrowstyle='->', color='#333333', lw=0.7))

    # ── Labels (z=8-9) ────────────────────────────────────────────────────────
    _lbbox = dict(boxstyle='round,pad=0.1', facecolor='white', alpha=0.55, edgecolor='none')
    for _, row in neighbors_u.iterrows():
        nome = row.get('nome', None)
        if not nome or isinstance(nome, float):
            continue
        cx, cy = row.geometry.centroid.x, row.geometry.centroid.y
        if xmin < cx < xmax and ymin < cy < ymax:
            ax.text(cx, cy, str(nome).upper(), ha='center', va='center',
                    fontsize=4.5, fontfamily=FONT, color='#1A1A1A', zorder=8, bbox=_lbbox)

    tgt_c = target_u.geometry.iloc[0].centroid
    ax.text(tgt_c.x, tgt_c.y, muni_nome.upper(), ha='center', va='center',
            fontsize=7, fontfamily=FONT, fontweight='bold', color='#1A1A1A', zorder=9,
            bbox=dict(boxstyle='round,pad=0.15', facecolor='white', alpha=0.65, edgecolor='none'))

    # ── Cartographic elements (UTM) ───────────────────────────────────────────
    na_x = xmin + (xmax-xmin)*0.06
    na_y = ymin + (ymax-ymin)*0.82
    _north_arrow(ax, na_x, na_y, (ymax-ymin)*0.05)
    _scale_bar_utm(ax, xmin, xmax, ymin, ymax)
    _setup_utm_graticule(ax, xmin, xmax, ymin, ymax, label_size=5.5)

    return utm_zone


def _draw_brazil(ax, states: gpd.GeoDataFrame, uf_sigla: str, regiao_sigla: str):
    b = states.total_bounds
    px = (b[2] - b[0]) * 0.04
    py = (b[3] - b[1]) * 0.04
    xmin, ymin = b[0]-px, b[1]-py
    xmax, ymax = b[2]+px, b[3]+py

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_facecolor('white')

    # All states: light fill + thin border
    states.plot(ax=ax, facecolor=C_INSET_BG, edgecolor='#444444',
                linewidth=0.35, zorder=2)

    # Target region: red outline
    if 'sigla' in states.columns:
        region_ufs = REGIAO_STATES.get(regiao_sigla, frozenset())
        reg = states[states['sigla'].isin(region_ufs)]
        reg.plot(ax=ax, facecolor='none', edgecolor=C_NE_RED, linewidth=1.1, zorder=3)

        # Target state: filled red dot at centroid
        tgt_state = states[states['sigla'] == uf_sigla]
        if not tgt_state.empty:
            cx = tgt_state.geometry.iloc[0].centroid.x
            cy = tgt_state.geometry.iloc[0].centroid.y
            ax.plot(cx, cy, 'o', color=C_NE_RED, markersize=3.5, zorder=5)

    ax.text(0.5, 0.08, 'BRASIL', transform=ax.transAxes, ha='center', va='bottom',
            fontsize=5.5, fontweight='bold', fontfamily=FONT, color='#111111')

    na_x = xmin + (xmax-xmin)*0.05
    na_y = ymax - (ymax-ymin)*0.18
    _north_arrow(ax, na_x, na_y, (ymax-ymin)*0.05)

    _setup_graticule(ax, xmin, xmax, ymin, ymax, label_size=4.5,
                     top=False, right=False)


def _draw_state(ax, state_munis: gpd.GeoDataFrame, muni_id: int, uf_nome: str):
    b  = state_munis.total_bounds
    px = (b[2]-b[0])*0.03
    py = (b[3]-b[1])*0.03
    xmin, ymin = b[0]-px, b[1]-py
    xmax, ymax = b[2]+px, b[3]+py

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_facecolor('white')

    state_munis.plot(ax=ax, facecolor=C_INSET_BG, edgecolor='#555555',
                     linewidth=0.25, zorder=2)

    # Mark target municipality as a filled star/dot
    tgt = state_munis[state_munis['codarea'].astype(str) == str(muni_id)]
    if not tgt.empty:
        cx = tgt.geometry.iloc[0].centroid.x
        cy = tgt.geometry.iloc[0].centroid.y
        ax.plot(cx, cy, marker='*', color='black', markersize=5, zorder=4)

    ax.text(0.5, 0.06, uf_nome.upper(), transform=ax.transAxes, ha='center', va='bottom',
            fontsize=5, fontweight='bold', fontfamily=FONT, color='#111111')

    na_x = xmin + (xmax-xmin)*0.05
    na_y = ymax - (ymax-ymin)*0.2
    _north_arrow(ax, na_x, na_y, (ymax-ymin)*0.07)

    _setup_graticule(ax, xmin, xmax, ymin, ymax, label_size=4.5,
                     top=False, right=False)


def _draw_legend(ax, muni_nome: str, uf_sigla: str, uf_nome: str = "",
                 regiao_nome: str = "Região", has_urban: bool = False):
    ax.set_axis_off()
    for sp in ax.spines.values():
        sp.set_visible(True)
        sp.set_edgecolor(C_FRAME)
        sp.set_linewidth(0.7)
    ax.set_facecolor('white')

    # Title
    ax.text(0.5, 0.96, "Delimitações", transform=ax.transAxes,
            ha='center', va='top', fontsize=7, fontweight='bold', fontfamily=FONT)

    handles = [
        mlines.Line2D([], [], color='#444444', lw=0.9,
                      marker=None, label='Brasil'),
        mlines.Line2D([], [], color=C_NE_RED, lw=1.1,
                      marker=None, label=regiao_nome),
        mlines.Line2D([], [], color=C_HVY, lw=1.3,
                      marker=None, label=uf_nome or uf_sigla),
        mpatches.Patch(facecolor=C_MUNI, edgecolor=C_HVY, lw=0.8,
                       label=f'{muni_nome}-{uf_sigla}'),
        mpatches.Patch(facecolor=C_NEIGHBOR, edgecolor=C_MED, lw=0.6,
                       label='Municípios vizinhos'),
    ]
    if has_urban:
        handles.append(
            mpatches.Patch(facecolor=C_URBAN, edgecolor='#7A5C9A', lw=0.7,
                           label='Sítio Urbano')
        )

    legend = ax.legend(
        handles=handles,
        loc='upper left',
        bbox_to_anchor=(0.04, 0.83),
        bbox_transform=ax.transAxes,
        frameon=False,
        fontsize=6,
        handlelength=1.8,
        handleheight=0.9,
        handletextpad=0.5,
        labelspacing=0.45,
    )
    ax.add_artist(legend)


def _draw_metadata(ax, fonte: str = "IBGE, 2022",
                   projecao: str = "Geográfica",
                   datum: str = "SIRGAS 2000",
                   autores: str = "",
                   organizacao: str = ""):
    ax.set_axis_off()
    for sp in ax.spines.values():
        sp.set_visible(True)
        sp.set_edgecolor(C_FRAME)
        sp.set_linewidth(0.7)
    ax.set_facecolor('white')

    lines = [
        f"Fonte: {fonte}",
        f"Projeção: {projecao}",
        f"Datum: {datum}",
    ]
    if autores:
        lines.append(autores)
    if organizacao:
        lines.append(f"Organização: {organizacao}")

    text = "\n".join(lines)
    ax.text(0.5, 0.5, text, transform=ax.transAxes,
            ha='center', va='center', fontsize=5.5, fontfamily=FONT,
            color='#222222', linespacing=1.6)


# ── main entry points ─────────────────────────────────────────────────────────

def generate_ibge_map(
    municipio:   dict,
    state_munis: gpd.GeoDataFrame,
    states:      gpd.GeoDataFrame,
    output_path: str,
    sitio_urbano: gpd.GeoDataFrame | None = None,
    fonte:       str = "IBGE, 2022",
    projecao:    str = "Geográfica",
    datum:       str = "SIRGAS 2000",
    autores:     str = "",
    organizacao: str = "",
) -> None:
    muni_id      = municipio['id']
    muni_nome    = municipio['nome']
    uf_sigla     = municipio['uf_sigla']
    uf_nome      = municipio['uf_nome']
    regiao_sigla = municipio.get('regiao_sigla', 'N')
    regiao_nome  = REGIAO_NOME.get(regiao_sigla, regiao_sigla)
    has_urban    = sitio_urbano is not None and not sitio_urbano.empty

    title = f"MUNICÍPIO DE {muni_nome.upper()}-{uf_sigla}"

    # ── figure ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(16.54, 11.69), dpi=150)
    fig.patch.set_facecolor('white')

    fig.text(0.5, 0.978, title, ha='center', va='top',
             fontsize=13, fontweight='bold', fontfamily=FONT, color='black')

    # Layout constants
    L, R, T, B = 0.025, 0.990, 0.958, 0.030
    SPLIT = 0.660   # main map ends here
    GAP   = 0.008

    mW = SPLIT - L - GAP
    rL = SPLIT + GAP
    rW = R - rL

    # Right column proportions (bottom → top)
    meta_h   = 0.090
    leg_h    = 0.130
    state_h  = 0.270
    brazil_h = T - B - meta_h - leg_h - state_h - 3*GAP

    ax_main   = fig.add_axes([L,  B, mW, T - B])
    ax_brazil = fig.add_axes([rL, B + meta_h + leg_h + state_h + 3*GAP, rW, brazil_h])
    ax_state  = fig.add_axes([rL, B + meta_h + leg_h + 2*GAP,            rW, state_h])
    ax_legend = fig.add_axes([rL, B + meta_h + GAP,                      rW, leg_h])
    ax_meta   = fig.add_axes([rL, B,                                      rW, meta_h])

    # ── panels ────────────────────────────────────────────────────────────────
    utm_zone  = _draw_main(ax_main, state_munis, muni_id, muni_nome, sitio_urbano)
    projecao_auto = f"SIRGAS 2000 / UTM Fuso {utm_zone}"
    _draw_brazil(ax_brazil, states, uf_sigla, regiao_sigla)
    _draw_state(ax_state, state_munis, muni_id, uf_nome)
    _draw_legend(ax_legend, muni_nome, uf_sigla, uf_nome, regiao_nome, has_urban)
    _draw_metadata(ax_meta, fonte, projecao_auto, datum, autores, organizacao)

    plt.savefig(output_path, format='png', bbox_inches='tight',
                facecolor='white', dpi=150)
    plt.close(fig)


def generate_ibge_map_bytes(
    municipio:    dict,
    state_munis:  gpd.GeoDataFrame,
    states:       gpd.GeoDataFrame,
    sitio_urbano: gpd.GeoDataFrame | None = None,
) -> bytes:
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        path = tmp.name
    try:
        generate_ibge_map(municipio, state_munis, states, path, sitio_urbano)
        with open(path, 'rb') as f:
            return f.read()
    finally:
        if os.path.exists(path):
            os.unlink(path)
