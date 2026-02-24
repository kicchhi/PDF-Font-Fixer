from util import replace_font
import fitz
import os
import pymupdf_fonts

file_path = "manual-zh.pdf"
if not os.path.exists(file_path):
    print(f"❌ Файл {file_path} не найден!")
    exit(1)

doc = fitz.open(file_path)
print(f"✅ PDF открыт, страниц: {len(doc)}")

font_name = "figo"
BASE_FONT_SIZE = 14
MIN_FONT_SIZE = 8
LINE_SPACING = 1.2
print(f"✅ Использую шрифт: {font_name}, базовый размер: {BASE_FONT_SIZE}")

font_obj = fitz.Font(font_name)

def calculate_morph_matrix(text, bbox, font_size, font_obj):
    original_width = bbox[2] - bbox[0]
    new_width = font_obj.text_length(text, fontsize=font_size)
    
    if new_width > 0:
        scale_x = original_width / new_width
        scale_y = 1.0
    else:
        scale_x = 1.0
        scale_y = 1.0
    
    scale_x = max(0.7, min(1.3, scale_x))
    return fitz.Matrix(scale_x, scale_y)

def wrap_text_smart(text, max_width, font_size, font_obj):
    """Умный перенос текста с учетом ширины символов"""
    if not text:
        return []
    
    words = text.split(' ')
    lines = []
    current_line = []
    
    for word in words:
        # Пробуем добавить слово к текущей строке
        test_line = ' '.join(current_line + [word])
        test_width = font_obj.text_length(test_line, fontsize=font_size)
        
        if test_width <= max_width:
            # Слово помещается
            current_line.append(word)
        else:
            if not current_line:
                # Строка пуста - слово слишком длинное, разбиваем
                chars = list(word)
                partial = []
                for char in chars:
                    partial.append(char)
                    partial_width = font_obj.text_length(''.join(partial), fontsize=font_size)
                    if partial_width > max_width:
                        # Убираем последний символ
                        partial.pop()
                        if partial:
                            lines.append(''.join(partial))
                        # Начинаем новую строку с оставшимися символами
                        remaining = ''.join(chars[len(partial):])
                        if remaining:
                            current_line = [remaining]
                        break
                else:
                    # Все символы поместились
                    current_line = [word]
            else:
                # Сохраняем текущую строку и начинаем новую
                lines.append(' '.join(current_line))
                current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def group_spans_into_lines(spans, tolerance=5):
    if not spans:
        return []
    
    spans.sort(key=lambda s: s['bbox'][1])
    
    lines = []
    current_line = [spans[0]]
    current_y = spans[0]['bbox'][1]
    
    for span in spans[1:]:
        span_y = span['bbox'][1]
        if abs(span_y - current_y) < tolerance:
            current_line.append(span)
        else:
            lines.append(current_line)
            current_line = [span]
            current_y = span_y
    
    if current_line:
        lines.append(current_line)
    
    return lines

def build_line_text_with_spaces(line_spans):
    if not line_spans:
        return ""
    
    line_spans.sort(key=lambda s: s['bbox'][0])
    
    text_parts = []
    for i, span in enumerate(line_spans):
        text_parts.append(span['text'])
        
        if i < len(line_spans) - 1:
            current_end = span['bbox'][2]
            next_start = line_spans[i+1]['bbox'][0]
            if next_start - current_end > 2:
                text_parts.append(' ')
    
    return ''.join(text_parts)

def calculate_line_height(font_size):
    return font_size * LINE_SPACING

def detect_and_adjust_overlaps(lines_info):
    if not lines_info:
        return lines_info
    
    lines_info.sort(key=lambda x: x['original_y0'])
    adjusted_lines = []
    
    for i, line in enumerate(lines_info):
        new_line = line.copy()
        current_size = line['font_size']
        
        if i > 0:
            prev_line = adjusted_lines[-1]
            prev_bottom = prev_line['y0'] + calculate_line_height(prev_line['font_size'])
            current_top = line['original_y0']
            
            overlap = prev_bottom - current_top
            
            if overlap > 2:
                new_size = max(MIN_FONT_SIZE, current_size - 2)
                new_line['font_size'] = new_size
                new_line['y0'] = current_top
                print(f"   ⚠️ Пересечение: уменьшаем шрифт с {current_size} до {new_size}")
                
                if i > 0:
                    prev_line = adjusted_lines[-1]
                    prev_bottom = prev_line['y0'] + calculate_line_height(prev_line['font_size'])
                    if prev_bottom > new_line['y0']:
                        new_line['y0'] = prev_bottom + 2
            else:
                new_line['font_size'] = BASE_FONT_SIZE
                new_line['y0'] = current_top
        
        adjusted_lines.append(new_line)
    
    return adjusted_lines

def insert_text_with_morph(page, text, x, y, font_size, font_name, matrix):
    point = fitz.Point(x, y)
    page.insert_text(
        point=point,
        text=text,
        fontsize=font_size,
        fontname=font_name,
        morph=(point, matrix)
    )

for page_num in range(len(doc)):
    page = doc[page_num]
    print(f"\n📄 Обработка страницы {page_num + 1}")
    
    blocks = page.get_text("dict")["blocks"]
    all_spans = []
    
    for block in blocks:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    if span["text"].strip():
                        all_spans.append({
                            'text': span["text"],
                            'bbox': span["bbox"],
                            'size': span["size"]
                        })
    
    lines = group_spans_into_lines(all_spans)
    
    lines_info = []
    for line_spans in lines:
        if line_spans:
            x0 = min(s['bbox'][0] for s in line_spans)
            y0 = min(s['bbox'][1] for s in line_spans)
            x1 = max(s['bbox'][2] for s in line_spans)
            line_text = build_line_text_with_spaces(line_spans)
            
            lines_info.append({
                'spans': line_spans,
                'text': line_text,
                'x0': x0,
                'y0': y0,
                'x1': x1,
                'original_y0': y0,
                'font_size': BASE_FONT_SIZE
            })
    
    adjusted_lines = detect_and_adjust_overlaps(lines_info)
    
    # Удаляем старый текст
    for line_info in lines_info:
        for span in line_info['spans']:
            rect = fitz.Rect(span['bbox'])
            page.add_redact_annot(rect)
    
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
    
    blocks_processed = 0
    
    for line_info in adjusted_lines:
        try:
            line_text = line_info['text']
            x0 = line_info['x0']
            y0 = line_info['y0']
            x1 = line_info['x1']
            font_size = line_info['font_size']
            
            # Ширина блока
            block_width = x1 - x0
            
            # Разбиваем текст на строки с учетом ширины
            wrapped_lines = wrap_text_smart(line_text, block_width, font_size, font_obj)
            
            for i, wrapped_line in enumerate(wrapped_lines):
                # Теперь применяем морфинг к каждой строке отдельно
                matrix = calculate_morph_matrix(
                    wrapped_line, 
                    [x0, y0, x1, y0 + font_size], 
                    font_size, 
                    font_obj
                )
                
                # Позиция Y для каждой подстроки
                y_pos = y0 + i * font_size * LINE_SPACING + font_size * 0.8
                
                insert_text_with_morph(page, wrapped_line, x0, y_pos, font_size, font_name, matrix)
                blocks_processed += 1
            
        except Exception as e:
            print(f"   ⚠️ Ошибка при обработке строки: {e}")
    
    print(f"   ✅ Обработано строк: {blocks_processed}")

output = "manual-fixed.pdf"
doc.save(output, garbage=4, deflate=True)
doc.close()
print(f"\n✅ Готово: {output}")
