import streamlit as st
import google.generativeai as genai
import pandas as pd
from io import BytesIO
from pypdf import PdfReader
from openpyxl.styles import Alignment, Font, Border, Side

st.set_page_config(page_title="VC 정밀 심사 리포트 시스템", layout="wide")
st.markdown("""
    <style>
    .report-box { padding: 20px; border-radius: 10px; border: 1px solid #ddd; background-color: #f9f9f9; }
    .critical { color: #d9534f; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚖️ 전문 심사역 정밀 리포트 생성기")

api_key = st.sidebar.text_input("Google API Key 입력", type="password")

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

if api_key:
    try:
        genai.configure(api_key=api_key)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        selected_model_name = next((m for m in available_models if 'pro' in m), "models/gemini-1.5-pro-latest")
        model = genai.GenerativeModel(selected_model_name)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            eval_criteria = st.text_area("📋 평가 지표 및 배점 가이드", height=200, placeholder="여기에 심사 기준을 상세히 넣으세요.")
        with col2:
            uploaded_files = st.file_uploader("📄 제안서(PDF) 업로드", type=['pdf'], accept_multiple_files=True)

        if st.button("🔥 AI Studio급 정밀 리포트 발행"):
            if not uploaded_files or not eval_criteria:
                st.warning("심사 기준과 파일을 모두 준비해 주세요.")
            else:
                results = []
                individual_reports = {}
                progress_bar = st.progress(0)
                
                for i, file in enumerate(uploaded_files):
                    st.write(f"🔬 {file.name} 분석 및 리포트 편집 중...")
                    pdf_text = extract_text_from_pdf(file)
                    
                    # AI STUDIO의 그 형식을 강제하는 프롬프트
                    prompt = f"""
                    당신은 20년 경력의 까칠한 VC 심사역입니다. 다음 제안서를 현미경 분석하여 '보고서' 형태로 출력하세요.
                    말투는 냉철하고 전문적이어야 하며, 미사여구는 모두 걷어내세요.

                    [심사 기준]
                    {eval_criteria}

                    [제안서 원문]
                    {pdf_text}

                    [리포트 필수 포함 내용 및 형식]
                    
                    # 1. 종합 평가 결과
                    - 점수: [00점] / 요약: [한 줄로 이 사업의 치명적 결함을 기술]

                    # 2. [0단계: 사전 내부 검토]
                    - 제안서 전체의 논리적 흐름과 비즈니스 모델의 현실성 비판.

                    # 3. [1단계: 실현 불가능한 구절 및 수치 비판]
                    - 본문의 특정 수치를 인용하여 '수치적 모순'을 증명할 것. (예: 인건비와 사업규모 불일치, 목표 인원과 매출의 괴리 등)

                    # 4. [2단계: 산업 수준 대비 진부함/차별성 판단]
                    - 2026년 현재 시장 기준에서 이 사업이 왜 진부한지, 경쟁사 대비 왜 부족한지 기술.

                    # 5. [3단계: 심사위원 압박 질문]
                    - 면접 시 기업을 무너뜨릴 날카로운 질문 5개.

                    # 6. 본 보고서 (상세 분석)
                    - [Risk Analysis]: R-1(운영), R-2(경제적), R-3(전략적)으로 구분하여 비판.
                    - [세부 점수표]: 사용자가 준 기준에 맞춰 점수를 매기고 '감점 근거'를 상세히 작성.
                    - [Red Flag]: 데이터 분식, 근거 부재, 실행력 의심 요소 나열.

                    결과 첫 줄은 반드시 '점수: 00점, 요약: 내용' 형식을 지키고, 이후부터는 위 목차대로 '리포트' 형식으로 작성하세요.
                    """
                    
                    response = model.generate_content(prompt)
                    full_text = response.text
                    
                    try:
                        first_line = full_text.split('\n')[0]
                        score = first_line.split('점수:')[1].split(',')[0].strip()
                        summary = first_line.split('요약:')[1].strip()
                    except:
                        score = "N/A"; summary = "상세 리포트 참조"

                    results.append({"파일명": file.name, "점수": score, "독설 요약": summary})
                    individual_reports[file.name] = full_text
                    progress_bar.progress((i + 1) / len(uploaded_files))

                # 엑셀 생성 및 '편집 수준'의 포맷팅 적용
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # 시트 1: 종합 요약
                    pd.DataFrame(results).to_excel(writer, index=False, sheet_name='종합분석표')
                    
                    # 시트 2~: 기업별 개별 리포트 (편집 적용)
                    for name, report in individual_reports.items():
                        report_lines = report.split('\n')
                        df_report = pd.DataFrame(report_lines, columns=[f'[{name}] 심사 보고서'])
                        df_report.to_excel(writer, index=False, sheet_name=name[:25])
                        
                        # 스타일링 (가독성 향상)
                        ws = writer.sheets[name[:25]]
                        ws.column_dimensions['A'].width = 120 # 칸을 대폭 넓힘
                        for cell in ws['A']:
                            cell.alignment = Alignment(wrap_text=True, vertical='top') # 줄바꿈 적용
                            if '#' in str(cell.value) or '[' in str(cell.value):
                                cell.font = Font(bold=True, size=12) # 소제목 강조
                
                st.success("✅ 편집이 완료된 정밀 리포트가 생성되었습니다.")
                st.download_button(label="📁 전문 심사 리포트 다운로드", data=output.getvalue(), file_name="AI_정밀_심사리포트_최종.xlsx")
                
    except Exception as e:
        st.error(f"⚠️ 시스템 오류: {e}")
else:
    st.info("💡 사이드바에 API Key를 입력하면 '정밀 리포트' 모드가 활성화됩니다.")
