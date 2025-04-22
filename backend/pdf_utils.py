from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def generate_pdf_from_json(data, output_path):
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    y = height - 40
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "Extracted Legal Document Data")
    c.setFont("Helvetica", 12)
    y -= 30

    def draw_dict(d, indent=0):
        nonlocal y
        for k, v in d.items():
            if isinstance(v, dict):
                c.drawString(40 + indent*20, y, f"{k}:")
                y -= 18
                draw_dict(v, indent+1)
            else:
                c.drawString(40 + indent*20, y, f"{k}: {v}")
                y -= 18

    draw_dict(data)
    c.save()
