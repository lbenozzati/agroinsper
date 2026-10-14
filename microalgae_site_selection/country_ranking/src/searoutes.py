"""Approximate sea distances on a hand-built waypoint graph (straits, canals and capes), Dijkstra on great-circle legs.

Not a routing engine: it avoids the gross error of straight lines across continents (e.g. Brazil -> Vietnam) and
is accurate to roughly +/-10% against published port-to-port tables for the lanes used here.
"""

from __future__ import annotations

import heapq
import math

# name: (lon, lat)
WAYPOINTS = {
    "w_atl_s": (-35.0, -20.0), "w_atl_eq": (-30.0, 0.0), "w_atl_n": (-35.0, 30.0), "w_atl_ne": (-15.0, 45.0),
    "w_finisterre": (-10.0, 43.5), "w_gibraltar": (-5.6, 36.0), "w_channel": (-1.0, 50.0),
    "w_north_sea": (3.0, 56.0), "w_scot_n": (-4.0, 59.3), "w_irish_w": (-11.0, 54.0),
    "w_suez_n": (32.3, 31.4), "w_suez_s": (32.6, 29.9), "w_med_w": (5.0, 38.0), "w_med_e": (20.0, 35.0),
    "w_babelmandeb": (43.4, 12.6), "w_arabian": (62.0, 13.0), "w_srilanka": (80.6, 5.5),
    "w_bengal": (86.0, 14.0), "w_malacca_n": (97.5, 6.0), "w_singapore": (104.0, 1.3),
    "w_scs_s": (108.0, 6.0), "w_scs_n": (114.0, 17.0), "w_luzon": (121.0, 20.5), "w_gulf_thai": (101.5, 9.0),
    "w_sunda": (105.8, -6.0), "w_java": (111.0, -5.5), "w_lombok": (115.7, -8.9), "w_ind_s": (95.0, -15.0),
    "w_good_hope": (18.5, -35.5), "w_ind_sw": (55.0, -30.0), "w_horn": (-67.3, -57.0),
    "w_atl_sw": (-50.0, -40.0), "w_pac_se": (-80.0, -45.0), "w_pac_chile_n": (-77.0, -20.0),
    "w_panama_p": (-79.6, 8.8), "w_panama_a": (-79.9, 9.4), "w_caribbean": (-75.0, 15.0),
    "w_yucatan": (-86.0, 21.5), "w_florida": (-80.5, 24.3), "w_gulf_mex": (-90.0, 25.0),
    "w_galapagos": (-90.0, -1.0), "w_pac_mex": (-106.0, 15.0), "w_pac_us": (-125.0, 30.0),
    "w_pac_n": (-160.0, 45.0), "w_pac_nw": (165.0, 45.0), "w_japan_e": (142.0, 35.0), "w_pac_c": (-150.0, 10.0),
    "w_pac_w": (150.0, 10.0), "w_celebes": (125.0, 5.0), "w_aus_w": (113.0, -30.0), "w_aus_s": (130.0, -38.0),
    "w_tasman": (150.0, -40.0), "w_cape_verde": (-25.0, 15.0), "w_canaries": (-17.0, 30.0),
    "w_magellan": (-70.5, -52.8), "w_pac_s1": (-150.0, -35.0), "w_pac_sc": (175.0, -15.0), "w_atl_nw": (-45.0, 42.0), "w_sea_mindanao": (122.0, 7.5), "w_visayas": (122.5, 11.5),
}

EDGES = [
    ("w_atl_s", "w_atl_eq"), ("w_atl_eq", "w_atl_n"), ("w_atl_n", "w_atl_ne"), ("w_atl_ne", "w_finisterre"),
    ("w_finisterre", "w_channel"), ("w_finisterre", "w_gibraltar"), ("w_channel", "w_north_sea"),
    ("w_atl_ne", "w_irish_w"), ("w_irish_w", "w_scot_n"), ("w_scot_n", "w_north_sea"),
    ("w_gibraltar", "w_med_w"), ("w_med_w", "w_med_e"), ("w_med_e", "w_suez_n"), ("w_suez_n", "w_suez_s"),
    ("w_suez_s", "w_babelmandeb"), ("w_babelmandeb", "w_arabian"), ("w_arabian", "w_srilanka"),
    ("w_srilanka", "w_bengal"), ("w_srilanka", "w_malacca_n"), ("w_bengal", "w_malacca_n"),
    ("w_malacca_n", "w_singapore"), ("w_singapore", "w_scs_s"), ("w_scs_s", "w_scs_n"), ("w_scs_s", "w_gulf_thai"),
    ("w_scs_n", "w_luzon"), ("w_singapore", "w_sunda"), ("w_singapore", "w_java"), ("w_sunda", "w_java"),
    ("w_java", "w_lombok"), ("w_sunda", "w_ind_s"), ("w_lombok", "w_ind_s"), ("w_ind_s", "w_srilanka"),
    ("w_ind_s", "w_ind_sw"), ("w_ind_sw", "w_good_hope"), ("w_arabian", "w_ind_sw"), ("w_good_hope", "w_atl_s"),
    ("w_atl_s", "w_atl_sw"), ("w_atl_sw", "w_horn"), ("w_horn", "w_pac_se"), ("w_pac_se", "w_pac_chile_n"),
    ("w_pac_chile_n", "w_galapagos"), ("w_galapagos", "w_panama_p"), ("w_panama_p", "w_panama_a"),
    ("w_panama_a", "w_caribbean"), ("w_caribbean", "w_atl_eq"), ("w_caribbean", "w_atl_n"),
    ("w_caribbean", "w_yucatan"), ("w_yucatan", "w_gulf_mex"), ("w_gulf_mex", "w_florida"), ("w_florida", "w_atl_n"),
    ("w_panama_p", "w_pac_mex"), ("w_pac_mex", "w_pac_us"), ("w_pac_us", "w_pac_n"), ("w_pac_n", "w_pac_nw"),
    ("w_pac_nw", "w_japan_e"), ("w_japan_e", "w_luzon"), ("w_pac_mex", "w_pac_c"), ("w_pac_c", "w_pac_w"),
    ("w_galapagos", "w_pac_c"), ("w_pac_w", "w_luzon"), ("w_pac_w", "w_celebes"), ("w_celebes", "w_sea_mindanao"),
    ("w_sea_mindanao", "w_visayas"), ("w_visayas", "w_luzon"), ("w_celebes", "w_java"), ("w_ind_s", "w_aus_w"),
    ("w_aus_w", "w_aus_s"), ("w_aus_s", "w_tasman"), ("w_tasman", "w_pac_w"), ("w_pac_chile_n", "w_pac_c"),
    ("w_atl_eq", "w_cape_verde"), ("w_cape_verde", "w_canaries"), ("w_canaries", "w_finisterre"),
    ("w_canaries", "w_gibraltar"), ("w_atl_sw", "w_magellan"), ("w_magellan", "w_pac_se"), ("w_tasman", "w_pac_s1"),
    ("w_pac_s1", "w_pac_se"), ("w_pac_s1", "w_pac_chile_n"), ("w_pac_w", "w_pac_sc"), ("w_pac_sc", "w_pac_s1"),
    ("w_florida", "w_atl_nw"), ("w_atl_nw", "w_irish_w"), ("w_atl_nw", "w_channel"), ("w_atl_s", "w_cape_verde"),
]


def gc_nm(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 3440.065 * math.asin(math.sqrt(h))


def build_graph(ports: dict[str, tuple[tuple[float, float], list[str]]]) -> dict[str, list[tuple[str, float]]]:
    """ports: name -> ((lon, lat), [waypoints it connects to])."""
    coords = dict(WAYPOINTS)
    g: dict[str, list[tuple[str, float]]] = {k: [] for k in coords}
    for a, b in EDGES:
        d = gc_nm(coords[a], coords[b])
        g[a].append((b, d))
        g[b].append((a, d))
    for p, (xy, links) in ports.items():
        coords[p] = xy
        g.setdefault(p, [])
        for w in links:
            d = gc_nm(xy, coords[w])
            g[p].append((w, d))
            g[w].append((p, d))
    g["_coords"] = coords  # type: ignore[assignment]
    return g


def shortest_nm(g: dict, a: str, b: str) -> float:
    if a == b:
        return 0.0
    coords = g["_coords"]
    if gc_nm(coords[a], coords[b]) < 400:  # same coast: direct short-sea leg
        return gc_nm(coords[a], coords[b]) * 1.15
    dist = {a: 0.0}
    pq = [(0.0, a)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == b:
            return d
        if d > dist.get(u, math.inf):
            continue
        for v, w in g[u]:
            nd = d + w
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return math.inf
