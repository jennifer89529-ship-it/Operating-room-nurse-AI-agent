# YOLOv13 手術器械辨識與備物輔助系統

本專題以手術室器械桌影像為核心，建立一套「YOLOv13 影像辨識 + 術式標準器械清單比對」的半自動備物輔助流程。系統目標不是取代護理師點器械，而是在備物與術前確認階段提供影像輔助、清單比對與缺漏提醒。

## 展示術式

本次報告聚焦 3 個術式：

| 術式 | 科別 | 對應器械盤 | 器械項目數 |
|---|---|---|---:|
| 動靜脈血管吻合術（A-V shunt） | 心臟血管外科 | A-V Shunt Set | 26 |
| 人工血管置放術（Port-A） | 一般外科 | Suture Set + Towel clip | 14 |
| 白內障手術（Cataract） | 眼科 | Phaco Cata Set + Phaco Handpiece Set | 18 |

## 專題核心流程

1. 收集單支器械照片與完整器械桌照片。
2. 將器械照片前處理為 300 x 300 影像，建立 YOLO 標註資料。
3. 使用 YOLO Adjust 工具匯入圖片、框選器械、修正文字標籤，輸出 YOLO label。
4. 建立完整器械桌資料集，依 70/15/15 分成 train、val、test。
5. 依醫院器械明細建立術式標準器械清單。
6. 以 YOLOv13 作為明顯器械辨識工具，並與術式清單進行比對。
7. 輸出「已辨識、待確認、可能缺少」的備物輔助結果。

## 使用工具

- Python 3.13
- Ultralytics / YOLOv13
- OpenCV / Pillow
- openpyxl
- YOLO Adjust 半自動標註工具
- Excel 術式器械清單
- GitHub 開源版本控管

## 主要檔案

| 路徑 | 說明 |
|---|---|
| `yolo_adjust_app.py` | 半自動標註工具，可導入圖片、框選器械、修改 text、輸出 YOLO labels |
| `run_yolo_adjust.bat` | Windows 啟動檔 |
| `instrument_yolo_dataset/` | 單支器械 YOLO 資料集 |
| `or_table_yolo_dataset/` | 完整器械桌 YOLO 資料集 |
| `procedure_instrument_checklist_更正版.xlsx` | 三術式與完整清單整理後的 Excel |
| `procedure_instrument_checklist.csv` | 系統可讀的器械清單 |
| `selected_procedure_items.csv` | 本次展示三術式的器械項目 |
| `report_outputs/` | 報告 PPT、逐字稿與圖表素材 |

## 報告素材

`report_outputs/mosquito_small_curved_needle_holder_comparison.jpg` 為 Mosquito、Small curved、Needle holder 三種相似器械的外觀比較圖，用於說明模型可能混淆的原因，以及為什麼辨識結果仍需搭配術式清單與人工確認。

## YOLOv13 訓練範例

```bash
yolo detect train data=instrument_yolo_dataset/data.yaml model=yolov13n.pt imgsz=300 epochs=100
```

完整器械桌資料集可作為後續進階訓練或驗證：

```bash
yolo detect train data=or_table_yolo_dataset/data.yaml model=yolov13n.pt imgsz=640 epochs=100
```

## 臨床導入定位

完整器械桌影像有器械重疊、反光、尺寸小、拍攝角度不固定等限制，因此本專題採用半自動策略：

- YOLOv13：辨識明顯可見的器械類別。
- 術式清單：提供該術式應備器械與數量。
- 人工確認：針對重疊、遮蔽或不確定器械進行最後核對。

## 開源授權

本專題程式碼採 MIT License 開放。若資料集中包含醫院內部影像或清單，正式公開前應移除可識別病人、院內資訊與未授權影像，或改以示範資料集替代。
