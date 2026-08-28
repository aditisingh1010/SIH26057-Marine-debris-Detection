# Ghost Pot Dataset Inspection

**Status: PARTIAL / BLOCKED (2026-08-28)**

## Source and download state

- Dataset: `PINGEcosystem/sss-crab-pot-detection-ds`
- Hugging Face revision observed: `b6a36ec00c9bb0070f30be4c1dd6cbe139423cd4`
- Storage target: `ml/data/raw/sss-crab-pot-detection-ds/` (ignored by Git)
- Repository metadata is public, but the image assets are gated (`401 Unauthorized`) without a local Hugging Face access token.
- The local Hugging Face client has no saved token. The attempted download left only the dataset card and Hugging Face cache metadata; it did not download raw sonar images or annotations.

## Available source metadata

The dataset card reports:

- 6,674 JPG images: 5,721 train, 555 valid, and 398 test (the repository contains 6,680 files including metadata files)
- Consumer-grade Humminbird side-scan sonar
- Delaware Inland Bays and Delaware Bay, shallow/turbid-water surveys
- JSON Lines (`metadata.jsonl`) annotations with one record per image
- Axis-aligned pixel boxes encoded as `[x, y, width, height]`
- Classes: `Crab-Pot` and `Maybe-Crab-Pot`
- Split directories named `train/`, `valid/`, and `test/`

The source metadata advertises an `image` / `objects` schema where `objects` contains `bbox`, `category`, and `area`. It also contains conflicting license text: front matter says `cc-by-sa-4.0`, while the bottom of the card says GPL. Resolve the license with the dataset owner before redistribution or production use.

## Existing SIH26057 dataset baseline

The existing `Dataset/` was inspected without modification:

| Property | Observed value |
| --- | ---: |
| Images | 909 JPG files |
| Image/label matching | 909/909 images have a same-stem TXT label; no extra TXT labels |
| Image sizes | 450 at 416x416; 459 at 1024x1024 |
| Aspect ratio | 1:1 for every image |
| Annotation format | YOLO TXT (`class x_center y_center width height`) |
| Total boxes | 176 |
| Empty label files | 769 |
| Class-id box counts | `0`: 118; `1`: 58 |
| Mean grayscale intensity (per-image mean) | 46.58/255 |
| Mean grayscale standard deviation | 36.02/255 |

The class IDs are intentionally retained as `debris_0` and `debris_1`. The available annotations do not establish a mapping to named debris types.

## Compatibility assessment

Both collections are side-scan-sonar object-detection data, and the Ghost Pot source is especially relevant because it uses consumer-grade Humminbird hardware. However, compatibility is **not yet established**. The required direct comparison cannot be completed until the gated assets are available locally.

Known differences:

- The baseline uses YOLO TXT labels with two unknown `debris_*` classes; Ghost Pot uses JSONL `[x, y, width, height]` boxes with named confidence-oriented crab-pot classes.
- The baseline mixes 416x416 and 1024x1024 images. Ghost Pot dimensions, aspect ratios, intensity distributions, swath layouts, acoustic shadows, and crop/mosaic conventions remain unverified.
- Ghost Pot's narrowly defined crab-pot target semantics should not be merged into `debris_0` or `debris_1` without a documented label-mapping decision and annotation review.

## Required next action

Authenticate the local client with an approved Hugging Face **read** token, for example:

```powershell
ml\.venv-hf\Scripts\hf auth login
```

Then re-run the download into the same ignored raw directory and inspect all JSONL files and samples before choosing between fine-tuning, combined training, or separate-domain models. Do not train, overwrite `best.pt`, convert labels, or merge datasets until that inspection is complete.
