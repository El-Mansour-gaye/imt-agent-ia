from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import tempfile

def generate_reco_pdf(profile_text: str) -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(tmp.name, pagesize=A4)

    c.setFont("Helvetica", 12)
    c.drawString(40, 800, "Plan personnalisé – IMT")
    c.drawString(40, 770, "Analyse de votre profil :")
    
    text_obj = c.beginText(40, 740)
    text_obj.setFont("Helvetica", 10)
    text_obj.setLeading(14)

    # Découpage basique pour éviter de sortir de la page
    for line in profile_text.split("\n"):
        # On pourrait ajouter un wrapping ici si nécessaire
        text_obj.textLine(line)

    c.drawText(text_obj)
    c.showPage()
    c.save()
    return tmp.name
