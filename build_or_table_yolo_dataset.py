import csv
import os
import shutil
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OR_BASE = Path(os.environ.get("OR_TABLE_IMAGE_ROOT", ROOT / "sample_or_table_images"))
OUT = ROOT / "or_table_yolo_dataset"

PROCEDURES = [
    (1, "PTA周邊動靜脈血管整形術", "心臟血管外科", "S__107593747_0.jpg", "train"),
    (2, "口腔腫瘤切除（Oral tumor excision）", "口腔外科", "S__107593748_0.jpg", "train"),
    (3, "白內障手術（Cataract）", "眼科", "S__107593749_0.jpg", "train"),
    (4, "人工血管置放術（Port-A）", "一般外科", "S__107593750_0.jpg", "train"),
    (5, "肛門膿瘍切開術", "大腸直腸外科", "S__107593751_0.jpg", "train"),
    (6, "子宮肌瘤切除術（基本器械組）", "婦產科", "S__107593752_0.jpg", "train"),
    (7, "子宮肌瘤切除術（完整器械組）", "婦產科", "S__107593753_0.jpg", "train"),
    (8, "子宮肌瘤切除術（含 self-retractor）", "婦產科", "S__107593754_0.jpg", "val"),
    (9, "子宮肌瘤切除術（含 self-retractor 進階）", "婦產科", "S__107593755_0.jpg", "val"),
    (10, "動靜脈血管吻合術（A-V shunt）", "心臟血管外科", "S__107593757.jpg", "test"),
]

CLASSES = [
    (0, "hemostatic_forceps", "止血鉗"),
    (1, "forceps", "鑷子"),
    (2, "needle_holder", "持針器"),
    (3, "scissors", "手術剪"),
    (4, "retractor", "撐開器"),
    (5, "clamp", "夾鉗"),
    (6, "scalpel_handle", "刀柄"),
    (7, "suction_tube", "吸引管或管路"),
    (8, "basin_bowl", "彎盆或碗盤"),
    (9, "needle_probe", "探針或針類"),
    (10, "other", "其他"),
]


def find_source_dir() -> Path:
    first_name = PROCEDURES[0][3]
    for candidate in OR_BASE.iterdir():
        if candidate.is_dir() and (candidate / first_name).exists():
            return candidate
    raise FileNotFoundError(f"Cannot find OR table image folder containing {first_name}")


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)


def make_contact_sheet(copied: list[tuple[int, str, str, str, str, str]]) -> Path:
    thumb_w, thumb_h = 360, 270
    label_h = 64
    cols = 2
    rows_n = (len(copied) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows_n * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msjh.ttc", 14)
    except Exception:
        font = ImageFont.load_default()

    for i, (idx, proc, _dept, _source, split, dst_name) in enumerate(copied):
        img_path = OUT / "images" / split / dst_name
        img = Image.open(img_path).convert("RGB")
        img.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = (i % cols) * thumb_w
        y = (i // cols) * (thumb_h + label_h)
        sheet.paste(img, (x + (thumb_w - img.width) // 2, y + 4))
        draw.rectangle([x, y, x + thumb_w - 1, y + thumb_h + label_h - 1], outline=(190, 190, 190))
        draw.text((x + 8, y + thumb_h + 6), f"{idx:02d} {split}  {dst_name}", fill=(0, 0, 0), font=font)
        draw.text((x + 8, y + thumb_h + 30), proc, fill=(0, 0, 0), font=font)

    path = OUT / "previews" / "or_table_contact_sheet.jpg"
    sheet.save(path, quality=92)
    return path


def main() -> None:
    src = find_source_dir()
    if OUT.exists():
        shutil.rmtree(OUT)
    for split in ["train", "val", "test"]:
        (OUT / "images" / split).mkdir(parents=True, exist_ok=True)
        (OUT / "labels" / split).mkdir(parents=True, exist_ok=True)
    (OUT / "previews").mkdir(parents=True, exist_ok=True)

    copied = []
    for idx, proc, dept, filename, split in PROCEDURES:
        src_file = src / filename
        dst_name = f"or_table_{idx:02d}{src_file.suffix.lower()}"
        dst_file = OUT / "images" / split / dst_name
        shutil.copy2(src_file, dst_file)
        copied.append((idx, proc, dept, filename, split, dst_name))

    write_csv(
        OUT / "procedure_mapping.csv",
        ["index", "procedure", "department", "source_file", "split", "dataset_image", "note"],
        [[*row, "依 Word 文件術式分組整理，待逐張框選器械"] for row in copied],
    )

    write_csv(
        OUT / "class_merge_table.csv",
        ["class_id", "english_name", "chinese_name", "display_name"],
        [[cid, en, zh, f"{zh} / {en}"] for cid, en, zh in CLASSES],
    )

    suggested = "; ".join([en for _cid, en, _zh in CLASSES])
    write_csv(
        OUT / "annotation_todo.csv",
        ["index", "split", "dataset_image", "procedure", "department", "annotation_status", "suggested_classes", "notes"],
        [[idx, split, dst_name, proc, dept, "todo", suggested, "先標主要手術器械；尺、背景、布單不要框"] for idx, proc, dept, _filename, split, dst_name in copied],
    )

    data_yaml = "\n".join(
        [
            "path: or_table_yolo_dataset",
            "train: images/train",
            "val: images/val",
            "test: images/test",
            "",
            "names:",
            *[f"  {cid}: {en}" for cid, en, _zh in CLASSES],
            "",
            "display_names:",
            *[f"  {cid}: {zh} / {en}" for cid, en, zh in CLASSES],
            "",
        ]
    )
    (OUT / "data.yaml").write_text(data_yaml, encoding="utf-8-sig")

    readme = """完整器械桌 YOLO 資料集標註說明

資料來源：請使用可公開或已授權的完整器械桌照片，並以 OR_TABLE_IMAGE_ROOT 指定來源資料夾。
依據：YOLOv13_手術器械辨識與備物輔助系統設計_完整版.docx 的 10 張術式器械桌分組

目前狀態：
1. 圖片已依 70/15/15 分成 train/val/test。
2. labels 目錄已建立，但尚未放入標註檔。請不要把空 txt 當成完成標註。
3. annotation_todo.csv 是逐張標註清單。
4. class_merge_table.csv 是建議先用的合併類別，適合 20 分鐘專案報告與 prototype。

建議標註規則：
1. 只框器械本體，不框尺、布單、桌面、手套或背景。
2. 框要貼近器械外緣，可以包含器械孔洞中間的空白，但不要大範圍包到旁邊器械。
3. 同一張桌上相同器械要一個一個框，不要用一個大框包整排。
4. 中文顯示用 display_name，YOLO 訓練仍以英文 class name 為主。
5. 若器械不確定，先標 other，報告時說明為待專家校正。

下一步：
1. 用 yolo_adjust_app.py 匯入 images/train、images/val、images/test 裡的圖片。
2. 逐張框選器械並選擇類別。
3. 匯出 YOLO labels 到對應 labels/train、labels/val、labels/test。
4. 完成後再執行 yolo train data=or_table_yolo_dataset/data.yaml。
"""
    (OUT / "README_標註說明.txt").write_text(readme, encoding="utf-8-sig")

    sheet_path = make_contact_sheet(copied)

    zip_path = ROOT / "or_table_yolo_dataset.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in OUT.rglob("*"):
            archive.write(path, path.relative_to(ROOT))

    print(f"source={src}")
    print(f"dataset={OUT}")
    print(f"contact_sheet={sheet_path}")
    print(f"zip={zip_path}")
    print(f"images={len(copied)}")


if __name__ == "__main__":
    main()
