from google.oauth2 import service_account
from googleapiclient.discovery import build
import time
import os
import re

# ================== 配置区 ==================
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDS_PATH")
if not CREDENTIALS_FILE:
    raise ValueError("GOOGLE_CREDS_PATH not set")

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = "Applications"

INPUT_FILE = "Jobs_linkedin_detail.txt"

START_ROW = 3

# ============================================

def parse_detail_txt(file_path):
    jobs = []
    current = {}

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("-") or line.startswith("="):
            if current.get("url"):
                jobs.append(current)
                current = {}
            continue

        if line.startswith("职位名称:"):
            if current:
                jobs.append(current)
            current = {}
            current["title"] = line.replace("职位名称:", "").strip()

        elif line.startswith("公司名称:"):
            current["company"] = line.replace("公司名称:", "").strip()

        elif line.startswith("地理位置:"):
            current["location"] = line.replace("地理位置:", "").strip()

        elif line.startswith("发布时间:"):
            current["posted"] = line.replace("发布时间:", "").strip()

        elif line.startswith("薪资范围:"):
            current["salary"] = line.replace("薪资范围:", "").strip()

        elif line.startswith("申请人数:"):
            current["applicants"] = line.replace("申请人数:", "").strip()

        elif line.startswith("网址:"):
            current["url"] = line.replace("网址:", "").strip()

    if current.get("url"):
        jobs.append(current)

    print(f"从 {file_path} 解析到 {len(jobs)} 条职位")
    return jobs


def get_sheet_service():
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=creds)
    return service


def append_to_sheet(service, spreadsheet_id, sheet_name, jobs):
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A:Z"
    ).execute()

    values = result.get("values", [])
    next_row = len(values) + 1 if values else START_ROW

    body = {"values": []}
    
    # 当前完整时间：年-月-日 时:分
    current_time_str = time.strftime("%Y-%m-%d %H:%M")

    for job in jobs:
        posted_raw = job.get("posted", "N/A")
        
        # 新格式：2026-03-04 18:01 Reposted 12 hours ago
        if posted_raw != "N/A":
            posted_formatted = f"{current_time_str} {posted_raw}"
        else:
            posted_formatted = f"{current_time_str} (未知)"

        row = [
            job.get("company", "N/A"),           # A列: 公司名
            job.get("title", "N/A"),             # B列: 职位名
            job.get("url", "N/A"),               # C列: 网址
            posted_formatted,                    # D列: Post时间（带当前时间）
            job.get("location", "N/A"),          # E列: 地理位置
            job.get("salary", "N/A"),            # F列: 薪水
            job.get("applicants", "N/A")         # G列: 当前申请人数
        ]
        body["values"].append(row)

    if body["values"]:
        append_result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A{next_row}",
            valueInputOption="RAW",
            body=body
        ).execute()

        print(f"成功追加 {len(body['values'])} 条数据到行 {next_row} 开始")
    else:
        print("没有数据可写入")


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"未找到输入文件: {INPUT_FILE}")
        return

    print("读取 LinkedIn 详情数据...")
    jobs = parse_detail_txt(INPUT_FILE)

    if not jobs:
        print("没有有效职位数据，结束")
        return

    service = get_sheet_service()
    append_to_sheet(service, SPREADSHEET_ID, SHEET_NAME, jobs)

    print("\n写入完成！请打开 Google Sheet 检查。")
    print("A列: 公司名 | B列: 职位名 | C列: 网址 | D列: Post时间（带当前时间 如 2026-03-04 18:01 Reposted 12 hours ago） | E列: 地理位置 | F列: 薪水 | G列: 当前申请人数")


if __name__ == "__main__":
    main()