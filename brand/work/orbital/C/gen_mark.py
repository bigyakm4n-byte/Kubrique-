#!/usr/bin/env python3
"""
KUBRIQUE orbital mark - construction C ("flat emblem / knot").

Three orbital rings drawn as solid two-tone shapes (one fill colour + transparent):
  ring-crescent : hoop seen nearly face-on, tilted -> lune between two ellipses
  ring-x1       : hoop seen nearly edge-on -> thin ellipse, upper-left to lower-right
  ring-x2       : hoop seen nearly edge-on -> thin ellipse, lower-left to upper-right
The over/under weave is shown knot-diagram style: wherever ring A passes OVER ring B,
ring B is cut by (A dilated by GAP).  Every cut is baked into exact elliptical-arc
geometry by a tiny boolean tracer below, so each ring is a set of explicit pieces
(front / back segments) and the SVG needs no masks or clipPaths.

Weave (alternating link, mirror-symmetric about the X2 axis):
  X1 over crescent at both limbs      -> crescent is cut by X1
  X2 over X1 at the centre            -> X1 is cut by X2
  crescent over X2 at the thick base  -> X2 is cut by crescent

Plain Python, no numpy.  Run:  python3 gen_mark.py
Writes mark.svg and preview.html next to this file.
"""
import math, os, sys

TAU = 2 * math.pi
HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ parameters
CX, CY  = 256.0, 256.0   # viewBox centre
ROT     = 45.0           # local frame rotation (deg). local -v (opening) -> upper-right
S       = 1.0            # global scale of the local-frame geometry
R_OUT   = 200.0          # crescent outer semi-axis along u
SQUASH  = 0.93           # tilt squash along v (hoop seen slightly off face-on)
R_IN    = 160.0          # inner ellipse semi-axis along u
D_IN    = 55.0           # inner ellipse shifted toward the opening (-v)
C_SHIFT = -15.0          # whole crescent shifted toward the opening so X1 meets thicker limbs
X_LEN   = 240.0          # X band semi-length
X_HALF  = 36.0           # X band half-width
GAP     = 7.5            # knot cut width (background shows through)
CORE_R  = 10.0           # luminous core dot
CORE_GAP= 7.0            # transparent halo around the dot
V_LIMIT = -60.0          # crescent cut on X2 only applies below this local v (keeps horns clear)
INSET   = 9.0            # detail hairline inset from band edges

FILL      = "#C9A24E"    # brass
DETAIL    = "#6E5119"    # darker brass for the hairlines
DETAIL_W  = 1.6

# ------------------------------------------------------------------ geometry helpers
def rot(x, y, deg):
    r = math.radians(deg); c, s = math.cos(r), math.sin(r)
    return (x * c - y * s, x * s + y * c)

class Ell:
    """Ellipse: centre, semi-axes a (along rotated x) and b, rotation phi (deg, SVG sense)."""
    def __init__(self, cx, cy, a, b, phi, name=""):
        self.cx, self.cy, self.a, self.b, self.phi, self.name = cx, cy, a, b, phi, name
    def pt(self, t):
        x, y = rot(self.a * math.cos(t), self.b * math.sin(t), self.phi)
        return (self.cx + x, self.cy + y)
    def local(self, x, y):
        return rot(x - self.cx, y - self.cy, -self.phi)
    def inside(self, x, y):
        xl, yl = self.local(x, y)
        return (xl / self.a) ** 2 + (yl / self.b) ** 2 < 1.0
    def normal(self, t):
        xl, yl = self.a * math.cos(t), self.b * math.sin(t)
        nx, ny = rot(xl / self.a ** 2, yl / self.b ** 2, self.phi)
        L = math.hypot(nx, ny)
        return (nx / L, ny / L)
    def grown(self, g, name=None):
        return Ell(self.cx, self.cy, self.a + g, self.b + g, self.phi, name or self.name)

def LE(cu, cv, a, b, phi_local=0.0, name=""):
    """Ellipse given in the local (u,v) frame -> global."""
    gx, gy = rot(cu * S, cv * S, ROT)
    return Ell(CX + gx, CY + gy, a * S, b * S, phi_local + ROT, name)

def to_local(x, y):
    u, v = rot(x - CX, y - CY, -ROT)
    return (u / S, v / S)

# ------------------------------------------------------------------ shapes
Eo = LE(0, C_SHIFT, R_OUT, R_OUT * SQUASH, name="Eo")             # crescent outer rim
Ei = LE(0, C_SHIFT - D_IN, R_IN, R_IN * SQUASH, name="Ei")        # crescent inner rim
E1 = LE(0, 0, X_LEN, X_HALF, name="E1")                           # X1 (local u axis)
E2 = LE(0, 0, X_HALF, X_LEN, name="E2")                           # X2 (local v axis)
Kin  = Ell(CX, CY, CORE_R, CORE_R, 0, "Kin")
Kout = Ell(CX, CY, CORE_R + CORE_GAP, CORE_R + CORE_GAP, 0, "Kout")

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

# final regions  (True = gold)
F_x1 = lambda x, y: E1.inside(x, y) and not E2_g.inside(x, y)
F_x2 = lambda x, y: E2.inside(x, y) and not in_crescent_cut(x, y) and not in_halo(x, y)
F_c  = lambda x, y: in_crescent(x, y) and not E1_g.inside(x, y)

# ------------------------------------------------------------------ boolean tracer
EPS = 0.08

class Arc:
    """Piece of ellipse E from parameter ts to te in traversal order; inc = increasing t."""
    def __init__(self, E, ts, te, inc):
        self.E, self.ts, self.te, self.inc = E, ts, te, inc
    def start_pt(self): return self.E.pt(self.ts)
    def end_pt(self):   return self.E.pt(self.te)
    def span(self):
        return ((self.te - self.ts) if self.inc else (self.ts - self.te)) % TAU
    def mid_t(self):
        return self.ts + (self.span() / 2 if self.inc else -self.span() / 2)

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
            inc = side[0]
            if inc:
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
                # run occupies indices i..j-1 (relative to k)
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
        sp = a.span()
        for m in range(n_per):
            f = m / n_per
            t = a.ts + (sp * f if a.inc else -sp * f)
            pts.append(a.E.pt(t))
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

def fmt(v):
    s = f"{v:.2f}"
    s = s.rstrip('0').rstrip('.') if '.' in s else s
    return "0" if s in ("-0", "") else s

def loop_d(loop, close=True):
    sx, sy = loop[0].start_pt()
    d = [f"M{fmt(sx)} {fmt(sy)}"]
    for a in loop:
        sp = a.span()
        if sp < 1e-7: continue
        ex, ey = a.end_pt()
        large = 1 if sp > math.pi else 0
        sweep = 1 if a.inc else 0
        d.append(f"A{fmt(a.E.a)} {fmt(a.E.b)} {fmt(a.E.phi)} {large} {sweep} {fmt(ex)} {fmt(ey)}")
    if close: d.append("Z")
    return " ".join(d)

def pieces(F, curves):
    """-> list of (outer_loop, [hole_loops], centroid_local)"""
    loops = chain(trace(F, curves))
    info = []
    for lp in loops:
        pts = loop_samples(lp)
        info.append((lp, pts, signed_area(pts)))
    # In SVG coords (y down) an "F inside" traversal (increasing t) is clockwise on screen,
    # which gives positive signed area with this formula; holes come out negative.
    outers = [x for x in info if x[2] > 0]
    holes  = [x for x in info if x[2] <= 0]
    result = []
    for lp, pts, ar in outers:
        result.append([lp, [], to_local(*centroid(pts)), pts])
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
    return ("arm-ul", "FRONT over crescent (upper-left limb); ends at the cut where X2 passes over") if u < 0 \
      else ("arm-lr", "FRONT over crescent (lower-right limb); ends at the cut where X2 passes over")
def name_x2(c):
    u, v = c
    r = math.hypot(u, v)
    if r < CORE_R + 1: return ("core", "luminous core dot, sits on the X2 band at the hub")
    if v > 120:        return ("tail-ll", "BACK: short tip emerging below the crescent's outer rim")
    return ("arm-ur", "FRONT over X1 at the hub; BACK under the crescent (cut at its inner rim); exits through the horns")
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
# Rim lines: outline of each ring's final region inset by INSET, keeping only the arcs
# that lie on the ring's own rims (not on the cut edges), drawn as open strokes.
def detail_arcs(F, own, cut):
    arcs = trace(F, own + cut)
    own_names = {e.name for e in own}
    out = []
    for a in arcs:
        if a.E.name in own_names and a.span() > 0.02:
            out.append(loop_d([a], close=False))
    return out

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

# ------------------------------------------------------------------ SVG
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <title>Kubrique mark - construction C, flat knot emblem</title>
  <desc>Crescent + X built from three interlocking orbital rings, drawn as a strictly two-tone
emblem (one brass fill, transparent cuts). The crescent is a hoop seen nearly face-on and tilted
(lune between two ellipses); the X is two hoops seen nearly edge-on (thin ellipses). Every crossing
is an alternating over/under: X1 over crescent (both limbs), X2 over X1 (hub), crescent over X2
(thick base). The under-ring is cut by the over-ring dilated by {GAP} units, so each ring is a set
of explicit front/back pieces; no masks, no clipPaths, no gradients. Hide #detail below ~64px.</desc>
  <g id="mark" fill="{FILL}" fill-rule="evenodd">
{ring_group("ring-crescent", c_pieces, name_c,
    "ring-crescent: hoop seen nearly face-on, tilted. Outer rim ellipse (" + fmt(Eo.a) + "x" + fmt(Eo.b) +
    "), inner rim ellipse (" + fmt(Ei.a) + "x" + fmt(Ei.b) + ") offset toward the opening. "
    "Pieces split by the X1 cut: body (centre) + two horns.")}
{ring_group("ring-x1", x1_pieces, name_x1,
    "ring-x1: hoop seen nearly edge-on, upper-left to lower-right (ellipse " + fmt(E1.a) + "x" + fmt(E1.b) +
    " rotated 45). Over the crescent at both limbs, under X2 at the hub (hence the two arm pieces).")}
{ring_group("ring-x2", x2_pieces, name_x2,
    "ring-x2: hoop seen nearly edge-on, lower-left to upper-right (ellipse " + fmt(E2.a) + "x" + fmt(E2.b) +
    " rotated 135). Over X1 at the hub, under the crescent at the thick base (hence arm + tail pieces). "
    "The hub piece carries the transparent halo (hole) and the core dot is a separate piece.")}
  </g>
  <!-- detail: hairline rims inset {INSET} units from every band edge, stopping short of each cut.
       Purely decorative; drop this group for favicon / small sizes. -->
  <g id="detail" fill="none" stroke="{DETAIL}" stroke-width="{DETAIL_W}" stroke-linecap="round" stroke-opacity="0.55">
'''
for d in det:
    svg += f'    <path d="{d}"/>\n'
svg += '''  </g>
</svg>
'''

with open(os.path.join(HERE, "mark.svg"), "w") as f:
    f.write(svg)

# ------------------------------------------------------------------ preview
inline = svg.replace('width="512" height="512"', '')
html = f'''<!doctype html>
<html><head><meta charset="utf-8"><title>C review</title>
<style>
  html,body{{margin:0;background:#555;font:11px/1.3 system-ui,sans-serif;color:#aaa}}
  .row{{display:flex;gap:0}}
  .tile{{position:relative;width:500px;height:460px;display:flex;align-items:center;justify-content:center}}
  .dark{{background:#0d0e13}} .light{{background:#f5f1e8}}
  .big svg{{width:420px;height:420px;display:block}}
  .small{{height:100px;display:flex;align-items:center;justify-content:center;gap:28px}}
  .s40 svg{{width:40px;height:40px}} .s32 svg{{width:32px;height:32px}} .s64 svg{{width:64px;height:64px}} .s96 svg{{width:96px;height:96px}}
  .sil #detail{{display:none}}
  .lab{{position:absolute;left:8px;top:6px;font-size:11px;opacity:.6}}
</style></head><body>
<div class="row">
  <div class="tile dark big">{inline}<span class="lab">420px dark</span></div>
  <div class="tile light big">{inline}<span class="lab" style="color:#333">420px light</span></div>
</div>
<div class="row">
  <div class="tile dark small">
    <span class="s96 sil">{inline}</span><span class="s64 sil">{inline}</span><span class="s40 sil">{inline}</span><span class="s32 sil">{inline}</span>
    <span class="s40">{inline}</span>
  </div>
  <div class="tile light small">
    <span class="s96 sil">{inline}</span><span class="s64 sil">{inline}</span><span class="s40 sil">{inline}</span><span class="s32 sil">{inline}</span>
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
print("svg bytes", len(svg))
