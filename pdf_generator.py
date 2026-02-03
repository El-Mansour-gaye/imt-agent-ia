from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import tempfile

def generate_reco_pdf(profile_text: str) -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(tmp.name, pagesize=A4)

    c.setFont("Helvetica", 12)
    c.drawString(40, 800, "Plan personnalisé – IMT")
    c.drawString(40, 770, "Analyse de votre profil :")
    
    y = 740
    for line in profile_text.split("\n"):
        c.drawString(40, y, line)
        y -= 15

    c.showPage()
    c.save()
    return tmp.name
