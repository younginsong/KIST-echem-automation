import streamlit as st

# --- 페이지 설정 ---
st.set_page_config(page_title="연구비 증빙 제출 시스템", page_icon="🧾", layout="wide")

st.title("🧾 연구비 지출 증빙 제출 시스템")
st.markdown("""
    ### 🚨 안내사항
    **빈칸을 채우고, 하라는 파일을 올리세요.** 조건이 맞지 않으면 제출 버튼이 활성화되지 않습니다.
    *(지원 파일 형식: PDF, PNG)*
""")
st.divider()

# ==========================================
# [STEP 1] 결제 수단 및 과제 선택
# ==========================================
st.subheader("1. 결제 정보 입력")

col1, col2 = st.columns(2)

with col1:
    payment_method = st.radio(
        "결제 수단을 선택하세요",
        ["법인카드", "연구비카드", "세금계산서"]
    )

with col2:
    if payment_method == "법인카드":
        available_projects = ["법인공용-운영비", "법인공용-LINC사업"]
    elif payment_method == "연구비카드":
        available_projects = ["연구재단-A과제", "산업부-B과제 (Microenvironment)", "환경부-C과제 (CO2)"]
    else: # 세금계산서
        available_projects = ["모든 과제 선택 가능", "연구재단-A과제", "산업부-B과제", "환경부-C과제"]

    project = st.selectbox(f"사용할 과제 계정 ({payment_method} 전용)", ["선택하세요"] + available_projects)

if project == "선택하세요":
    st.info("👈 과제를 선택해야 다음 단계가 열립니다.")
    st.stop()


# ==========================================
# [STEP 2] 100만원 이상 고액 검증
# ==========================================
st.divider()
st.subheader("2. 고액 결제 여부 확인")

amount_check = st.radio(
    "총 결제 금액이 100만 원 이상입니까?",
    ["아니오 (100만 원 미만)", "네 (100만 원 이상)"],
    horizontal=True
)

uploaded_files = {} # 파일 담을 딕셔너리
is_high_price_checked = True 

if amount_check == "네 (100만 원 이상)":
    st.error("💰 100만 원 이상 고액 건입니다. 사전 검수 내역이 필수입니다.")
    uploaded_files['audit_proof'] = st.file_uploader(
        "★ 검수 완료 메일/카톡 캡처 업로드 [필수]", type=['png', 'pdf']
    )
    if not uploaded_files.get('audit_proof'):
        is_high_price_checked = False


# ==========================================
# [STEP 3] 지출 항목별 상세 업로드
# ==========================================
st.divider()
st.subheader("3. 지출 항목 및 증빙 업로드")

if not is_high_price_checked:
    st.warning("👆 위 100만원 이상 검수 증빙을 먼저 올리세요.")
    st.stop()

# --- 지출 항목 리스트 관리 (수정사항 2번 반영) ---
expense_types = [
    "재료비", "연구실 환경 유지비", "사무기기 및 SW", 
    "학회/세미나 등록비", "인쇄비 (포스터/책)", 
    "논문 게재료"
]

# '연구실 운영비'는 세금계산서일 때 아예 안 뜨게 설정
if payment_method != "세금계산서":
    expense_types.append("연구실 운영비 (식대/다과)")

category = st.selectbox("지출 항목을 선택하세요", expense_types)
st.markdown(f"**[{category}]** 선택함 - 아래 필수 서류를 모두 제출하세요.")


# --- 공통 필수 서류 ---
c1, c2 = st.columns(2)
with c1:
    if "카드" in payment_method:
        st.success("💳 카드는 '거래명세서'만 제출하면 됩니다. (매출전표 X)")
    else:
        uploaded_files['tax_invoice'] = st.file_uploader("1. 세금계산서 [필수]", type=['pdf', 'xml', 'png'])

with c2:
    uploaded_files['statement'] = st.file_uploader("2. 거래명세서 [필수]", type=['png', 'pdf'])


# --- 항목별 추가 필수 서류 ---
extra_requirements_met = False 

# [Helper] 인터넷 구매 여부 판단 (카드일 때만)
def check_is_online():
    return st.checkbox("인터넷 주문입니까? (쿠팡, 네이버 등)", value=True)

# -------------------------------------------------------
# Logic Start
# -------------------------------------------------------

if category == "재료비":
    st.success("✅ 재료비는 기본 서류만 제출하면 됩니다.")
    extra_requirements_met = True

elif category == "연구실 환경 유지비":
    # 수정사항 1번: 세금계산서면 사유만, 카드면 캡처+사유
    if payment_method == "세금계산서":
        st.info("세금계산서 건이므로 '필요 사유'만 작성해주세요.")
        reason = st.text_input("4. 필요 사유 작성 [필수]")
        if reason: extra_requirements_met = True
    else:
        # 카드 결제
        st.info("환경용품 구매: 주문내역 캡처와 사유가 필요합니다.")
        uploaded_files['order_capture'] = st.file_uploader("3. 주문내역 캡처 [필수]", type=['png', 'pdf'])
        reason = st.text_input("4. 필요 사유 작성 [필수]")
        if uploaded_files.get('order_capture') and reason:
            extra_requirements_met = True

elif category == "사무기기 및 SW":
    st.info("전산소모품/GPT결제 등")
    # 세금계산서가 아닐 때만 인터넷 여부 물어봄
    is_online = False
    if payment_method != "세금계산서":
        is_online = check_is_online()
    
    if is_online:
        uploaded_files['order_capture'] = st.file_uploader("3. 인터넷 주문내역 캡처", type=['png', 'pdf'])
    
    reason = st.text_input("4. 필요 사유 한 줄 작성 [필수]")
    
    if reason:
        if is_online and not uploaded_files.get('order_capture'):
            extra_requirements_met = False
        else:
            extra_requirements_met = True

elif category == "학회/세미나 등록비":
    st.info("학회비: 등록증, 일시/장소 정보, 등록비 기준표가 모두 필요합니다.")
    c_a, c_b, c_c = st.columns(3)
    uploaded_files['conf_reg'] = c_a.file_uploader("3. 학회등록증", type=['pdf', 'png'])
    uploaded_files['conf_info'] = c_b.file_uploader("4. 일시/장소 캡처", type=['png', 'pdf'])
    uploaded_files['conf_fee'] = c_c.file_uploader("5. 등록비 기준표", type=['png', 'pdf'])
    
    if uploaded_files.get('conf_reg') and uploaded_files.get('conf_info') and uploaded_files.get('conf_fee'):
        extra_requirements_met = True

elif category == "인쇄비 (포스터/책)":
    st.info("인쇄비: 결과물 증빙이 필요합니다.")
    print_type = st.radio("인쇄 종류", ["포스터", "책(제본)"])
    if print_type == "포스터":
        uploaded_files['poster_file'] = st.file_uploader("3. 포스터 원본 파일 (PDF)", type=['pdf'])
        if uploaded_files.get('poster_file'): extra_requirements_met = True
    else:
        uploaded_files['book_cover'] = st.file_uploader("3. 책 앞표지 사진", type=['png', 'pdf'])
        if uploaded_files.get('book_cover'): extra_requirements_met = True

elif category == "논문 게재료":
    st.info("논문: 표지 또는 그림 파일이 필요합니다.")
    paper_type = st.radio("비용 종류", ["게재/교정료", "삽화(그림) 제작비"])
    if paper_type == "게재/교정료":
        uploaded_files['paper_cover'] = st.file_uploader("3. 논문 표지 (교정 시에도 표지)", type=['pdf', 'png'])
        if uploaded_files.get('paper_cover'): extra_requirements_met = True
    else:
        uploaded_files['figure_file'] = st.file_uploader("3. 제작한 그림 파일", type=['png', 'pdf'])
        if uploaded_files.get('figure_file'): extra_requirements_met = True

elif category == "연구실 운영비 (식대/다과)":
    # 수정사항 2번: 카드 전용, 인터넷/오프라인 분기
    # 이미 위에서 '세금계산서'는 이 항목 선택 불가하게 처리함.
    
    # 1. 금액 체크
    is_under_100k = st.checkbox("결제 금액이 10만 원 미만입니까?", value=False)
    
    if not is_under_100k:
        st.error("🚫 연구실 운영비는 10만 원 미만일 때만 청구 가능합니다.")
        extra_requirements_met = False
    else:
        # 2. 구매 경로 질문 (여기서 갈라짐)
        buy_route = st.radio("구매 경로를 선택하세요", ["인터넷 주문", "오프라인 매장(식당/카페 등)"])
        
        if buy_route == "인터넷 주문":
            st.info("인터넷 주문: 주문내역 화면 캡처가 필요합니다.")
            uploaded_files['order_capture'] = st.file_uploader("3. 주문내역 화면 캡처 [필수]", type=['png', 'pdf'])
            if uploaded_files.get('order_capture'): 
                extra_requirements_met = True
        else:
            # 오프라인
            st.warning("⚠️ 오프라인 구매: 상세 품목이 찍힌 영수증이 필요합니다.")
            uploaded_files['detail_receipt'] = st.file_uploader("3. 거래내역(품목) 포함된 영수증 [필수]", type=['png', 'pdf'])
            
            if uploaded_files.get('detail_receipt'):
                extra_requirements_met = True


# --- 최종 제출 버튼 ---
st.divider()

# 1. 기본 서류 체크
basic_files_ok = False
if "카드" in payment_method:
    if uploaded_files.get('statement'):
        basic_files_ok = True
else: # 세금계산서
    if uploaded_files.get('tax_invoice') and uploaded_files.get('statement'):
        basic_files_ok = True

# 제출 가능 여부 판단
all_clear = is_high_price_checked and basic_files_ok and extra_requirements_met

if all_clear:
    if st.button("제출하기 (Submit)", type="primary"):
        st.balloons()
        st.success(f"""
            ✅ 제출 완료!
            - 결제수단: {payment_method}
            - 과제: {project}
            - 항목: {category}
            
            서류가 완벽합니다. 담당자에게 전송되었습니다.
        """)
else:
    st.error("🚫 필수 서류가 누락되었거나 조건이 맞지 않습니다. 위 내용을 확인하세요.")
    st.button("제출 불가 (조건 미달)", disabled=True)
