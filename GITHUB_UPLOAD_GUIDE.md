# GitHub 上傳與開源設定

## 建議 repo 名稱

`yolov13-surgical-instrument-assistant`

## 上傳前檢查

1. 確認沒有病人資料、員工資料、院內不可公開文件。
2. 若完整器械桌照片屬院內資料，公開前建議先移除影像，僅保留程式、CSV 範例與 README。
3. 保留 `README.md`、`LICENSE`、程式碼、CSV、YAML，方便老師看到完整流程。

## Git 指令

```bash
git init
git add README.md LICENSE .gitignore GITHUB_UPLOAD_GUIDE.md
git add yolo_adjust_app.py run_yolo_adjust.bat
git add build_*.py extract_selected_procedures.py
git add procedure_instrument_checklist.csv report_checklist_summary.csv selected_procedure_items.csv
git add instrument_yolo_dataset/data.yaml instrument_yolo_dataset/class_names.json instrument_yolo_dataset/display_names.csv
git add or_table_yolo_dataset/data.yaml or_table_yolo_dataset/procedure_mapping.csv or_table_yolo_dataset/class_merge_table.csv or_table_yolo_dataset/annotation_todo.csv
git commit -m "Initial open-source project for surgical instrument assistance"
git branch -M main
git remote add origin https://github.com/<your-account>/yolov13-surgical-instrument-assistant.git
git push -u origin main
```

## GitHub 網頁設定

1. 到 GitHub 建立 public repository。
2. Repository description 建議填：
   `YOLOv13-based surgical instrument recognition and procedure checklist assistance prototype.`
3. 勾選 Public。
4. 上傳後確認 README 可以正常顯示。

## 報告用說法

本專題程式碼將以 GitHub public repository 方式開放，內容包含標註工具、資料集結構、術式器械清單、YOLOv13 訓練設定與系統流程文件。因臨床影像涉及院內資料治理，公開版本會以去識別化或示範資料為主。
