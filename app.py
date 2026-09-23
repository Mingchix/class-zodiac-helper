from datetime import date, timedelta
from io import BytesIO
import math
import random

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data.zodiac_profiles import PROFILES, DISCLAIMER
from utils.date_utils import calculate_age
from utils.zodiac import get_zodiac, get_element
from data.age_profiles import get_age_profile
from utils.excel_utils import detect_excel_columns, process_import, build_class_statistics, is_sensitive_column, read_online_excel
from utils.export_utils import export_analysis_excel, export_html_report

st.set_page_config(page_title="班级星座小助手 Online", page_icon="✨", layout="wide")
st.title("🌟 班级星座小助手 Online")
st.caption("用生日数据做一个轻松、有趣的班级观察工具。星座部分仅用于班级互动，不用于学生心理、能力或行为评价。")
ONLINE_PRIVACY_NOTICE = """Online 版不支持身份证号上传。\n\n请仅上传包含“姓名 + 出生日期”的数据。请勿上传身份证号、家庭住址、电话号码、医疗信息等与本功能无关的敏感信息。\n\nOnline 版运行于云端服务器，上传的数据会经过网络传输，请仅上传完成本功能所必要的信息。"""
st.warning(ONLINE_PRIVACY_NOTICE)
st.info("星座与四象内容仅用于文化娱乐和班级互动，不属于心理测评、能力评估或教育诊断。")

if "students" not in st.session_state:
    st.session_state.students = pd.DataFrame(columns=["student_key", "name", "birthday", "age", "zodiac", "element", "zodiac_keywords", "zodiac_description", "interaction_tip", "age_group", "teacher_age_tip", "source", "row_number"])
if "import_errors" not in st.session_state:
    st.session_state.import_errors = pd.DataFrame(columns=["Excel行号", "姓名", "问题类型", "问题说明"])
if "pending_import" not in st.session_state:
    st.session_state.pending_import = None


def _clear_current_data():
    for key in (
        "students", "import_errors", "pending_import", "online_excel_upload",
        "activity_groups", "guess_student", "bingo", "question", "roster_editor",
        "manual_name", "manual_birthday", "allow_manual_duplicate", "student_card_name",
        "reference_date",
    ):
        st.session_state.pop(key, None)
    st.session_state["_show_clear_notice"] = True

def _student_record(name, birthday, ref, source, row=0, key=None):
    age = calculate_age(birthday, ref)
    zodiac = get_zodiac(birthday)
    profile = PROFILES[zodiac]
    age_group, tip = get_age_profile(age)
    return {"student_key": key or f"S{len(st.session_state.students)+1:04d}", "name": name, "birthday": birthday, "age": age, "zodiac": zodiac, "element": get_element(zodiac), "zodiac_keywords": profile["keywords"], "zodiac_description": profile["description"], "interaction_tip": profile["tip"], "age_group": age_group, "teacher_age_tip": tip, "source": source, "row_number": row}

def _add_student(name, birthday, ref, source):
    record = _student_record(name, birthday, ref, source)
    st.session_state.students = pd.concat([st.session_state.students, pd.DataFrame([record])], ignore_index=True)

def _already_exists(name, birthday):
    frame = st.session_state.students
    return bool(((frame["name"].str.casefold() == name.casefold()) & (frame["birthday"] == birthday)).any()) if not frame.empty else False

reference_date = st.sidebar.date_input("统计日期", value=date.today(), key="reference_date")
tabs = st.tabs(["🏠 首页", "✍️ 手动录入", "📥 Excel 导入", "📊 班级统计", "👤 学生卡片", "🎉 班级玩法", "🔒 隐私说明"])

with tabs[0]:
    st.subheader("几分钟整理一份轻量的班级观察")
    st.write("手动添加学生，或从 Excel 导入姓名与生日；查看星座、四象、生日月份和年龄阶段提醒，并导出报告。")
    st.info(ONLINE_PRIVACY_NOTICE)
    st.markdown("**星座仅作趣味互动**；班主任提醒主要依据年龄阶段生成。请依据学生真实行为、兴趣、长期沟通和专业教育依据作出教育判断。")
    st.metric("当前名单", f"{len(st.session_state.students)} 人")
    if len(st.session_state.students):
        st.dataframe(st.session_state.students[["name", "birthday", "age", "zodiac", "element"]].rename(columns={"name":"姓名", "birthday":"出生日期", "age":"年龄", "zodiac":"星座", "element":"四象"}), width="stretch", hide_index=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("载入虚构示例数据", width="stretch"):
            sample = [("林小满", date(2012, 3, 21)), ("周星河", date(2012, 11, 8)), ("陈可可", date(2013, 2, 19)), ("许知夏", date(2012, 7, 30))]
            for name, birthday in sample:
                _add_student(name, birthday, reference_date, "示例")
            st.rerun()
    with c2:
        st.button("清空当前数据", on_click=_clear_current_data, width="stretch")
    if st.session_state.pop("_show_clear_notice", False):
        st.success("当前会话数据已清空。")

with tabs[1]:
    st.subheader("添加学生")
    allow_manual_duplicate = st.checkbox("确认允许完全重复的姓名和生日", value=False, key="allow_manual_duplicate")
    with st.form("manual_add", clear_on_submit=True):
        name = st.text_input("学生姓名", key="manual_name")
        birthday = st.date_input("出生日期", value=date(2012, 1, 1), min_value=date(1900, 1, 1), max_value=reference_date, key="manual_birthday")
        submitted = st.form_submit_button("添加学生")
    if submitted:
        if not name.strip():
            st.error("请填写学生姓名。")
        elif _already_exists(name.strip(), birthday) and not allow_manual_duplicate:
            st.warning("名单中已有相同姓名和生日的记录，请确认是否重复。")
        else:
            _add_student(name.strip(), birthday, reference_date, "手动")
            st.success("已添加。")
            st.rerun()
    if len(st.session_state.students):
        st.subheader("当前名单（可编辑）")
        edited = st.data_editor(st.session_state.students[["name", "birthday", "age", "zodiac", "element"]].rename(columns={"name":"姓名", "birthday":"出生日期", "age":"年龄", "zodiac":"星座", "element":"四象"}), disabled=["年龄", "星座", "四象"], num_rows="dynamic", width="stretch", key="roster_editor")
        if st.button("保存名单编辑"):
            rows = []
            for _, row in edited.iterrows():
                nm = str(row["姓名"]).strip()
                try:
                    bd = pd.to_datetime(row["出生日期"]).date()
                    if nm and bd <= reference_date:
                        rows.append(_student_record(nm, bd, reference_date, "手动"))
                except Exception:
                    continue
            st.session_state.students = pd.DataFrame(rows)
            st.success("名单已更新。")
            st.rerun()

with tabs[2]:
    st.subheader("Excel 导入")
    st.markdown("""
支持的 Excel 格式：`.xlsx`、`.xls`\n\n姓名 + 出生日期\n\n| 姓名 | 出生日期 |\n|---|---|\n| 张三 | 2012-03-21 |\n| 李四 | 2012-11-08 |\n\n日期支持 `2012-03-21`、`2012/03/21`、`2012.03.21`、`20120321` 和 Excel 原生日期。\n\n**注意：Online 版不支持身份证号上传。**
""")
    output = BytesIO()
    pd.DataFrame(columns=["姓名", "出生日期"]).to_excel(output, index=False)
    st.download_button("下载生日模板", output.getvalue(), file_name="班级导入模板_生日.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
    uploaded = st.file_uploader("选择班级名单文件", type=["xlsx", "xls"], key="online_excel_upload")
    if uploaded:
        try:
            source_df, sensitive_headers = read_online_excel(uploaded)
            if sensitive_headers:
                st.warning("检测到与本功能无关的敏感列。Online 版不会读取、展示或导出这些列；建议上传前先从文件中删除。")
            detected = detect_excel_columns(source_df)
            cols = list(source_df.columns)
            if not cols:
                st.warning("没有找到可用于本功能的安全列。未读取被排除的敏感列。")
            else:
                a, b = st.columns(2)
                name_col = a.selectbox("姓名列", cols, index=cols.index(detected["name"]) if detected.get("name") in cols else 0)
                birthday_options = ["不使用"] + cols
                birth_default = cols.index(detected["birthday"]) + 1 if detected.get("birthday") in cols else 0
                birthday_col = b.selectbox("出生日期列", birthday_options, index=birth_default)
                if detected.get("name") and detected.get("birthday"):
                    st.caption(f"自动识别：姓名列「{detected['name']}」；出生日期列「{detected['birthday']}」。")
                safe_preview_columns = [name_col]
                if birthday_col != "不使用" and birthday_col != name_col:
                    safe_preview_columns.append(birthday_col)
                st.caption(f"文件预览（仅显示已选择的姓名与出生日期；共 {len(source_df)} 行）")
                st.dataframe(source_df[safe_preview_columns].head(10), width="stretch", hide_index=True)
                if not detected.get("birthday") and birthday_col == "不使用":
                    st.warning("未检测到出生日期列。Online 版仅支持“姓名 + 出生日期”格式，不会解析身份证号。")
                if st.button("预览导入结果", disabled=birthday_col == "不使用"):
                    imported_students, errors = process_import(source_df, name_col, birthday_col, reference_date)
                    existing_keys = {(str(r["name"]).casefold(), r["birthday"]) for _, r in st.session_state.students.iterrows()}
                    imported_students["duplicate_warning"] = [bool(flag or (str(name).casefold(), birthday) in existing_keys) for flag, name, birthday in zip(imported_students["duplicate_warning"], imported_students["name"], imported_students["birthday"])]
                    st.session_state.pending_import = (imported_students, errors)
                if st.session_state.pending_import is not None:
                    preview_students, preview_errors = st.session_state.pending_import
                    st.write(f"可导入：**{len(preview_students)} 人**　需要检查：**{len(preview_errors)} 条**")
                    possible_duplicates = int(preview_students["duplicate_warning"].sum())
                    if possible_duplicates:
                        st.warning(f"发现 {possible_duplicates} 条姓名和生日均与名单重复的记录，默认会跳过；如确需保留，请勾选下方选项。")
                    if not preview_students.empty:
                        preview_table = preview_students[["name", "birthday", "age", "zodiac", "element", "duplicate_warning"]].rename(columns={"name":"姓名", "birthday":"出生日期", "age":"年龄", "zodiac":"星座", "element":"四象", "duplicate_warning":"可能重复"})
                        st.dataframe(preview_table, width="stretch", hide_index=True)
                    if not preview_errors.empty:
                        st.dataframe(preview_errors, width="stretch", hide_index=True)
                    keep_duplicates = st.checkbox("保留可能重复的记录", value=False, help="默认跳过姓名和出生日期均相同的记录；勾选后会全部保留。")
                    if st.button("确认导入并分析", type="primary"):
                        existing = st.session_state.students
                        to_import = preview_students if keep_duplicates else preview_students[~preview_students["duplicate_warning"]]
                        st.session_state.students = pd.concat([existing, to_import], ignore_index=True).drop(columns=["duplicate_warning"], errors="ignore")
                        st.session_state.import_errors = pd.concat([st.session_state.import_errors, preview_errors], ignore_index=True)
                        st.session_state.pending_import = None
                        st.success(f"成功导入 {len(to_import)} 人；需要检查 {len(preview_errors)} 条。")
                        st.rerun()
        except Exception as exc:
            st.error(f"无法读取该文件：{exc}")

students = st.session_state.students.copy()
if not students.empty:
    # Recalculate age and age-stage guidance whenever the selected reference date changes.
    refreshed = [_student_record(r["name"], r["birthday"], reference_date, r.get("source", "名单"), r.get("row_number", 0), r.get("student_key")) for _, r in students.iterrows()]
    students = pd.DataFrame(refreshed)
    st.session_state.students = students
stats = build_class_statistics(students, reference_date)

with tabs[3]:
    st.subheader("班级统计")
    if students.empty:
        st.info("添加或导入学生后即可查看统计。")
    else:
        s = stats["summary"]
        metrics = st.columns(6)
        for col, label, value in zip(metrics, ["班级人数", "平均年龄", "最小年龄", "最大年龄", "本月生日", "星座种类"], [s["total"], s["average_age"], s["min_age"], s["max_age"], s["this_month"], int((stats["zodiac"]["人数"] > 0).sum())]):
            col.metric(label, value)
        left, right = st.columns(2)
        with left:
            st.plotly_chart(px.bar(stats["zodiac"], x="人数", y="星座", orientation="h", title="十二星座人数", category_orders={"星座": list(reversed(stats["zodiac"]["星座"].tolist()))}), width="stretch")
            st.dataframe(stats["zodiac"], width="stretch", hide_index=True)
        with right:
            st.plotly_chart(px.pie(stats["element"], names="四象", values="人数", hole=.55, title="四象分布"), width="stretch")
            st.dataframe(stats["element"], width="stretch", hide_index=True)
        st.plotly_chart(px.bar(stats["months"], x="月份", y="人数", title="生日月份分布", category_orders={"月份": list(range(1, 13))}), width="stretch")
        counts = stats["zodiac"].sort_values("人数", ascending=False)
        leaders = "、".join(counts.loc[counts["人数"] == counts.iloc[0]["人数"], "星座"].astype(str)) if counts.iloc[0]["人数"] else "暂无"
        elements = "、".join(f"{r['四象']} {r['人数']} 人" for _, r in stats["element"].iterrows())
        st.info(f"本班共有 {s['total']} 名同学，人数较多的星座是{leaders}。{elements}。星座只是轻松的班级互动话题，了解学生仍应结合真实行为、兴趣、学习状态、同伴关系和长期沟通。")
        st.download_button("导出班级分析.xlsx", export_analysis_excel(students, stats, st.session_state.import_errors), file_name="班级分析.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button("导出班级星座报告.html", export_html_report(students, stats), file_name="班级星座报告.html", mime="text/html")

with tabs[4]:
    st.subheader("学生卡片")
    st.caption(DISCLAIMER)
    if students.empty:
        st.info("添加或导入学生后即可生成学生卡片。")
    else:
        chosen = st.selectbox("选择学生", students["name"].tolist(), key="student_card_name")
        for _, r in students[students["name"] == chosen].iterrows():
            st.markdown(f"### {r['name']}")
            st.write(f"生日：{r['birthday']}　·　年龄：{r['age']} 岁　·　星座：{r['zodiac']}　·　四象：{r['element']}")
            left, right = st.columns(2)
            with left:
                st.subheader("趣味星座内容")
                st.write("关键词：" + "、".join(r["zodiac_keywords"]))
                st.write(r["zodiac_description"])
                st.caption(r["interaction_tip"])
            with right:
                st.subheader(f"年龄阶段提醒 · {r['age_group']}")
                st.write(r["teacher_age_tip"])
            st.divider()

with tabs[5]:
    st.subheader("班级玩法")
    if students.empty:
        st.info("添加或导入学生后即可生成活动内容。")
    else:
        activities = st.tabs(["星座地图", "临时混合小组", "猜猜星座", "生日与祝福", "关键词云", "班级星空海报", "Bingo 与班会问题"])
        with activities[0]:
            st.caption("星座地图用于班会展示；不建议依据星座进行长期座位、成绩、纪律分组或能力分层。")
            for _, r in stats["zodiac"].iterrows():
                names = students.loc[students["zodiac"] == r["星座"], "name"].tolist()
                if names:
                    st.write(f"**{r['星座']}** · {r['人数']} 人：" + "、".join(names))
            st.subheader("四象临时地图")
            for element in ["火象", "土象", "风象", "水象"]:
                st.write(f"{'🔥' if element=='火象' else '🌱' if element=='土象' else '🌬' if element=='风象' else '💧'} {element}：" + "、".join(students.loc[students["element"] == element, "name"].tolist()))
        with activities[1]:
            group_count = st.number_input("临时小组数量", min_value=2, max_value=max(2, len(students)), value=min(4, max(2, len(students))), step=1)
            if st.button("随机生成临时小组"):
                groups = [[] for _ in range(int(group_count))]
                for element in ["火象", "土象", "风象", "水象"]:
                    members = students[students["element"] == element].sample(frac=1, random_state=random.randrange(999999))
                    offset = random.randrange(int(group_count))
                    for index, (_, person) in enumerate(members.iterrows()):
                        groups[(offset + index) % int(group_count)].append(person["name"])
                st.session_state.activity_groups = groups
            for i, group in enumerate(st.session_state.get("activity_groups", []), 1):
                st.write(f"**第 {i} 组：**" + "、".join(group))
            st.caption("小组仅供一次性破冰或游戏使用，不作为长期固定分组。")
        with activities[2]:
            anonymous = st.checkbox("匿名展示", value=True)
            if st.button("随机抽取一位同学"):
                st.session_state.guess_student = students.sample(1).iloc[0].to_dict()
            if "guess_student" in st.session_state:
                person = st.session_state.guess_student
                st.write(("一位同学" if anonymous else person["name"]) + f" · 生日月份：{person['birthday'].month} 月 · 趣味关键词：" + "、".join(person["zodiac_keywords"]))
                st.caption("可以邀请同学猜星座；这是互动游戏，不用于验证个性。")
        with activities[3]:
            month = st.selectbox("查看月份", list(range(1, 13)), index=reference_date.month-1)
            month_names = students[students["birthday"].map(lambda d: d.month == month)]["name"].tolist()
            teacher_only = st.checkbox("仅教师可见模式", value=True)
            if teacher_only:
                st.write(f"{month} 月生日：" + ("、".join(month_names) if month_names else "暂无"))
            else:
                st.write(f"{month} 月共有 {len(month_names)} 位同学过生日。")
            st.caption("生日名单仅在当前本机页面展示，请注意控制可见范围。")
            birthday_students = students[students["birthday"].map(lambda d: d.month == month)]
            if not birthday_students.empty:
                element = birthday_students.iloc[0]["element"]
                wish = {"火象":"愿你保持好奇与行动力，也给自己留一点慢慢长大的时间。", "土象":"愿新的一岁有踏实的收获，也有轻松自在的时刻。", "风象":"愿你继续带着好奇探索新想法，也遇到有趣的新伙伴。", "水象":"愿新的一岁有温暖陪伴，也有自由表达和想象的空间。"}[element]
                st.write(f"生日祝福示例：{wish}")
        with activities[4]:
            st.caption("这是根据星座文化生成的娱乐内容，不代表班级真实性格统计。")
            keyword_counts = {}
            for _, person in students.iterrows():
                for keyword in person["zodiac_keywords"]:
                    keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
            keywords = list(keyword_counts)
            angles = [2 * math.pi * i / max(1, len(keywords)) for i in range(len(keywords))]
            sizes = [16 + 12 * keyword_counts[key] / max(keyword_counts.values()) for key in keywords]
            fig = go.Figure(go.Scatter(x=[0.9 * math.cos(a) for a in angles], y=[0.55 * math.sin(a) for a in angles], mode="text", text=keywords, textfont={"size": sizes, "color": ["#d97706", "#15803d", "#0284c7", "#7c3aed", "#db2777", "#475569"] * 2}, hovertemplate="%{text}<extra></extra>"))
            fig.update_layout(title="班级趣味关键词云", xaxis={"visible": False}, yaxis={"visible": False}, showlegend=False, height=380, margin={"l": 10, "r": 10, "t": 55, "b": 10})
            st.plotly_chart(fig, width="stretch")
        with activities[5]:
            st.write(f"班级人数：{stats['summary']['total']} 人 · 星座种类：{int((stats['zodiac']['人数'] > 0).sum())} 种")
            st.dataframe(stats["zodiac"], width="stretch", hide_index=True)
            st.dataframe(stats["element"], width="stretch", hide_index=True)
            st.download_button("下载班级星空海报 HTML", export_html_report(students, stats), file_name="我的班级星空海报.html", mime="text/html")
        with activities[6]:
            if st.button("生成星座 Bingo 提示"):
                prompts = ["找到一位火象同学", "找到一位和你同月生日的同学", "找到一位水象同学", "找到一位生日在下半年的同学", "找到一位和你不同星座的同学"]
                st.session_state.bingo = random.sample(prompts, 4)
            if "bingo" in st.session_state:
                st.write("　 |　 ".join(st.session_state.bingo))
            questions = ["如果让你设计一次班级活动，你最想加入什么？", "你更喜欢一个人完成任务还是一起讨论？", "你遇到困难时更喜欢先行动还是先制定计划？", "你希望老师怎样给你反馈？"]
            if st.button("随机班会问题"):
                st.session_state.question = random.choice(questions)
            if "question" in st.session_state:
                st.info(st.session_state.question)

with tabs[6]:
    st.subheader("隐私与使用说明")
    st.markdown(ONLINE_PRIVACY_NOTICE)
    st.markdown("星座及四象内容仅用于文化娱乐和班级互动，不属于心理测评、能力评估或教育诊断。请勿据此评价学生成绩、心理、品行或行为。")
