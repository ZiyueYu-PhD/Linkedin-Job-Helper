import subprocess
import sys
import time
import os
from datetime import datetime, timedelta

# =============================
# 每天固定运行时间点（24小时制）
# =============================
RUN_TIMES = [
    (6, 0),   # 早上 06:00
    (18, 0)   # 晚上 18:00
]

# 要执行的脚本顺序
scripts = [
    "linkedin_scraper_website.py",
    "linkedin_scraper_detail.py",
    "write_into_google_sheet.py",
    "dedeplicate_sheet.py",
    "Job_analysis.py"
]

# 需要每次运行前清理的文件
FILES_TO_DELETE = [
    "Jobs_linkedin_recent.txt",
    "Jobs_linkedin_detail.txt"
]


# =============================
# 删除旧数据文件
# =============================
def cleanup_files():
    print("\n🧹 清理旧数据文件")

    for file in FILES_TO_DELETE:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"🗑 已删除: {file}")
            except Exception as e:
                print(f"⚠ 删除失败 {file}: {e}")
        else:
            print(f"✔ 不存在: {file}")


# =============================
# 运行单个脚本
# =============================
def run_script(script, step, total):
    print("\n" + "="*60)
    print(f"🚀 Step {step}/{total} - {script}")
    print("="*60)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🕒 当前时间: {now}")
    print(f"🐍 Python解释器: {sys.executable}")

    abs_path = os.path.abspath(script)
    print(f"📄 脚本路径: {abs_path}")

    if not os.path.exists(script):
        print(f"❌ 文件不存在: {script}")
        sys.exit(1)
    else:
        print("✅ 文件存在")

    print(f"▶️ 即将运行: {script}")
    print("-"*60)

    start = time.time()

    try:
        subprocess.run([sys.executable, script], check=True)
        duration = round(time.time() - start, 2)
        print("-"*60)
        print(f"✅ {script} 完成")
        print(f"⏱ 用时: {duration} 秒")

    except subprocess.CalledProcessError as e:
        print(f"❌ {script} 执行失败 (退出码: {e.returncode})")
        print("🛑 终止后续流程")
        sys.exit(1)


# =============================
# 执行完整流程
# =============================
def run_pipeline():
    print("\n🔥 自动求职系统启动 - 开始新一轮任务")

    cleanup_files()

    total = len(scripts)
    print(f"\n📦 共 {total} 个步骤\n")
    print("📋 执行列表:")
    for i, s in enumerate(scripts, 1):
        print(f"   {i}. {s}")
    print()

    for i, script in enumerate(scripts, start=1):
        run_script(script, i, total)

    print("\n" + "="*60)
    print("🎉 本轮所有步骤完成！")
    print("="*60)


# =============================
# 计算距离下一个运行时间点的秒数
# =============================
def seconds_until_next_run():
    now = datetime.now()
    
    today_6am = now.replace(hour=6, minute=0, second=0, microsecond=0)
    today_6pm = now.replace(hour=18, minute=0, second=0, microsecond=0)
    
    candidates = []
    
    if now < today_6am:
        candidates.append(today_6am)
    if now < today_6pm:
        candidates.append(today_6pm)
    
    tomorrow = now + timedelta(days=1)
    candidates.append(tomorrow.replace(hour=6, minute=0, second=0, microsecond=0))
    candidates.append(tomorrow.replace(hour=18, minute=0, second=0, microsecond=0))
    
    next_run = min(candidates)
    return (next_run - now).total_seconds(), next_run


# =============================
# 等待到下一个时间点
# =============================
def wait_until_next_run():
    while True:
        wait_seconds, next_run_time = seconds_until_next_run()

        hours = int(wait_seconds // 3600)
        minutes = int((wait_seconds % 3600) // 60)
        seconds = int(wait_seconds % 60)

        print(f"\n⏳ 距离下次运行: {hours}小时 {minutes}分钟 {seconds}秒")
        print(f"（预计下次运行时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}）")

        time.sleep(wait_seconds)

        print(f"\n⏰ 到达运行时间 {next_run_time.strftime('%H:%M')}，开始新一轮任务")
        run_pipeline()


# =============================
# 主程序
# =============================
if __name__ == "__main__":
    print("🕐 自动任务调度器启动")
    print(f"⏰ 每天固定运行时间点: 早上06:00 和 晚上18:00")

    # ================== 新增开关（你想要的功能） ==================
    RUN_IMMEDIATELY = True   # ←←← 改成 False = 启动后不立即运行，等待到早上6点才开始第一次运行
                              #      改成 True  = 启动后立即运行一次（原来的行为）
    # ============================================================

    if RUN_IMMEDIATELY:
        print("\n🚀 启动后立即执行一次完整流程")
        run_pipeline()
    else:
        print("\n⏳ 启动后等待到下一个时间点（早上06:00）才开始第一次运行")

    # 之后进入循环，等待下一个 6:00 或 18:00
    wait_until_next_run()