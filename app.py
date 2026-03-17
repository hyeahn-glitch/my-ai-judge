import streamlit as st
import google.generativeai as genai
import pandas as pd
from io import BytesIO
from pypdf import PdfReader

# 1. 페이지 설정
st.set_page_config(page_title="AI 전문 심사역", layout="wide")
st.title("⚖️ AI 다중 제안서 심사 시스템 (최종 완성판)")

# 2. 사이드바 API 키
api_key = st.sidebar.text_input("Google API Key 입력", type="password")

def extract_text_from_pdf(pdf_file):
    """PDF에서 텍스트를 안전하게 추출하는 함수"""
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

if api_key:
    try:
        genai.configure(api_key=api_key)
        # 2026년 기준 가장 범용적인 모델 명칭 사용
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        col1, col2 = st.columns(2)
        with col1:
            eval_criteria = st.text_area("심사 기준 (엑셀 내용을 복사해서 넣으세요)", height=200)
        with col2:
            uploaded_files = st.file_uploader("제안서 PDF 업로드", type=['pdf'], accept_multiple_files=True)

        if st.button("🚀 심사 시작 및 리포트 생성"):
            if not uploaded_files or not eval_criteria:
                st.warning("심사 기준과 파일을 모두 확인해 주세요.")
            else:
                results = []
                individual_reports = {}
                progress_bar = st.progress(0)
                
                for i, file in enumerate(uploaded_files):
                    st.write(f"🔍 {file.name} 분석 중...")
                    
                    try:
                        # PDF에서 텍스트 추출
                        pdf_text = extract_text_from_pdf(file)
                        
                        prompt = f"""
                        당신은 냉철한 전문 심사역입니다. 다음 심사 기준에 따라 제안서를 분석하세요.
                        [심사 기준]
                        {eval_criteria}
                        
                        [제안서 본문]
                        {pdf_text}
                        
                        [요구사항 - 반드시 지킬 것]
                        1. 결과의 첫 줄은 반드시 '점수: 00점, 요약: 내용' 형식으로 작성하세요.
                        2. 그 아래에 '지능형 리서치', '의사결정 지원(근거)', '불성실 탐지(레드플래그)' 내용을 구체적으로 쓰세요.
                        3. 전문적이고 비판적인 톤을 유지하세요.
                        """
                        
                        response = model.generate_content(prompt)
                        full_text = response.text
                        
                        # 데이터 요약 추출
                        try:
                            summary_line = full_text.split('\n')[0]
                            score = summary_line.split('점수:')[1].split(',')[0].strip()
                            summary = summary_line.split('요약:')[1].strip()
                        except:
                            score = "확인필요"
                            summary = "요약 추출 오류 (상세 시트 확인)"

                        results.append({"기업/파일명": file.name, "점수": score, "핵심 요약": summary})
                        individual_reports[file.name] = full_text
                        
                    except Exception as e:
                        st.error(f"{file.name} 처리 중 오류: {str(e)}")
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))

                # 3. 엑셀 파일 생성
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    pd.DataFrame(results).to_excel(writer, index=False, sheet_name='종합분석표')
                    for name, report in individual_reports.items():
                        # 시트 이름은 30자 제한
                        clean_name = name[:25].replace(".pdf", "")
                        pd.DataFrame([{"상세 리포트": report}]).to_excel(writer, index=False, sheet_name=clean_name)
                
                st.success("✅ 심사가 완료되었습니다!")
                st.download_button(
                    label="📁 심사 결과 엑셀 다운로드",
                    data=output.getvalue(),
                    file_name="AI_심사_결과보고서.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
    except Exception as e:
        st.error(f"⚠️ 시스템 연결 오류: {e}. API 키가 정확한지 확인해 주세요.")
else:
    st.info("💡 왼쪽 사이드바에 Google API Key를 입력하면 시작할 수 있습니다.")
