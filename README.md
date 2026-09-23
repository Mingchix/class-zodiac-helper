# 班级星座小助手 Online

基于 Streamlit 的班级生日、星座和四象趣味统计工具。

Online 版本仅支持：

- 手动输入姓名 + 出生日期
- Excel 上传姓名 + 出生日期（`.xlsx` / `.xls`）

Online 版本不支持身份证号。请勿上传身份证号码，也不要上传与本功能无关的家庭住址、电话号码、医疗信息等敏感信息。云端会接收必要的姓名与生日用于当前会话分析；数据不写入永久数据库。可使用“清空当前数据”结束并清除本会话中的应用数据。

星座和四象仅供文化娱乐与班级互动，不属于心理测评、能力评估或教育诊断，不应用于成绩、纪律、分班、座位或教育机会判断。

## 本地运行

```bash
python -m venv .venv-online
```

Windows PowerShell：

```powershell
.\.venv-online\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

macOS / Linux：

```bash
source .venv-online/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Excel 格式

推荐第一行为表头，包含“姓名”和“出生日期”。姓名列别名支持：`姓名`、`学生姓名`、`名字`、`Name`；生日列别名支持：`生日`、`出生日期`、`出生年月`、`出生年月日`、`出生时间`、`DOB`、`Birthday`。无法识别时可以手动选择安全列。

日期支持 `2012-03-21`、`2012/03/21`、`2012.03.21`、`20120321` 和 Excel 原生日期。被识别为证件号码、地址、电话或医疗信息的列会在 Excel 读取阶段排除，不进入页面预览、分析或导出。

## 测试

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## 隐私和部署

本项目不调用外部 API 或第三方分析服务。运行于 Streamlit Community Cloud 时，用户上传的姓名和生日会经网络传至云端服务器处理；不要上传身份证号或其他与分析无关的敏感信息。应用不配置云端永久学生数据库。

首次部署请在 Streamlit Community Cloud 连接此仓库并选择 `main` 分支和 `app.py`。项目不需要 API Key、数据库密码或 Streamlit Secrets。
