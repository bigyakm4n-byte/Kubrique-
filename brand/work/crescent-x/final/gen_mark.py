#!/usr/bin/env python3
"""
CRESCENT X - final (round 3) mark generator for KUBRIQUE.  Plain python, no numpy.

Writes, next to itself:
  crescent-x-mono.svg        hero mark, one fill #111111 on transparent
  crescent-x-mono-light.svg  same, fill #F3E7C3 (for dark backgrounds)
  crescent-x-colour.svg      crescent #111111, rings deep teal #0F6E74, rings in front
  crescent-x.svg             animated: slow whole-mark rotation (CSS) + per-ring sheen and
                             gold-rose-violet-teal colour cycle (SMIL), no JavaScript
  crescent-x-lockup.svg      mark + wordmark "CRESCENT X" (live font; outline before print)
  preview.html / frames.html review pages (rendered to review.png / frames.png)

Construction (viewBox 0 0 512 512; "u" = viewBox units)
  ring-crescent : a classic two-circle lunar crescent facing RIGHT (Turkish-flag orientation):
                  outer circle (centre O, radius R) minus an inner circle of radius r whose
                  centre is shifted d to the RIGHT along the horizontal axis only, so the two
                  horns are mirror images about the horizontal centre line.  d and r are solved
                  from the horn angle (+/- HORN_DEG) and the maximum thickness THICK at 9 o'clock.
                  Two exact arcs.
  ring-x1       : descending orbital ring, tilt +X1.th deg: outer ellipse (A x B) minus a lens
                  ellipse (a x b) with the same centre and tilt, shifted d along the ring's
                  perpendicular, so the band is thick on one long edge and thin on the other and
                  the two ends are identical (mirror-symmetric about the minor axis).  Thick on
                  its lower-left edge.  Evenodd pair of ellipses (four exact arcs).
  ring-x2       : ascending orbital ring, tilt X2.th deg, same construction, thick on its
                  upper-left edge.
  The two rings share the crescent's horizontal centre line; their centres sit to the right of
  the crescent's centre so that each ring's left tip clears the crescent's inner edge by TIP_GAP
  (solved numerically, the same gap for both rings), and the right tips sit in the open mouth of
  the crescent, past the horn tips.  The rings never lie across the crescent body.

Weave: x1 over x2 at the X centre (the only crossings).  The gap (GAP each side of x1) is an
explicit transparent cut: x2 is drawn through a mask in which x1's outline is stroked 2*GAP wide,
so the whole mark recolours from the single fill on <g id="mark">.  The script enumerates every
crossing between the outlines and refuses to write if one is not in the expected table (a
re-tune cannot silently create an un-woven crossing, e.g. a ring end landing on the crescent).
"""
import math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ parameters (u)
INK, LIGHT, TEAL = "#111111", "#F3E7C3", "#0F6E74"
GAP = 7.5            # weave gap each side of x1 where it passes over x2
TIP_GAP = 9.5        # clear air between each ring's left tip and the crescent's inner edge

R = 222.0            # crescent outer radius
HORN_DEG = 47.0      # horn tips at +/- HORN_DEG from the horizontal (about 1:25 and 4:35 o'clock)
THICK = 47.0         # maximum crescent thickness, at 9 o'clock (10.6 % of the outer diameter)

# rings: outer ellipse A x B, lens a x b, lens offset d along the ring's +n axis, tilt th (deg)
# (+n = (-sin th, cos th): down-left for the descending ring, down-right for the ascending one)
X1 = dict(A=200.0, B=49.0, a=179.0, b=24.0, d=-19.0, th=35.0)   # thick (+n) lower-left edge 44 u, thin 6 u
X2 = dict(A=196.0, B=48.0, a=176.0, b=30.0, d=6.0, th=-33.0)    # thick (-n) upper-left edge 24 u, thin 12 u

TITLE = "Crescent X"
ARIA = "Crescent X, the Kubrique logo mark: a lunar crescent facing right and two interlocking orbital rings forming an X"


# ------------------------------------------------------------------ helpers
def f(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


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


def crescent_path(O, I):
    """circle O minus circle I, as outer arc horn->horn (through the body) + inner arc back"""
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
    n = 400
    outer = [O.pt(t1 + ((t2 - t1) % (2 * math.pi)) * i / n) for i in range(n + 1)]
    sp = ((u1 - u2) if ccw else (u2 - u1)) % (2 * math.pi)
    inner = [I.pt(u1 + (-sp if ccw else sp) * i / n) for i in range(n + 1)]
    horns = [math.degrees(math.atan2(p[1] - O.cy, p[0] - O.cx)) for p in (p1, p2)]
    return d, [("outer", outer), ("inner", inner)], horns


def ring(spec, cx, cy):
    """outer ellipse and lens for a ring spec centred at (cx, cy)"""
    th = math.radians(spec["th"])
    nx, ny = -math.sin(th), math.cos(th)
    E = Ell(cx, cy, spec["A"], spec["B"], spec["th"])
    L = Ell(cx + spec["d"] * nx, cy + spec["d"] * ny, spec["a"], spec["b"], spec["th"])
    return E, L


# ------------------------------------------------------------------ solve the crescent
cosH = math.cos(math.radians(HORN_DEG))
CUT_D = THICK * (2 * R - THICK) / (2 * (R * (1 + cosH) - THICK))   # inner circle centre offset (right)
CUT_R = R - THICK + CUT_D                                          # inner circle radius


# ------------------------------------------------------------------ place the rings (crescent centre at the origin)
def tip_gap(spec, cx):
    """clear air between the ring's left tip and the inner circle (centre (CUT_D, 0), radius CUT_R)"""
    E, L = ring(spec, cx, 0.0)
    worst = 0.0
    for p in E.poly(1440):
        if p[0] < cx:
            worst = max(worst, math.hypot(p[0] - CUT_D, p[1]))
    return CUT_R - worst


def solve_cx(spec):
    lo, hi = -100.0, 200.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if tip_gap(spec, mid) < TIP_GAP:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


X1_CX, X2_CX = solve_cx(X1), solve_cx(X2)

# bbox of the union (relative to the crescent centre) -> centre the composition in the box
_O0, _I0 = Ell(0, 0, R, R, 0), Ell(CUT_D, 0, CUT_R, CUT_R, 0)
_d, _edges, _ = crescent_path(_O0, _I0)
_pts = _edges[0][1] + ring(X1, X1_CX, 0)[0].poly() + ring(X2, X2_CX, 0)[0].poly()
_bx0, _bx1 = min(p[0] for p in _pts), max(p[0] for p in _pts)
_by0, _by1 = min(p[1] for p in _pts), max(p[1] for p in _pts)
OX, OY = 256.0 - 0.5 * (_bx0 + _bx1), 256.0 - 0.5 * (_by0 + _by1)   # crescent centre in the box

CO, CI = Ell(OX, OY, R, R, 0.0), Ell(OX + CUT_D, OY, CUT_R, CUT_R, 0.0)
CRES_D, CRES_EDGES, HORNS = crescent_path(CO, CI)
E1, L1 = ring(X1, OX + X1_CX, OY)
E2, L2 = ring(X2, OX + X2_CX, OY)
X1_D = E1.whole() + " " + L1.whole()
X2_D = E2.whole() + " " + L2.whole()
OUTLINES = {"crescent": CRES_EDGES,
            "x1": [("outer", E1.poly()), ("lens", L1.poly())],
            "x2": [("outer", E2.poly()), ("lens", L2.poly())]}
XC = (0.5 * (E1.cx + E2.cx), OY)   # ring centre

# expected crossings (shape pair, approximate location in u, radius) -> who is over
EXPECTED = [("x1", "x2", XC, 120, "x1 over x2 (X centre)")]


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


def in_crescent(p):
    return math.hypot(p[0] - CO.cx, p[1] - CO.cy) <= R and math.hypot(p[0] - CI.cx, p[1] - CI.cy) >= CUT_R


def ring_clearance(E):
    """min distance from the ring's outer outline to the crescent outline; also whether any point is inside the crescent"""
    cres = [p for _, pts in CRES_EDGES for p in pts[::2]]
    best, where, bad = 1e9, None, 0
    for p in E.poly(720):
        if in_crescent(p):
            bad += 1
        dmin = min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in cres)
        if dmin < best:
            best, where = dmin, p
    return best, where, bad


# ------------------------------------------------------------------ SVG
def defs_block(P="cx"):
    g2 = f(2 * GAP)
    return f'''    <path id="{P}-crescent" d="{CRES_D}"/>
    <path id="{P}-x1" fill-rule="evenodd" d="{X1_D}"/>
    <path id="{P}-x2" fill-rule="evenodd" d="{X2_D}"/>
    <!-- weave gap: x2 is cut by x1's outline stroked {g2} wide, so the gaps are transparent -->
    <mask id="{P}-under-x1" maskUnits="userSpaceOnUse" x="0" y="0" width="512" height="512">
      <rect width="512" height="512" fill="#fff"/>
      <use href="#{P}-x1" xlink:href="#{P}-x1" fill="#000" fill-rule="evenodd" stroke="#000" stroke-width="{g2}" stroke-linejoin="round"/>
    </mask>'''


WEAVE_COMMENT = '''  <!--
    CRESCENT X. Weave table (over, under): x1 (descending ring) over x2 (ascending ring) at the X
    centre; neither ring crosses the crescent (their left tips clear its inner edge, their right
    tips sit in its open mouth). Stacking crescent, x2, x1; the gap is a transparent cut shape
    (mask), so recolour the whole mark by changing the one fill on #mark.
    Generated by gen_mark.py - edit the parameters there, not this file.
  -->'''


def rings_block(prefix="cx", fills=None):
    fl = lambda k: f' fill="{fills[k]}"' if fills else ""
    return f'''    <use id="ring-crescent" href="#{prefix}-crescent" xlink:href="#{prefix}-crescent"{fl("crescent")}/>
    <use id="ring-x2" href="#{prefix}-x2" xlink:href="#{prefix}-x2" mask="url(#{prefix}-under-x1)"{fl("x2")}/>
    <use id="ring-x1" href="#{prefix}-x1" xlink:href="#{prefix}-x1"{fl("x1")}/>'''


def svg_static(ink, fills=None):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 512 512" width="512" height="512" role="img" aria-label="{ARIA}">
  <title>{TITLE}</title>
{WEAVE_COMMENT}
  <defs>
{defs_block()}
  </defs>
  <g id="mark" fill="{ink}">
{rings_block(fills=fills)}
  </g>
</svg>
'''


# colour cycle: gold -> rose -> violet -> teal -> gold (24 s); sheen = lighter tint, deep = darker shade of the same hue
BASE = ["#D9B35A", "#D98A9A", "#9A86D9", "#6FC7C2", "#D9B35A"]
SHEEN = ["#FFF1C2", "#FFD6DE", "#DCD3FF", "#C9F6F2", "#FFF1C2"]
DEEP = ["#B88F36", "#B8647A", "#6F5CC2", "#3FA39D", "#B88F36"]


def gradient(gid, cx, cy, half, period, reverse, begin="0s"):
    """linear gradient across the ring (userSpaceOnUse) rotating about the ring's centre, so a bright
    sheen band sweeps round the ring like a highlight on a spinning hoop; stops cycle the colours"""
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
{gradient("cx-sheen-crescent", CO.cx, CO.cy, R, 26, False, begin)}
{gradient("cx-sheen-x1", E1.cx, E1.cy, X1["A"], 14, False, begin)}
{gradient("cx-sheen-x2", E2.cx, E2.cy, X2["A"], 20, True, begin)}
  </defs>
  <g id="spin">
    <g id="mark" fill="{BASE[0]}">
{rings_block(fills=fills)}
    </g>
  </g>
</svg>
'''


# lockup geometry: mark at 1.5x, wordmark below with 1.5 cap heights of clear space
LK_SCALE, LK_FS, LK_LS = 1.5, 92.0, 0.25
LK_CAP = 0.70 * LK_FS                       # Montserrat / Jost cap height ~0.70 em
LK_TOP = 111.0                              # top margin to the mark's top (= bottom margin below the baseline)
LK_X = (1024 - 512 * LK_SCALE) / 2
LK_Y = LK_TOP - _by0 * LK_SCALE - 256 * LK_SCALE + 256 * LK_SCALE  # placeholder, fixed below


def svg_lockup(ink=INK):
    top_of_mark = 256 + _by0            # mark's top in the 512 box (bbox is centred)
    bottom_of_mark = 256 + _by1
    ty = LK_TOP - top_of_mark * LK_SCALE
    mark_bottom = ty + bottom_of_mark * LK_SCALE
    gap = 1.5 * LK_CAP
    baseline = mark_bottom + gap + LK_CAP
    height = baseline + LK_TOP
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1024 {f(height)}" width="1024" height="{f(height)}" role="img" aria-label="{ARIA}, with the wordmark CRESCENT X">
  <title>{TITLE}</title>
{WEAVE_COMMENT}
  <!-- The wordmark is live text (Montserrat / Jost / Futura / Century Gothic, 600, 0.25em tracking), set {f(gap)} u
       ({f(gap / LK_CAP)} cap heights) below the mark. Outline it before print or any use where the font is not guaranteed. -->
  <defs>
{defs_block()}
  </defs>
  <g id="lockup" fill="{ink}">
    <g id="mark" transform="translate({f(LK_X)} {f(ty)}) scale({f(LK_SCALE)})">
{rings_block()}
    </g>
    <text id="wordmark" x="{f(512 + LK_FS * LK_LS / 2)}" y="{f(baseline)}" text-anchor="middle" font-family="Montserrat, Jost, Futura, 'Century Gothic', Helvetica, Arial, sans-serif" font-weight="600" font-size="{f(LK_FS)}" letter-spacing="{f(LK_FS * LK_LS)}">CRESCENT X</text>
  </g>
</svg>
'''


SCRATCH = "/tmp/claude-0/-home-user-Kubrique-/1089e9da-6911-5cb8-8308-49f4fb2445d5/scratchpad"
REF = SCRATCH + "/orbital/target-crop.png"
BEFORE = SCRATCH + "/cx-final/before/crescent-x-mono.svg"
APPROVED = SCRATCH + "/cx-final/approved/approved.jpg"


def zoom(label, left, cx, cy, scale=1.5, w=230, h=160):
    """a w x h window onto the mono SVG drawn at 512*scale px, centred on (cx, cy) u"""
    return (f'<div class="box zoom" style="left:{left}px"><span class="lab">{label}</span>'
            f'<img src="crescent-x-mono.svg" style="width:{512*scale:.0f}px;height:{512*scale:.0f}px;left:{w/2 - cx*scale:.0f}px;top:{h/2 - cy*scale:.0f}px"></div>')


def preview_html():
    tip1 = min(E1.poly(720), key=lambda p: p[0])
    tip2 = min(E2.poly(720), key=lambda p: p[0])
    end1 = max(E1.poly(720), key=lambda p: p[0])
    end2 = max(E2.poly(720), key=lambda p: p[0])
    zooms = "\n".join([
        zoom("x1 tip / crescent (top-left)", 10, tip1[0] + 10, tip1[1]),
        zoom("x2 tip / crescent (bottom-left)", 250, tip2[0] + 10, tip2[1]),
        zoom("X centre weave", 490, XC[0] - 30, XC[1]),
        zoom("x2 end / upper horn", 730, end2[0] - 20, end2[1] + 10),
        zoom("x1 end / lower horn", 970, end1[0] - 20, end1[1] - 10)])
    return f'''<!doctype html>
<html><head><meta charset="utf-8"><title>Crescent X - round 3 review</title>
<style>
  html,body{{margin:0;background:#fff;font:11px/1.3 Helvetica,Arial,sans-serif;color:#666}}
  body{{width:1200px;height:673px;position:relative;overflow:hidden}}
  .lab{{position:absolute;font-size:11px;color:#888;z-index:2;left:6px;top:4px;white-space:nowrap}}
  .box{{position:absolute;overflow:hidden;background:#fff}}
  img{{display:block}}
  .ref{{left:10px;top:10px;width:290px;height:290px}}
  .ref img{{position:absolute;left:-57px;top:-39px;width:394px}}
  .before{{left:310px;top:10px;width:290px;height:290px}}
  .before img{{width:290px;height:290px}}
  .after{{left:610px;top:10px;width:290px;height:290px}}
  .after img{{width:290px;height:290px}}
  .appr{{left:910px;top:10px;width:280px;height:290px}}
  .appr img{{position:absolute;left:-40px;top:-20px;width:360px}}
  .dark{{left:10px;top:312px;width:180px;height:180px;background:#0d0e13}}
  .dark img{{width:180px;height:180px}}
  .strip{{position:absolute;display:flex;gap:12px;align-items:flex-end}}
  .strip div{{display:flex;flex-direction:column;align-items:center;gap:3px}}
  .strip.d{{left:200px;top:312px;height:172px;background:#0d0e13;color:#889;padding:4px 8px}}
  .strip.l{{left:440px;top:312px;height:180px}}
  .colour{{left:760px;top:312px;width:180px;height:180px}}
  .colour img{{width:180px;height:180px}}
  .lockup{{left:950px;top:312px;width:240px;height:180px}}
  .lockup img{{height:180px;margin:0 auto}}
  .zoom{{top:503px;width:230px;height:160px;border:1px solid #eee}}
  .zoom img{{position:absolute}}
</style></head><body>
<div class="box ref"><span class="lab">reference (round 1)</span><img src="file://{REF}"></div>
<div class="box before"><span class="lab">before: previous final</span><img src="file://{BEFORE}"></div>
<div class="box after"><span class="lab">after: crescent-x-mono.svg</span><img src="crescent-x-mono.svg"></div>
<div class="box appr"><span class="lab">client-approved layout (raster)</span><img src="file://{APPROVED}"></div>
<div class="box dark"><img src="crescent-x-mono-light.svg"></div>
<div class="strip d">
  <div><img src="crescent-x-mono-light.svg" width="64" height="64"><span>64</span></div>
  <div><img src="crescent-x-mono-light.svg" width="40" height="40"><span>40</span></div>
  <div><img src="crescent-x-mono-light.svg" width="24" height="24"><span>24</span></div>
  <div><img src="crescent-x-mono-light.svg" width="16" height="16"><span>16</span></div>
</div>
<div class="strip l">
  <div><img src="crescent-x-mono.svg" width="120" height="120"><span>120</span></div>
  <div><img src="crescent-x-mono.svg" width="64" height="64"><span>64</span></div>
  <div><img src="crescent-x-mono.svg" width="40" height="40"><span>40</span></div>
  <div><img src="crescent-x-mono.svg" width="24" height="24"><span>24</span></div>
  <div><img src="crescent-x-mono.svg" width="16" height="16"><span>16</span></div>
</div>
<div class="box colour"><span class="lab">crescent-x-colour.svg</span><img src="crescent-x-colour.svg"></div>
<div class="box lockup"><span class="lab">lockup</span><img src="crescent-x-lockup.svg"></div>
{zooms}
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
<div class="fr" style="padding:8px"><img src="crescent-x-lockup.svg" style="width:auto;height:220px;background:#fff"><span>lockup</span></div>
</body></html>
'''


def diagnostics():
    out = []
    def thick(ang):
        t = math.radians(ang)
        r = R
        while r > 0 and not CI.inside((CO.cx + r * math.cos(t), CO.cy + r * math.sin(t))):
            r -= 0.25
        return R - r
    clock = lambda a: ((a + 90) % 360) / 30
    out.append(f"crescent: centre ({CO.cx:.1f},{CO.cy:.1f}) R {R}, inner circle r {CUT_R:.2f} shifted {CUT_D:.2f} right; "
               f"horns at {HORNS[0]:.1f} / {HORNS[1]:.1f} deg ({clock(HORNS[0]):.2f} / {clock(HORNS[1]):.2f} o'clock)")
    out.append(f"crescent thickness at 9 / 12 / 6 / 10:30 / 7:30 o'clock: {thick(180):.1f} / {thick(270):.1f} / {thick(90):.1f} / "
               f"{thick(225):.1f} / {thick(135):.1f} u ({100 * thick(180) / (2 * R):.1f} % of the diameter at 9 o'clock); "
               f"band < 16 u beyond +/-{next(a for a in range(0, 180) if thick(180 - a) < 16):.0f} deg from 9 o'clock")
    for name, E, L, spec in (("x1", E1, L1, X1), ("x2", E2, L2, X2)):
        best, where, bad = ring_clearance(E)
        tip = min(E.poly(720), key=lambda p: p[0])
        end = max(E.poly(720), key=lambda p: p[0])
        worst = 99
        for i in range(720):
            q = L.pt(2 * math.pi * i / 720)
            x, y = E.local(q)
            k = 1 / math.sqrt((x / E.a) ** 2 + (y / E.b) ** 2)
            worst = min(worst, (k - 1) * math.hypot(x, y))
        out.append(f"{name}: centre ({E.cx:.1f},{E.cy:.1f}) tilt {spec['th']} deg, bands {spec['B'] - spec['b'] + abs(spec['d']):.0f} / "
                   f"{spec['B'] - spec['b'] - abs(spec['d']):.0f} u, thinnest {worst:.1f} u; left tip ({tip[0]:.1f},{tip[1]:.1f}) "
                   f"clearance to the crescent {best:.1f} u at ({where[0]:.0f},{where[1]:.0f}); right tip ({end[0]:.1f},{end[1]:.1f}) "
                   f"at r = {math.hypot(end[0] - CO.cx, end[1] - CO.cy) / R:.3f} R, {math.degrees(math.atan2(end[1] - CO.cy, end[0] - CO.cx)):.1f} deg; "
                   f"points inside the crescent: {bad}")
    xs = [p[0] for p in _pts]
    ys = [p[1] for p in _pts]
    out.append(f"bbox x {OX + min(xs):.1f}..{OX + max(xs):.1f}  y {OY + min(ys):.1f}..{OY + max(ys):.1f}  "
               f"centre ({OX + (min(xs) + max(xs)) / 2:.1f},{OY + (min(ys) + max(ys)) / 2:.1f}); X centre ({XC[0]:.1f},{XC[1]:.1f})")
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
    for name, E, L, spec in (("x1", E1, L1, X1), ("x2", E2, L2, X2)):
        best, where, inside = ring_clearance(E)
        if inside or best < TIP_GAP - 0.5:
            sys.exit(f"{name} touches or lies across the crescent (clearance {best:.1f} u, {inside} points inside) - nothing written")
    files = {"crescent-x-mono.svg": svg_static(INK),
             "crescent-x-mono-light.svg": svg_static(LIGHT),
             "crescent-x-colour.svg": svg_static(INK, fills={"crescent": INK, "x1": TEAL, "x2": TEAL}),
             "crescent-x.svg": svg_animated(), "crescent-x-lockup.svg": svg_lockup(),
             "preview.html": preview_html(), "frames.html": FRAMES}
    os.makedirs(os.path.join(HERE, "frames"), exist_ok=True)
    for t in (0, 6, 12, 18):
        files[f"frames/t{t}.svg"] = svg_animated(begin=f"-{t}s", delay=f"-{t}s")
    for name, txt in files.items():
        with open(os.path.join(HERE, name), "w") as fh:
            fh.write(txt)
    print("wrote " + ", ".join(files))


if __name__ == "__main__":
    main()
