import os

import json

import shutil

from pathlib import Path

from PIL import Image



CLASS_MAPPING = {

    "Crab-Pot": 0

}



def convert_dataset():

    raw_root = Path("ml/data/raw/ghost_pot")

    processed_root = Path("ml/data/processed/ghost_pot")



    # Split map: raw_split -> processed_split

    split_map = {

        "train": "train",

        "valid": "val",

        "test": "test"

    }



    # Ensure processed directory structure

    for p_split in split_map.values():

        (processed_root / "images" / p_split).mkdir(parents=True, exist_ok=True)

        (processed_root / "labels" / p_split).mkdir(parents=True, exist_ok=True)



    stats = {

        "images_copied": 0,

        "images_per_split": {"train": 0, "val": 0, "test": 0},

        "total_boxes_read": 0,

        "total_boxes_written": 0,

        "clipped_boxes": 0,

        "invalid_boxes": 0,

        "class_counts": {},

        "background_images": {"train": 0, "val": 0, "test": 0},

        "missing_images": 0,

        "duplicate_mappings": 0,

        "label_files_created": 0

    }



    all_processed_image_stems = set()



    for raw_split, p_split in split_map.items():

        sdir = raw_root / raw_split

        if not sdir.exists():

            print(f"Warning: Raw split directory {sdir} does not exist!")

            continue



        jsonl_path = sdir / "metadata.jsonl"

        records = {}

        if jsonl_path.exists():

            with open(jsonl_path, "r", encoding="utf-8") as f:

                for line in f:

                    line = line.strip()

                    if not line:

                        continue

                    data = json.loads(line)

                    fname = data.get("file_name")

                    if fname in records:

                        stats["duplicate_mappings"] += 1

                    records[fname] = data



        images_on_disk = list(sdir.glob("*.jpg"))

        print(f"Processing split '{raw_split}' -> '{p_split}': {len(images_on_disk)} images found.")



        for img_path in images_on_disk:

            fname = img_path.name

            stem = img_path.stem



            if stem in all_processed_image_stems:

                stats["duplicate_mappings"] += 1

            all_processed_image_stems.add(stem)



            # Destination paths

            dest_img = processed_root / "images" / p_split / fname

            dest_label = processed_root / "labels" / p_split / f"{stem}.txt"



            # Copy image file

            shutil.copy2(img_path, dest_img)

            stats["images_copied"] += 1

            stats["images_per_split"][p_split] += 1



            # Read image dimensions to ensure exact W, H

            with Image.open(img_path) as img:

                img_w, img_h = img.size



            rec = records.get(fname)

            if not rec:

                stats["missing_images"] += 1  # Record missing in jsonl

                # Create empty label file for background image

                with open(dest_label, "w", encoding="utf-8") as lf:

                    pass

                stats["label_files_created"] += 1

                stats["background_images"][p_split] += 1

                continue



            objs = rec.get("objects", {})

            bboxes = objs.get("bbox", [])

            categories = objs.get("category", [])



            yolo_lines = []



            if not bboxes:

                stats["background_images"][p_split] += 1

            else:

                for bbox, cat in zip(bboxes, categories):

                    stats["total_boxes_read"] += 1

                    if cat not in CLASS_MAPPING:

                        print(f"Unexpected category '{cat}' in {fname}")

                        stats["invalid_boxes"] += 1

                        continue



                    cid = CLASS_MAPPING[cat]

                    stats["class_counts"][cat] = stats["class_counts"].get(cat, 0) + 1



                    x_min, y_min, bw, bh = bbox

                    x_max = x_min + bw

                    y_max = y_min + bh



                    # Check if clipping is needed

                    clipped = False

                    cx_min = max(0.0, min(float(img_w), float(x_min)))

                    cy_min = max(0.0, min(float(img_h), float(y_min)))

                    cx_max = max(0.0, min(float(img_w), float(x_max)))

                    cy_max = max(0.0, min(float(img_h), float(y_max)))



                    if abs(cx_min - x_min) > 1e-4 or abs(cy_min - y_min) > 1e-4 or abs(cx_max - x_max) > 1e-4 or abs(cy_max - y_max) > 1e-4:

                        clipped = True

                        stats["clipped_boxes"] += 1



                    cbw = cx_max - cx_min

                    cbh = cy_max - cy_min



                    if cbw <= 0 or cbh <= 0:

                        stats["invalid_boxes"] += 1

                        continue



                    # Calculate normalized center & dimensions

                    x_center = (cx_min + cx_max) / (2.0 * img_w)

                    y_center = (cy_min + cy_max) / (2.0 * img_h)

                    norm_w = cbw / img_w

                    norm_h = cbh / img_h



                    # Validate ranges [0, 1]

                    if not (0.0 <= x_center <= 1.0 and 0.0 <= y_center <= 1.0 and 0.0 < norm_w <= 1.0 and 0.0 < norm_h <= 1.0):

                        print(f"Invalid normalized coordinates in {fname}: {x_center}, {y_center}, {norm_w}, {norm_h}")

                        stats["invalid_boxes"] += 1

                        continue



                    yolo_lines.append(f"{cid} {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}")

                    stats["total_boxes_written"] += 1



            # Write label file

            with open(dest_label, "w", encoding="utf-8") as lf:

                if yolo_lines:

                    lf.write("\n".join(yolo_lines) + "\n")

            stats["label_files_created"] += 1



    # Write dataset YAML

    yaml_content = f"""# Ghost Pot YOLO Dataset Configuration

path: ml/data/processed/ghost_pot

train: images/train

val: images/val

test: images/test



nc: 1

names:

  0: crab_pot

"""

    yaml_path = processed_root / "data.yaml"

    with open(yaml_path, "w", encoding="utf-8") as yf:

        yf.write(yaml_content)



    print("Dataset conversion completed successfully!")

    return stats



if __name__ == "__main__":

    s = convert_dataset()

    print("\n--- CONVERSION SUMMARY ---")

    print(json.dumps(s, indent=2))
