from playwright.sync_api import sync_playwright
import time
import random
import base64
import json
import re
import os
from datetime import datetime
from openai import OpenAI

# ==========================
# 配置
# ==========================
INPUT_FILE = "Jobs_linkedin_recent.txt"      # 第一步输出的文件
OUTPUT_FILE = "Jobs_linkedin_detail.txt"

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    raise ValueError("OPENAI_API_KEY not set")
client = OpenAI(api_key=OPENAI_KEY)

# 防封号延迟
MIN_DELAY = 3
MAX_DELAY = 5

def parse_links():
    jobs = []
    current = {}
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("=") or line.startswith("-"):
                if current.get("url"):
                    jobs.append(current)
                    current = {}
                continue
            if line.startswith("关键词:"):
                current["keyword"] = line.replace("关键词:", "").strip()
            elif line.startswith("职位名称:"):
                current["title"] = line.replace("职位名称:", "").strip()
            elif line.startswith("网址:"):
                current["url"] = line.replace("网址:", "").strip()
    if current.get("url"):
        jobs.append(current)
    print(f"从 {INPUT_FILE} 读取到 {len(jobs)} 个职位链接")
    return jobs


def screenshot_and_analyze(page, url):
    print(f"正在处理: {url}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        time.sleep(random.uniform(6, 10))   # 让 top card 完全加载

        # 优先截取 top card 区域（最清晰、最有用）
        top_card = page.locator('.jobs-unified-top-card, .top-card-layout, div:has(> h1)')
        if top_card.count() > 0:
            screenshot_bytes = top_card.first.screenshot()
            print("[截图] 已截取 top card 区域")
        else:
            screenshot_bytes = page.screenshot(full_page=False)  # 全 viewport
            print("[截图] 未找到 top card，使用 viewport 截图")

        # 转 base64
        base64_image = base64.b64encode(screenshot_bytes).decode("utf-8")

        # ====================== GPT-4o Vision 分析 ======================
        prompt = """
你现在是一个精准的LinkedIn职位信息提取器。
请严格从图片中提取以下字段，只提取可见的文本，不要猜测，不要添加任何额外说明。

请直接返回JSON格式（不要加任何其他文字）：

{
  "公司名称": "提取公司名称",
  "职位名称": "提取职位标题",
  "网址": "提取职位链接",
  "发布时间": "提取发布时间，例如 Reposted 12 hours ago 或 21 hours ago",
  "地理位置": "提取地点，例如 San Jose, CA",
  "薪资范围": "提取薪资，例如 $45.75/hr - $50/hr 或 $20/hr",
  "职位类型": "提取 Full-time / On-site / Hybrid 等",
  "申请人数": "提取申请人数，例如 Over 100 people clicked apply"
}

如果某个字段在图片中完全看不到，请填 "N/A"
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=800,
            temperature=0.0
        )

        raw = response.choices[0].message.content.strip()
        # 清理可能的多余 markdown
        raw = re.sub(r'^```json\n|```$', '', raw).strip()

        data = json.loads(raw)

        result = {
            "职位名称": data.get("职位名称", "N/A"),
            "公司名称": data.get("公司名称", "N/A"),
            "地理位置": data.get("地理位置", "N/A"),
            "发布时间": data.get("发布时间", "N/A"),
            "薪资范围": data.get("薪资范围", "N/A"),
            "职位类型": data.get("职位类型", "N/A"),
            "申请人数": data.get("申请人数", "N/A"),
            "网址": url
        }

        print(f"✅ AI 提取完成 → {result['职位名称']} @ {result['公司名称']}")
        return result

    except Exception as e:
        print(f"❌ 处理失败: {e}")
        return {
            "职位名称": "N/A",
            "公司名称": "N/A",
            "地理位置": "N/A",
            "发布时间": "N/A",
            "薪资范围": "N/A",
            "职位类型": "N/A",
            "申请人数": "N/A",
            "网址": url
        }


def main():
    jobs = parse_links()
    if not jobs:
        print("没有找到链接！")
        return

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir="linkedin_profile",
            headless=False,          # 先用 False 观察，稳定后改 True
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        )
        page = context.new_page()

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("LinkedIn 职位详情提取（AI视觉分析版）\n")
            f.write(f"提取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总职位数: {len(jobs)}\n")
            f.write("=" * 90 + "\n\n")

            for idx, job in enumerate(jobs, 1):
                print(f"\n[{idx}/{len(jobs)}] 处理: {job.get('title', '未知职位')}")

                detail = screenshot_and_analyze(page, job["url"])

                # 写入干净格式
                f.write(f"职位名称: {detail['职位名称']}\n")
                f.write(f"公司名称: {detail['公司名称']}\n")
                f.write(f"地理位置: {detail['地理位置']}\n")
                f.write(f"发布时间: {detail['发布时间']}\n")
                f.write(f"薪资范围: {detail['薪资范围']}\n")
                f.write(f"职位类型: {detail['职位类型']}\n")
                f.write(f"申请人数: {detail['申请人数']}\n")
                f.write(f"网址: {detail['网址']}\n")
                f.write("-" * 100 + "\n\n")
                f.flush()

                # 防封号
                time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

                if idx % 3 == 0:
                    print("休息 3-5 秒防封...")
                    time.sleep(random.uniform(3, 5))

        print("\n" + "="*90)
        print("✅ 全部处理完成！")
        print(f"输出文件: {OUTPUT_FILE}")
        print("="*90)

        context.close()


if __name__ == "__main__":
    main()