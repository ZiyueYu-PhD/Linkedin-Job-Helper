import os
import re
import json
import time
import random
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import APIError
from PyPDF2 import PdfReader
from playwright.sync_api import sync_playwright

# ==========================
# 🔐 OPENAI
# ==========================
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    raise ValueError("OPENAI_API_KEY not set")
client = OpenAI(api_key=OPENAI_KEY)

# ==========================
# 默认结果
# ==========================
DEFAULT_RESULT = {
    "apply_score": 5.0,
    "recommendation": "可投递",
    "decision_reason": "未抓到职位描述"
}

# ==========================
# 📄 CV
# ==========================
CV_PATH = os.getenv("CV_PATH")


def load_cv_text():
    if not os.path.exists(CV_PATH):
        return ""
    reader = PdfReader(CV_PATH)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text[:12000]

CV_TEXT = load_cv_text()

# ==========================
# Google Sheets
# ==========================
json_path = os.getenv("GOOGLE_CREDS_PATH")
if not json_path:
    raise ValueError("GOOGLE_CREDS_PATH not set")

SPREADSHEET_NAME = "Darling intern"
TARGET_SHEET = "待投递（新版 超级好用）"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(json_path, scope)
gc = gspread.authorize(creds)
sheet = gc.open(SPREADSHEET_NAME).worksheet(TARGET_SHEET)

# ==========================
# JD抓取（保持原样）
# ==========================
def fetch_text(url):
    if not url:
        return ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            page.goto(url, timeout=60000)
            time.sleep(random.uniform(4,6))

            page.mouse.wheel(0, 2000)
            time.sleep(2)

            if "linkedin.com" in url:
                selectors = [
                    "div.jobs-description-content__text",
                    "section.jobs-description",
                    "div.jobs-box__html-content"
                ]

            elif "indeed.com" in url:
                for _ in range(6):
                    page.mouse.wheel(0, 3000)
                    time.sleep(1)

                try:
                    page.wait_for_selector("#jobDescriptionText", timeout=15000)
                except:
                    pass

                selectors = [
                    "#jobDescriptionText",
                    "[data-testid='jobsearch-JobComponent-description']",
                    ".jobsearch-JobComponent-description"
                ]
            else:
                selectors = ["body"]

            text = ""

            for sel in selectors:
                loc = page.locator(sel)
                if loc.count() > 0:
                    try:
                        text = loc.first.inner_text().strip()
                        if len(text) > 200:
                            break
                    except:
                        continue

            if len(text) < 200:
                text = page.inner_text("body")

            context.close()
            return re.sub(r"\s+", " ", text)[:12000]

        except Exception as e:
            print("抓取失败:", e)
            context.close()
            return ""

# ==========================
# ⭐ GPT分析（0-10分 + recommendation）
# ==========================
def analyze_with_cv(jd_text):

    prompt = f"""
你是一名熟悉美国就业市场、出口管制政策及OPT/H1B现实情况的职业分析顾问。

请根据【职位描述】与【候选人简历】进行深入评估，并严格按照以下步骤分析：

━━━━━━━━━━━━━━━━━━
【第一步：身份与敏感性筛查（最优先）以及 岗位类型筛查（实习岗位要求）】

首先检查该职位是否存在以下任一情况：

• 明确要求 US Citizen / Green card / Security clearance  
• ITAR / EAR / Export Control 限制  
• Defense / Aerospace / Government / National security  
• 涉及敏感技术或国家安全相关工作  

如果存在以上任一情况：

→ apply_score 必须为 0.0  
→ recommendation 必须为 "不推荐"  
→ 在理由中明确说明限制原因  


由于候选人当前只接受 **暑期实习岗位（Summer Internship），且不得超过Master级别的intern**。

因此需要判断该职位是否属于满足该要求的实习岗位。

通常实习岗位会出现以下关键词之一：

• Intern / Internship  
• Summer Intern / Summer Internship  
• Co-op / Coop  
• Summer Analyst / Summer Associate  
• Student Researcher / Research Intern  
• Graduate Intern  

如果职位描述或职位标题中 **完全没有任何实习相关关键词，并且明显是正式全职岗位（Full-time role）**：
如果职位描述或职位标题中 **出现了PHD Level相关的要求(PhD)**：

→ apply_score 必须为 0.0  
→ recommendation 必须为 "不推荐"  
→ 理由中说明：该岗位为正式岗位而非实习岗位  

⚠️注意：

有些实习岗位在 LinkedIn 上的 Job Type 可能标为 **Full-time**，  
但如果标题或描述中包含 **Intern / Internship / Summer / Co-op 等实习关键词**，  
仍然应判断为实习岗位，可以继续评估。

只有在 **完全没有任何实习迹象** 时才判定为非实习岗位。

━━━━━━━━━━━━━━━━━━
【第二步：技能匹配度】

对比职位要求技能 与 简历技能：

• 编程语言  
• 数据分析 / 机器学习工具  
• 软件与平台  
• 技术深度  

评估匹配程度与差距。

━━━━━━━━━━━━━━━━━━
【第三步：经历匹配度】

对比职位工作内容 与 候选人过往经历：

• 实习或项目相关性  
• 行业或领域契合度  
• 可迁移经验程度  

说明匹配情况。

━━━━━━━━━━━━━━━━━━
【第四步：综合评分】

在没有身份限制前提下：

给出 0.0–10.0 分评分（必须包含一位小数，例如 7.8 / 4.2 / 10.0）

评分参考：

0.0 = 无法申请 / 明确限制  
0.1–3.0 = 匹配度极低，几乎无竞争力  
3.1–5.0 = 有一定相关性，但竞争力较弱  
5.1–7.0 = 基本匹配，可投递  
7.1–8.5 = 匹配良好，建议优先投递  
8.6–10.0 = 高度匹配，强烈建议投递  

评分权重：
维度：技能匹配度
权重：30%
说明（评估岗位要求的核心技能与候选人技能栈的匹配程度，例如Python、SQL、Machine Learning、Data Analysis、Product Analytics等。如果技能与JD高度重合，简历更容易通过ATS筛选并进入HR或Hiring Manager的第一轮评估。）

维度：经历匹配度
权重：30%
说明（评估候选人过往实习、项目或研究经历与岗位职责的相关性。如果已有类似业务场景、技术应用或行业经验，例如数据分析项目、AI模型开发或业务分析实践，通常更容易被认为可以快速上手岗位。）

维度：竞争强度
权重：10%
说明（评估该岗位整体申请竞争情况，例如公司知名度、岗位热门程度、申请人数规模等。如果岗位属于热门公司或热门职位类别，通常会吸引大量申请者，从而降低获得面试机会的概率。）

维度：岗位难度
权重：10%
说明（判断岗位实际门槛，例如是否要求较高的技术深度、复杂的工具栈、或超出实习/初级岗位的经验要求。有些岗位虽然标注为Intern或Entry-level，但实际期望较高，会显著增加获得面试的难度。）

维度：成长与学习机会
权重：10%
说明（评估该岗位是否能提供实际能力提升与职业成长，例如是否有导师指导、是否参与核心项目、是否能接触关键技术或业务流程，以及是否存在return offer或长期发展机会。）

维度：公司文化与团队环境
权重：10%
说明（综合考虑公司整体文化氛围和团队工作环境，例如员工评价、团队协作氛围、工作节奏、以及是否支持员工成长与学习。良好的文化环境通常意味着更好的工作体验和长期职业发展价值。）

⚠️要求：

• 分数必须包含一位小数（除非为 0.0 或 10.0）  
• 不要默认整数评分  

━━━━━━━━━━━━━━━━━━
【第五步：投递推荐】

根据分数给出简短推荐（仅以下三种选项之一）：

- "强烈推荐" （分数 8.6–10.0）
- "建议投递" （分数 7.1–8.5）
- "可投递" （分数 5.1–7.0）
- "不推荐" （分数 0.0–5.0，或有身份限制）

━━━━━━━━━━━━━━━━━━
【输出要求】

仅返回 JSON， decision_reason书写过程中第一第二第三步都用【】框起来 不允许换行：

{{
  "apply_score": 数字（0.0-10.0，必须有小数点，除非0或10）,
  "recommendation": "强烈推荐 / 建议投递 / 可投递 / 不推荐",
  "decision_reason": "不少于250字的深入分析，必须自然、具体、有判断逻辑，不要模板化或流水线语言"
}}

━━━━━━━━━━━━━━━━━━
【候选人简历】
{CV_TEXT}

━━━━━━━━━━━━━━━━━━
【职位描述】
{jd_text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    return json.loads(response.choices[0].message.content)


# ==========================
# 颜色（根据 0-10 分渐变）
# ==========================
def color_score(cell, score):
    score = float(score)
    if score <= 3.0:
        color = {"red": 1.0, "green": 0.5, "blue": 0.5}  # 深红
    elif score <= 5.0:
        color = {"red": 1.0, "green": 0.8, "blue": 0.5}  # 橙红
    elif score <= 7.0:
        color = {"red": 1.0, "green": 1.0, "blue": 0.6}  # 黄
    elif score <= 8.5:
        color = {"red": 0.6, "green": 1.0, "blue": 0.6}  # 浅绿
    else:
        color = {"red": 0.2, "green": 0.8, "blue": 0.4}  # 深绿
    
    sheet.format(cell, {"backgroundColor": color})


# ==========================
# 写入（新列对应）
# ==========================
def safe_write(idx, result):
    score_raw = result.get("apply_score", 5.0)
    # 四舍五入到一位小数
    score = round(float(score_raw), 1)
    
    recommendation = result.get("recommendation", "可投递")
    reason = result.get("decision_reason", "")

    for _ in range(3):
        try:
            # I列：投递推荐（文字）
            sheet.update(f"I{idx}", [[recommendation]])

            # K列：AI 数字评分（带小数）
            sheet.update(f"K{idx}", [[score]])
            color_score(f"K{idx}", score)
            color_score(f"I{idx}", score)  # I列也上色，与 K 一致

            # L列：AI 注释/理由
            sheet.update(f"L{idx}", [[reason]])

            return True
        except APIError:
            time.sleep(5)
    return False


# ==========================
# 主程序
# ==========================
rows = sheet.get_all_values()
total = len(rows) - 1

print(f"\n🚀 开始分析，共 {total} 行\n")

for idx, row in enumerate(rows[1:], start=2):

    # 如果 K列已有数字（已处理），跳过
    if len(row) >= 11 and row[10].strip() and re.match(r'^\d+\.?\d*$', row[10].strip()):
        continue

    url = row[2] if len(row) >= 3 else ""  # 假设 C列是网址（从索引2开始）
    if not url:
        continue

    print(f"分析 {idx-1}/{total} - {url}")

    jd_text = fetch_text(url)

    if not jd_text or len(jd_text) < 200:
        print("未抓到JD → 默认评分")
        safe_write(idx, DEFAULT_RESULT)
        continue

    try:
        result = analyze_with_cv(jd_text)
    except Exception as e:
        print("GPT失败 → 默认评分", e)
        result = DEFAULT_RESULT

    safe_write(idx, result)
    time.sleep(1)

print("\n🎉 完成")
