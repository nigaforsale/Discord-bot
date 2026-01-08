# Python Discord bot 

> 這是一個基於 Python 與 discord.py 開發的多功能 Discord 機器人。它整合了 客服單系統、網路查詢工具、伺服器管理功能。
> 專案採用模組化設計，具備完善的錯誤處理與日誌記錄功能。

## 安裝與執行

1.環境需求
-    Python 3.8 或以上版本

2.下載專案
-    ```git clone https://github.com/nigaforsale/Discord-bot.git```

3.安裝依賴套件
-    ```pip install -r requirements.txt```

4.設定環境變數 (.env)
> 請在專案根目錄建立一個名為 .env 的檔案，並填入以下內容：
-    您的機器人 Token  
>     ```DISCORD_TOKEN=Your_Discord_Bot_Token``` 
-    用於接收報錯日誌的 Webhook URL
>     ```LOG_WEBHOOK_URL=Your_Webhook_URL``` 

5.啟動機器人
-    ```python bot.py```

## 注意事項
- 權限設定：請確保機器人在 Discord 伺服器中擁有 Manage Channels (管理頻道) 與 Manage Messages (管理訊息) 的權限，否則客服單與刪除訊息功能將無法運作。

- 安全性：絕對不要將 .env 檔案上傳到 GitHub 或分享給他人。

- API 限制：IP 查詢功能使用 ip-api.com 的免費端點，請勿在短時間內大量頻繁請求，以免被封鎖。

## 主要功能

### 客服單系統 (Ticket System)

- 一鍵開單：透過按鈕 (Button) 快速建立私密客服頻道。

- 自動權限管理：只有開單者與管理員能看到頻道。

- 對話紀錄歸檔：關閉客服單時，自動將對話紀錄存為 .txt 檔案。

- 紀錄發送：自動將對話紀錄副本私訊給開單者留存。

- 持久化按鈕：機器人重啟後，面板上的按鈕依然有效。

### 網路與系統工具

- /dns <domain>：查詢網域解析紀錄 (A, CNAME, MX)。

- /ip <ip>：查詢 IP 地理位置、ISP 與反解資訊。

- /whois <domain>：查詢網域註冊商與到期日。

- /ping：查看機器人延遲，以及伺服器的 CPU 與 RAM 使用率。

### 管理員功能

- /ticket_setup：發送客服單建立面板 (支援指定頻道)。

- /delete <count>：批量刪除訊息 (Purge)。

- /kick / /ban：踢出或封鎖成員 (含身分組權限檢查)。

- /nick：強制修改成員暱稱。

### 日誌與監控

- 本地日誌：自動建立 log/ 資料夾並記錄運行日誌。

- Webhook 警報：當發生錯誤或警告時，自動發送通知到指定的 Discord 頻道。

Created by xNone1337