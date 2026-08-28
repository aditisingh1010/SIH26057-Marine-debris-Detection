import os

import yaml

from pathlib import Path



def audit_yolo_dataset():

    proc_root = Path("ml/data/processed/ghost_pot")

    yaml_file = proc_root / "data.yaml"



    assert yaml_file.exists(), f"{yaml_file} does not exist!"



    with open(yaml_file, "r", encoding="utf-8") as f:

        data_cfg = yaml.safe_load(f)



    print("YAML config content:")

    print(data_cfg)



    splits = ["train", "val", "test"]

    expected_counts = {"train": 5721, "val": 555, "test": 398}



    total_images = 0

    total_labels = 0

    total_yolo_boxes = 0

    invalid_labels = 0

    missing_labels = 0

    missing_images = 0

    class_id_counts = {}



    for split in splits:

        img_dir = proc_root / "images" / split

        lbl_dir = proc_root / "labels" / split



        img_files = {f.stem: f for f in img_dir.glob("*.jpg")}

        lbl_files = {f.stem: f for f in lbl_dir.glob("*.txt")}



        assert len(img_files) == expected_counts[split], f"Expected {expected_counts[split]} images in {split}, got {len(img_files)}"

        assert len(lbl_files) == expected_counts[split], f"Expected {expected_counts[split]} labels in {split}, got {len(lbl_files)}"



        total_images += len(img_files)

        total_labels += len(lbl_files)



        # Check matching

        img_stems = set(img_files.keys())

        lbl_stems = set(lbl_files.keys())



        if img_stems != lbl_stems:

            missing_labels += len(img_stems - lbl_stems)

            missing_images += len(lbl_stems - img_stems)



        for stem, lpath in lbl_files.items():

            with open(lpath, "r", encoding="utf-8") as lf:

                lines = [line.strip() for line in lf if line.strip()]

                for line in lines:

                    parts = line.split()

                    if len(parts) != 5:

                        invalid_labels += 1

                        continue

                    try:

                        cid = int(parts[0])

                        cx = float(parts[1])

                        cy = float(parts[2])

                        w = float(parts[3])

                        h = float(parts[4])



                        class_id_counts[cid] = class_id_counts.get(cid, 0) + 1



                        if not (0.0 <= cx <= 1.0 and 0.0 <= cy <= 1.0 and 0.0 < w <= 1.0 and 0.0 < h <= 1.0):

                            invalid_labels += 1

                        else:

                            total_yolo_boxes += 1

                    except ValueError:

                        invalid_labels += 1



    print("\n--- AUDIT RESULTS ---")

    print(f"Total Images: {total_images} (expected 6,674)")

    print(f"Total Label Files: {total_labels} (expected 6,674)")

    print(f"Total YOLO Bounding Boxes: {total_yolo_boxes} (expected 9,311)")

    print(f"Invalid Labels: {invalid_labels} (expected 0)")

    print(f"Missing Labels: {missing_labels} (expected 0)")

    print(f"Missing Images: {missing_images} (expected 0)")

    print(f"Class ID Distribution: {class_id_counts}")



    assert total_images == 6674

    assert total_labels == 6674

    assert total_yolo_boxes == 9311

    assert invalid_labels == 0

    assert missing_labels == 0

    assert missing_images == 0

    print("ALL AUDIT ASSERTS PASSED PERFECTLY!")



if __name__ == "__main__":

    audit_yolo_dataset()
