from pathlib import Path

from openpyxl import Workbook

HEADERS = ["序号", "测试用例标题", "测试步骤", "预期结果", "执行状态", "实际结果", "失败描述", "关联 Issue"]


def generate_checklist(source_markdown: Path, output_excel: Path) -> None:
    lines = source_markdown.read_text(encoding="utf-8").splitlines()
    title = "未命名测试用例"
    steps = ""
    expected = ""
    for line in lines:
        if line.startswith("## "):
            title = line.removeprefix("## ").strip()
        elif line.startswith("步骤:"):
            steps = line.removeprefix("步骤:").strip()
        elif line.startswith("预期:"):
            expected = line.removeprefix("预期:").strip()

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(HEADERS)
    sheet.append([1, title, steps, expected, "pending", "", "", ""])
    workbook.save(output_excel)
