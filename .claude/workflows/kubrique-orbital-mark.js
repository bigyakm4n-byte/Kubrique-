export const meta = {
  name: 'kubrique-orbital-mark',
  description: 'Design the Kubrique logo (crescent + X from interlocking orbital rings) via a judged panel, then refine and animate the winner',
  whenToUse: 'Run from the repo root on any OS. Optional args: { refsDir: "brand/reference" } for inspiration photos, { workDir: "brand/work/orbital" } to change the output folder.',
  phases: [
    { title: 'Design', detail: 'four independent SVG candidates, each a different construction' },
    { title: 'Judge', detail: 'three judges with distinct lenses score the rendered candidates' },
    { title: 'Refine', detail: 'polish the winner, add slow spin and colour cycle' },
  ],
}

// Paths are RELATIVE TO THE REPO ROOT (the directory Claude Code was started in).
// Agents resolve them to absolute paths themselves, so this runs on Windows, macOS and Linux.
const WORK = (args && args.workDir) || 'brand/work/orbital'
const REFS = (args && args.refsDir) || 'brand/reference'

const ENV = `
ENVIRONMENT NOTES (cross-platform)
- You start in the repository root. Work only inside the folder ${WORK}/ (create it). Resolve it to an absolute path first (pwd / Get-Location) because file:// URLs need absolute paths. Use forward slashes in file:// URLs even on Windows (file:///C:/Users/...).
- Python: try "python3", then "python", then "py -3". numpy may not be installed; do the maths in plain Python.
- Headless browser for rendering PNG review images. Probe in this order and use the first that exists:
    Windows:  "C:/Program Files/Google/Chrome/Application/chrome.exe",
              "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
              "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
              "%LOCALAPPDATA%/Google/Chrome/Application/chrome.exe"
    macOS:    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    Linux:    /opt/pw-browsers/chromium, chromium, chromium-browser, google-chrome
  Command shape (one line):
    <browser> --headless=new --disable-gpu --hide-scrollbars --window-size=1000,560 --screenshot=<ABS out.png> file:///<ABS preview.html>
  Add --no-sandbox on Linux. On Windows run it from a shell that supports quoted paths. If the screenshot file does not appear, try --headless (old mode) instead of --headless=new.
  If no browser can be found, say so in your notes, skip rendering, and still return the SVG; reason about geometry from the source. Do not install anything.
- Inspiration photos may exist in ${REFS}/ (any .jpg/.png). If the folder is missing or empty, proceed without them: they were only inspiration.
`

const BRIEF = `
You are designing a logo mark for KUBRIQUE, a conceptual aerospace architecture project (reusable hypersonic vehicles, orbital staging, public-domain engineering). The mark will be used at 32px favicon size up to a large hero, on dark and on light backgrounds.

THE CONCEPT (from the client, verbatim intent): "a crescent moon with an X, where the rings are interconnected like orbital rings". A chandelier (photos, if present, in ${REFS}/) was only the inspiration: an armillary-like cluster of crystal hoops interlocking around a bulb. Do NOT reproduce the chandelier. Take from it only: hoops in different planes that weave over and under each other, thin metallic rims, and a luminous centre.

WHAT THE MARK MUST DO
1. Silhouette reads at a glance as a CRESCENT with an X inside/through it.
2. The X is made of two orbital rings seen nearly edge-on (each ring projects as a long lens/band), crossing at the centre.
3. The crescent is a third orbital ring, seen closer to face-on and tilted, so its band is wide on one side and tapers to nothing on the other (that taper is what makes it a crescent, not a cut-off circle).
4. The three rings are INTERCONNECTED: every crossing shows a consistent over/under weave (like a knot or gyroscope gimbals). A viewer should be able to trace each ring passing in front of one and behind another.
5. A small luminous core at the centre (the "bulb" / star / engine), optional but welcome.
6. Must survive: 32px (silhouette only), one-colour, dark and light backgrounds.

TECHNICAL
- Output a standalone SVG, viewBox="0 0 512 512", no external refs, no raster. Hand-write clean geometry or generate it with a Python script. If you generate, keep the generator script next to the SVG.
- Render for your own review: write an HTML file that shows the SVG at 420px on #0d0e13, at 420px on #f5f1e8, and at 40px on both, screenshot it with the headless browser described below, then LOOK at the PNG with the Read tool. Iterate up to 4 times until the geometry really reads. Be honest in your notes about what still does not work.
- Static only for now (animation is added later), but structure the SVG so each ring is its own <g> with an id (ring-crescent, ring-x1, ring-x2) and the over/under weave is done with clipPath or by splitting each ring into front and back segments. Note in the SVG which segments are front/back.
- Colour: a gold/brass metal for rims plus a glassy translucent band is the default palette, but you may propose another. Keep every colour explicit (no currentColor tricks that vanish on one background).
${ENV}`

const DESIGN_SCHEMA = {
  type: 'object',
  properties: {
    candidate: { type: 'string' },
    approach: { type: 'string' },
    svgPath: { type: 'string' },
    pngPath: { type: 'string', description: 'absolute path of the review render, or "none" if no browser was available' },
    notes: { type: 'string', description: 'what works, what does not, what you would fix with more time' },
  },
  required: ['candidate', 'approach', 'svgPath', 'pngPath', 'notes'],
}

const APPROACHES = [
  { key: 'A', prompt: `Construction A, TRUE 3D PROJECTION: write a Python script that models three rings as thin tori / short cylindrical bands in 3D (radius ~190, band width ~30), each in its own plane: ring-x1 and ring-x2 are tilted so that in the chosen camera view they appear nearly edge-on and cross at roughly +/-40 degrees through the centre; ring-crescent is tilted so it appears as a wide ellipse whose visible band tapers (choose a camera slightly above/below its plane so the near wall is wide and the far wall vanishes). Sample each ring into ~96 quads, depth-sort all quads (painter's algorithm) and emit SVG polygons with per-quad shading from the surface normal. The depth sort gives you the over/under weave for free. Then simplify: merge runs of quads into paths where you can, so the SVG stays under ~60KB.` },
  { key: 'B', prompt: `Construction B, HAND-DRAWN ELLIPSES WITH CLIPPED WEAVE: author the SVG by hand. The crescent ring is the region between two offset ellipses (outer ellipse minus an inner ellipse shifted toward one side) so it tapers to points. Each X ring is a lens: the region between two shallow arcs, long axis ~360px, max width ~56px, rotated +/-42 degrees. Do the weave explicitly: split each ring into 'front' and 'back' halves using clipPath rectangles/ellipses so that at each of the crossings the correct ring is on top (decide a consistent weave: crescent over x1 at its upper crossing, under x1 at its lower crossing; x1 over x2 at the centre; x2 over crescent where it exits, etc.). Add thin double rims (1.5px gold lines) along each band edge and a few facet lines inside the glassy band.` },
  { key: 'C', prompt: `Construction C, FLAT EMBLEM / KNOT: a strictly two-tone, solid-shape mark like a Japanese mon or a maritime knot badge. No gradients. The crescent and the two X bands are solid gold shapes on the background; the interconnection is shown purely by small background-coloured gaps (2-3px 'cuts') where one band passes under another, the way knot diagrams and Celtic rings do. Prioritise a silhouette that is unmistakable at 32px. Then make a second layer group (id="detail") with subtle inner lines that can be hidden at small sizes.` },
  { key: 'D', prompt: `Construction D, WIREFRAME ASTROLABE: thin-line construction, like an astrolabe or gyroscope diagram. Each ring is drawn as a double rim (two parallel 2px strokes ~26px apart) with short tick marks between the rims to suggest the crystal prisms; the crescent ring is a tilted ellipse pair whose rims converge to a point at the thin end. The X rings are nearly edge-on ellipse pairs. Make the weave by breaking strokes with gaps (stroke-dasharray/explicit segments) where a ring passes behind another. Fill the band interiors with a very faint glass tint so the mark still has mass at small size. Aim for an engineering-drawing elegance that suits an aerospace brand.` },
]

phase('Design')
log('Four designers building the crescent-X orbital mark, each with a different construction')
const candidates = (await parallel(APPROACHES.map(a => () =>
  agent(`${BRIEF}

YOUR CONSTRUCTION
${a.prompt}

Work in ${WORK}/${a.key}/ (create it). Save the final SVG as ${WORK}/${a.key}/mark.svg and the final review render as ${WORK}/${a.key}/review.png. Return candidate="${a.key}" and ABSOLUTE paths.`,
    { label: `design:${a.key}`, phase: 'Design', schema: DESIGN_SCHEMA })
))).filter(Boolean)

log(`${candidates.length} candidates produced`)
if (candidates.length === 0) return { error: 'no candidates produced' }

const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    rankings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          candidate: { type: 'string' },
          score: { type: 'number', description: '0-10' },
          strengths: { type: 'string' },
          weaknesses: { type: 'string' },
        },
        required: ['candidate', 'score', 'strengths', 'weaknesses'],
      },
    },
    winner: { type: 'string' },
    fixes: { type: 'array', items: { type: 'string' }, description: 'concrete, specific fixes for the winner' },
    graft: { type: 'array', items: { type: 'string' }, description: 'ideas from runners-up worth grafting into the winner' },
  },
  required: ['lens', 'rankings', 'winner', 'fixes', 'graft'],
}

const LENSES = [
  { key: 'concept', prompt: 'LENS: CONCEPT FIDELITY. Does each mark read, at a glance, as "a crescent with an X, made of interconnected orbital rings"? Is the crescent a real crescent (tapering), is the X clearly two rings seen edge-on rather than two bars, and can you trace an over/under weave at every crossing? Compare against the client intent, not against any chandelier photos (those were inspiration only).' },
  { key: 'craft', prompt: 'LENS: LOGO CRAFT. Judge as a brand identity designer: silhouette strength at 40px, balance and optical centring in the 512 box, consistent stroke weights, no tangents or near-misses between shapes, works on dark AND light, would survive one-colour embroidery. Penalise anything that looks like a clip-art gradient blob.' },
  { key: 'geometry', prompt: 'LENS: GEOMETRIC COHERENCE. Could these three rings actually exist as circles in 3D around one centre? Check ellipse proportions and tilts for mutual consistency, that each ring\'s band width is plausible given its foreshortening, that the weave is physically consistent (no ring that is both over and under the same ring at the same crossing, no ring that passes over everything), and that the crescent taper comes from tilt rather than from a chunk missing.' },
]

phase('Judge')
const candidateList = candidates.map(c => `- Candidate ${c.candidate} (${c.approach}): SVG ${c.svgPath}, render ${c.pngPath}. Designer notes: ${c.notes}`).join('\n')
const verdicts = (await parallel(LENSES.map(l => () =>
  agent(`You are judging logo candidates for KUBRIQUE (conceptual aerospace architecture). The brief: a crescent moon with an X through it, both built from interconnected orbital rings that weave over and under each other, with a luminous centre; must work at 32px and on dark or light.

${l.prompt}

Candidates (LOOK at every render PNG with the Read tool; if a render is "none" or ambiguous, open the SVG source and, if a headless browser is available, render it yourself):
${candidateList}
${ENV}
Score each 0-10 under your lens, pick a winner, and give concrete fixes for the winner (specific: "move the crescent's thin tip 20px further from the x2 band so there is no tangent", not "improve balance"). Also list ideas from runners-up worth grafting into the winner.`,
    { label: `judge:${l.key}`, phase: 'Judge', schema: JUDGE_SCHEMA })
))).filter(Boolean)

const totals = {}
for (const v of verdicts) for (const r of v.rankings) totals[r.candidate] = (totals[r.candidate] || 0) + r.score
const ranked = Object.entries(totals).sort((a, b) => b[1] - a[1])
const winnerKey = ranked.length ? ranked[0][0] : candidates[0].candidate
const winner = candidates.find(c => c.candidate === winnerKey) || candidates[0]
log(`Judges' totals: ${ranked.map(([k, s]) => `${k}=${s}`).join(', ')}. Winner: ${winner.candidate}`)

const REFINE_SCHEMA = {
  type: 'object',
  properties: {
    staticSvgPath: { type: 'string' },
    animatedSvgPath: { type: 'string' },
    framesPngPath: { type: 'string', description: 'one PNG showing several animation frames side by side, or "none"' },
    notes: { type: 'string' },
  },
  required: ['staticSvgPath', 'animatedSvgPath', 'framesPngPath', 'notes'],
}

phase('Refine')
const judgeNotes = verdicts.map(v => `## ${v.lens}\nRankings: ${v.rankings.map(r => `${r.candidate}=${r.score} (+ ${r.strengths} / - ${r.weaknesses})`).join('; ')}\nFixes for winner: ${v.fixes.join(' | ')}\nGraft: ${v.graft.join(' | ')}`).join('\n\n')
const refined = await agent(`${BRIEF}

You are the finishing designer. The judged winner is Candidate ${winner.candidate} (${winner.approach}) at ${winner.svgPath} (render ${winner.pngPath}). Designer notes: ${winner.notes}

All candidates, for grafting ideas:
${candidateList}

Judges' verdicts:
${judgeNotes}

YOUR JOB
1. Apply the judges' fixes to the winner and graft the runner-up ideas that genuinely help. Keep the crescent + X silhouette and the over/under weave. Save as ${WORK}/final/mark-static.svg. Render and LOOK at it on dark and light, 420px and 40px, iterate up to 4 times.
2. Make the animated version ${WORK}/final/mark-animated.svg. The client asked: "the rings spin slowly and change colour". Implement:
   - Each ring SPINS ABOUT ITS OWN AXIS: the band stays in place but its surface travels around it. Do this with facet/prism marks that glide along each ring (animate stroke-dashoffset on a dashed stroke that follows the ring's centreline path, or SMIL <animateMotion>/<animate> on segment positions). Each ring at a different slow period (roughly 18s, 26s, 40s), one of them counter-direction.
   - A very slow whole-mark precession is allowed only if it never breaks the crescent-X read; if in doubt leave it out.
   - COLOUR CYCLE: the metal/glass colours drift through a cycle (for example gold -> rose -> violet -> teal -> gold) over ~24s using SMIL <animate attributeName="stop-color"> on gradient stops or on fills. Use SMIL or CSS inside the SVG only; it must animate when the SVG is opened directly in a browser and when used in an <img>. No JavaScript.
   - Respect prefers-reduced-motion with a CSS media query that pauses the CSS animations (SMIL cannot be paused by CSS; keep the SMIL colour drift gentle).
3. Prove the animation: render at least 4 frames at different times into ONE side-by-side PNG ${WORK}/final/frames.png. Technique: lay four copies of the SVG in one HTML page, each copy with its CSS animations given a different negative animation-delay (0s, -6s, -12s, -18s) and its SMIL animations given begin="-6s" etc., then screenshot once. LOOK at frames.png and confirm the rings visibly spin and the colour visibly changes between frames.
4. Also copy the finished files to brand/kubrique-logo-static.svg and brand/kubrique-logo.svg (overwrite the drafts there).
5. Keep the static SVG under ~40KB and the animated one under ~60KB. Both must be valid XML (python -c "import xml.dom.minidom,sys; xml.dom.minidom.parse(sys.argv[1])" <file>).
Return ABSOLUTE paths.`,
  { label: 'refine:final', phase: 'Refine', schema: REFINE_SCHEMA })

return { candidates, verdicts, totals, winner: winner.candidate, refined }
