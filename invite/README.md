# First Light — interactive invitation

A single self-contained HTML file. No build step, no dependencies, no network
calls. Open `index.html` in any browser, or drop it on any static host.

## What it does

- **Sealed envelope.** Click or press Enter on it to break the wax seal — the
  flap folds back and the card rises out.
- **Animated hero plate.** A canvas painting of the vehicle climbing off the
  range at night. The bright spot travelling around each collar band is the
  rotating detonation, which is the whole point of the architecture.
- **Live countdown** to ignition, correct in every timezone.
- **Order of the evening**, venue with a range diagram, and links out to maps
  and to a downloadable calendar file.
- **Manifest** of everyone invited, searchable by name or role.
- **RSVP** that remembers the answer on the device, plus an email reply.

## Editing it

Everything you need to change sits in one place: the `CONFIG` block near the
top of the `<script>` at the bottom of `index.html`, marked

```
▸ EDIT EVERYTHING HERE ◂
```

The page rebuilds itself from that object, so you never touch the markup.

| Field | Notes |
| --- | --- |
| `eventISO` | Keep the UTC offset (`+01:00`) — the countdown depends on it. |
| `durationHours` | Used for the calendar file's end time. |
| `details` | Rows of `[label, value, footnote]`. Add or remove freely. |
| `programme` | Rows of `[time, what, footnote]`. |
| `venue.mapsQuery` | What gets searched when someone taps "Open in maps". |
| `guests` | `{ name, role }`, plus `plus: true` to mark a plus-one. |
| `rsvpEmail` | Where "Reply by email" sends the reply. |

The guest count and the "with a guest" tally are counted from the list, so they
stay correct on their own.

## Design notes

Sodium amber on deep indigo — the colours of a range at night. Flame cyan is
held back for the plume and the live dot and used nowhere else. Old-style serif
for anything you read, mono for anything you look up.

The card is themed twice: the same invitation at night, and printed on bone
paper at dawn. It follows the viewer's light or dark setting. The hero plate
stays dark in both, because a photographic plate doesn't change with the room
it's hung in.

Motion is disabled wherever `prefers-reduced-motion` is set; the plate then
renders as a single still frame.
