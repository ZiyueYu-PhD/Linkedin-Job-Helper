from playwright.sync_api import sync_playwright
import time
import random

keywords = [
    "Data Scientist Intern",
    "Machine Learning Intern",
    "AI Intern",
    "Data Analyst Intern",
    "Business Analyst Intern",
    "Product Analyst Intern",
    "Product Manager Intern"
]

MAX_JOBS_PER_KEYWORD =20
MAX_PAGES_PER_KEYWORD = 3
MAX_TIME_PER_KEYWORD = 300


def main():
    start_time = time.time()
    total_jobs_collected = 0

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir="linkedin_profile",
            headless=False,
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        output_file = "Jobs_linkedin_recent.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("LinkedIn 实习职位链接采集（最近24小时内）\n")
            f.write(f"采集时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")

            for kw in keywords:
                print(f"\n=== 处理关键词: {kw} (最多翻 {MAX_PAGES_PER_KEYWORD} 页，或 5 分钟超时) ===")

                keyword_start = time.time()

                encoded_kw = kw.replace(" ", "%20")
                url = (
                    f"https://www.linkedin.com/jobs/search/?keywords={encoded_kw}"
                    "&location=United%20States&f_TPR=r43200&f_E=1,2&f_JT=F,I"
                    )

                page.goto(url, wait_until="domcontentloaded", timeout=90000)
                time.sleep(random.uniform(5, 10))

                try:
                    page.wait_for_selector('div.job-card-container, li[data-job-id], div.jobs-search-results__list-item', timeout=60000)
                    print("职位列表容器已检测到")
                except:
                    print(f"未检测到职位列表 → 检查登录/结果/页面加载 {kw}")
                    page.screenshot(path=f"debug_{kw.replace(' ', '_')}_load_fail.png", full_page=True)
                    f.write(f"关键词: {kw} → 无结果或加载失败\n\n")
                    continue

                jobs_seen = set()
                page_num = 1

                while len(jobs_seen) < MAX_JOBS_PER_KEYWORD and page_num <= MAX_PAGES_PER_KEYWORD:
                    if time.time() - keyword_start > MAX_TIME_PER_KEYWORD:
                        print(f"关键词 '{kw}' 超时（超过 5 分钟），强制跳到下一个关键词")
                        break

                    print(f"\n--- 第 {page_num} 页 ---")

                    job_cards = page.locator('div.job-card-container, li[data-job-id], div.jobs-search-results__list-item, li.jobs-search-results__list-item, div[data-job-id]')
                    current_count = job_cards.count()
                    print(f"本页可见卡片数: {current_count}")

                    new_count = 0

                    for i in range(current_count):
                        if len(jobs_seen) >= MAX_JOBS_PER_KEYWORD:
                            break

                        card = job_cards.nth(i)

                        title_link = card.locator(
                            'a.job-card-list__title, a[data-tracking-control-name*="search-card"], a.base-card__full-link, a'
                        )
                        if title_link.count() == 0:
                            continue

                        try:
                            job_title = title_link.inner_text(timeout=8000).strip()
                        except:
                            job_title = "N/A"

                        if not job_title or job_title in jobs_seen:
                            continue

                        jobs_seen.add(job_title)
                        new_count += 1

                        link = title_link.get_attribute("href") or ""
                        if link.startswith('/'):
                            link = "https://www.linkedin.com" + link

                        if "/jobs/view/" not in link:
                            continue

                        f.write(f"关键词: {kw}\n")
                        f.write(f"职位名称: {job_title}\n")
                        f.write(f"网址: {link}\n")
                        f.write("-" * 70 + "\n\n")
                        f.flush()

                        print(f"  → 新采集: {job_title} ({link})")

                    print(f"本页新增: {new_count} 个 | 累计: {len(jobs_seen)} / {MAX_JOBS_PER_KEYWORD}")

                    # 精确匹配搜索结果区的下一页按钮（避免匹配公司照片区）
                    next_button = page.locator(
                        'button.artdeco-pagination__button--next.jobs-search-pagination__button--next[aria-label*="Next"], '
                        'button.jobs-search-pagination__button--next, '
                        'button[aria-label*="View next page"]'
                    )

                    if next_button.count() > 0:
                        if next_button.count() > 1:
                            print(f"警告：找到 {next_button.count()} 个 'Next' 按钮，选择第一个")
                        if next_button.is_enabled():
                            print("找到下一页按钮，点击跳转...")
                            try:
                                next_button.first.click(timeout=10000)
                                time.sleep(random.uniform(6, 12))
                                page.wait_for_load_state("domcontentloaded", timeout=30000)
                                print("已跳转到下一页")
                                page_num += 1
                            except Exception as e:
                                print(f"点击下一页失败: {e}，停止翻页")
                                break
                        else:
                            print("下一页按钮不可用，结束该关键词")
                            break
                    else:
                        print("没有找到下一页按钮，结束该关键词")
                        break

                print(f"关键词 '{kw}' 完成，共采集 {len(jobs_seen)} 个唯一职位")
                total_jobs_collected += len(jobs_seen)

        total_time = round(time.time() - start_time, 2)
        print("\n" + "="*60)
        print("✅ LinkedIn 链接抓取完成")
        print(f"📊 总职位链接数量: {total_jobs_collected}")
        print(f"⏱ 总耗时: {total_time} 秒")
        print(f"输出文件: {output_file}")
        print("="*60)

        context.close()


if __name__ == "__main__":
    main()