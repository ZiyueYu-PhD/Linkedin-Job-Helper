import os
import re
from urllib.parse import urlparse, parse_qs
from google.oauth2 import service_account
import gspread
from gspread.exceptions import APIError

# ==========================
# Google Sheet 设置
# ==========================
BASE_DIR=os.path.dirname(os.path.abspath(__file__))
json_path = os.getenv("GOOGLE_CREDS_PATH")

if not json_path or not os.path.exists(json_path):
    raise ValueError(
        "GOOGLE_CREDS_PATH not set or file not found. "
        "Please set environment variable to your credentials JSON."
    )


SPREADSHEET_NAME = "Job Tracking System"
TARGET_SHEET = "Applications"

SCOPES=[
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds=service_account.Credentials.from_service_account_file(json_path,scopes=SCOPES)
gc=gspread.authorize(creds)
sheet=gc.open(SPREADSHEET_NAME).worksheet(TARGET_SHEET)


# ==========================
# 提取唯一 Job ID
# ==========================
def extract_job_id(url):
    try:
        parsed=urlparse(url)

        # LinkedIn
        match=re.search(r"/jobs/view/(\d+)",parsed.path)
        if match:
            return "linkedin_"+match.group(1)

        # Indeed
        qs=parse_qs(parsed.query)
        if "jk" in qs:
            return "indeed_"+qs["jk"][0]

        # Glassdoor (可扩展)
        match=re.search(r"Job-.*?-([\d]+)\.htm",url)
        if match:
            return "glassdoor_"+match.group(1)

        # 如果识别不了，就用去掉参数后的URL
        return parsed.scheme+"//"+parsed.netloc+parsed.path

    except:
        return url


# ==========================
# 去重逻辑
# ==========================
def deduplicate_by_job_id():
    print("正在读取所有行...")
    rows=sheet.get_all_values()

    if len(rows)<=1:
        print("Sheet 为空或只有表头，无需去重")
        return

    url_column=2
    seen_ids=set()
    rows_to_delete=[]

    for idx,row in enumerate(rows[1:],start=2):
        if len(row)<=url_column:
            continue

        url=row[url_column].strip()
        if not url:
            continue

        job_id=extract_job_id(url)

        if job_id in seen_ids:
            print(f"发现重复 JobID（行 {idx}）：{job_id} → 将删除")
            rows_to_delete.append(idx)
        else:
            seen_ids.add(job_id)

    print("\n去重统计：")
    print(f"原始总行数（含表头）：{len(rows)}")
    print(f"重复行数：{len(rows_to_delete)}")
    print(f"保留行数（含表头）：{len(rows)-len(rows_to_delete)}")

    if not rows_to_delete:
        print("没有发现重复职位")
        return

    print("\n⚡ 自动删除重复行")

    rows_to_delete.sort(reverse=True)
    deleted_count=0

    for row_num in rows_to_delete:
        try:
            sheet.delete_rows(row_num)
            deleted_count+=1
            print(f"已删除行 {row_num}")
        except APIError as e:
            print(f"删除行 {row_num} 失败: {e}")

    print(f"\n删除完成！共删除 {deleted_count} 行重复数据")


if __name__=="__main__":
    try:
        deduplicate_by_job_id()
    except Exception as e:
        print(f"程序异常：{e}")