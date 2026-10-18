#!/usr/bin/env python3
"""
CRESCENT X - final mark generator for KUBRIQUE (plain python, no numpy).

Writes, next to itself:
  crescent-x-mono.svg        #111111 on transparent      crescent-x-mono-light.svg   #F3E7C3
  crescent-x.svg             animated (CSS rotation + SMIL sheen + colour cycle, no JS)
  crescent-x-lockup.svg      mark + wordmark "CRESCENT X" (live font, outline before print)
  preview.html / frames.html review pages (rendered to review.png / frames.png by the workflow)

Construction (viewBox 0 0 512 512, "u" = viewBox units; crescent centre O=(265,256), R=222)
  ring-crescent : circle (O,R) minus a cut-out ellipse CUT (216.7 x 202.4 u, rotated +8.4 deg,
                  centre 25.8 u left of O).  Fitted to the reference's inner edge with the horns
                  pinned at -126 / +134 deg (10.8 / 7.5 o'clock).  Two exact arcs.
  ring-x2       : ascending ring, -31.7 deg: outer ellipse minus a slightly smaller lens ellipse
                  that is shifted toward the lower-right edge and twisted -2.3 deg, so the
                  upper-left band thins and the lower-right band thickens toward the upper-right
                  tip (a hoop seen from slightly above).  Evenodd pair of ellipses (four arcs).
  ring-x1       : descending ring, +27.3 deg.  The reference's x1 is not an ellipse minus an
                  ellipse: it is a swooshing band (51 u at the centre) that tapers to a blunt
                  rounded end pushed into the crescent at ~46 deg, and whose upper-left end
                  rounds over into a thin horn (sliver) that runs back along the top of the loop
                  and fades out before the X centre, leaving the loop open.  It is drawn as ONE
                  closed outline: each long edge is a cubic Hermite spline n(s) in the ring's own
                  frame (knots = (s, n, dn/ds), measured from the approved reference), which is
                  exactly a chain of cubic Beziers, and the three rounded ends are pairs of
                  tangent-continuous Beziers.  Sixteen smooth segments; sharp only at the sliver tip.

Weave (verified against the reference crops): x1 over x2 at both centre crossings; x1 over the
crescent at its lower-right end; x2 over the crescent at its upper-right tip.  Crescent horns,
the x1 loop/horn and the x2 lower-left end cross nothing.  Stacking: crescent -> x2 -> x1.
Gaps (GAP u each side of the over-ring) are explicit cut shapes: each under-ring is masked by the
over-ring's outline stroked 2*GAP wide, so the gaps are transparent and the whole mark recolours
from the single fill on <g id="mark">.  gen_mark.py enumerates every crossing between the
outlines and refuses to write if one is not in the expected list (so a re-tune cannot silently
create a new, un-woven crossing).
"""
import math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ parameters (u)
INK, LIGHT = "#111111", "#F3E7C3"
GAP = 7.5                                   # weave gap each side of the over-ring (ref: 6.7-7.9)

OX, OY, R = 265.0, 256.0, 222.0             # crescent outer circle
CUT = (239.2, 255.4, 216.7, 202.4, 8.4)     # cut-out ellipse: cx, cy, a, b, rotation (deg, cw)

# x2 (ascending): outer ellipse E and lens L, each (cx, cy, a, b, rotation)
X2E = (231.8, 268.4, 225.1, 55.2, -31.7)
X2L = (227.3, 274.0, 199.7, 35.6, -34.0)

# x1 (descending): local frame (origin, axis angle); s along the axis toward the lower right,
# n perpendicular, positive toward the lower-left.  Knots are (s, n, dn/ds).
X1_O, X1_TH = (223.74, 261.10), 27.3
X1_UPPER = [(-185.0, -13.2, 0.30), (-150.0, -7.6, 0.11), (-100.0, -4.2, 0.04), (-40.0, -3.3, 0.0),
            (40.0, -5.0, 0.0), (110.0, -4.8, 0.06), (170.0, 1.3, 0.25), (200.0, 11.5, 0.50),
            (225.5, 26.6, 1.05)]                                   # band's upper-right edge
X1_LOWER = [(-222.0, 4.0, 1.05), (-180.0, 30.5, 0.38), (-130.0, 43.6, 0.14), (-70.0, 47.8, 0.0),
            (0.0, 46.0, -0.04), (70.0, 41.7, -0.085), (150.0, 36.5, 0.0), (200.0, 39.8, 0.17),
            (214.0, 43.0, 0.40)]                                   # band's lower-left edge (ends 11.5 u before the
                                                                   # upper edge so the end chord is square to the band)
X1_HORN_OUT = [(-222.0, -42.0, -0.90), (-200.0, -56.8, -0.45), (-170.0, -67.5, -0.25),
               (-135.0, -73.4, -0.09), (-100.0, -75.5, 0.0), (-64.0, -74.6, 0.03)]   # sliver, outer edge
X1_HORN_IN = [(-185.0, -46.5, -1.20), (-170.0, -56.8, -0.50), (-145.0, -65.0, -0.25),
              (-115.0, -70.9, -0.12), (-85.0, -73.6, -0.05), (-64.0, -74.6, -0.03)]  # sliver, inner edge
X1_END = (-231.1, -22.7)      # extreme of the ring's rounded upper-left end
X1_HOLE_END = (-191.0, -29.5) # extreme of the loop hole's rounded end
X1_TIP_REACH = 9.0            # the lower-right cap's nose sits this far beyond the mid-point of its edge ends

TITLE = "Crescent X"
ARIA = "Crescent X, the Kubrique logo mark: a crescent and two interlocking orbital rings forming an X"


# ------------------------------------------------------------------ helpers
def f(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def unit(v):
    l = math.hypot(*v)
    return (v[0] / l, v[1] / l)


class Ell:
    def __init__(self, cx, cy, a, b, th_deg):
        self.cx, self.cy, self.a, self.b, self.th = cx, cy, a, b, th_deg
        self.c, self.s = math.cos(math.radians(th_deg)), math.sin(math.radians(th_deg))

    def pt(self, t):
        x, y = self.a * math.cos(t), self.b * math.sin(t)
        return (self.cx + x * self.c - y * self.s, self.cy + x * self.s + y * self.c)

    def local(self, p):
        dx, dy = p[0] - self.cx, p[1] - self.cy
        return (dx * self.c + dy * self.s, -dx * self.s + dy * self.c)

    def inside(self, p):
        x, y = self.local(p)
        return (x / self.a) ** 2 + (y / self.b) ** 2 < 1.0

    def param_of(self, p):
        x, y = self.local(p)
        return math.atan2(y / self.b, x / self.a)

    def arc(self, t1, t2, ccw=False):
        span = ((t1 - t2) if ccw else (t2 - t1)) % (2 * math.pi)
        x, y = self.pt(t2)
        return f"A{f(self.a)} {f(self.b)} {f(self.th)} {1 if span > math.pi else 0} {0 if ccw else 1} {f(x)} {f(y)}"

    def whole(self):
        p0 = self.pt(0.0)
        return f"M{f(p0[0])} {f(p0[1])} {self.arc(0.0, math.pi)} {self.arc(math.pi, 0.0)} Z"

    def poly(self, n=720):
        return [self.pt(2 * math.pi * i / n) for i in range(n + 1)]


def intersections(E, L, n=4000):
    """parameters t on E where E crosses L"""
    ts, prev = [], None
    for i in range(n + 1):
        t = -math.pi + 2 * math.pi * i / n
        v = L.inside(E.pt(t))
        if prev is not None and v != prev[1]:
            lo, hi = prev[0], t
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                if L.inside(E.pt(mid)) == prev[1]:
                    lo = mid
                else:
                    hi = mid
            ts.append(0.5 * (lo + hi))
        prev = (t, v)
    return ts


def crescent():
    """circle minus cut-out ellipse, as outer arc horn->horn (through 3 o'clock) + inner arc back"""
    O, I = Ell(OX, OY, R, R, 0.0), Ell(*CUT)
    ts = intersections(O, I)
    assert len(ts) == 2, f"crescent: expected 2 horns, got {len(ts)}"
    t1, t2 = ts
    mid = t1 + ((t2 - t1) % (2 * math.pi)) / 2
    if I.inside(O.pt(mid)):
        t1, t2 = t2, t1
    p1, p2 = O.pt(t1), O.pt(t2)
    u1, u2 = I.param_of(p2), I.param_of(p1)
    midl = u1 + ((u2 - u1) % (2 * math.pi)) / 2
    ccw = not O.inside(I.pt(midl))
    d = f"M{f(p1[0])} {f(p1[1])} {O.arc(t1, t2)} {I.arc(u1, u2, ccw=ccw)} Z"
    # polylines of the two visible edges (for the crossing check)
    n = 400
    outer = [O.pt(t1 + ((t2 - t1) % (2 * math.pi)) * i / n) for i in range(n + 1)]
    sp = ((u1 - u2) if ccw else (u2 - u1)) % (2 * math.pi)
    inner = [I.pt(u1 + (-sp if ccw else sp) * i / n) for i in range(n + 1)]
    horns = [math.degrees(math.atan2(p[1] - OY, p[0] - OX)) for p in (p1, p2)]
    return d, [("outer", outer), ("inner", inner)], O, I, horns


# ---- x1: Hermite edges -> cubic Beziers in the local frame, then into the global frame
X1_C, X1_S = math.cos(math.radians(X1_TH)), math.sin(math.radians(X1_TH))


def x1_global(p):
    s, n = p
    return (X1_O[0] + s * X1_C - n * X1_S, X1_O[1] + s * X1_S + n * X1_C)


def hermite_beziers(knots):
    """[(s, n, m)] -> list of cubic Bezier control quads in local coords, increasing s"""
    out = []
    for (s0, n0, m0), (s1, n1, m1) in zip(knots, knots[1:]):
        h = s1 - s0
        out.append(((s0, n0), (s0 + h / 3, n0 + m0 * h / 3), (s1 - h / 3, n1 - m1 * h / 3), (s1, n1)))
    return out


def reverse_beziers(segs):
    return [(d, c, b, a) for (a, b, c, d) in reversed(segs)]


def cap_bezier(A, ta, B, tb):
    """one cubic from A (unit tangent ta) to B (unit tangent tb), handles sized like a circular arc"""
    c = (B[0] - A[0], B[1] - A[1])
    L = math.hypot(*c)
    cosang = max(-1.0, min(1.0, ta[0] * tb[0] + ta[1] * tb[1]))
    th = math.acos(cosang)
    if th < 1e-6:
        k = L / 3
    else:
        r = L / (2 * math.sin(th / 2))
        k = (4 / 3) * math.tan(th / 4) * r
    return (A, (A[0] + ta[0] * k, A[1] + ta[1] * k), (B[0] - tb[0] * k, B[1] - tb[1] * k), B)


def x1_outline():
    """closed outline of x1 as a list of cubic Beziers (local coords)"""
    up, lo = X1_UPPER, X1_LOWER
    ho, hi = X1_HORN_OUT, X1_HORN_IN
    segs = []
    # band upper edge, +s
    segs += hermite_beziers(up)
    # lower-right rounded end: U8 -> nose P -> L8
    U8, L8 = up[-1], lo[-1]
    tU = unit((1.0, U8[2]))
    dmid = unit((1.0, 0.5 * (U8[2] + L8[2])))
    mid = (0.5 * (U8[0] + L8[0]), 0.5 * (U8[1] + L8[1]))
    P = (mid[0] + X1_TIP_REACH * dmid[0], mid[1] + X1_TIP_REACH * dmid[1])
    tP = (-dmid[1], dmid[0])
    tL = unit((-1.0, -L8[2]))
    segs.append(cap_bezier((U8[0], U8[1]), tU, P, tP))
    segs.append(cap_bezier(P, tP, (L8[0], L8[1]), tL))
    # band lower edge, -s
    segs += reverse_beziers(hermite_beziers(lo))
    # upper-left rounded end: L0 -> extreme -> B0 (start of the horn's outer edge)
    L0, B0 = lo[0], ho[0]
    segs.append(cap_bezier((L0[0], L0[1]), unit((-1.0, -L0[2])), X1_END, (0.0, -1.0)))
    segs.append(cap_bezier(X1_END, (0.0, -1.0), (B0[0], B0[1]), unit((1.0, B0[2]))))
    # horn outer edge, +s, to the sliver tip
    segs += hermite_beziers(ho)
    # horn inner edge (hole's upper boundary), -s, back to the hole's end
    segs += reverse_beziers(hermite_beziers(hi))
    # hole's rounded end: H0 -> extreme -> U0
    H0, U0 = hi[0], up[0]
    segs.append(cap_bezier((H0[0], H0[1]), unit((-1.0, -H0[2])), X1_HOLE_END, (0.0, 1.0)))
    segs.append(cap_bezier(X1_HOLE_END, (0.0, 1.0), (U0[0], U0[1]), unit((1.0, U0[2]))))
    return segs


def bez_pt(seg, t):
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = seg
    u = 1 - t
    return (u * u * u * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t * x3,
            u * u * u * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t * t * t * y3)


def x1_path_and_poly():
    segs = [tuple(x1_global(p) for p in seg) for seg in x1_outline()]
    d = [f"M{f(segs[0][0][0])} {f(segs[0][0][1])}"]
    for (_, c1, c2, p3) in segs:
        d.append(f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p3[0])} {f(p3[1])}")
    d.append("Z")
    poly = []
    for seg in segs:
        poly += [bez_pt(seg, i / 24) for i in range(24)]
    poly.append(poly[0])
    return " ".join(d), poly, segs


# ------------------------------------------------------------------ build
CRES_D, CRES_EDGES, CO, CI, HORNS = crescent()
E2, L2 = Ell(*X2E), Ell(*X2L)
X2_D = E2.whole() + " " + L2.whole()
X1_D, X1_POLY, X1_SEGS = x1_path_and_poly()
OUTLINES = {"crescent": CRES_EDGES, "x2": [("outer", E2.poly()), ("lens", L2.poly())], "x1": [("outline", X1_POLY)]}

# expected crossings (shape pair, approximate location in u, radius) -> who is over
EXPECTED = [("x1", "x2", (169, 257), 50, "x1 over x2 (upper-left band of x2 crosses x1's two edges, X centre)"),
            ("x1", "x2", (263, 303), 50, "x1 over x2 (lower-right band of x2 crosses x1's two edges, X centre)"),
            ("x1", "crescent", (410, 400), 50, "x1 over crescent (x1's rounded end pierces the band)"),
            ("x2", "crescent", (420, 150), 50, "x2 over crescent (x2's tip docks on the inner edge)")]


def seg_intersect(p1, p2, p3, p4):
    d = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0])
    if abs(d) < 1e-12:
        return None
    t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / d
    u = ((p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])) / d
    if 0 <= t <= 1 and 0 <= u <= 1:
        return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))
    return None


def crossings():
    """every intersection between outlines of different shapes, clustered"""
    raw = []
    keys = list(OUTLINES)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            for na, A in OUTLINES[keys[i]]:
                for nb, B in OUTLINES[keys[j]]:
                    # coarse bbox grid to keep this quick
                    for a0, a1 in zip(A, A[1:]):
                        ax0, ax1 = min(a0[0], a1[0]) - 0.01, max(a0[0], a1[0]) + 0.01
                        ay0, ay1 = min(a0[1], a1[1]) - 0.01, max(a0[1], a1[1]) + 0.01
                        for b0, b1 in zip(B, B[1:]):
                            if max(b0[0], b1[0]) < ax0 or min(b0[0], b1[0]) > ax1 or max(b0[1], b1[1]) < ay0 or min(b0[1], b1[1]) > ay1:
                                continue
                            p = seg_intersect(a0, a1, b0, b1)
                            if p:
                                raw.append((keys[i], keys[j], f"{na}x{nb}", p))
    clusters = []
    for ka, kb, e, p in raw:
        for c in clusters:
            if c["pair"] == (ka, kb) and math.hypot(c["p"][0] - p[0], c["p"][1] - p[1]) < 40:
                c["n"] += 1
                c["edges"].add(e)
                c["p"] = ((c["p"][0] * (c["n"] - 1) + p[0]) / c["n"], (c["p"][1] * (c["n"] - 1) + p[1]) / c["n"])
                break
        else:
            clusters.append({"pair": (ka, kb), "p": p, "n": 1, "edges": {e}})
    report, bad = [], []
    for c in clusters:
        hit = [x for x in EXPECTED if {x[0], x[1]} == set(c["pair"]) and math.hypot(x[2][0] - c["p"][0], x[2][1] - c["p"][1]) < x[3]]
        line = f"{c['pair'][0]} x {c['pair'][1]} at ({c['p'][0]:.0f},{c['p'][1]:.0f}), {c['n']} edge hits [{', '.join(sorted(c['edges']))}] -> " + (hit[0][4] if hit else "UNEXPECTED")
        report.append(line)
        if not hit:
            bad.append(line)
    return report, bad


# ------------------------------------------------------------------ SVG
def defs_block(ink_id_prefix="cx"):
    g2 = f(2 * GAP)
    P = ink_id_prefix
    return f'''    <path id="{P}-crescent" d="{CRES_D}"/>
    <path id="{P}-x1" d="{X1_D}"/>
    <path id="{P}-x2" fill-rule="evenodd" d="{X2_D}"/>
    <!-- weave gaps: each under-ring is cut by the over-ring's outline stroked {g2} wide (transparent gaps) -->
    <mask id="{P}-under-x1" maskUnits="userSpaceOnUse" x="0" y="0" width="512" height="512">
      <rect width="512" height="512" fill="#fff"/>
      <use href="#{P}-x1" xlink:href="#{P}-x1" fill="#000" stroke="#000" stroke-width="{g2}" stroke-linejoin="round"/>
    </mask>
    <mask id="{P}-under-x1-x2" maskUnits="userSpaceOnUse" x="0" y="0" width="512" height="512">
      <rect width="512" height="512" fill="#fff"/>
      <use href="#{P}-x1" xlink:href="#{P}-x1" fill="#000" stroke="#000" stroke-width="{g2}" stroke-linejoin="round"/>
      <use href="#{P}-x2" xlink:href="#{P}-x2" fill="#000" fill-rule="evenodd" stroke="#000" stroke-width="{g2}" stroke-linejoin="round"/>
    </mask>'''


WEAVE_COMMENT = '''  <!--
    CRESCENT X. Weave table (over, under): x1 over x2 at the X centre; x1 over the crescent at the lower
    right; x2 over the crescent at the upper right. Stacking crescent, x2, x1; the gaps are transparent
    cut shapes (masks), so recolour the whole mark by changing the one fill on #mark.
    Generated by gen_mark.py - edit the parameters there, not this file.
  -->'''


def rings_block(prefix="cx", fills=None):
    fl = lambda k: f' fill="{fills[k]}"' if fills else ""
    return f'''    <use id="ring-crescent" href="#{prefix}-crescent" xlink:href="#{prefix}-crescent" mask="url(#{prefix}-under-x1-x2)"{fl("crescent")}/>
    <use id="ring-x2" href="#{prefix}-x2" xlink:href="#{prefix}-x2" mask="url(#{prefix}-under-x1)"{fl("x2")}/>
    <use id="ring-x1" href="#{prefix}-x1" xlink:href="#{prefix}-x1"{fl("x1")}/>'''


def svg_mono(ink):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 512 512" width="512" height="512" role="img" aria-label="{ARIA}">
  <title>{TITLE}</title>
{WEAVE_COMMENT}
  <defs>
{defs_block()}
  </defs>
  <g id="mark" fill="{ink}">
{rings_block()}
  </g>
</svg>
'''


# colour cycle: gold -> rose -> violet -> teal -> gold (24 s); sheen = lighter tint of the same hue
BASE = ["#D9B35A", "#D98A9A", "#9A86D9", "#6FC7C2", "#D9B35A"]
SHEEN = ["#FFF1C2", "#FFD6DE", "#DCD3FF", "#C9F6F2", "#FFF1C2"]
DEEP = ["#B88F36", "#B8647A", "#6F5CC2", "#3FA39D", "#B88F36"]


def gradient(gid, cx, cy, half, period, reverse, begin="0s"):
    """linear gradient across the ring (userSpaceOnUse) that rotates about the ring's centre, so a
    bright sheen band sweeps round the ring like a highlight on a spinning hoop"""
    vals = ";".join
    fr, to = ("360", "0") if reverse else ("0", "360")
    stops = ""
    for off, cols in (("0", DEEP), ("0.32", BASE), ("0.5", SHEEN), ("0.68", BASE), ("1", DEEP)):
        stops += f'''
      <stop offset="{off}" stop-color="{cols[0]}">
        <animate attributeName="stop-color" values="{vals(cols)}" dur="24s" begin="{begin}" repeatCount="indefinite"/>
      </stop>'''
    return f'''    <linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{f(cx - half)}" y1="{f(cy)}" x2="{f(cx + half)}" y2="{f(cy)}">
      <animateTransform attributeName="gradientTransform" type="rotate" from="{fr} {f(cx)} {f(cy)}" to="{to} {f(cx)} {f(cy)}" dur="{period}s" begin="{begin}" repeatCount="indefinite"/>{stops}
    </linearGradient>'''


def svg_animated(begin="0s", delay="0s"):
    fills = {"crescent": "url(#cx-sheen-crescent)", "x1": "url(#cx-sheen-x1)", "x2": "url(#cx-sheen-x2)"}
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 512 512" width="512" height="512" role="img" aria-label="{ARIA}">
  <title>{TITLE}</title>
{WEAVE_COMMENT}
  <style>
    #spin {{ transform-box: view-box; transform-origin: 256px 256px; animation: cx-spin 90s linear infinite; animation-delay: {delay}; }}
    @keyframes cx-spin {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
    @media (prefers-reduced-motion: reduce) {{ #spin {{ animation-play-state: paused; }} }}
  </style>
  <defs>
{defs_block()}
    <!-- per-ring sheen: a rotating gradient (own period each, x2 reversed) whose stops cycle gold-rose-violet-teal over 24 s -->
{gradient("cx-sheen-crescent", OX, OY, R, 26, False, begin)}
{gradient("cx-sheen-x1", X1_O[0], X1_O[1], 240, 14, False, begin)}
{gradient("cx-sheen-x2", X2E[0], X2E[1], 230, 20, True, begin)}
  </defs>
  <g id="spin">
    <g id="mark" fill="{BASE[0]}">
{rings_block(fills=fills)}
    </g>
  </g>
</svg>
'''


def svg_lockup(ink=INK):
    # mark at 1.5x in a 1024 x 1080 box (mark spans y 111..777), wordmark baseline at 932: cap height ~66 u,
    # so the gap between the mark and the type is ~90 u, about an eighth of the mark's width, as in the reference. letter-spacing adds a trailing space after
    # the last glyph, so the text anchor is nudged right by half of one spacing to centre it optically.
    fs, ls = 92.0, 0.25
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1024 1080" width="1024" height="1080" role="img" aria-label="{ARIA}, with the wordmark CRESCENT X">
  <title>{TITLE}</title>
{WEAVE_COMMENT}
  <!-- The wordmark is live text (Montserrat / Jost / Futura / Century Gothic, 600, 0.25em tracking). Outline it before print or any use where the font is not guaranteed. -->
  <defs>
{defs_block()}
  </defs>
  <g id="lockup" fill="{ink}">
    <g id="mark" transform="translate(128 60) scale(1.5)">
{rings_block()}
    </g>
    <text id="wordmark" x="{f(512 + fs * ls / 2)}" y="932" text-anchor="middle" font-family="Montserrat, Jost, Futura, 'Century Gothic', Helvetica, Arial, sans-serif" font-weight="600" font-size="{f(fs)}" letter-spacing="{f(fs * ls)}">CRESCENT X</text>
  </g>
</svg>
'''


REF = "/tmp/claude-0/-home-user-Kubrique-/1089e9da-6911-5cb8-8308-49f4fb2445d5/scratchpad/orbital/target-crop.png"

PREVIEW = '''<!doctype html>
<html><head><meta charset="utf-8"><title>Crescent X - final review</title>
<style>
  html,body{margin:0;background:#fff;font:11px/1.3 Helvetica,Arial,sans-serif;color:#666}
  body{width:1200px;height:673px;position:relative;overflow:hidden}
  .lab{position:absolute;font-size:11px;color:#888;z-index:2;left:6px;top:4px}
  .box{position:absolute;overflow:hidden;background:#fff}
  img{display:block}
  .ref{left:10px;top:10px;width:300px;height:300px}
  .ref img{position:absolute;left:-59px;top:-40px;width:408px}
  .mine{left:320px;top:10px;width:300px;height:300px}
  .mine img{position:absolute;left:0;top:-5px;width:300px;height:300px}
  .ovl{left:630px;top:10px;width:300px;height:300px}
  .ovl img.r{position:absolute;left:-59px;top:-40px;width:408px;opacity:.4}
  .ovl img.m{position:absolute;left:0;top:-5px;width:300px;height:300px;opacity:.7;filter:invert(1) sepia(1) saturate(30) hue-rotate(-30deg)}
  .dark{left:940px;top:10px;width:250px;height:420px;background:#0d0e13}
  .dark img.big{width:250px;height:250px;margin:0}
  .strip{position:absolute;left:10px;top:320px;display:flex;gap:14px;align-items:flex-end;height:130px}
  .strip div{display:flex;flex-direction:column;align-items:center;gap:3px}
  .strip.d{left:950px;top:270px;background:#0d0e13;color:#889;padding:4px}
  .zoom{top:460px;width:224px;height:200px}
  .zoom img{position:absolute;width:800px;height:800px}
</style></head><body>
<div class="box ref"><span class="lab">reference</span><img src="file://REF"></div>
<div class="box mine"><span class="lab">final / crescent-x-mono.svg</span><img src="crescent-x-mono.svg"></div>
<div class="box ovl"><span class="lab">overlay (mine = red)</span><img class="r" src="file://REF"><img class="m" src="crescent-x-mono.svg"></div>
<div class="box dark"><img class="big" src="crescent-x-mono-light.svg"></div>
<div class="strip">
  <div><img src="crescent-x-mono.svg" width="120" height="120"><span>120</span></div>
  <div><img src="crescent-x-mono.svg" width="64" height="64"><span>64</span></div>
  <div><img src="crescent-x-mono.svg" width="40" height="40"><span>40</span></div>
  <div><img src="crescent-x-mono.svg" width="24" height="24"><span>24</span></div>
  <div><img src="crescent-x-mono.svg" width="16" height="16"><span>16</span></div>
</div>
<div class="strip d">
  <div><img src="crescent-x-mono-light.svg" width="64" height="64"><span>64</span></div>
  <div><img src="crescent-x-mono-light.svg" width="40" height="40"><span>40</span></div>
  <div><img src="crescent-x-mono-light.svg" width="24" height="24"><span>24</span></div>
  <div><img src="crescent-x-mono-light.svg" width="16" height="16"><span>16</span></div>
</div>
<div class="box zoom" style="left:10px"><span class="lab">centre x1.56</span><img src="crescent-x-mono.svg" style="left:-250px;top:-300px"></div>
<div class="box zoom" style="left:244px"><span class="lab">x1 end / crescent</span><img src="crescent-x-mono.svg" style="left:-520px;top:-500px"></div>
<div class="box zoom" style="left:478px"><span class="lab">x2 tip / crescent</span><img src="crescent-x-mono.svg" style="left:-520px;top:-120px"></div>
<div class="box zoom" style="left:712px"><span class="lab">x1 loop + horn</span><img src="crescent-x-mono.svg" style="left:-10px;top:-120px"></div>
<div class="box zoom" style="left:946px"><span class="lab">x2 lower-left end</span><img src="crescent-x-mono.svg" style="left:-10px;top:-480px"></div>
</body></html>
'''

FRAMES = '''<!doctype html>
<html><head><meta charset="utf-8"><title>Crescent X - animation frames</title>
<style>
  html,body{margin:0;background:#0d0e13;font:12px Helvetica,Arial,sans-serif;color:#aab}
  body{width:1200px;height:673px;display:flex;flex-wrap:wrap;align-content:flex-start;gap:14px;padding:12px;box-sizing:border-box}
  .fr{display:flex;flex-direction:column;align-items:center;gap:6px}
  .fr img{width:280px;height:280px;display:block}
  .light{background:#fff;color:#556}
</style></head><body>
<div class="fr"><img src="frames/t0.svg"><span>t = 0 s</span></div>
<div class="fr"><img src="frames/t6.svg"><span>t = 6 s</span></div>
<div class="fr"><img src="frames/t12.svg"><span>t = 12 s</span></div>
<div class="fr"><img src="frames/t18.svg"><span>t = 18 s</span></div>
<div class="fr light" style="padding:8px"><img src="crescent-x.svg" style="width:220px;height:220px"><span>crescent-x.svg on white (live)</span></div>
<div class="fr" style="padding:8px"><img src="crescent-x.svg" style="width:220px;height:220px"><span>crescent-x.svg on dark (live)</span></div>
<div class="fr" style="padding:8px"><img src="crescent-x-lockup.svg" style="width:209px;height:220px;background:#fff"><span>lockup</span></div>
</body></html>
'''


def diagnostics():
    out = []
    # crescent
    def thick(ang):
        t = math.radians(ang)
        r = R
        while r > 0 and not CI.inside((OX + r * math.cos(t), OY + r * math.sin(t))):
            r -= 0.25
        return R - r
    out.append(f"crescent horns at {HORNS[0]:.1f} / {HORNS[1]:.1f} deg (clock {((HORNS[0]+90)%360)/30:.2f} / {((HORNS[1]+90)%360)/30:.2f}); "
               f"thickness at 0/-60/+60/-90/+90 deg: {thick(0):.1f} / {thick(-60):.1f} / {thick(60):.1f} / {thick(-90):.1f} / {thick(90):.1f} u")
    # x2 tips and band widths
    tipUR, tipLL = E2.pt(0.0), E2.pt(math.pi)
    def band_depth(p):
        t = math.atan2(p[1] - OY, p[0] - OX)
        r = R
        while r > 0 and not CI.inside((OX + r * math.cos(t), OY + r * math.sin(t))):
            r -= 0.25
        return math.hypot(p[0] - OX, p[1] - OY) - r, R - math.hypot(p[0] - OX, p[1] - OY)
    di, do = band_depth(tipUR)
    out.append(f"x2 upper-right tip at ({tipUR[0]:.1f},{tipUR[1]:.1f}): {di:.1f} u past the crescent's inner edge, {do:.1f} u inside the outer edge; "
               f"lower-left extreme at ({tipLL[0]:.1f},{tipLL[1]:.1f}) (ref 40.9,385.5)")
    # min x2 band width
    worst = 99
    for i in range(720):
        q = L2.pt(2 * math.pi * i / 720)
        x, y = E2.local(q)
        k = 1 / math.sqrt((x / E2.a) ** 2 + (y / E2.b) ** 2)
        worst = min(worst, (k - 1) * math.hypot(x, y))
    out.append(f"x2 thinnest band {worst:.1f} u")
    # x1 nose
    nose = max(X1_POLY, key=lambda p: math.hypot(p[0] - OX, p[1] - OY) if 20 < math.degrees(math.atan2(p[1] - OY, p[0] - OX)) < 70 else 0)
    di, do = band_depth(nose)
    out.append(f"x1 nose at ({nose[0]:.1f},{nose[1]:.1f}) bearing {math.degrees(math.atan2(nose[1]-OY, nose[0]-OX)):.1f} deg: {di:.1f} u past the inner edge, {do:.1f} u inside the outer edge -> {do - GAP:.1f} u of crescent outside the halo")
    # bbox
    xs = [p[0] for pl in OUTLINES.values() for _, pts in pl for p in pts if True]
    ys = [p[1] for pl in OUTLINES.values() for _, pts in pl for p in pts]
    # crescent inner edge is inside the circle; the bbox of the union is the outer arc + rings
    out.append(f"bbox x {min(xs):.1f}..{max(xs):.1f}  y {min(ys):.1f}..{max(ys):.1f}  centre ({(min(xs)+max(xs))/2:.1f},{(min(ys)+max(ys))/2:.1f})")
    return out


def main():
    rep, bad = crossings()
    print("crossings:")
    for r in rep:
        print("  " + r)
    for d in diagnostics():
        print(d)
    if bad:
        sys.exit("UNEXPECTED crossing(s) - weave table does not cover them, nothing written:\n  " + "\n  ".join(bad))
    files = {"crescent-x-mono.svg": svg_mono(INK), "crescent-x-mono-light.svg": svg_mono(LIGHT),
             "crescent-x.svg": svg_animated(), "crescent-x-lockup.svg": svg_lockup(),
             "preview.html": PREVIEW.replace("REF", REF), "frames.html": FRAMES}
    os.makedirs(os.path.join(HERE, "frames"), exist_ok=True)
    for t in (0, 6, 12, 18):
        files[f"frames/t{t}.svg"] = svg_animated(begin=f"-{t}s", delay=f"-{t}s")
    for name, txt in files.items():
        with open(os.path.join(HERE, name), "w") as fh:
            fh.write(txt)
    print("wrote " + ", ".join(files))


if __name__ == "__main__":
    main()
