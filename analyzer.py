import os

def analyze_site(data):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"status": "لم يتم تشغيل AI", "message": "أضف OPENAI_API_KEY لتفعيل التحليل الذكي."}
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    corpus = "\n\n".join(f"URL: {p['url']}\nTITLE: {p['title']}\nTEXT: {p['text'][:7000]}" for p in data["pages"])[:50000]
    prompt = f'''أنت محلل مواقع ومتاجر إلكترونية. حلل الموقع التالي بشكل عملي وقابل للتحويل إلى تقرير تجاري.
ركز على: تجربة العميل والثقة؛ وضوح الاسترجاع والاستبدال؛ وضوح الشحن والتوصيل؛ الخصوصية؛ قنوات التواصل والشكاوى؛ نقاط القوة؛ الفجوات والمخاطر؛ فرص التحسين ذات الأولوية.
لا تخترع معلومات غير موجودة. إذا لم تجد معلومة قل "غير موجودة". أجب بالعربية وبعناوين واضحة، واذكر الأدلة من الصفحات عند توفرها.
البيانات:\n{corpus}'''
    response = client.responses.create(model=os.getenv("OPENAI_MODEL", "gpt-5-mini"), input=prompt)
    return {"ai_analysis": response.output_text}
