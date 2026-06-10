from __future__ import annotations

import csv
import json
import math
import re
import shutil
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageOps


SOURCE_DIR = Path("D:/\u5668\u68b0\u5716")
EXCEL_PATH = SOURCE_DIR / "\u5668\u68b0\u6e05\u55ae.xlsx"
OUTPUT_DIR = Path("instrument_yolo_dataset")
IMAGE_SIZE = (300, 300)
MIN_COMPONENT_AREA = 25


def clean_text(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def safe_stem(value) -> str:
    text = clean_text(value)
    if not text:
        return ""
    if text.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")):
        return Path(text).stem
    if re.fullmatch(r"\d+(\.0)?", text):
        return str(int(float(text)))
    return Path(text).stem


def find_image(stem: str) -> Path | None:
    for ext in [".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG", ".bmp", ".webp"]:
        path = SOURCE_DIR / f"{stem}{ext}"
        if path.exists():
            return path
    return None


def preprocess_image(path: Path) -> Image.Image:
    try:
        resampling = Image.Resampling.LANCZOS
    except AttributeError:
        resampling = Image.LANCZOS
    image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return image.resize(IMAGE_SIZE, resampling)


def connected_components(mask: np.ndarray) -> list[tuple[int, int, int, int, int]]:
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    components: list[tuple[int, int, int, int, int]] = []
    for y in range(height):
        for x in range(width):
            if not mask[y, x] or visited[y, x]:
                continue
            stack = [(x, y)]
            visited[y, x] = True
            min_x = max_x = x
            min_y = max_y = y
            area = 0
            while stack:
                cx, cy = stack.pop()
                area += 1
                min_x = min(min_x, cx)
                max_x = max(max_x, cx)
                min_y = min(min_y, cy)
                max_y = max(max_y, cy)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < width and 0 <= ny < height and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((nx, ny))
            if area >= MIN_COMPONENT_AREA:
                components.append((min_x, min_y, max_x, max_y, area))
    return components


def dilate_mask(mask: np.ndarray, iterations: int = 2) -> np.ndarray:
    result = mask.copy()
    for _ in range(iterations):
        padded = np.pad(result, 1, mode="constant", constant_values=False)
        result = (
            padded[1:-1, 1:-1]
            | padded[:-2, 1:-1]
            | padded[2:, 1:-1]
            | padded[1:-1, :-2]
            | padded[1:-1, 2:]
            | padded[:-2, :-2]
            | padded[:-2, 2:]
            | padded[2:, :-2]
            | padded[2:, 2:]
        )
    return result


def estimate_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    arr = np.asarray(image).astype(np.int16)
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    maxc = arr.max(axis=2)
    minc = arr.min(axis=2)
    chroma = maxc - minc

    # The images are mostly surgical instruments on green cloth. Keep pixels
    # that do not look like the green background, then suppress bright neutral
    # ruler-like regions so the box focuses on the instrument where possible.
    green_bg = (g > 70) & (g > r * 1.12) & (g > b * 1.05)
    bright_neutral = (maxc > 150) & (chroma < 45)
    dark_mark = (maxc < 95) & (chroma < 55)
    mask = (~green_bg) & (~bright_neutral | dark_mark)

    components = connected_components(dilate_mask(mask, iterations=2))
    if not components:
        return 0, 0, IMAGE_SIZE[0] - 1, IMAGE_SIZE[1] - 1

    kept: list[tuple[int, int, int, int, int]] = []
    for min_x, min_y, max_x, max_y, area in components:
        width = max_x - min_x + 1
        height = max_y - min_y + 1
        if width < 5 or height < 5:
            continue
        crop = arr[min_y : max_y + 1, min_x : max_x + 1]
        mean_v = float(crop.max(axis=2).mean())
        mean_chroma = float((crop.max(axis=2) - crop.min(axis=2)).mean())
        long_ratio = max(width / max(height, 1), height / max(width, 1))
        if mean_v > 155 and mean_chroma < 35 and long_ratio > 3.0:
            continue
        kept.append((min_x, min_y, max_x, max_y, area))

    if not kept:
        kept = sorted(components, key=lambda c: c[4], reverse=True)[:2]

    min_x = min(c[0] for c in kept)
    min_y = min(c[1] for c in kept)
    max_x = max(c[2] for c in kept)
    max_y = max(c[3] for c in kept)
    pad = 5
    return (
        max(0, min_x - pad),
        max(0, min_y - pad),
        min(IMAGE_SIZE[0] - 1, max_x + pad),
        min(IMAGE_SIZE[1] - 1, max_y + pad),
    )


def yolo_line(class_id: int, bbox: tuple[int, int, int, int]) -> str:
    x1, y1, x2, y2 = bbox
    width, height = IMAGE_SIZE
    box_w = max(1, x2 - x1 + 1)
    box_h = max(1, y2 - y1 + 1)
    x_center = (x1 + box_w / 2) / width
    y_center = (y1 + box_h / 2) / height
    return f"{class_id} {x_center:.6f} {y_center:.6f} {box_w / width:.6f} {box_h / height:.6f}"


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def main() -> None:
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(EXCEL_PATH)

    images_dir = OUTPUT_DIR / "images" / "train"
    labels_dir = OUTPUT_DIR / "labels" / "train"
    previews_dir = OUTPUT_DIR / "previews"
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)
    previews_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(EXCEL_PATH)
    class_ids: OrderedDict[str, int] = OrderedDict()
    rows = []
    missing = []

    for _, row in df.iterrows():
        stem = safe_stem(row.get("照片名稱"))
        name = clean_text(row.get("器械名稱"))
        department = clean_text(row.get("科別"))
        purpose = clean_text(row.get("用途"))
        if not stem or not name:
            continue
        source_image = find_image(stem)
        if source_image is None:
            missing.append({"照片名稱": stem, "器械名稱": name})
            continue
        if name not in class_ids:
            class_ids[name] = len(class_ids)

        class_id = class_ids[name]
        image = preprocess_image(source_image)
        bbox = estimate_bbox(image)
        output_stem = f"{int(stem):03d}" if stem.isdigit() else stem
        image_path = images_dir / f"{output_stem}.jpg"
        label_path = labels_dir / f"{output_stem}.txt"
        preview_path = previews_dir / f"{output_stem}.jpg"

        image.save(image_path, quality=92)
        label_path.write_text(yolo_line(class_id, bbox) + "\n", encoding="utf-8")

        preview = image.copy()
        draw = ImageDraw.Draw(preview)
        draw.rectangle(bbox, outline=(220, 30, 30), width=3)
        draw.text((bbox[0], max(0, bbox[1] - 12)), f"{class_id} {name}", fill=(220, 30, 30))
        preview.save(preview_path, quality=92)

        rows.append(
            {
                "source_file": source_image.name,
                "output_image": str(image_path),
                "output_label": str(label_path),
                "class_id": class_id,
                "class_name": name,
                "department": department,
                "purpose": purpose,
                "bbox_x1": bbox[0],
                "bbox_y1": bbox[1],
                "bbox_x2": bbox[2],
                "bbox_y2": bbox[3],
            }
        )

    names_path = OUTPUT_DIR / "class_names.json"
    names_path.write_text(json.dumps(class_ids, ensure_ascii=False, indent=2), encoding="utf-8")

    data_yaml = OUTPUT_DIR / "data.yaml"
    data_yaml.write_text(
        "\n".join(
            [
                f"path: {OUTPUT_DIR.resolve()}",
                "train: images/train",
                "val: images/train",
                "names:",
                *[f"  {class_id}: {yaml_quote(name)}" for name, class_id in class_ids.items()],
                "",
            ]
        ),
        encoding="utf-8",
    )

    with (OUTPUT_DIR / "annotation_report.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["source_file"])
        writer.writeheader()
        writer.writerows(rows)

    if missing:
        with (OUTPUT_DIR / "missing_images.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=["照片名稱", "器械名稱"])
            writer.writeheader()
            writer.writerows(missing)

    print(json.dumps({"rows": len(rows), "classes": len(class_ids), "missing": len(missing)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
