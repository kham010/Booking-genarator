import os
from flask import Flask, render_template, request, send_file
import openai
import requests
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import uuid

# إعداد التطبيق
app = Flask(__name__)

# إعداد مفاتيح API من المتغيرات البيئية
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

# --- توليد النص ---
def generate_text(prompt):
    try:
        openai.api_key = OPENAI_API_KEY
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message['content']
    except Exception as e:
        return f"❌ خطأ في توليد النص: {str(e)}"

# --- توليد الصور ---
def generate_image(prompt):
    try:
        response = requests.post(
            "https://api.replicate.com/v1/models/stability-ai/sdxl/predictions",
            headers={
                "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
                "Content-Type": "application/json"
            },
            json={"input": {"prompt": prompt}}
        )
        return response.json()['output'][0]
    except Exception as e:
        return "https://via.placeholder.com/300x400?text=فشل+في+توليد+الصورة"

# --- إنشاء PDF ---
def create_pdf(text, image_url, filename):
    try:
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter
        
        # إضافة الغلاف
        if image_url.startswith("http"):
            from reportlab.lib.utils import ImageReader
            img = ImageReader(image_url)
            c.drawImage(img, 50, height - 450, width=200, height=300)
        
        # كتابة النص
        c.setFont("Helvetica", 12)
        lines = text.split('\n')
        y = 700
        for line in lines:
            if y < 50:
                c.showPage()
                y = 750
            c.drawString(50, y, line[:80])  # قصر السطر
            y -= 15
            
        c.save()
        return True
    except Exception as e:
        print(f"❌ خطأ في إنشاء PDF: {str(e)}")
        return False

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate_book():
    prompt = request.form.get("prompt")
    book_type = request.form.get("book_type")

    if not prompt or not book_type:
        return "⚠️ يجب ملء جميع الحقول!"

    # توليد النصوص
    full_prompt = f"""
    أنت كاتب محترف متخصص في {book_type}.
    اكتب كتابًا كاملًا حول "{prompt}" يتضمن:
    - غلاف جذاب بلغة عربية.
    - مقدمة (صفحة واحدة).
    - 5 فصول رئيسية، كل فصل به 3 عناوين فرعية.
    - خاتمة.
    استخدم لغة واضحة ومباشرة تناسب القارئ العربي.
    """
    
    book_text = generate_text(full_prompt)

    # توليد الغلاف
    cover_prompt = f"Arabic book cover showing '{prompt}'"
    cover_url = generate_image(cover_prompt)

    # إنشاء ملف PDF
    filename = f"generated_books/book_{uuid.uuid4()}.pdf"
    success = create_pdf(book_text, cover_url, filename)

    if success:
        return render_template("index.html", book_path=filename)
    else:
        return "❌ فشل في إنشاء الكتاب. حاول مرة أخرى."

if __name__ == "__main__":
    # إنشاء مجلد للكتب المولدة إذا لم يكن موجودًا
    if not os.path.exists("generated_books"):
        os.makedirs("generated_books")
        
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
