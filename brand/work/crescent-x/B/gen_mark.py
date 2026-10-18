#!/usr/bin/env python3
"""
CRESCENT X mark for KUBRIQUE - construction B (parametric, plain Python).

Three shapes, all built from circles, ellipses and offset/elliptical arcs:

  ring-crescent  outer circle (C_cx, C_cy, C_R) minus an inner circle of radius C_r
                 whose centre is offset by C_d in direction C_psi.  Classic crescent:
                 the horns are the two intersection points of the circles.
  ring-x1        (descending)  outer ellipse E1 (a, b, tilt th) minus a LENS.
  ring-x2        (ascending)   same construction, tilt negative.

The lens of each ring is bounded by two half-ellipse arcs that share the lens tips
(-a2, 0) and (+a2, 0) on the ring axis: v = h1*s(u) and v = h2*s(u) with
s(u) = sqrt(1 - u^2/a2^2) and h1 < h2 (signed heights along the ring normal).
Because the arcs are coaxial with E1 and a2 < a, the lens is always inside E1, the
band is thick on one long edge (width b - h2 at the centre) and thin on the other
(width b + h1), and both tips of the ring stay sharp.  A small twist (tau) rotates
the lens about the ring centre; a shift (s) slides it along the axis.

Weave:  the over/under TABLE below lists (over, under) pairs.  Every edge of the
OVER shape cuts a transparent channel of width GAP through the UNDER shape (an SVG
mask: the over shape, dilated by a round stroke).  Crossings between the sampled
outlines are found numerically and listed in the SVG comment, and the script
refuses to write if a crossing has no table entry, so the knot is consistent.

Parameters are given in the pixel space of the approved reference bitmap
(1170 x 1191 px) so they can be measured straight off it; the mark is then scaled
and centred into the 512 x 512 viewBox.

Run:  python3 gen_mark.py [key=value ...]        (any parameter below can be overridden)
Writes mark.svg (#111111), mark-light.svg (#F3E7C3), mark-overlay.svg (red review aid),
preview.html (reference / mark / overlay / sizes) and params.json next to itself.
Review render:
  /opt/pw-browsers/chromium --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
      --window-size=1200,1000 --screenshot=review.png file://$PWD/preview.html
"""
import math, os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
REF_IMG = "/tmp/claude-0/-home-user-Kubrique-/1089e9da-6911-5cb8-8308-49f4fb2445d5/scratchpad/orbital/target-crop.png"
REF_W, REF_H = 1170, 1191

# ------------------------------------------------------------------ parameters
P = dict(
    # crescent ---------------------------------------------------------------
    C_cx=616.3, C_cy=528.5, C_R=365.9,  # outer circle (fitted to the reference's outer edge, sd 2.3 px)
    C_d=35.0, C_psi=182.5,              # inner-circle centre offset: distance, direction (deg, y-down)
    C_tip=49.15,                        # half-angle (deg) from the offset direction to each horn, seen from the outer centre
    C_r=0.0,                            # inner radius; 0 = derive it from C_tip (keeps the horns where the reference has them)
    # ring x1 (descending, upper-left -> lower-right) --------------------------
    x1_cx=548.3, x1_cy=536.9, x1_a=372.0, x1_b=86.0, x1_th=27.31,
    x1_a2=345.0, x1_wneg=5.5, x1_wpos=85.0, x1_tau=0.94, x1_s=15.0,
    # ring x2 (ascending, lower-left -> upper-right) ---------------------------
    x2_cx=560.3, x2_cy=550.5, x2_a=377.0, x2_b=94.0, x2_th=-30.0,
    x2_a2=324.5, x2_wneg=43.25, x2_wpos=30.5, x2_tau=-2.25, x2_s=-9.0,
    # weave / layout -----------------------------------------------------------
    gap=5.0,          # weave channel width, reference px
    box=512.0, margin=40.0,
)
# wneg / wpos: band width at the ring centre on the -normal / +normal side.
# normal n = (-sin th, cos th): for x1 (th>0) +n points down-left, for x2 (th<0) +n points down-right.

# (over, under) - every edge of OVER cuts a channel through UNDER
TABLE = [("x1", "x2"), ("x2", "crescent"), ("x1", "crescent")]

INK = "#111111"
LIGHT = "#F3E7C3"

for arg in sys.argv[1:]:
    k, v = arg.split("=", 1)
    if k not in P:
        sys.exit(f"unknown parameter {k}")
    P[k] = float(v)


# ------------------------------------------------------------------ helpers
def f(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def rot(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def seg_intersect(p1, p2, p3, p4):
    d = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0])
    if abs(d) < 1e-12:
        return None
    t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / d
    u = ((p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])) / d
    if 0 <= t <= 1 and 0 <= u <= 1:
        return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))
    return None


def poly_intersections(A, B):
    out = []
    # bounding boxes to skip far segments
    for i in range(len(A) - 1):
        a0, a1 = A[i], A[i + 1]
        ax0, ax1 = min(a0[0], a1[0]), max(a0[0], a1[0])
        ay0, ay1 = min(a0[1], a1[1]), max(a0[1], a1[1])
        for j in range(len(B) - 1):
            b0, b1 = B[j], B[j + 1]
            if max(b0[0], b1[0]) < ax0 or min(b0[0], b1[0]) > ax1:
                continue
            if max(b0[1], b1[1]) < ay0 or min(b0[1], b1[1]) > ay1:
                continue
            p = seg_intersect(a0, a1, b0, b1)
            if p:
                out.append(p)
    return out


# ------------------------------------------------------------------ geometry (reference space)
class Ring:
    """Elliptical band: outer ellipse minus a coaxial two-arc lens."""

    def __init__(self, k):
        g = lambda n: P[f"{k}_{n}"]
        self.k = k
        self.cx, self.cy, self.a, self.b, self.th = g("cx"), g("cy"), g("a"), g("b"), g("th")
        self.a2, self.tau, self.s = g("a2"), g("tau"), g("s")
        self.h1 = -self.b + g("wneg")      # lens boundary on the -n side
        self.h2 = self.b - g("wpos")       # lens boundary on the +n side
        assert self.h1 < self.h2, f"{k}: lens has no height (wneg + wpos >= 2b)"
        assert self.a2 < self.a, f"{k}: lens longer than the ring"
        self.u = (math.cos(math.radians(self.th)), math.sin(math.radians(self.th)))
        self.n = (-self.u[1], self.u[0])

    def T(self, x, y):                     # ring-local (u, v) -> global
        return (self.cx + x * self.u[0] + y * self.n[0], self.cy + x * self.u[1] + y * self.n[1])

    def TL(self, x, y):                    # lens-local -> global (twist + shift)
        x, y = rot(x, y, self.tau)
        return self.T(x + self.s, y)

    def outer_pts(self, N=720):
        return [self.T(self.a * math.cos(2 * math.pi * i / N), self.b * math.sin(2 * math.pi * i / N)) for i in range(N + 1)]

    def lens_pts(self, N=720):
        pts = []
        for i in range(N // 2 + 1):           # upper curve (h2) from -a2 to +a2
            ph = math.pi * i / (N // 2)
            pts.append(self.TL(-self.a2 * math.cos(ph), self.h2 * math.sin(ph)))
        for i in range(N // 2 + 1):           # lower curve (h1) back
            ph = math.pi * i / (N // 2)
            pts.append(self.TL(self.a2 * math.cos(ph), self.h1 * math.sin(ph)))
        return pts

    def inside_outer(self, p):
        dx, dy = p[0] - self.cx, p[1] - self.cy
        x = dx * self.u[0] + dy * self.u[1]
        y = dx * self.n[0] + dy * self.n[1]
        return (x / self.a) ** 2 + (y / self.b) ** 2 <= 1

    def inside_lens(self, p):
        dx, dy = p[0] - self.cx, p[1] - self.cy
        x = dx * self.u[0] + dy * self.u[1] - self.s
        y = dx * self.n[0] + dy * self.n[1]
        x, y = rot(x, y, -self.tau)
        if abs(x) >= self.a2:
            return False
        s = math.sqrt(1 - (x / self.a2) ** 2)
        return self.h1 * s < y < self.h2 * s

    def inside(self, p):
        return self.inside_outer(p) and not self.inside_lens(p)

    def vertices(self):
        return self.T(-self.a, 0), self.T(self.a, 0)

    def lens_margin(self):
        """smallest distance from the lens outline to the outer ellipse (sampled)"""
        best = 1e9
        for p in self.lens_pts(360):
            dx, dy = p[0] - self.cx, p[1] - self.cy
            x = dx * self.u[0] + dy * self.u[1]
            y = dx * self.n[0] + dy * self.n[1]
            # radial scale to the ellipse along the direction of (x,y)
            r = math.hypot(x, y)
            if r < 1e-9:
                continue
            re = 1 / math.sqrt((x / r / self.a) ** 2 + (y / r / self.b) ** 2)
            best = min(best, re - r)
        return best

    def path(self, S):
        """SVG path (global coords, scaled by S): outer ellipse + lens, for evenodd fill"""
        a, b, th = self.a, self.b, self.th
        T = lambda x, y: S(self.T(x, y))
        d = [f"M{T(-a, 0)}"]
        for x, y in ((0, -b), (a, 0), (0, b), (-a, 0)):
            d.append(f"A{f(a*S.s)} {f(b*S.s)} {f(th)} 0 1 {T(x, y)}")
        d.append("Z")
        a2, h1, h2, rtn = self.a2, self.h1, self.h2, self.th + self.tau
        L = lambda x, y: S(self.TL(x, y))
        d.append(f"M{L(-a2, 0)}")
        for h, pts in ((h2, ((0, h2), (a2, 0))), (h1, ((0, h1), (-a2, 0)))):
            if abs(h) < 0.05:
                for x, y in pts:
                    d.append(f"L{L(x, y)}")
                continue
            # upper curve (-a2 -> +a2): h>0 goes via +v = counter-clockwise on screen = sweep 0
            # lower curve (+a2 -> -a2): h>0 goes via +v = clockwise on screen        = sweep 1
            sweep = (0 if h > 0 else 1) if h is h2 else (1 if h > 0 else 0)
            for x, y in pts:
                d.append(f"A{f(a2*S.s)} {f(abs(h)*S.s)} {f(rtn)} 0 {sweep} {L(x, y)}")
        d.append("Z")
        return " ".join(d)


class Crescent:
    def __init__(self):
        self.cx, self.cy, self.R = P["C_cx"], P["C_cy"], P["C_R"]
        self.d, self.psi = P["C_d"], P["C_psi"]
        if P["C_r"] > 0:
            self.r = P["C_r"]
        else:   # horn at angle C_tip from the offset direction, seen from the outer centre
            t = math.radians(P["C_tip"])
            self.r = math.sqrt(self.R ** 2 + self.d ** 2 - 2 * self.R * self.d * math.cos(t))
        self.icx = self.cx + self.d * math.cos(math.radians(self.psi))
        self.icy = self.cy + self.d * math.sin(math.radians(self.psi))
        # horns: intersection of the circles
        D = self.d
        assert abs(self.R - self.r) < D < self.R + self.r, "circles do not intersect: no horns"
        x = (D * D + self.R ** 2 - self.r ** 2) / (2 * D)          # along the offset direction
        y = math.sqrt(self.R ** 2 - x * x)
        ux, uy = math.cos(math.radians(self.psi)), math.sin(math.radians(self.psi))
        h = [(self.cx + x * ux - y * uy, self.cy + x * uy + y * ux), (self.cx + x * ux + y * uy, self.cy + x * uy - y * ux)]
        h.sort(key=lambda p: p[1])
        self.top, self.bot = h[0], h[1]
        self.tip_angle = math.degrees(math.atan2(y, x))     # half-angle at the outer centre

    def ang_o(self, p):
        return math.atan2(p[1] - self.cy, p[0] - self.cx)

    def ang_i(self, p):
        return math.atan2(p[1] - self.icy, p[0] - self.icx)

    def outer_pts(self, N=720):
        """outer arc from the top horn, through the thick side, to the bottom horn"""
        a0, a1 = self.ang_o(self.top), self.ang_o(self.bot)
        thick = math.radians(self.psi + 180)
        # go from a0 to a1 in the direction that passes through `thick`
        span = (a1 - a0) % (2 * math.pi)
        if (thick - a0) % (2 * math.pi) > span:
            span -= 2 * math.pi
        return [(self.cx + self.R * math.cos(a0 + span * i / N), self.cy + self.R * math.sin(a0 + span * i / N)) for i in range(N + 1)]

    def inner_pts(self, N=720):
        a0, a1 = self.ang_i(self.bot), self.ang_i(self.top)
        thick = math.radians(self.psi + 180)
        span = (a1 - a0) % (2 * math.pi)
        if (thick - a0) % (2 * math.pi) > span:
            span -= 2 * math.pi
        return [(self.icx + self.r * math.cos(a0 + span * i / N), self.icy + self.r * math.sin(a0 + span * i / N)) for i in range(N + 1)]

    def inside(self, p):
        return math.hypot(p[0] - self.cx, p[1] - self.cy) <= self.R and math.hypot(p[0] - self.icx, p[1] - self.icy) > self.r

    def band_depth(self, p):
        """how far p lies inside the band, measured from the inner edge (+ = inside the band)"""
        return math.hypot(p[0] - self.icx, p[1] - self.icy) - self.r

    def width_at(self, deg):
        t = math.radians(deg - self.psi)
        disc = self.r ** 2 - self.d ** 2 * math.sin(t) ** 2
        if disc < 0:
            return 0.0
        return max(0.0, self.R - (self.d * math.cos(t) + math.sqrt(disc)))

    def path(self, S):
        o = self.outer_pts(8)
        i = self.inner_pts(8)
        # flags from the sampled arcs: sweep 1 = angle increasing (clockwise on screen)
        def flags(pts, c):
            a0 = math.atan2(pts[0][1] - c[1], pts[0][0] - c[0])
            a1 = math.atan2(pts[1][1] - c[1], pts[1][0] - c[0])
            step = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
            total = abs(step) * 8
            return (1 if total > math.pi else 0), (1 if step > 0 else 0)
        lo, so = flags(o, (self.cx, self.cy))
        li, si = flags(i, (self.icx, self.icy))
        return (f"M{S(self.top)} A{f(self.R*S.s)} {f(self.R*S.s)} 0 {lo} {so} {S(self.bot)} "
                f"A{f(self.r*S.s)} {f(self.r*S.s)} 0 {li} {si} {S(self.top)} Z")


class Scale:
    def __init__(self, s, tx, ty):
        self.s, self.tx, self.ty = s, tx, ty

    def __call__(self, p):
        return f"{f(p[0]*self.s + self.tx)} {f(p[1]*self.s + self.ty)}"

    def pt(self, p):
        return (p[0] * self.s + self.tx, p[1] * self.s + self.ty)


# ------------------------------------------------------------------ build
def build():
    cres = Crescent()
    x1, x2 = Ring("x1"), Ring("x2")
    shapes = {"crescent": cres, "x1": x1, "x2": x2}
    outlines = {
        "crescent": [("outer", cres.outer_pts()), ("inner", cres.inner_pts())],
        "x1": [("outer", x1.outer_pts()), ("lens", x1.lens_pts())],
        "x2": [("outer", x2.outer_pts()), ("lens", x2.lens_pts())],
    }
    # bbox + scale into the box
    xs = [p[0] for k in outlines for _, pl in outlines[k] for p in pl]
    ys = [p[1] for k in outlines for _, pl in outlines[k] for p in pl]
    bb = (min(xs), min(ys), max(xs), max(ys))
    size = max(bb[2] - bb[0], bb[3] - bb[1])
    s = (P["box"] - 2 * P["margin"]) / size
    S = Scale(s, P["box"] / 2 - s * (bb[0] + bb[2]) / 2, P["box"] / 2 - s * (bb[1] + bb[3]) / 2)

    # crossings between outlines of different shapes, clustered
    raw = []
    keys = list(outlines)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            for na, A in outlines[keys[i]]:
                for nb, B in outlines[keys[j]]:
                    for p in poly_intersections(A, B):
                        raw.append((keys[i], keys[j], na, nb, p))
    clusters = []
    for ka, kb, na, nb, p in raw:
        for c in clusters:
            if c["pair"] == (ka, kb) and math.hypot(c["p"][0] - p[0], c["p"][1] - p[1]) < 45:
                c["n"] += 1
                c["edges"].add(f"{ka}.{na}x{kb}.{nb}")
                break
        else:
            clusters.append({"pair": (ka, kb), "p": p, "n": 1, "edges": {f"{ka}.{na}x{kb}.{nb}"}})
    over_of = {}
    for o, u in TABLE:
        over_of.setdefault(frozenset((o, u)), []).append((o, u))
    report = []
    bad = False
    for c in clusters:
        ent = over_of.get(frozenset(c["pair"]), [])
        if len(ent) != 1:
            bad = True
            who = "NO TABLE ENTRY" if not ent else "AMBIGUOUS"
        else:
            who = f"{ent[0][0]} over {ent[0][1]}"
        q = S.pt(c["p"])
        report.append(f"{c['pair'][0]} x {c['pair'][1]} at ({q[0]:.1f},{q[1]:.1f}) [{c['n']} edge hits: {', '.join(sorted(c['edges']))}] -> {who}")
    return cres, x1, x2, shapes, outlines, bb, S, report, bad


def svg(ink, S, cres, x1, x2, report, note="", extra=""):
    g = P["gap"] * S.s
    d = {"crescent": cres.path(S), "x1": x1.path(S), "x2": x2.path(S)}
    unders = {}
    for o, u in TABLE:
        unders.setdefault(u, []).append(o)
    masks = []
    for u, overs in unders.items():
        uses = "\n      ".join(
            f'<use href="#shape-{o}" xlink:href="#shape-{o}" fill="#000" fill-rule="evenodd" stroke="#000" stroke-width="{f(2*g)}" stroke-linejoin="round"/>'
            for o in overs)
        masks.append(f'''    <mask id="cut-{u}" maskUnits="userSpaceOnUse" x="0" y="0" width="{f(P['box'])}" height="{f(P['box'])}">
      <rect width="{f(P['box'])}" height="{f(P['box'])}" fill="#fff"/>
      {uses}
    </mask>''')
    order = ["crescent", "x2", "x1"]     # bottom to top: every UNDER is drawn before its OVER
    body = []
    for k in order:
        m = f' mask="url(#cut-{k})"' if k in unders else ""
        body.append(f'    <use id="ring-{k}" href="#shape-{k}" xlink:href="#shape-{k}"{m}/>')
    tbl = "; ".join(f"{o} over {u}" for o, u in TABLE)
    rep = "\n    ".join(report)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {f(P['box'])} {f(P['box'])}" width="{f(P['box'])}" height="{f(P['box'])}" role="img" aria-label="Kubrique CRESCENT X mark">
  <title>KUBRIQUE - CRESCENT X mark (construction B)</title>
  <!--
    A crescent (outer circle minus an offset inner circle) and two orbital rings
    (ellipse minus a coaxial two-arc lens) woven into an X.
    Weave table: {tbl}.
    Crossings found between the sampled outlines (viewBox coordinates):
    {rep}
    Weave channels are transparent (masks: the OVER shape dilated by a {f(2*g)}px round stroke),
    so the whole mark recolours by changing the one fill on #mark.{note}
    Generated by gen_mark.py - edit the parameters there, not this file.
  -->
  <defs>
    <path id="shape-crescent" d="{d['crescent']}"/>
    <path id="shape-x1" d="{d['x1']}"/>
    <path id="shape-x2" d="{d['x2']}"/>
{chr(10).join(masks)}
  </defs>
  <g id="mark" fill="{ink}" fill-rule="evenodd"{extra}>
{chr(10).join(body)}
  </g>
</svg>
'''


PREVIEW = '''<!doctype html>
<html><head><meta charset="utf-8"><title>CRESCENT X - construction B review</title>
<style>
  html,body{{margin:0;padding:0;background:#fff}}
  body{{width:1200px;height:1000px;font:12px/1.3 system-ui,sans-serif;color:#555;position:relative;overflow:hidden}}
  .lbl{{position:absolute;font-size:11px;letter-spacing:.08em;text-transform:uppercase}}
  .ov{{position:absolute;left:840px;top:20px;width:340px;height:346px;overflow:hidden;background:#fff}}
  .ov img{{position:absolute}}
  .dark{{position:absolute;left:0;top:450px;width:1200px;height:550px;background:#0d0e13;color:#8a8f9a}}
  .sm{{position:absolute;display:flex;gap:26px;align-items:flex-end}}
  .sm div{{display:flex;flex-direction:column;align-items:center;gap:6px}}
  img{{display:block}}
</style></head><body>
<img src="file://{ref}" style="position:absolute;left:10px;top:12px;width:420px;height:428px">
<div class="lbl" style="left:14px;top:0">reference</div>
<img src="mark.svg" style="position:absolute;left:430px;top:16px;width:420px;height:420px">
<div class="lbl" style="left:434px;top:0">mark.svg 420px</div>
<div class="ov"><img src="file://{ref}" style="left:{ox}px;top:{oy}px;width:{ow}px;height:{oh}px"><img src="mark-overlay.svg" style="left:{sx}px;top:{sy}px;width:{sw}px;height:{sw}px;opacity:.62"></div>
<div class="lbl" style="left:844px;top:0">overlay (red = mine)</div>
<div class="sm" style="left:850px;top:382px">
  <div><img src="mark.svg" width="64" height="64"><span>64</span></div>
  <div><img src="mark.svg" width="40" height="40"><span>40</span></div>
  <div><img src="mark.svg" width="24" height="24"><span>24</span></div>
  <div><img src="mark.svg" width="16" height="16"><span>16</span></div>
</div>
<div class="dark">
  <img src="mark-light.svg" style="position:absolute;left:40px;top:60px;width:420px;height:420px">
  <div class="lbl" style="left:44px;top:40px">mark-light.svg 420px on #0d0e13</div>
  <div class="sm" style="left:520px;top:200px">
    <div><img src="mark-light.svg" width="120" height="120"><span>120</span></div>
    <div><img src="mark-light.svg" width="64" height="64"><span>64</span></div>
    <div><img src="mark-light.svg" width="40" height="40"><span>40</span></div>
    <div><img src="mark-light.svg" width="24" height="24"><span>24</span></div>
    <div><img src="mark-light.svg" width="16" height="16"><span>16</span></div>
  </div>
  <div style="position:absolute;left:520px;top:380px;width:640px;white-space:pre-wrap;font-size:11px">{notes}</div>
</div>
</body></html>
'''


def main():
    cres, x1, x2, shapes, outlines, bb, S, report, bad = build()
    # --- diagnostics
    lines = []
    lines.append(f"crescent: R={cres.R:.1f} r={cres.r:.1f} d={cres.d:.1f} psi={cres.psi:.2f}  horns top=({cres.top[0]:.0f},{cres.top[1]:.0f}) bottom=({cres.bot[0]:.0f},{cres.bot[1]:.0f})  tip half-angle={cres.tip_angle:.1f}")
    lines.append("crescent width by angle: " + " ".join(f"{a}:{cres.width_at(a):.0f}" for a in range(-120, 140, 20)))
    for r in (x1, x2):
        v0, v1 = r.vertices()
        lines.append(f"{r.k}: centre=({r.cx:.0f},{r.cy:.0f}) a={r.a:.0f} b={r.b:.0f} th={r.th:.1f} lens a2={r.a2:.0f} h1={r.h1:.0f} h2={r.h2:.0f} "
                     f"band widths at centre {r.b + r.h1:.0f}(-n) / {r.b - r.h2:.0f}(+n); lens margin to outer ellipse {r.lens_margin():.1f}")
        for name, v in (("tip A", v0), ("tip B", v1)):
            where = ("in crescent band, %.1f px past the inner edge" % cres.band_depth(v)) if cres.inside(v) else (
                "inside the opening, %.1f px short of the band" % -cres.band_depth(v) if math.hypot(v[0]-cres.cx, v[1]-cres.cy) < cres.R else "outside the outer circle")
            lines.append(f"   {name} at ({v[0]:.0f},{v[1]:.0f}): {where}")
    for name, h in (("top horn", cres.top), ("bottom horn", cres.bot)):
        hit = [r.k for r in (x1, x2) if r.inside(h)]
        dmin = min(math.hypot(h[0]-p[0], h[1]-p[1]) for r in (x1, x2) for _, pl in outlines[r.k] for p in pl)
        lines.append(f"crescent {name} at ({h[0]:.0f},{h[1]:.0f}): {'inside ' + ','.join(hit) if hit else 'free'}; nearest ring edge {dmin:.1f} px")
    lines.append(f"bbox (ref px) = {tuple(round(v,1) for v in bb)}  size {bb[2]-bb[0]:.0f} x {bb[3]-bb[1]:.0f}; scale {S.s:.4f}; gap {P['gap']*S.s:.2f} viewBox px")
    lines.append("crossings:")
    lines.extend("   " + r for r in report)
    txt = "\n".join(lines)
    print(txt)
    if bad:
        sys.exit("weave table does not cover every crossing - fix TABLE")
    # --- files
    with open(os.path.join(HERE, "mark.svg"), "w") as fh:
        fh.write(svg(INK, S, cres, x1, x2, report))
    with open(os.path.join(HERE, "mark-light.svg"), "w") as fh:
        fh.write(svg(LIGHT, S, cres, x1, x2, report, note="\n    Light variant for dark backgrounds."))
    with open(os.path.join(HERE, "mark-overlay.svg"), "w") as fh:
        fh.write(svg("#e53935", S, cres, x1, x2, report, note="\n    Review aid: red overlay."))
    # overlay geometry: reference shown at k px per ref px inside a 340px panel, centred on the mark bbox
    k = 340.0 / 780.0
    bcx, bcy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    ox, oy = 170 - bcx * k, 173 - bcy * k
    sw = P["box"] * k / S.s
    sx, sy = 170 - P["box"] / 2 * k / S.s, 173 - P["box"] / 2 * k / S.s
    with open(os.path.join(HERE, "preview.html"), "w") as fh:
        fh.write(PREVIEW.format(ref=REF_IMG, ox=f(ox), oy=f(oy), ow=f(REF_W * k), oh=f(REF_H * k), sx=f(sx), sy=f(sy), sw=f(sw),
                                notes=txt.replace("<", "&lt;")))
    with open(os.path.join(HERE, "params.json"), "w") as fh:
        json.dump(P, fh, indent=1)


if __name__ == "__main__":
    main()
