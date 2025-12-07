import streamlit as st
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# ==========================================
# [설정] 페이지 및 디자인
# ==========================================
st.set_page_config(page_title="연구비 증빙 제출 시스템", page_icon="🧾", layout="wide")

st.markdown("""
    <style>
    [data-testid="stFileUploader"] {
        background-color: #f8f9fa;
        border: 2px dashed #cccccc;
        border-radius: 10px;
        padding: 15px;
        transition: all 0.3s ease;
    }
    [data-testid="stFileUploader"]:hover {
        background-color: #e3e6ea;
        border-color: #4CAF50;
    }
    [data-testid="stFileUploader"] section > div {
        color: #333333;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🧾 연구비 지출 증빙 제출 시스템")
st.markdown("### 🚨 안내: 작성된 내용은 안희영 선생님에게 메일로 전송됩니다.")
st.divider()

# ==========================================
# [기능 0] 상태 초기화 함수
# ==========================================
def reset_amount_check():
    # 결제 수단이 바뀌면 고액 여부를 무조건 '아니오'로 돌려놓음
    st.session_state['amount_radio_key'] = "아니오 (100만 원 미만)"


# ==========================================
# [기능 1] 이메일 발송 함수
# ==========================================
def send_email_with_attachments(data_summary, files_dict):
    try:
        sender_email = st.secrets["email"]["sender_address"]
        sender_pass = st.secrets["email"]["sender_password"]
        receiver_emails = st.secrets["email"]["receiver_address"]

        msg = MIMEMultipart()
        msg['Subject'] = f"[연구비제출] {data_summary['성명']} - {data_summary['항목']} ({data_summary['날짜']})"
        msg['From'] = sender_email
        msg['To'] = receiver_emails

        body = f"""
        <h3>🧾 연구비 증빙 서류 제출 알림</h3>
        <p>연구비 지출 증빙 서류가 접수되었습니다.</p>
        <p>아래 내용을 확인하여 시스템에 등록 부탁드립니다.</p>
        <hr>
        <ul>
            <li><b>성명:</b> <span style="color:blue;">{data_summary['성명']}</span></li>
            <li><b>과제명:</b> {data_summary['과제']}</li>
            <li><b>지출항목:</b> {data_summary['항목']} ({data_summary['결제수단']})</li>
            <li><b>고액여부:</b> {data_summary['고액']}</li>
            <li><b>사유/내용:</b> {data_summary['사유']}</li>
            <li><b>제출일시:</b> {data_summary['날짜']} (KST)</li>
        </ul>
        <hr>
        <p>※ 첨부된 파일({len([f for f in files_dict.values() if f is not None])}개)을 확인해주세요.</p>
        """
        msg.attach(MIMEText(body, 'html'))

        for key, file_obj in files_dict.items():
            if file_obj is not None:
                file_obj.seek(0)
                safe_name = f"{data_summary['날짜'][:10]}_{data_summary['성명']}_{key}_{file_obj.name}"
                part = MIMEApplication(file_obj.read(), Name=safe_name)
                part.add_header('Content-Disposition', 'attachment', filename=safe_name)
                msg.attach(part)

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_pass)
            server.send_message(msg)
        
        return True
    except Exception as e:
        st.error(f"📧 메일 발송 실패: {e}")
        return False


# ==========================================
# [UI] 화면 구성
# ==========================================

# [STEP 0] 사용자 이름 입력
st.subheader("0. 신청자 정보")

member_list = [
    "선택하세요",
    "가서현", "강은솔", "강장훈", "고성현", "김다연", "김도경", "김도일", "김동진", 
    "김민기", "김민솔", "김성례", "김소희", "김은수", "김응답", "김충희", "김현영", 
    "김현우", "김현철", "김형래", "류태경", "마가렛", "맹정훈", "박담대", "박민우", 
    "박수빈", "박예찬", "박준범", "박준우", "박지수", "박지현", "방현석", "서범원", 
    "서새인", "석다현", "소원", "송영인", "엄희성", "오명환", "왕찌아루", "우종인", 
    "유미린", "윤지은", "윤하영", "이경록", "이나라", "이대현", "이미영", "이영록", 
    "이우진", "이정연", "이준호", "이지민", "이형건", "이호진", "임재형", "임철완", 
    "장규민", "전지호", "정원석", "조성호", "조은별", "채영현", "최동철", "최수민", 
    "최원용", "최재형", "케지아", "한만호", "현우인", "황수현"
]

user_name = st.selectbox("신청자 성명", member_list)

if user_name == "선택하세요":
    st.info("성명을 먼저 선택해주세요.")
    st.stop()

# [STEP 1] 결제 정보
st.subheader("1. 결제 정보 입력")
col1, col2 = st.columns(2)
with col1:
    payment_method = st.radio(
        "결제 수단을 선택하세요", 
        ["법인카드", "연구비카드", "세금계산서"],
        key="payment_method_radio",
        on_change=reset_amount_check
    )

with col2:
    if payment_method == "법인카드":
        available_projects = ["법인공용-운영비", "법인공용-LINC사업"]
    elif payment_method == "연구비카드":
        available_projects = ["연구재단-A과제", "산업부-B과제 (Microenvironment)", "환경부-C과제 (CO2)"]
    else: 
        available_projects = ["모든 과제 선택 가능", "연구재단-A과제", "산업부-B과제", "환경부-C과제"]
    project = st.selectbox(f"사용할 과제 계정", ["선택하세요"] + available_projects)

if project == "선택하세요":
    st.info("👈 과제를 선택해주세요.")
    st.stop()

# [STEP 2] 고액 결제 확인
st.divider()
st.subheader("2. 고액 결제 여부")

amount_check = st.radio(
    "100만 원 이상입니까?", 
    ["아니오 (100만 원 미만)", "네 (100만 원 이상)"], 
    horizontal=True,
    key="amount_radio_key" 
)

uploaded_files = {} 
is_high_price_checked = True 

# 파일 확장자 설정 (jpg 제외)
file_types = ['png', 'pdf', 'jpeg']

if amount_check == "네 (100만 원 이상)":
    st.error("💰 고액 건: 사전 검수 내역 필수")
    uploaded_files['audit_proof'] = st.file_uploader("★ 검수 완료 캡처 [필수]", type=file_types)
    if not uploaded_files.get('audit_proof'): is_high_price_checked = False

# [STEP 3] 상세 항목
st.divider()
st.subheader("3. 지출 항목 및 증빙")
if not is_high_price_checked:
    st.warning("👆 고액 검수 증빙을 먼저 올리세요.")
    st.stop()

expense_types = ["재료비", "연구실 환경 유지비", "사무기기 및 SW", "학회/세미나 등록비", "인쇄비 (포스터/책)", "논문 게재료"]
if payment_method != "세금계산서": expense_types.append("연구실 운영비 (식대/다과)")

category = st.selectbox("지출 항목 선택", expense_types)
st.markdown(f"**[{category}]** 선택함 - 필수 서류를 제출하세요.")

c1, c2 = st.columns(2)
with c1:
    if "카드" in payment_method: st.success("💳 카드는 거래명세서만 제출")
    else: uploaded_files['tax_invoice'] = st.file_uploader("1. 세금계산서 [필수]", type=file_types)
with c2:
    uploaded_files['statement'] = st.file_uploader("2. 거래명세서 [필수]", type=file_types)

extra_requirements_met = False 
reason_text = ""
def check_is_online(): return st.checkbox("인터넷 주문입니까? (쿠팡 등)", value=True)

# 로직 시작
if category == "재료비":
    extra_requirements_met = True
elif category == "연구실 환경 유지비":
    if payment_method == "세금계산서":
        reason_text = st.text_input("4. 필요 사유 [필수]")
        if reason_text: extra_requirements_met = True
    else:
        # ★ 수정됨: 여기서도 인터넷 주문 여부를 물어봄
        is_online = check_is_online()
        if is_online:
            uploaded_files['order_capture'] = st.file_uploader("3. 인터넷 주문내역 캡처", type=file_types)
        else:
            uploaded_files['detail_receipt'] = st.file_uploader("3. 상세 영수증 (품목 확인용)", type=file_types)
            
        reason_text = st.text_input("4. 필요 사유 [필수]")
        
        # 조건 확인: (주문내역 또는 상세영수증) AND 사유
        has_file = uploaded_files.get('order_capture') or uploaded_files.get('detail_receipt')
        if has_file and reason_text: extra_requirements_met = True
        
elif category == "사무기기 및 SW":
    is_online = False
    if payment_method != "세금계산서": is_online = check_is_online()
    if is_online: uploaded_files['order_capture'] = st.file_uploader("3. 인터넷 주문내역", type=file_types)
    reason_text = st.text_input("4. 사유 [필수]")
    if reason_text:
        if is_online and not uploaded_files.get('order_capture'): extra_requirements_met = False
        else: extra_requirements_met = True
elif category == "학회/세미나 등록비":
    c_a, c_b, c_c = st.columns(3)
    uploaded_files['conf_reg'] = c_a.file_uploader("3. 학회등록증", type=file_types)
    uploaded_files['conf_info'] = c_b.file_uploader("4. 일시/장소", type=file_types)
    uploaded_files['conf_fee'] = c_c.file_uploader("5. 등록비 기준표", type=file_types)
    if uploaded_files.get('conf_reg') and uploaded_files.get('conf_info') and uploaded_files.get('conf_fee'): extra_requirements_met = True
elif category == "인쇄비 (포스터/책)":
    print_type = st.radio("인쇄 종류", ["포스터", "책"])
    if print_type == "포스터":
        uploaded_files['poster_file'] = st.file_uploader("3. 포스터 원본", type=file_types)
        if uploaded_files.get('poster_file'): extra_requirements_met = True
    else:
        uploaded_files['book_cover'] = st.file_uploader("3. 책 앞표지", type=file_types)
        if uploaded_files.get('book_cover'): extra_requirements_met = True
elif category == "논문 게재료":
    paper_type = st.radio("비용 종류", ["게재/교정료", "삽화"])
    if paper_type == "게재/교정료":
        uploaded_files['paper_cover'] = st.file_uploader("3. 논문 표지", type=file_types)
        if uploaded_files.get('paper_cover'): extra_requirements_met = True
    else:
        uploaded_files['figure_file'] = st.file_uploader("3. 그림 파일", type=file_types)
        if uploaded_files.get('figure_file'): extra_requirements_met = True
elif category == "연구실 운영비 (식대/다과)":
    is_under_100k = st.checkbox("10만 원 미만입니까?", value=False)
    if not is_under_100k:
        st.error("🚫 10만 원 미만만 청구 가능")
        extra_requirements_met = False
    else:
        buy_route = st.radio("구매 경로", ["인터넷 주문", "오프라인 매장"])
        if buy_route == "인터넷 주문":
            uploaded_files['order_capture'] = st.file_uploader("3. 주문내역 캡처", type=file_types)
            if uploaded_files.get('order_capture'): extra_requirements_met = True
        else:
            uploaded_files['detail_receipt'] = st.file_uploader("3. 상세 영수증", type=file_types)
            if uploaded_files.get('detail_receipt'): extra_requirements_met = True

# [STEP 4] 제출 버튼
st.divider()
basic_files_ok = False
if "카드" in payment_method:
    if uploaded_files.get('statement'): basic_files_ok = True
else:
    if uploaded_files.get('tax_invoice') and uploaded_files.get('statement'): basic_files_ok = True

all_clear = is_high_price_checked and basic_files_ok and extra_requirements_met

if all_clear:
    if st.button("선생님에게 메일 보내기 (Submit)", type="primary"):
        status_box = st.empty()
        status_box.info("⏳ 메일 발송 중입니다... (창을 닫지 마세요)")
        
        # [수정] 한국 시간(KST = UTC+9) 설정
        kst = datetime.timezone(datetime.timedelta(hours=9))
        current_time = datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        
        mail_summary = {
            "성명": user_name,
            "과제": project,
            "항목": category,
            "결제수단": payment_method,
            "고액": amount_check,
            "사유": reason_text if reason_text else "-",
            "날짜": current_time
        }

        if send_email_with_attachments(mail_summary, uploaded_files):
            status_box.empty()
            st.balloons()
            receivers = st.secrets["email"]["receiver_address"]
            st.success(f"""
                ✅ 제출 완료!
                입력하신 정보가 담당자({receivers})에게 
                성공적으로 전송되었습니다.
            """)
        else:
            status_box.error("메일 발송에 실패했습니다.")
else:
    st.error("🚫 필수 서류 누락")
    st.button("제출 불가", disabled=True)