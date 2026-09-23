from io import BytesIO
from html import escape
import pandas as pd

EXPORT_COLUMNS = {"姓名": "name", "出生日期": "birthday", "年龄": "age", "星座": "zodiac", "四象": "element",
                  "星座趣味关键词": "zodiac_keywords", "星座趣味描述": "zodiac_description", "年龄阶段": "age_group", "班主任年龄阶段提示": "teacher_age_tip"}

def export_analysis_excel(students, stats, errors=None):
    output = BytesIO()
    safe = pd.DataFrame({label: students[col].map(lambda x: ", ".join(x) if isinstance(x, list) else x) for label, col in EXPORT_COLUMNS.items()})
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        safe.to_excel(writer, sheet_name="学生结果", index=False)
        stats["zodiac"].to_excel(writer, sheet_name="星座统计", index=False)
        stats["element"].to_excel(writer, sheet_name="四象统计", index=False)
        (errors if errors is not None else pd.DataFrame(columns=["Excel行号", "姓名", "问题类型", "问题说明"])).to_excel(writer, sheet_name="导入问题", index=False)
    return output.getvalue()

def export_html_report(students, stats):
    z_rows = "".join(f"<tr><td>{escape(str(r['星座']))}</td><td>{int(r['人数'])}</td><td>{r['占比']:.1%}</td></tr>" for _, r in stats["zodiac"].iterrows())
    e_rows = "".join(f"<tr><td>{escape(str(r['四象']))}</td><td>{int(r['人数'])}</td><td>{r['占比']:.1%}</td></tr>" for _, r in stats["element"].iterrows())
    m_rows = "".join(f"<tr><td>{int(r['月份'])} 月</td><td>{int(r['人数'])}</td></tr>" for _, r in stats["months"].iterrows())
    cards = "".join(f"<article><h3>{escape(str(r['name']))}</h3><p>生日：{r['birthday']}　年龄：{r['age']} 岁　{r['zodiac']} / {r['element']}</p><section><b>趣味星座内容</b><p>{escape(r['zodiac_description'])}</p></section><section><b>年龄阶段提醒：{escape(r['age_group'])}</b><p>{escape(r['teacher_age_tip'])}</p></section></article>" for _, r in students.iterrows())
    return f"""<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>班级分析报告</title><style>body{{font-family:system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#263247}}table{{border-collapse:collapse}}td,th{{padding:.5rem 1rem;border:1px solid #ddd}}article{{border:1px solid #ddd;border-radius:12px;padding:1rem;margin:1rem 0}}section{{display:inline-block;vertical-align:top;width:42%;margin:1% 2% 1% 0;padding:.5rem;background:#f5f7fb}}.notice{{background:#fff7df;padding:1rem}}</style><h1>班级星座小助手 Online · 分析报告</h1><p>班级总人数：{len(students)}　平均年龄：{stats['summary']['average_age']}　年龄范围：{stats['summary']['min_age']}～{stats['summary']['max_age']} 岁</p><div class='notice'>星座与四象内容仅用于趣味互动，不代表心理评估或学生固定判断；班主任提醒依据年龄阶段生成。Online 版仅支持姓名与出生日期，请勿上传身份证或其他无关敏感信息。</div><h2>星座统计</h2><table>{z_rows}</table><h2>四象统计</h2><table>{e_rows}</table><h2>生日月份统计</h2><table>{m_rows}</table><h2>学生卡片</h2>{cards}<footer>请教师妥善保存含有学生生日的信息。</footer></html>"""
