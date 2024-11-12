import fitz 
from googletrans import Translator

def extract_text_blocks(pdf_path):
    doc = fitz.open(pdf_path)
    pages_blocks = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        blocks = page.get_text("dict")["blocks"]
        page_blocks = []
        for block in blocks:
            if "lines" in block:
                block_text = ""
                block_bbox = None
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span["text"].strip():
                            bbox = span["bbox"]
                            if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                                bbox = [float(coord) for coord in bbox]
                                if block_bbox is None:
                                    block_bbox = bbox
                                else:
                                    block_bbox[0] = min(block_bbox[0], bbox[0])
                                    block_bbox[1] = min(block_bbox[1], bbox[1])
                                    block_bbox[2] = max(block_bbox[2], bbox[2])
                                    block_bbox[3] = max(block_bbox[3], bbox[3])
                                block_text += span["text"] + " "
                if block_text.strip():
                    page_blocks.append({
                        "text": block_text.strip(),
                        "bbox": block_bbox
                    })
        pages_blocks.append(page_blocks)
    return pages_blocks

def translate_text(text, dest_language):
    translator = Translator()
    try:
        translation = translator.translate(text, dest=dest_language)
        return translation.text
    except Exception as e:
        print(f"Translation error for text: '{text}'")
        print(e)
        return None

def create_translated_pdf(input_pdf_path, output_pdf_path, dest_language='en'):
    doc = fitz.open(input_pdf_path)
    pages_blocks = extract_text_blocks(input_pdf_path)

    for page_num, page_blocks in enumerate(pages_blocks):
        page = doc.load_page(page_num)
        for block in page_blocks:
            text = block["text"]
            bbox = block["bbox"]

            # print(f"Processing block: '{text}' with bbox: {bbox}")

            if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                try:
                    rect = fitz.Rect(bbox)
                    translated_text = translate_text(text, dest_language)

                    if translated_text:
                        page.add_redact_annot(rect, text="")
                        page.apply_redactions()

                        html = f'''
                        <div style="font-size:80px; text-align:justify;">
                            {translated_text}
                        </div>
                        '''                        
                        page.insert_htmlbox(rect, html)
                    else:
                        print(f"Skipping block due to translation error: '{text}'")
                except Exception as e:
                    print(f"Error processing block: '{text}' with bbox: {bbox}")
                    print(e)
            else:
                print(f"Invalid bbox: {bbox}")

    doc.save(output_pdf_path)

if __name__ == "__main__":
    input_pdf = "Odin_english.pdf" 
    output_pdf = "output_translated.pdf"  
    dest_lang = 'es'  
    create_translated_pdf(input_pdf, output_pdf, dest_lang)