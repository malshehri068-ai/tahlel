import streamlit as st
from crawler import crawl_site
from analyzer import analyze_site
from report import build_pdf

st.set_page_config(page_title="تحليل | Tahlel", page_icon="📊", layout="wide")
st.title("تحليل")
st.caption("تحليل المواقع والمتاجر: زحف ذكي + تحليل AI + تقرير PDF قابل للتسليم")

url = st.text_input("رابط الموقع", placeholder="https://example.com")
max_pages = st.slider("الحد الأقصى للصفحات", 5, 50, 20)
use_ai = st.checkbox("تفعيل تحليل AI", value=True)

if st.button("ابدأ التحليل", type="primary", disabled=not url):
    with st.spinner("جاري الزحف والتحليل..."):
        data = crawl_site(url, max_pages=max_pages)
        analysis = analyze_site(data) if use_ai else {}
        st.session_state["data"] = data
        st.session_state["analysis"] = analysis

if "data" in st.session_state:
    data = st.session_state["data"]
    analysis = st.session_state.get("analysis", {})
    st.subheader("ملخص")
    cols = st.columns(5)
    labels = [("returns", "الاسترجاع"), ("shipping", "الشحن"), ("privacy", "الخصوصية"), ("complaints", "الشكاوى"), ("contact", "التواصل")]
    for col, (key, label) in zip(cols, labels):
        col.metric(label, "موجود" if data["special_pages"].get(key) else "غير موجود")
    st.subheader("الصفحات المكتشفة")
    for key, value in data["special_pages"].items():
        st.write(f"**{key}**: {value or 'لم يتم العثور عليها'}")
    st.subheader("عدد الصفحات المفحوصة")
    st.write(len(data["pages"]))
    if analysis:
        st.subheader("تحليل AI")
        if analysis.get("ai_analysis"):
            st.write(analysis["ai_analysis"])
        else:
            st.info(analysis.get("message", "لم يتوفر تحليل AI."))
    if st.button("توليد تقرير PDF"):
        pdf = build_pdf(data, analysis)
        st.download_button("تحميل التقرير", pdf, "tahlel-report.pdf", "application/pdf")
