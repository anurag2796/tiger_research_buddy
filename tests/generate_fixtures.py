
import fitz
import os

def create_digital_pdf(path):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "This is a digital text PDF. It contains searchable text.", fontsize=12)
    page.insert_text((50, 70), "Lorem ipsum dolor sit amet, consectetur adipiscing elit.", fontsize=10)
    page.insert_text((50, 90), "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.", fontsize=10)
    page.insert_text((50, 110), "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.", fontsize=10)
    doc.save(path)
    print(f"Created {path}")

def create_scanned_pdf(path):
    doc = fitz.open()
    page = doc.new_page()
    # Create an image appearance by drawing text as shapes/image
    # actually easiest is to render a page to image then put it back
    
    # temp doc to render
    temp = fitz.open()
    tp = temp.new_page()
    tp.insert_text((50, 50), "This is a scanned PDF (image only).", fontsize=12)
    pix = tp.get_pixmap()
    
    # insert image to real doc
    page.insert_image(page.rect, pixmap=pix)
    doc.save(path)
    print(f"Created {path}")

def create_mixed_rotated_pdf(path):
    doc = fitz.open()
    
    # Page 1: Digital Text
    p1 = doc.new_page()
    p1.insert_text((50, 50), "Page 1: Digital Text.", fontsize=12)
    
    # Page 2: Rotated Text
    p2 = doc.new_page()
    p2.insert_text((50, 50), "Page 2: Rotated 90 Degrees.", fontsize=12)
    p2.set_rotation(90)
    
    # Page 3: Scanned Image
    p3 = doc.new_page()
    # reuse pixmap logic
    temp = fitz.open()
    tp = temp.new_page()
    tp.insert_text((50, 50), "Page 3: Scanned Image.", fontsize=12)
    pix = tp.get_pixmap()
    p3.insert_image(p3.rect, pixmap=pix)
    
    doc.save(path)
    print(f"Created {path}")

def create_tables_complex_pdf(path):
    doc = fitz.open()
    page = doc.new_page()
    
    text = "Here is some financial data:\n\n"
    page.insert_text((50, 50), text, fontsize=12)
    
    # Simulate a table without grid lines (heuristic bait)
    y = 80
    header = "Year    Revenue    Cost    Profit"
    page.insert_text((50, y), header, fontname="Courier", fontsize=10)
    y += 15
    
    rows = [
        "2020    1000       800     200",
        "2021    1200       900     300",
        "2022    1500       1000    500",
        "2023    1800       1200    600",
    ]
    
    for row in rows:
        page.insert_text((50, y), row, fontname="Courier", fontsize=10)
        y += 15
        
    page.insert_text((50, y+20), "End of data.", fontsize=12)
    doc.save(path)
    print(f"Created {path}")

if __name__ == "__main__":
    os.makedirs("tests/fixtures", exist_ok=True)
    create_digital_pdf("tests/fixtures/digital.pdf")
    create_scanned_pdf("tests/fixtures/scanned.pdf")
    create_mixed_rotated_pdf("tests/fixtures/mixed_rotated.pdf")
    create_tables_complex_pdf("tests/fixtures/tables_complex.pdf")
