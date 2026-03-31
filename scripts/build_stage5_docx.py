from pathlib import Path
import re

from docx import Document
from docx.shared import Pt


ROOT = Path(r"C:\Users\Misha\Documents\GitHub\MyProject1")
SOURCE_PATH = ROOT / "docs" / "stage5_submission_ru.md"
OUTPUT_PATH = ROOT / "docs" / "5.docx"


def normalize_line(line: str) -> str:
    line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1: \2", line)
    line = line.replace("`", "")
    return line


def main() -> None:
    text = SOURCE_PATH.read_text(encoding="utf-8")
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(14)

    for raw_line in text.splitlines():
        document.add_paragraph(normalize_line(raw_line.strip()))

    document.save(OUTPUT_PATH)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
