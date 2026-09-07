# Judge kit (3 files)

Use these on Upload at `http://localhost:5173`. Coordinates in `03_nav.example.json` are **example only** — not from a real ping header.

| File | What to do |
|---|---|
| `01_labeled_sss.jpg` | Real SSS frame with a YOLO label in `Dataset/2018`. Run **Demo** (25%) then **Survey** (10%). Survey may show extra weak boxes. |
| `02_empty_seafloor.jpg` | Real SSS frame with an **empty** label file. Expect few or no boxes. Shows the filter saying no. |
| `03_nav.example.json` | Attach as optional metadata with `01_labeled_sss.jpg` so the map can plot. Status will be `computed` because heading + `pixel_size_m` are present. **Do not present these lat/lon as a real survey fix.** |

Rehearsal order:

1. `01` with **no** metadata → Result overlay, Map says unavailable.
2. `01` + `03` → Map has a pin. Download JSON/CSV.
3. `02` → empty or near-empty result.

Demo vs Survey: **Demo** (default) uses the conservative detector gate — cleaner overlay. **Survey** proposes weaker boxes and keeps ≥10% — more candidates, more noise. Use Demo for the accurate live show.
