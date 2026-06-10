完整器械桌 YOLO 資料集標註說明

資料來源：請將可公開或已授權的完整器械桌照片放在 sample_or_table_images，或以 OR_TABLE_IMAGE_ROOT 環境變數指定來源資料夾。
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
