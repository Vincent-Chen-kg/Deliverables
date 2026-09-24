import asyncio
import json
from pathlib import Path
from docx import Document
from docx.shared import Inches
from datetime import datetime, timedelta


SCRIPT_DIR = Path(__file__).resolve().parent
PARENT_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR =  PARENT_DIR / "templates"

def load_manifest(json_path: str, key) -> list:
    """Reads the JSON manifest and returns a set of registered image titles."""
    path = Path(json_path)
    if not path.is_file():
        raise FileNotFoundError(f"Manifest not found at {json_path}")
        
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
        return data.get(key, [])


def resolve_image_path(title: str, manifest: set, path: str, extension: str = ".png") -> Path | None:
    """Validates if image is registered in manifest and exists on disk."""
    if title not in manifest:
        return None
        
    img_path = Path(SCRIPT_DIR / f"{path}/{title}{extension}")
    return img_path if img_path.is_file() else None


def find_paragraphs_by_style(doc: Document, target_style: str):
    """Yields (index, paragraph) tuples that match target style name."""
    target = target_style.lower()
    for index, para in enumerate(doc.paragraphs):
        if target in para.style.name.lower():
            yield index, para


def insert_image_below_paragraph(doc: Document, index: int, image_path: Path, width_inches: float = 6.5):
    """Inserts an image into the paragraph following the index, handling doc bounds."""
    run = get_below_paragraph(doc, index)
    run.add_picture(str(image_path), width=Inches(width_inches))

def get_below_paragraph(doc: Document, index: int, ):
    if index + 1 < len(doc.paragraphs):
        target_para = doc.paragraphs[index + 1]
    else:
        target_para = doc.add_paragraph()

    return target_para.add_run()


def _sync_process_document(
    doc: Document,
    output_path: str,
    target_style: str,
    json_path: str,
    path: str,
    image_width: float
) -> int:
    """Synchronous pipeline that combines I/O, matching, and editing."""
    manifest = set(load_manifest(SCRIPT_DIR / json_path, "images"))
    inserted_count = 0

    print("--- Processing Paragraphs ---")
    for index, paragraph in find_paragraphs_by_style(doc, target_style):
        title = paragraph.text.strip()
        print(f"Matched Paragraph {index} [{paragraph.style.name}]: '{title}'")

        img_path = resolve_image_path(title, manifest, path)
        if img_path:
            insert_image_below_paragraph(doc, index, img_path, width_inches=image_width)
            inserted_count += 1
            print(f"  └─ Successfully inserted image: {img_path}")
        else:
            print(f"  └─ Image resolution failed for '{title}'. Check {json_path} or file existence.")

    if inserted_count > 0:
        doc.save(output_path)
        print(f"\nSaved modified document to: {output_path}")
    
    return inserted_count

async def add_image_after_figure_label_async(
    doc: Document,
    output_path: str,
    target_style: str = "figure title",
    json_path: str = "images.json",
    path: str =  ".",
    image_width: float = 6.5,
    **kwargs
) -> int:
    """Non-blocking async wrapper to process docx files."""
    return await asyncio.to_thread(
        _sync_process_document,
        doc,
        output_path,
        target_style,
        json_path,
        path,
        image_width
    )


def add_text_to_paragraphs(doc:Document, section_name: str, output_path: str, month, style:str, indentifier: str, json_path: str):
    sections = load_manifest(PARENT_DIR / json_path,section_name)

    for index, paragraph in find_paragraphs_by_style(doc, style):
        title = paragraph.text.strip()
        
        if indentifier not in title:
            continue
        section_num = int(title.split(".", 1)[0])-1

        print(f"Matched Paragraph {index} [{paragraph.style.name}]: '{title}'")
        if section_num < len(sections):
            run = get_below_paragraph(doc, index)
            run.text +=sections[section_num].format(target_date=month)
        break

    doc.save(output_path)


async def main(path: str=".", date: str | None = None, template: str = TEMPLATE_DIR / "template2.docx"
) -> None:
    if not Path(template).exists():
        raise FileNotFoundError(f"Template not found at {template}")
        
    # Handle dynamic default arguments cleanly
    month = date or datetime.now().strftime("%B %Y")

    doc = Document(template)

    output_path=f"{path}/deliverable.docx"
    inserted = await add_image_after_figure_label_async(
        doc=doc,
        output_path=output_path,
        target_style="figure title",
        path=path
    )
    print(f"Finished processing. Total images inserted: {inserted}")
    
    ex_sum_path = "executive_summaries.json"
    if Path(ex_sum_path).exists():
        add_text_to_paragraphs(
            doc=doc, 
            output_path=output_path, 
            json_path=ex_sum_path,
            section_name="sections",
            style= "heading", 
            indentifier= "Executive summary",
            month = month
        )
    else:
        print(f"Executive summaries JSON not found at {ex_sum_path}")
    
    print(f"\nSaved modified document to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())