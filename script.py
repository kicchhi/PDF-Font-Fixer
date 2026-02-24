from util import replace_font
import fitz
import os
import pymupdf_fonts  # важно импортировать!

file_path = "ML1.pdf"
if not os.path.exists(file_path):
    print(f"❌ Файл {file_path} не найден!")
    exit(1)

doc = fitz.open(file_path)
print(f"✅ PDF открыт, страниц: {len(doc)}")

# Доступные шрифты после установки pymupdf-fonts:
# "figo" - FiraGO (поддерживает кириллицу)
# "cjk" - CJK (поддерживает кириллицу)
# "notos" - Noto Sans (поддерживает кириллицу)

font_name = "figo"  # или "cjk", "notos"
print(f"✅ Использую шрифт: {font_name}")

for page_num in range(len(doc)):
    page = doc[page_num]
    print(f"📄 Обработка страницы {page_num + 1}")
    
    blocks = page.get_text("dict")["blocks"]
    blocks_count = 0
    
    for block in blocks:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    if span["text"].strip():
                        try:
                            replace_font(
                                doc,
                                page_num,
                                span["bbox"],
                                font_name,  # имя встроенного шрифта
                                72
                            )
                            blocks_count += 1
                        except Exception as e:
                            print(f"   ⚠️ Ошибка: {e}")
    
    print(f"   ✅ Обработано блоков: {blocks_count}")

output = "ML-fixed.pdf"
doc.save(output, garbage=4, deflate=True)
doc.close()
print(f"✅ Готово: {output}") 
