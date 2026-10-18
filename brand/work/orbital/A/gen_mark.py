#!/usr/bin/env python3
"""
KUBRIQUE orbital mark - construction A: true 3D projection.

Three short cylindrical bands ("orbital rings") are modelled in 3D, each in its
own plane.  Every ring is sampled into N quads, every quad is projected by a
camera, all quads are ordered with a painter's algorithm (far -> near, derived
from real projected overlaps, not just a global depth sort) and emitted as SVG
paths.  The over/under weave therefore falls out of the geometry.

Plain Python 3, no numpy.  Usage:
    python3 gen_mark.py                # writes mark.svg, mark-mono.svg, params.json
    python3 gen_mark.py --out foo.svg  # other file name
    python3 gen_mark.py --rot-x1 20    # extra rotation (deg) of ring x1 in its own
                                       # plane (for animation frames later)
"""
import math, sys, json, argparse, os

# ---------------------------------------------------------------- vectors
def add(a, b): return (a[0]+b[0], a[1]+b[1], a[2]+b[2])
def sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def mul(a, s): return (a[0]*s, a[1]*s, a[2]*s)
def dot(a, b): return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def length(a): return math.sqrt(dot(a, a))
def norm(a):
    l = length(a)
    return (a[0]/l, a[1]/l, a[2]/l)
def rad(d): return d * math.pi / 180.0

def axis_from_tilt(theta_deg, phi_deg):
    """Ring axis: theta = tilt away from the view axis (0 = face-on, 90 = edge-on),
    phi = azimuth (deg, counter-clockwise from +x, y up) of the tilt direction."""
    t, p = rad(theta_deg), rad(phi_deg)
    return (math.sin(t)*math.cos(p), math.sin(t)*math.sin(p), math.cos(t))

# ---------------------------------------------------------------- camera
class Camera:
    """Camera on +z looking at the origin, y up.  D=None -> orthographic."""
    def __init__(self, D=None, cx=256.0, cy=256.0, scale=1.0):
        self.D, self.cx, self.cy, self.scale = D, cx, cy, scale
    def project(self, p):
        x, y, z = p
        if self.D is not None:
            f = self.D / (self.D - z)
            x, y = x*f, y*f
        return (self.cx + x*self.scale, self.cy - y*self.scale)
    def depth(self, p):           # larger = nearer to the camera
        if self.D is None:
            return p[2]
        x, y, z = p
        return -math.sqrt(x*x + y*y + (self.D - z)**2)
    def to_cam(self, p):          # unit vector from p towards the camera
        if self.D is None:
            return (0.0, 0.0, 1.0)
        return norm((-p[0], -p[1], self.D - p[2]))

# ---------------------------------------------------------------- rings
class Ring:
    def __init__(self, rid, R, w, axis, N, phase_deg=0.0, label="", Rz=None):
        self.id, self.R, self.w, self.N, self.label = rid, R, w, N, label
        self.Rz = R if Rz is None else Rz      # semi-axis along v (depth-ish); R is along u (image plane)
        self.n = norm(axis)
        nx, ny, nz = self.n
        # u lies in the image plane, perpendicular to the axis' image component
        u = (1.0, 0.0, 0.0) if abs(nx) + abs(ny) < 1e-9 else norm((-ny, nx, 0.0))
        self.u = u
        self.v = cross(self.n, u)          # v has z = sin(theta) >= 0: "near" side
        self.phase = rad(phase_deg)
    def radial(self, t):
        """Outward surface normal of the band wall at ring angle t (unit)."""
        t += self.phase
        # for an elliptical ring the normal is (cos t / R, sin t / Rz) in the (u, v) basis
        return norm(add(mul(self.u, math.cos(t)/self.R), mul(self.v, math.sin(t)/self.Rz)))
    def point(self, t, s):
        tt = t + self.phase
        return add(add(mul(self.u, self.R*math.cos(tt)), mul(self.v, self.Rz*math.sin(tt))), mul(self.n, s))

class Quad:
    __slots__ = ("ring", "idx", "t0", "t1", "p3", "p2", "c3", "depth",
                 "normal", "outer", "fill", "rimA", "rimB", "tocam", "bbox", "kind")
    def __init__(self, ring, idx, t0, t1):
        self.ring, self.idx, self.t0, self.t1 = ring, idx, t0, t1
        self.kind = "quad"

def build_quads(ring, cam):
    quads = []
    h = ring.w / 2.0
    for i in range(ring.N):
        t0 = 2*math.pi*i/ring.N
        t1 = 2*math.pi*(i+1)/ring.N
        q = Quad(ring, i, t0, t1)
        # corners: edge A at s=+h (t0->t1), edge B at s=-h (t0->t1)
        a0, a1 = ring.point(t0, +h), ring.point(t1, +h)
        b0, b1 = ring.point(t0, -h), ring.point(t1, -h)
        q.p3 = (a0, a1, b1, b0)
        q.p2 = tuple(cam.project(p) for p in q.p3)
        q.c3 = mul(add(add(a0, a1), add(b0, b1)), 0.25)
        q.depth = cam.depth(q.c3)
        q.normal = ring.radial(0.5*(t0+t1))        # outward radial
        q.tocam = cam.to_cam(q.c3)
        q.outer = dot(q.normal, q.tocam) > 0.0       # outside wall faces camera?
        xs = [p[0] for p in q.p2]; ys = [p[1] for p in q.p2]
        q.bbox = (min(xs), min(ys), max(xs), max(ys))
        quads.append(q)
    return quads

# ---------------------------------------------------------------- overlap (SAT)
def _axes(poly):
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]; x1, y1 = poly[(i+1) % n]
        ex, ey = x1-x0, y1-y0
        l = math.hypot(ex, ey)
        if l < 1e-9: continue
        yield (-ey/l, ex/l)

def polys_overlap(pa, pb, eps=0.35):
    """Separating-axis test for two convex polygons; eps shrinks the overlap so
    merely touching shapes are not counted."""
    for ax, ay in list(_axes(pa)) + list(_axes(pb)):
        a = [x*ax + y*ay for x, y in pa]; b = [x*ax + y*ay for x, y in pb]
        if max(a) - eps <= min(b) or max(b) - eps <= min(a):
            return False
    return True

def bbox_overlap(a, b, eps=0.35):
    return not (a[2]-eps <= b[0] or b[2]-eps <= a[0] or a[3]-eps <= b[1] or b[3]-eps <= a[1])

# ---------------------------------------------------------------- shading
def clamp01(x): return 0.0 if x < 0 else (1.0 if x > 1 else x)

def hexcol(rgb):
    return "#%02x%02x%02x" % tuple(int(round(clamp01(c)*255)) for c in rgb)

def shade(normal, tocam, L, mat, qsteps=(13, 6)):
    """Lambert + Blinn-Phong on a quantised grid so neighbouring quads share colours."""
    n = normal if dot(normal, tocam) > 0 else mul(normal, -1.0)
    diff = clamp01(dot(n, L))
    h = norm(add(L, tocam))
    spec = clamp01(dot(n, h)) ** mat["p"]
    # Fresnel-ish rim: bands seen at a grazing angle look more metallic
    graze = 1.0 - clamp01(dot(n, tocam))
    diff = round(diff*qsteps[0]) / qsteps[0]
    spec = round(spec*qsteps[1]) / qsteps[1]
    graze = round(graze*3) / 3
    base, hi = mat["base"], mat["hi"]
    out = []
    for c in range(3):
        v = base[c] * (mat["amb"] + mat["kd"]*diff) + graze*mat["kg"]*(hi[c]-base[c])
        v = v + spec*mat["ks"]*(hi[c] - v)
        out.append(clamp01(v))
    return hexcol(out)

# Palette: gold/brass metal for rims, warm glass band.  Chosen to sit mid-value so
# it reads on both #0d0e13 and #f5f1e8.
MATERIALS = {
    "glass_outer": dict(base=(0.84, 0.64, 0.28), hi=(1.00, 0.96, 0.80), amb=0.52, kd=0.50, ks=0.50, kg=0.22, p=18, opacity=0.93),
    "glass_inner": dict(base=(0.40, 0.27, 0.10), hi=(0.80, 0.66, 0.40), amb=0.50, kd=0.35, ks=0.15, kg=0.05, p=12, opacity=0.16),
    "rim_outer":   dict(base=(0.60, 0.42, 0.14), hi=(1.00, 0.97, 0.85), amb=0.45, kd=0.50, ks=0.85, kg=0.20, p=26, opacity=1.0),
    "rim_inner":   dict(base=(0.55, 0.40, 0.16), hi=(0.95, 0.85, 0.55), amb=0.45, kd=0.45, ks=0.45, kg=0.10, p=16, opacity=0.45, wmul=0.55),
}

# ---------------------------------------------------------------- painter ordering
class CoreItem:
    """The luminous core sits at depth 0 and takes part in the ordering."""
    def __init__(self, cam, r):
        self.kind = "core"; self.ring = None; self.idx = -1
        self.c3 = (0.0, 0.0, 0.0); self.depth = cam.depth(self.c3)
        cx, cy = cam.project(self.c3)
        self.p2 = ((cx-r, cy-r), (cx+r, cy-r), (cx+r, cy+r), (cx-r, cy+r))
        self.bbox = (cx-r, cy-r, cx+r, cy+r)
        self.outer = True

def order_items(items):
    """Return a list of segments.  A segment is a list of consecutive quads of
    one ring (an arc) that may be drawn as a unit without breaking any
    far-before-near constraint between projected-overlapping quads."""
    n = len(items)
    succ = [[] for _ in range(n)]
    indeg = [0]*n
    for i in range(n):
        a = items[i]
        for j in range(i+1, n):
            b = items[j]
            if a.ring is not None and a.ring is b.ring:
                d = abs(a.idx - b.idx)
                if d <= 1 or d >= a.ring.N-1:
                    continue                      # neighbours share an edge
            if not bbox_overlap(a.bbox, b.bbox): continue
            if not polys_overlap(a.p2, b.p2): continue
            if a.depth < b.depth: succ[i].append(j); indeg[j] += 1
            else:                 succ[j].append(i); indeg[i] += 1
    drawn = [False]*n
    by_ring = {}
    for i, it in enumerate(items):
        if it.ring is not None:
            by_ring.setdefault(it.ring.id, {})[it.idx] = i
    segments = []
    remaining = n
    forced = 0
    def draw(i):
        nonlocal remaining
        drawn[i] = True; remaining -= 1
        for s in succ[i]:
            indeg[s] -= 1
    while remaining:
        ready = [i for i in range(n) if not drawn[i] and indeg[i] == 0]
        if not ready:                              # cycle (near-equal depths): force the farthest
            cand = [i for i in range(n) if not drawn[i]]
            start = min(cand, key=lambda i: (indeg[i], items[i].depth)); forced += 1
        else:
            start = min(ready, key=lambda i: items[i].depth)
        it = items[start]
        draw(start)
        if it.ring is None:
            segments.append([start]); continue
        arc = [start]
        ring = it.ring; idxmap = by_ring[ring.id]
        # extend forward
        k = it.idx
        while len(arc) < ring.N:
            k = (k + 1) % ring.N
            j = idxmap[k]
            if drawn[j] or indeg[j] != 0: break
            draw(j); arc.append(j)
        k = it.idx
        while len(arc) < ring.N:
            k = (k - 1) % ring.N
            j = idxmap[k]
            if drawn[j] or indeg[j] != 0: break
            draw(j); arc.insert(0, j)
        segments.append(arc)
    return segments, forced

# ---------------------------------------------------------------- SVG helpers
def f2(x): return ("%.1f" % x).replace(".0", "") if abs(x - round(x)) < 0.05 else "%.1f" % x

def path_for_run(quads):
    """Union of a contiguous run of quads: edge A forward, edge B backward."""
    pts = [quads[0].p2[0]] + [q.p2[1] for q in quads]          # A edge: a0 then each a1
    pts += [quads[-1].p2[2]] + [q.p2[3] for q in reversed(quads)]  # B edge: b1 (last) then b0 backwards
    return "M" + " ".join("%s,%s" % (f2(x), f2(y)) for x, y in pts) + "Z"

def polyline_for_run(quads, edge):
    if edge == "A": pts = [quads[0].p2[0]] + [q.p2[1] for q in quads]
    else:           pts = [quads[0].p2[3]] + [q.p2[2] for q in quads]
    return "M" + " ".join("%s,%s" % (f2(x), f2(y)) for x, y in pts)

def runs_by(quads, key):
    runs, cur = [], [quads[0]]
    for q in quads[1:]:
        if key(q) == key(cur[-1]): cur.append(q)
        else: runs.append(cur); cur = [q]
    runs.append(cur)
    return runs

def seg_side(quads):
    d = sum(q.depth for q in quads)/len(quads)
    return "front" if d > 0 else "back"

def emit_segment_group(gid, quads, rimw, mono=None):
    side = seg_side(quads)
    facing = "outer" if all(q.outer for q in quads) else ("inner" if not any(q.outer for q in quads) else "mixed")
    a0 = math.degrees(quads[0].t0); a1 = math.degrees(quads[-1].t1)
    out = ['  <g id="%s" data-side="%s" data-facing="%s" data-arc="%.0f-%.0f">' % (gid, side, facing, a0, a1)]
    out.append('   <!-- %s: %s wall, arc %.0f..%.0f deg -->' % (side.upper(), facing, a0, a1))
    if mono is not None:
        # silhouette: outer walls only, one colour
        for run in runs_by(quads, lambda q: q.outer):
            if run[0].outer:
                out.append('   <path d="%s"/>' % path_for_run(run))
    else:
        # Fills are opaque inside a sub-group; translucency comes from the group's opacity so the
        # same-colour hairline stroke (which hides anti-aliasing seams) never doubles up.
        for cls, want in (("gi", False), ("go", True)):
            runs = [r for r in runs_by(quads, lambda q: (q.fill, q.outer)) if r[0].outer == want]
            if not runs: continue
            out.append('   <g class="%s">' % cls)
            for run in runs:
                out.append('    <path fill="%s" stroke="%s" d="%s"/>' % (run[0].fill, run[0].fill, path_for_run(run)))
            out.append('   </g>')
        # brass rims along both band edges (A: s=+w/2, B: s=-w/2)
        for cls, want in (("ri", False), ("ro", True)):
            lines = []
            for edge in ("A", "B"):
                key = (lambda q: (q.rimA, q.outer)) if edge == "A" else (lambda q: (q.rimB, q.outer))
                for run in runs_by(quads, key):
                    if run[0].outer != want: continue
                    col = run[0].rimA if edge == "A" else run[0].rimB
                    lines.append('    <path stroke="%s" d="%s"/>' % (col, polyline_for_run(run, edge)))
            if lines:
                out.append('   <g class="%s">' % cls); out.extend(lines); out.append('   </g>')
    out.append('  </g>')
    return "\n".join(out), side

# ---------------------------------------------------------------- collision check
def collisions(rings, samples=720):
    """Rough 3D self-intersection test between the band surfaces of each ring pair:
    walk ring A's band (both edges) and see whether it crosses ring B's cylinder wall
    (radius R_B about B's axis) while inside B's band height.  Returns a list of notes."""
    notes = []
    for A in rings:
        for B in rings:
            if A is B: continue
            for s in (-A.w/2, 0.0, A.w/2):
                prev = None
                for k in range(samples+1):
                    t = 2*math.pi*k/samples
                    p = A.point(t, s)
                    zeta = dot(p, B.n)
                    # radial distance from B's axis, measured in B's (u,v) metric (ellipse support)
                    pu, pv = dot(p, B.u), dot(p, B.v)
                    f = math.sqrt((pu/B.R)**2 + (pv/B.Rz)**2) - 1.0
                    if prev is not None and prev[0]*f < 0 and abs(zeta) < B.w/2 + 1.0:
                        notes.append("%s crosses %s wall at t=%.0f deg (zeta=%.1f, band half-width %.1f)" % (A.id, B.id, math.degrees(t), zeta, B.w/2))
                    prev = (f, zeta)
    return notes

# ---------------------------------------------------------------- main build
def build(P):
    cam = Camera(D=P["camera_D"], cx=256.0, cy=256.0, scale=P["scale"])
    L = norm(tuple(P["light"]))
    rings = [
        Ring("ring-crescent", P["crescent"]["R"], P["crescent"]["w"],
             axis_from_tilt(P["crescent"]["theta"], P["crescent"]["phi"]), P["N"], P["crescent"].get("rot", 0.0), "crescent", P["crescent"].get("Rz")),
        Ring("ring-x1", P["x1"]["R"], P["x1"]["w"], axis_from_tilt(P["x1"]["theta"], P["x1"]["phi"]), P["N"], P["x1"].get("rot", 0.0), "x1", P["x1"].get("Rz")),
        Ring("ring-x2", P["x2"]["R"], P["x2"]["w"], axis_from_tilt(P["x2"]["theta"], P["x2"]["phi"]), P["N"], P["x2"].get("rot", 0.0), "x2", P["x2"].get("Rz")),
    ]
    P["_collisions"] = collisions(rings)
    items = []
    for r in rings:
        qs = build_quads(r, cam)
        for q in qs:
            q.fill = shade(q.normal, q.tocam, L, MATERIALS["glass_outer"]) if q.outer else P["inner_fill"]
            rm = MATERIALS["rim_outer" if q.outer else "rim_inner"]
            # rims: edge A (s=+h) and edge B (s=-h) get slightly different normals (tilted by the axis)
            nA = norm(add(q.normal, mul(r.n, 0.55))); nB = norm(sub(q.normal, mul(r.n, 0.55)))
            q.rimA = shade(nA, q.tocam, L, rm); q.rimB = shade(nB, q.tocam, L, rm)
        items.extend(qs)
    core = CoreItem(cam, P["core_r"])
    items.append(core)
    segments, forced = order_items(items)
    return cam, rings, items, segments, forced

def svg_text(P, cam, rings, items, segments, mono=None):
    W = 512
    counters = {}
    defs, order = [], []
    stats = {"segments": 0, "per_ring": {}}
    per_ring_groups = {r.id: [] for r in rings}
    for seg in segments:
        it0 = items[seg[0]]
        if it0.kind == "core":
            order.append("CORE"); continue
        ring = it0.ring
        quads = [items[i] for i in seg]
        k = counters.get(ring.id, 0); counters[ring.id] = k+1
        gid = "%s-s%02d" % (ring.id, k)
        g, side = emit_segment_group(gid, quads, P["rim_w"], mono)
        per_ring_groups[ring.id].append(g)
        order.append(gid)
        stats["segments"] += 1
        stats["per_ring"][ring.id] = stats["per_ring"].get(ring.id, 0) + 1
    head = ['<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="Kubrique mark: a crescent and an X formed by three interlocking orbital rings">' % (W, W, W, W),
            ' <title>Kubrique orbital mark (construction A)</title>',
            ' <!-- Generated by gen_mark.py: three cylindrical bands in 3D, projected and depth-sorted.',
            '      Each ring lives in <defs> as its own <g id="ring-..."> split into arc segments;',
            '      data-side="front|back" says whether the arc is nearer (front) or farther (back) than the',
            '      centre plane, data-facing says whether you see the outside or the inside wall of the band.',
            '      The <g id="mark"> block draws the segments in painter order (far -> near) with <use>, which',
            '      is what produces the over/under weave at every crossing. -->']
    if mono is None:
        go, gi, ro, ri = MATERIALS["glass_outer"], MATERIALS["glass_inner"], MATERIALS["rim_outer"], MATERIALS["rim_inner"]
        head += [' <style>',
                 '  /* go/gi: glass band, outside/inside wall.  ro/ri: brass rim, outside/inside wall. */',
                 '  .go{opacity:%.2f}.gi{opacity:%.2f}.go path,.gi path{stroke-width:.7;stroke-linejoin:round}' % (go["opacity"], gi["opacity"]),
                 '  .ro{opacity:%.2f}.ri{opacity:%.2f}.ro path,.ri path{fill:none;stroke-linecap:round;stroke-linejoin:round}' % (ro["opacity"], ri["opacity"]),
                 '  .ro path{stroke-width:%s}.ri path{stroke-width:%s}' % (f2(P["rim_w"]), f2(P["rim_w"]*ri.get("wmul", 1.0))),
                 ' </style>',
                 ' <defs>',
                 '  <radialGradient id="core-glow" cx="0.5" cy="0.5" r="0.5">',
                 '   <stop offset="0" stop-color="#fff8e1" stop-opacity="1"/>',
                 '   <stop offset="0.18" stop-color="#ffe9a8" stop-opacity="0.95"/>',
                 '   <stop offset="0.45" stop-color="#f0b84a" stop-opacity="0.45"/>',
                 '   <stop offset="1" stop-color="#f0b84a" stop-opacity="0"/>',
                 '  </radialGradient>']
    else:
        head += [' <defs>']
    for r in rings:
        head.append(' <g id="%s" data-R="%s" data-w="%s">' % (r.id, f2(r.R), f2(r.w)))
        head.extend(per_ring_groups[r.id])
        head.append(' </g>')
    head.append(' </defs>')
    body = [' <g id="mark"%s>' % ('' if mono is None else ' fill="%s"' % mono)]
    for gid in order:
        if gid == "CORE":
            if mono is None:
                body.append('  <g id="core"><!-- luminous core, drawn at depth 0: behind the front arcs, in front of the back arcs -->')
                body.append('   <circle cx="256" cy="256" r="%s" fill="url(#core-glow)"/><circle cx="256" cy="256" r="%s" fill="#fffaf0"/></g>' % (f2(P["core_r"]), f2(P["core_dot"])))
            else:
                body.append('  <g id="core"><circle cx="256" cy="256" r="%s"/></g>' % f2(P["core_dot"]*1.6))
        else:
            body.append('  <use xlink:href="#%s" href="#%s"/>' % (gid, gid))
    if mono is None:
        body.append('  <g id="core-shine"><!-- the core seen through the glass of the front arcs -->')
        body.append('   <circle cx="256" cy="256" r="%s" fill="url(#core-glow)" opacity="0.55"/><circle cx="256" cy="256" r="%s" fill="#fff6dc" opacity="0.9"/></g>' % (f2(P["core_r"]*0.45), f2(P["core_dot"]*0.6)))
    body.append(' </g>')
    body.append('</svg>')
    return "\n".join(head + body) + "\n", stats

DEFAULT = {
    "N": 96, "scale": 1.0, "camera_D": None, "light": [-0.38, 0.56, 0.74], "inner_fill": "#5a3f16",
    "rim_w": 2.2, "core_r": 54, "core_dot": 7,
    "crescent": {"R": 196, "w": 92, "theta": 42, "phi": 0},
    "x1": {"R": 216, "w": 38, "theta": 86.5, "phi": 130},
    "x2": {"R": 190, "Rz": 125, "w": 38, "theta": 86.5, "phi": 50},
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", help="JSON file overriding DEFAULT")
    ap.add_argument("--out", default="mark.svg")
    ap.add_argument("--mono", default="mark-mono.svg")
    ap.add_argument("--rot-crescent", type=float, default=None)
    ap.add_argument("--rot-x1", type=float, default=None)
    ap.add_argument("--rot-x2", type=float, default=None)
    a = ap.parse_args()
    P = json.loads(json.dumps(DEFAULT))
    if a.params:
        with open(a.params) as f:
            for k, v in json.load(f).items():
                if isinstance(v, dict) and k in P: P[k].update(v)
                else: P[k] = v
    for key, val in (("crescent", a.rot_crescent), ("x1", a.rot_x1), ("x2", a.rot_x2)):
        if val is not None: P[key]["rot"] = val
    cam, rings, items, segments, forced = build(P)
    svg, stats = svg_text(P, cam, rings, items, segments)
    with open(a.out, "w") as f: f.write(svg)
    if a.mono:
        msvg, _ = svg_text(P, cam, rings, items, segments, mono="#1a1710")
        with open(a.mono, "w") as f: f.write(msvg)
    with open(os.path.splitext(a.out)[0] + ".params.json", "w") as f: json.dump(P, f, indent=1)
    print("quads=%d segments=%d forced=%d size=%dB" % (len(items)-1, stats["segments"], forced, len(svg)))
    print("collisions:", P["_collisions"] or "none")
    print("per ring:", stats["per_ring"])
    for seg in segments:
        it = items[seg[0]]
        if it.kind == "core": print("  CORE"); continue
        qs = [items[i] for i in seg]
        print("  %-14s %-5s n=%2d arc %4.0f..%4.0f  depth %6.1f..%6.1f  outer=%d/%d" % (
            it.ring.id, seg_side(qs), len(qs), math.degrees(qs[0].t0), math.degrees(qs[-1].t1),
            min(q.depth for q in qs), max(q.depth for q in qs), sum(q.outer for q in qs), len(qs)))

if __name__ == "__main__":
    main()
