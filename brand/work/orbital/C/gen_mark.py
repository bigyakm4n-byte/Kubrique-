#!/usr/bin/env python3
"""
KUBRIQUE orbital mark - construction C ("flat emblem / knot").

Three orbital rings drawn as solid two-tone shapes (one fill colour + transparent):
  ring-crescent : hoop seen nearly face-on, tilted -> lune between two ellipses
  ring-x1       : hoop seen nearly edge-on -> blunt lens (superellipse), upper-left to lower-right
  ring-x2       : hoop seen nearly edge-on -> blunt lens (superellipse), lower-left to upper-right
The over/under weave is shown knot-diagram style: wherever ring A passes OVER ring B,
ring B is cut by (A dilated by GAP).  Every cut is baked into exact geometry by a small
boolean tracer (elliptical arcs for the ellipses, fitted cubic Beziers for the superellipses),
so each ring is a set of explicit pieces (front / back segments) and the SVG needs no masks.

Weave (alternating link, mirror-symmetric about the X2 axis):
  X1 over crescent at both limbs      -> crescent is cut by X1
  X2 over X1 at the centre            -> X1 is cut by X2
  crescent over X2 at the thick base  -> X2 is cut by crescent

Plain Python, no numpy.  Run:  python3 gen_mark.py   (writes mark.svg + preview.html here)
"""
import math, os, sys

TAU = 2 * math.pi
HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ parameters (viewBox 512)
CX, CY  = 256.0, 256.0   # hub
ROT     = 45.0           # local frame rotation (deg): local -v (crescent opening) -> upper-right
S       = 1.0            # global scale of the local-frame geometry
R_OUT   = 200.0          # crescent outer semi-axis along u
SQUASH  = 0.94           # tilt squash along v (hoop seen slightly off face-on)
R_IN    = 152.0          # inner rim semi-axis along u          (0.76 R)
D_IN    = 66.0           # inner rim shifted toward the opening  (0.33 R)
C_SHIFT = -14.0          # whole crescent nudged toward the opening so X1 meets thicker limbs
X_LEN   = 240.0          # X band semi-length
X_HALF  = 40.0           # X band half-width
X_N     = 3.0            # superellipse exponent of the X bands (2 = ellipse, big = bar)
GAP     = 8.5            # knot cut width (background shows through)
CORE_R  = 10.0           # luminous core dot
CORE_GAP= 7.5            # transparent halo around the dot
V_LIMIT = -60.0          # crescent cut on X2 only applies below this local v (keeps horns clear)
INSET   = 9.0            # detail hairline inset from band edges

FILL      = "#C9A24E"    # brass
DETAIL    = "#6E5119"    # darker brass for the hairlines
DETAIL_W  = 1.5

# ------------------------------------------------------------------ geometry helpers
def rot(x, y, deg):
    r = math.radians(deg); c, s = math.cos(r), math.sin(r)
    return (x * c - y * s, x * s + y * c)

def spow(v, e):
    return math.copysign(abs(v) ** e, v)

class Curve:
    """Closed convex curve: centre, semi-axes a,b, rotation phi (deg, SVG sense), exponent n."""
    def __init__(self, cx, cy, a, b, phi, n=2.0, name=""):
        self.cx, self.cy, self.a, self.b, self.phi, self.n, self.name = cx, cy, a, b, phi, n, name
    @property
    def is_ellipse(self): return abs(self.n - 2.0) < 1e-9
    def pt(self, t):
        e = 2.0 / self.n
        x, y = rot(self.a * spow(math.cos(t), e), self.b * spow(math.sin(t), e), self.phi)
        return (self.cx + x, self.cy + y)
    def local(self, x, y):
        return rot(x - self.cx, y - self.cy, -self.phi)
    def inside(self, x, y):
        xl, yl = self.local(x, y)
        return abs(xl / self.a) ** self.n + abs(yl / self.b) ** self.n < 1.0
    def normal(self, t):
        e = 2.0 / self.n
        xl, yl = self.a * spow(math.cos(t), e), self.b * spow(math.sin(t), e)
        n = self.n
        gx = n * spow(xl / self.a, n - 1) / self.a
        gy = n * spow(yl / self.b, n - 1) / self.b
        nx, ny = rot(gx, gy, self.phi)
        L = math.hypot(nx, ny)
        return (nx / L, ny / L)
    def tangent(self, t, inc=True):
        nx, ny = self.normal(t)
        return (-ny, nx) if inc else (ny, -nx)
    def grown(self, g, name=None):
        return Curve(self.cx, self.cy, self.a + g, self.b + g, self.phi, self.n, name or self.name)

def LE(cu, cv, a, b, phi_local=0.0, n=2.0, name=""):
    """Curve given in the local (u,v) frame -> global."""
    gx, gy = rot(cu * S, cv * S, ROT)
    return Curve(CX + gx, CY + gy, a * S, b * S, phi_local + ROT, n, name)

def to_local(x, y):
    u, v = rot(x - CX, y - CY, -ROT)
    return (u / S, v / S)

# ------------------------------------------------------------------ shapes
Eo = LE(0, C_SHIFT, R_OUT, R_OUT * SQUASH, name="Eo")             # crescent outer rim
Ei = LE(0, C_SHIFT - D_IN, R_IN, R_IN * SQUASH, name="Ei")        # crescent inner rim
E1 = LE(0, 0, X_LEN, X_HALF, n=X_N, name="E1")                    # X1 along local u -> UL..LR
E2 = LE(0, 0, X_HALF, X_LEN, n=X_N, name="E2")                    # X2 along local v -> LL..UR
Kin  = Curve(CX, CY, CORE_R, CORE_R, 0, name="Kin")
Kout = Curve(CX, CY, CORE_R + CORE_GAP, CORE_R + CORE_GAP, 0, name="Kout")

Eo_g, Ei_g = Eo.grown(GAP), Ei.grown(-GAP)        # dilated crescent
E1_g, E2_g = E1.grown(GAP), E2.grown(GAP)         # dilated X bands

def in_crescent(x, y):
    return Eo.inside(x, y) and not Ei.inside(x, y)

def in_crescent_cut(x, y):
    """Dilated crescent, restricted to its lower part (the horns never touch X2)."""
    u, v = to_local(x, y)
    return v > V_LIMIT and Eo_g.inside(x, y) and not Ei_g.inside(x, y)

def in_halo(x, y):
    return Kout.inside(x, y) and not Kin.inside(x, y)

# final regions (True = gold)
F_x1 = lambda x, y: E1.inside(x, y) and not E2_g.inside(x, y)
F_x2 = lambda x, y: E2.inside(x, y) and not in_crescent_cut(x, y) and not in_halo(x, y)
F_c  = lambda x, y: in_crescent(x, y) and not E1_g.inside(x, y)

# ------------------------------------------------------------------ boolean tracer
EPS = 0.08

class Arc:
    """Piece of curve E from parameter ts to te in traversal order; inc = increasing t."""
    def __init__(self, E, ts, te, inc):
        self.E, self.ts, self.te, self.inc = E, ts, te, inc
    def start_pt(self): return self.E.pt(self.ts)
    def end_pt(self):   return self.E.pt(self.te)
    def span(self):
        return ((self.te - self.ts) if self.inc else (self.ts - self.te)) % TAU
    def t_at(self, f):
        return self.ts + (self.span() * f if self.inc else -self.span() * f)

def active_at(E, F, t):
    px, py = E.pt(t); nx, ny = E.normal(t)
    return F(px - EPS * nx, py - EPS * ny) != F(px + EPS * nx, py + EPS * ny)

def refine(E, F, t_off, t_on):
    for _ in range(45):
        tm = 0.5 * (t_off + t_on)
        if active_at(E, F, tm): t_on = tm
        else: t_off = tm
    return 0.5 * (t_off + t_on)

def trace(F, curves, N=4096):
    arcs = []
    for E in curves:
        act, side = [], []
        for i in range(N):
            t = TAU * i / N
            px, py = E.pt(t); nx, ny = E.normal(t)
            fin = F(px - EPS * nx, py - EPS * ny); fout = F(px + EPS * nx, py + EPS * ny)
            act.append(fin != fout); side.append(fin)
        if not any(act):
            continue
        if all(act):
            if side[0]:
                arcs += [Arc(E, 0.0, math.pi, True), Arc(E, math.pi, TAU, True)]
            else:
                arcs += [Arc(E, TAU, math.pi, False), Arc(E, math.pi, 0.0, False)]
            continue
        k = act.index(False)
        i = 0
        while i < N:
            if act[(k + i) % N]:
                j = i
                while j < N and act[(k + j) % N]:
                    j += 1
                if j - i < 2:            # one-sample flicker where another curve grazes this one
                    i = j; continue
                t_a = TAU * (k + i - 1) / N; t_b = TAU * (k + i) / N
                t_c = TAU * (k + j - 1) / N; t_d = TAU * (k + j) / N
                t0 = refine(E, F, t_a, t_b)
                t1 = refine(E, F, t_d, t_c)
                sides = [side[(k + m) % N] for m in range(i, j)]
                inc = sum(sides) * 2 >= len(sides)
                if 0 < sum(sides) < len(sides):
                    print("warning: mixed side inside a run on", E.name, file=sys.stderr)
                arcs.append(Arc(E, t0, t1, True) if inc else Arc(E, t1, t0, False))
                i = j
            else:
                i += 1
    return arcs

def dist(p, q): return math.hypot(p[0] - q[0], p[1] - q[1])

def chain(arcs, tol=0.8):
    loops, used = [], [False] * len(arcs)
    for i, a in enumerate(arcs):
        if used[i]: continue
        used[i] = True
        loop = [a]; start = a.start_pt(); cur = a.end_pt()
        while dist(cur, start) > tol:
            best, bd = None, 1e9
            for j, b in enumerate(arcs):
                if used[j]: continue
                d = dist(b.start_pt(), cur)
                if d < bd: bd, best = d, j
            if best is None or bd > tol:
                raise RuntimeError(f"open loop near {cur} (best gap {bd:.3f})")
            used[best] = True; loop.append(arcs[best]); cur = arcs[best].end_pt()
        loops.append(loop)
    return loops

def loop_samples(loop, n_per=24):
    pts = []
    for a in loop:
        for m in range(n_per):
            pts.append(a.E.pt(a.t_at(m / n_per)))
    return pts

def signed_area(pts):
    s = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]; x1, y1 = pts[(i + 1) % len(pts)]
        s += x0 * y1 - x1 * y0
    return s / 2

def centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

def point_in_poly(p, poly):
    x, y = p; inside = False
    for i in range(len(poly)):
        x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % len(poly)]
        if (y0 > y) != (y1 > y):
            xi = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if xi > x: inside = not inside
    return inside

# ------------------------------------------------------------------ path emission
def fmt(v):
    s = f"{v:.2f}"
    s = s.rstrip('0').rstrip('.') if '.' in s else s
    return "0" if s in ("-0", "") else s

def fit_cubic(E, t0, t1, inc):
    """Least-squares cubic from E.pt(t0) to E.pt(t1) with fixed end tangent directions."""
    P0, P3 = E.pt(t0), E.pt(t1)
    T0 = E.tangent(t0, inc); T1 = E.tangent(t1, not inc)
    M = 16
    ts = [t0 + (t1 - t0) * k / M for k in range(M + 1)]
    pts = [E.pt(t) for t in ts]
    cl = [0.0]
    for k in range(1, len(pts)): cl.append(cl[-1] + dist(pts[k], pts[k - 1]))
    us = [c / cl[-1] for c in cl]
    # B(u) = (1-u)^3 P0 + 3(1-u)^2 u P1 + 3(1-u) u^2 P2 + u^3 P3,  P1 = P0 + al*T0, P2 = P3 + be*T1
    a11 = a12 = a22 = b1 = b2 = 0.0
    for u, P in zip(us, pts):
        w1 = 3 * (1 - u) ** 2 * u; w2 = 3 * (1 - u) * u ** 2
        base = ((1 - u) ** 3 + w1) * P0[0] + (w2 + u ** 3) * P3[0], ((1 - u) ** 3 + w1) * P0[1] + (w2 + u ** 3) * P3[1]
        A1 = (w1 * T0[0], w1 * T0[1]); A2 = (w2 * T1[0], w2 * T1[1])
        r = (P[0] - base[0], P[1] - base[1])
        a11 += A1[0] ** 2 + A1[1] ** 2; a12 += A1[0] * A2[0] + A1[1] * A2[1]; a22 += A2[0] ** 2 + A2[1] ** 2
        b1 += A1[0] * r[0] + A1[1] * r[1]; b2 += A2[0] * r[0] + A2[1] * r[1]
    det = a11 * a22 - a12 * a12
    if abs(det) < 1e-12:
        al = be = dist(P0, P3) / 3
    else:
        al = (b1 * a22 - b2 * a12) / det; be = (a11 * b2 - a12 * b1) / det
    P1 = (P0[0] + al * T0[0], P0[1] + al * T0[1]); P2 = (P3[0] + be * T1[0], P3[1] + be * T1[1])
    # error check
    err = 0.0
    for u, P in zip(us, pts):
        bx = (1 - u) ** 3 * P0[0] + 3 * (1 - u) ** 2 * u * P1[0] + 3 * (1 - u) * u ** 2 * P2[0] + u ** 3 * P3[0]
        by = (1 - u) ** 3 * P0[1] + 3 * (1 - u) ** 2 * u * P1[1] + 3 * (1 - u) * u ** 2 * P2[1] + u ** 3 * P3[1]
        err = max(err, dist((bx, by), P))
    return P1, P2, P3, err

def emit_arc(a):
    """-> list of path command strings continuing from the arc's start point."""
    E = a.E
    sp = a.span()
    if sp < 1e-7: return []
    if E.is_ellipse:
        ex, ey = a.end_pt()
        large = 1 if sp > math.pi else 0
        sweep = 1 if a.inc else 0
        return [f"A{fmt(E.a)} {fmt(E.b)} {fmt(E.phi)} {large} {sweep} {fmt(ex)} {fmt(ey)}"]
    # superellipse: split so that no piece crosses a quadrant boundary (tips) and pieces are small
    cmds = []
    pieces = max(2, int(math.ceil(sp / (math.pi / 10))))
    bounds = [a.t_at(k / pieces) for k in range(pieces + 1)]
    # insert quadrant boundaries (multiples of pi/2) that fall strictly inside
    extra = []
    tmin, tmax = (a.ts, a.ts + sp) if a.inc else (a.ts - sp, a.ts)
    k0 = math.floor(tmin / (math.pi / 2)) - 1
    while k0 * math.pi / 2 <= tmax + 1:
        q = k0 * math.pi / 2
        if tmin + 1e-6 < q < tmax - 1e-6: extra.append(q)
        k0 += 1
    allb = sorted(set(bounds + extra), reverse=not a.inc)
    for t0, t1 in zip(allb[:-1], allb[1:]):
        stack = [(t0, t1)]
        while stack:
            u0, u1 = stack.pop(0)
            P1, P2, P3, err = fit_cubic(E, u0, u1, a.inc)
            if err > 0.04 and abs(u1 - u0) > 1e-3:
                um = 0.5 * (u0 + u1); stack = [(u0, um), (um, u1)] + stack
            else:
                cmds.append(f"C{fmt(P1[0])} {fmt(P1[1])} {fmt(P2[0])} {fmt(P2[1])} {fmt(P3[0])} {fmt(P3[1])}")
    return cmds

def loop_d(loop, close=True):
    sx, sy = loop[0].start_pt()
    d = [f"M{fmt(sx)} {fmt(sy)}"]
    for a in loop:
        d += emit_arc(a)
    if close: d.append("Z")
    return " ".join(d)

def pieces(F, curves):
    """-> list of (outer_loop, [hole_loops], centroid_local)"""
    loops = chain(trace(F, curves))
    info = [(lp, loop_samples(lp)) for lp in loops]
    info = [(lp, pts, signed_area(pts)) for lp, pts in info]
    outers = [x for x in info if x[2] > 0]      # F-inside traversal = clockwise on screen = +area here
    holes  = [x for x in info if x[2] <= 0]
    result = [[lp, [], to_local(*centroid(pts)), pts] for lp, pts, ar in outers]
    for lp, pts, ar in holes:
        c = centroid(pts)
        cands = [r for r in result if point_in_poly(c, r[3])]
        cands.sort(key=lambda r: abs(signed_area(r[3])))
        if not cands: raise RuntimeError("hole without parent")
        cands[0][1].append(lp)
    return [(r[0], r[1], r[2]) for r in result]

# ------------------------------------------------------------------ build pieces
x1_pieces = pieces(F_x1, [E1, E2_g])
x2_pieces = pieces(F_x2, [E2, Eo_g, Ei_g, Kin, Kout])
c_pieces  = pieces(F_c,  [Eo, Ei, E1_g])

def name_x1(c):
    u, v = c
    return ("arm-ul", "FRONT over the crescent's upper limb; ends at the cut where X2 passes over at the hub") if u < 0 \
      else ("arm-lr", "FRONT over the crescent's right limb; ends at the cut where X2 passes over at the hub")
def name_x2(c):
    u, v = c
    if math.hypot(u, v) < CORE_R + 1: return ("core", "luminous core dot (own piece, sits in the halo hole of arm-ur)")
    if v > 120: return ("tail-ll", "BACK: short blunt tip emerging below the crescent's outer rim")
    return ("arm-ur", "FRONT over X1 at the hub; BACK under the crescent (cut along its inner rim); exits between the horns")
def name_c(c):
    u, v = c
    if v < -40 and u < 0: return ("horn-upper", "BACK: horn beyond the X1 cut, tapers to nothing (points up)")
    if v < -40 and u > 0: return ("horn-right", "BACK: horn beyond the X1 cut, tapers to nothing (points right)")
    return ("body", "FRONT over X2 at the thick base; BACK under X1 (cut on both limbs)")

def ring_group(gid, plist, namer, comment):
    out = [f"  <!-- {comment} -->", f"  <g id=\"{gid}\">"]
    for lp, holes, c in sorted(plist, key=lambda p: namer(p[2])[0]):
        nm, note = namer(c)
        d = loop_d(lp) + "".join(" " + loop_d(h) for h in holes)
        out.append(f"    <!-- {nm}: {note} -->")
        out.append(f"    <path id=\"{gid}-{nm}\" d=\"{d}\"/>")
    out.append("  </g>")
    return "\n".join(out)

# ------------------------------------------------------------------ detail hairlines
def detail_arcs(F, own, cut):
    """Outline of the inset region, keeping only arcs on the ring's own rims, as open strokes."""
    arcs = trace(F, own + cut)
    own_names = {e.name for e in own}
    return [loop_d([a], close=False) for a in arcs if a.E.name in own_names and a.span() > 0.02]

Eo_i, Ei_i = Eo.grown(-INSET, "Eo"), Ei.grown(INSET, "Ei")
E1_i, E2_i = E1.grown(-INSET, "E1"), E2.grown(-INSET, "E2")
E1_gg, E2_gg = E1.grown(GAP + INSET), E2.grown(GAP + INSET)
Eo_gg, Ei_gg = Eo.grown(GAP + INSET), Ei.grown(-GAP - INSET)
Kout_g = Kout.grown(INSET)

def in_crescent_cut_i(x, y):
    u, v = to_local(x, y)
    return v > V_LIMIT and Eo_gg.inside(x, y) and not Ei_gg.inside(x, y)

D_x1 = lambda x, y: E1_i.inside(x, y) and not E2_gg.inside(x, y)
D_x2 = lambda x, y: E2_i.inside(x, y) and not in_crescent_cut_i(x, y) and not Kout_g.inside(x, y)
D_c  = lambda x, y: Eo_i.inside(x, y) and not Ei_i.inside(x, y) and not E1_gg.inside(x, y)

det = []
det += detail_arcs(D_x1, [E1_i], [E2_gg])
det += detail_arcs(D_x2, [E2_i], [Eo_gg, Ei_gg, Kout_g])
det += detail_arcs(D_c,  [Eo_i, Ei_i], [E1_gg])

# ------------------------------------------------------------------ bbox report
allpts = []
for pl in (x1_pieces, x2_pieces, c_pieces):
    for lp, holes, c in pl: allpts += loop_samples(lp, 48)
bx0 = min(p[0] for p in allpts); bx1 = max(p[0] for p in allpts)
by0 = min(p[1] for p in allpts); by1 = max(p[1] for p in allpts)

# ------------------------------------------------------------------ SVG
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <title>Kubrique mark - construction C, flat knot emblem</title>
  <desc>Crescent + X built from three interlocking orbital rings, drawn as a strictly two-tone
emblem (one brass fill, transparent cuts). The crescent is a hoop seen nearly face-on and tilted
(lune between two ellipses); the X is two hoops seen nearly edge-on (blunt lenses). Every crossing
is an alternating over/under: X1 over crescent (both limbs), X2 over X1 (hub), crescent over X2
(thick base). The under-ring is cut by the over-ring dilated by {GAP} units, so each ring is a set
of explicit front/back pieces; no masks, no clipPaths, no gradients. Hide #detail below ~64px.
Ink bbox: {fmt(bx0)},{fmt(by0)} to {fmt(bx1)},{fmt(by1)}.</desc>
  <g id="mark" fill="{FILL}" fill-rule="evenodd">
{ring_group("ring-crescent", c_pieces, name_c,
    "ring-crescent: hoop seen nearly face-on, tilted. Outer rim ellipse " + fmt(Eo.a) + "x" + fmt(Eo.b) +
    ", inner rim ellipse " + fmt(Ei.a) + "x" + fmt(Ei.b) + " offset toward the opening. "
    "Split by the X1 cut into body + two horns.")}
{ring_group("ring-x1", x1_pieces, name_x1,
    "ring-x1: hoop seen nearly edge-on, upper-left to lower-right (blunt lens " + fmt(2*E1.a) + "x" + fmt(2*E1.b) +
    ", superellipse n=" + fmt(X_N) + ", rotated 45). Over the crescent at both limbs, under X2 at the hub -> two arm pieces.")}
{ring_group("ring-x2", x2_pieces, name_x2,
    "ring-x2: hoop seen nearly edge-on, lower-left to upper-right (same lens rotated 135). Over X1 at the hub, "
    "under the crescent at the thick base -> arm + tail pieces; the arm carries the transparent halo, the core dot is its own piece.")}
  </g>
  <!-- detail: hairline rims inset {INSET} units from every band edge, stopping short of each cut.
       Decorative only; drop this group for favicon / small sizes. -->
  <g id="detail" fill="none" stroke="{DETAIL}" stroke-width="{DETAIL_W}" stroke-linecap="round" stroke-opacity="0.5">
'''
for d in det:
    svg += f'    <path d="{d}"/>\n'
svg += '''  </g>
</svg>
'''
with open(os.path.join(HERE, "mark.svg"), "w") as f:
    f.write(svg)

# ------------------------------------------------------------------ preview page (1000 x 560)
inline = svg.replace('width="512" height="512"', '')
html = f'''<!doctype html>
<html><head><meta charset="utf-8"><title>C review</title>
<style>
  html,body{{margin:0;background:#555;font:11px/1.3 system-ui,sans-serif;color:#aaa}}
  .row{{display:flex}}
  .tile{{position:relative;width:500px;height:460px;display:flex;align-items:center;justify-content:center}}
  .dark{{background:#0d0e13}} .light{{background:#f5f1e8}}
  .big svg{{width:420px;height:420px;display:block}}
  .small{{height:100px;gap:26px}}
  .small span{{display:block;line-height:0}}
  .s128 svg{{width:128px;height:128px}} .s64 svg{{width:64px;height:64px}} .s40 svg{{width:40px;height:40px}} .s32 svg{{width:32px;height:32px}} .s16 svg{{width:16px;height:16px}}
  .sil #detail{{display:none}}
  .lab{{position:absolute;left:8px;top:6px;font-size:11px;opacity:.6}}
</style></head><body>
<div class="row">
  <div class="tile dark big">{inline}<span class="lab">420px dark</span></div>
  <div class="tile light big">{inline}<span class="lab" style="color:#333">420px light</span></div>
</div>
<div class="row">
  <div class="tile dark small"><span class="lab">silhouette (no #detail): 128 / 64 / 40 / 32 / 16 - then 40 with detail</span>
    <span class="s128 sil">{inline}</span><span class="s64 sil">{inline}</span><span class="s40 sil">{inline}</span><span class="s32 sil">{inline}</span><span class="s16 sil">{inline}</span>
    <span class="s40">{inline}</span>
  </div>
  <div class="tile light small">
    <span class="s128 sil">{inline}</span><span class="s64 sil">{inline}</span><span class="s40 sil">{inline}</span><span class="s32 sil">{inline}</span><span class="s16 sil">{inline}</span>
    <span class="s40">{inline}</span>
  </div>
</div>
</body></html>
'''
with open(os.path.join(HERE, "preview.html"), "w") as f:
    f.write(html)

print("pieces: x1", len(x1_pieces), "x2", len(x2_pieces), "crescent", len(c_pieces), "| detail arcs", len(det))
for nm, pl, namer in (("x1", x1_pieces, name_x1), ("x2", x2_pieces, name_x2), ("c", c_pieces, name_c)):
    for lp, holes, c in pl:
        print(f"  {nm}:{namer(c)[0]:12s} arcs={len(lp)} holes={len(holes)} local-centroid=({c[0]:.0f},{c[1]:.0f})")
print(f"ink bbox x {bx0:.1f}..{bx1:.1f}  y {by0:.1f}..{by1:.1f}   (w {bx1-bx0:.0f}, h {by1-by0:.0f}, centre {(bx0+bx1)/2:.1f},{(by0+by1)/2:.1f})")
print("svg bytes", len(svg))
