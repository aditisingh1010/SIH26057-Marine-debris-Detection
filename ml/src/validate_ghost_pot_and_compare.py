import os

import json

import glob

import math

from pathlib import Path

import numpy as np

from PIL import Image



def validate_ghost_pot():

    raw_dir = Path("ml/data/raw/ghost_pot")

    splits = ["train", "valid", "test"]



    results = {

        "completeness": {},

        "file_counts": {},

        "disk_usage_mb": 0,

        "jsonl_status": {},

        "image_decoding": {},

        "dimensions": {},

        "formats": {},

        "annotations": {

            "total_boxes": 0,

            "boxes_per_split": {},

            "class_counts": {},

            "images_per_class": {},

            "background_images": {},

            "bbox_format": "[x_min, y_min, w, h] in absolute pixels",

            "out_of_bounds_boxes": 0,

            "non_positive_boxes": 0,

            "invalid_coords_details": []

        },

        "corrupt_files": [],

        "missing_images_on_disk": [],

        "missing_annotation_records": [],

        "duplicate_records": [],

        "intensity_contrast": {}

    }



    # Calculate disk usage & total files

    total_bytes = 0

    total_files_count = 0

    for root, dirs, files in os.walk(raw_dir):

        for f in files:

            total_files_count += 1

            total_bytes += os.path.getsize(os.path.join(root, f))

    results["disk_usage_mb"] = round(total_bytes / (1024 * 1024), 2)

    results["total_files_in_dir"] = total_files_count



    all_class_names = set()

    total_images_all_splits = 0



    for split in splits:

        sdir = raw_dir / split

        if not sdir.exists():

            print(f"Directory {sdir} does not exist!")

            continue



        jsonl_path = sdir / "metadata.jsonl"

        images_on_disk = {f.name: f for f in sdir.glob("*.jpg")}



        results["file_counts"][split] = {

            "images_on_disk": len(images_on_disk),

            "jsonl_exists": jsonl_path.exists()

        }

        total_images_all_splits += len(images_on_disk)



        # Parse JSONL

        records_by_filename = {}

        jsonl_lines = 0

        duplicate_in_split = []



        if jsonl_path.exists():

            with open(jsonl_path, "r", encoding="utf-8") as f:

                for line_idx, line in enumerate(f):

                    line = line.strip()

                    if not line:

                        continue

                    jsonl_lines += 1

                    try:

                        data = json.loads(line)

                        fname = data.get("file_name")

                        if fname in records_by_filename:

                            duplicate_in_split.append((split, fname))

                        records_by_filename[fname] = data

                    except json.JSONDecodeError as e:

                        print(f"Error parsing line {line_idx} in {jsonl_path}: {e}")



        results["jsonl_status"][split] = {

            "total_lines": jsonl_lines,

            "unique_records": len(records_by_filename),

            "duplicates": len(duplicate_in_split)

        }

        if duplicate_in_split:

            results["duplicate_records"].extend(duplicate_in_split)



        # Check matching

        jsonl_fnames = set(records_by_filename.keys())

        disk_fnames = set(images_on_disk.keys())



        missing_on_disk = jsonl_fnames - disk_fnames

        missing_in_jsonl = disk_fnames - jsonl_fnames



        if missing_on_disk:

            results["missing_images_on_disk"].extend([(split, fn) for fn in missing_on_disk])

        if missing_in_jsonl:

            results["missing_annotation_records"].extend([(split, fn) for fn in missing_in_jsonl])



        # Validate images and annotations

        split_boxes = 0

        split_class_counts = {}

        split_images_per_class = {}

        split_background_images = 0



        dims_list = []

        formats_set = set()



        means = []

        stds = []



        for fname, img_path in images_on_disk.items():

            # Check decode

            try:

                with Image.open(img_path) as img:

                    img.verify()

                # Re-open for properties & numpy array

                with Image.open(img_path) as img:

                    w, h = img.size

                    mode = img.mode

                    fmt = img.format or "JPEG"

                    formats_set.add((fmt, mode))

                    dims_list.append((w, h))



                    # Convert to grayscale numpy array for intensity & contrast

                    gray_img = img.convert("L")

                    arr = np.array(gray_img, dtype=np.float32)

                    means.append(float(np.mean(arr)))

                    stds.append(float(np.std(arr)))



            except Exception as e:

                results["corrupt_files"].append((split, fname, str(e)))

                continue



            # Annotation check for this image

            rec = records_by_filename.get(fname)

            if not rec:

                split_background_images += 1

                continue



            objs = rec.get("objects", {})

            bboxes = objs.get("bbox", [])

            categories = objs.get("category", [])



            if not bboxes:

                split_background_images += 1

            else:

                seen_classes_in_img = set()

                for bbox, cat in zip(bboxes, categories):

                    all_class_names.add(cat)

                    split_boxes += 1

                    results["annotations"]["total_boxes"] += 1



                    split_class_counts[cat] = split_class_counts.get(cat, 0) + 1

                    results["annotations"]["class_counts"][cat] = results["annotations"]["class_counts"].get(cat, 0) + 1

                    seen_classes_in_img.add(cat)



                    # Validate box bounds: [x_min, y_min, w, h]

                    x, y, bw, bh = bbox

                    if bw <= 0 or bh <= 0:

                        results["annotations"]["non_positive_boxes"] += 1

                        results["annotations"]["invalid_coords_details"].append((split, fname, bbox, "non-positive size"))

                    if x < 0 or y < 0 or (x + bw) > w + 1e-2 or (y + bh) > h + 1e-2:

                        results["annotations"]["out_of_bounds_boxes"] += 1

                        results["annotations"]["invalid_coords_details"].append((split, fname, bbox, f"out of bounds for img {w}x{h}"))



                for cat in seen_classes_in_img:

                    split_images_per_class[cat] = split_images_per_class.get(cat, 0) + 1

                    results["annotations"]["images_per_class"][cat] = results["annotations"]["images_per_class"].get(cat, 0) + 1



        results["annotations"]["boxes_per_split"][split] = split_boxes

        results["annotations"]["background_images"][split] = split_background_images

        results["image_decoding"][split] = {

            "total_checked": len(images_on_disk),

            "successfully_decoded": len(dims_list),

            "corrupt_count": len(images_on_disk) - len(dims_list)

        }



        unique_dims = sorted(list(set(dims_list)))

        results["dimensions"][split] = {

            "unique_shapes_w_h": unique_dims,

            "min_w": min(d[0] for d in dims_list) if dims_list else 0,

            "max_w": max(d[0] for d in dims_list) if dims_list else 0,

            "min_h": min(d[1] for d in dims_list) if dims_list else 0,

            "max_h": max(d[1] for d in dims_list) if dims_list else 0,

        }

        results["formats"][split] = [f"{fmt}/{mode}" for fmt, mode in formats_set]

        results["intensity_contrast"][split] = {

            "mean_intensity": round(float(np.mean(means)), 2) if means else 0,

            "mean_contrast_std": round(float(np.mean(stds)), 2) if stds else 0

        }



    results["all_detected_classes"] = list(all_class_names)

    results["total_images_all_splits"] = total_images_all_splits

    return results



def inspect_existing_dataset():

    dataset_dir = Path("Dataset")

    subdirs = ["2010", "2018"]



    total_images = 0

    labeled_images = 0

    background_images = 0

    total_boxes = 0

    class_counts = {}

    dims_list = []

    means = []

    stds = []



    for sub in subdirs:

        spath = dataset_dir / sub

        if not spath.exists():

            continue

        img_files = list(spath.glob("*.png")) + list(spath.glob("*.jpg")) + list(spath.glob("*.tif")) + list(spath.glob("*.bmp"))

        for img_path in img_files:

            total_images += 1

            txt_path = img_path.with_suffix(".txt")



            try:

                with Image.open(img_path) as img:

                    w, h = img.size

                    dims_list.append((w, h))

                    gray_img = img.convert("L")

                    arr = np.array(gray_img, dtype=np.float32)

                    means.append(float(np.mean(arr)))

                    stds.append(float(np.std(arr)))

            except Exception as e:

                print(f"Error opening existing dataset image {img_path}: {e}")



            has_label = False

            if txt_path.exists():

                with open(txt_path, "r", encoding="utf-8") as f:

                    lines = [l.strip() for l in f if l.strip()]

                    if lines:

                        has_label = True

                        for l in lines:

                            parts = l.split()

                            if parts:

                                cid = parts[0]

                                class_counts[cid] = class_counts.get(cid, 0) + 1

                                total_boxes += 1

            if has_label:

                labeled_images += 1

            else:

                background_images += 1



    unique_dims = sorted(list(set(dims_list)))

    return {

        "total_images": total_images,

        "labeled_images": labeled_images,

        "background_images": background_images,

        "total_boxes": total_boxes,

        "class_counts": class_counts,

        "unique_shapes_w_h": unique_dims,

        "mean_intensity": round(float(np.mean(means)), 2) if means else 0,

        "mean_contrast_std": round(float(np.mean(stds)), 2) if stds else 0

    }



if __name__ == "__main__":

    print("Running Ghost Pot validation...")

    gp_res = validate_ghost_pot()

    print("Running Existing Dataset audit...")

    ex_res = inspect_existing_dataset()



    full_output = {

        "ghost_pot": gp_res,

        "existing_dataset": ex_res

    }



    with open("ml/data/ghost_pot_validation_results.json", "w", encoding="utf-8") as f:

        json.dump(full_output, f, indent=2)



    print("DONE! Saved results to ml/data/ghost_pot_validation_results.json")
