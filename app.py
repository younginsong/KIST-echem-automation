import streamlit as st
import datetime
import re
import base64 # 첨부파일 인코딩용
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

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
st.markdown("### 🚨 안내: 작성된 내용은 안희영 연구행정원에게 메일로 전송됩니다.")
st.divider()

# ==========================================
# [기능 0] 상태 관리 및 초기화
# ==========================================
# 세션 상태 초기화 (폼 리셋을 위한 ID 관리)
if 'form_id' not in st.session_state:
    st.session_state.form_id = 0
if 'is_submitted' not in st.session_state:
    st.session_state.is_submitted = False

def reset_amount_check():
    # 결제 수단 변경 시 고액 여부 초기화
    key_name = f"amount_radio_key_{st.session_state.form_id}"
    if key_name in st.session_state:
        st.session_state[key_name] = "아니오 (100만 원 미만)"

# ==========================================
# [기능 1] 이메일 발송 함수 (SendGrid 적용)
# ==========================================
def send_email_with_attachments(data_summary, files_dict):
    try:
        # secrets.toml에서 정보 가져오기
        api_key = st.secrets["email"]["sendgrid_api_key"]
        from_email = st.secrets["email"]["sender_address"]
        to_email = st.secrets["email"]["receiver_address"]

        # 메일 제목 및 본문 구성
        subject = f"[연구비제출] {data_summary['성명']} - {data_summary['항목']} ({data_summary['날짜']})"
        
        html_content = f"""
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

        # SendGrid Mail 객체 생성
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )

        # 파일 첨부 로직 (Base64 인코딩 필수)
        for key, file_obj in files_dict.items():
            if file_obj is not None:
                # 1. 파일 포인터 초기화
                file_obj.seek(0)
                # 2. 읽어서 Base64 인코딩
                file_data = file_obj.read()
                encoded_file = base64.b64encode(file_data).decode()
                
                # 3. 파일명 생성
                safe_name = f"{data_summary['날짜'][:10]}_{data_summary['성명']}_{key}_{file_obj.name}"
                
                # 4. Attachment 객체 생성 및 추가
                attachment = Attachment(
                    FileContent(encoded_file),
                    FileName(safe_name),
                    FileType(file_obj.type),
                    Disposition('attachment')
                )
                message.add_attachment(attachment)

        # SendGrid 클라이언트로 전송
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        # HTTP 상태 코드 확인 (200~299는 성공)
        if 200 <= response.status_code < 300:
            return True
        else:
            st.error(f"❌ 전송 실패 (상태 코드: {response.status_code})")
            return False

    except Exception as e:
        st.error(f"📧 메일 발송 시스템 에러: {e}")
        return False


# ==========================================
# [UI] 화면 구성
# ==========================================

# [STEP 0] 사용자 이름 입력 (초기화되지 않음 - 계속 유지)
st.subheader("0. 신청자 정보")
user_name = st.text_input("신청자 성명", placeholder="성명을 직접 입력하세요")

if not user_name.strip():
    st.info("👈 성명을 먼저 입력해주세요.")
    st.stop()

# -------------------------------------------------------
# 제출 완료 화면 (추가 신청 버튼 표시)
# -------------------------------------------------------
if st.session_state.is_submitted:
    st.success(f"✅ **{user_name}**님의 증빙 서류가 성공적으로 전송되었습니다.")
    st.balloons()
    
    st.markdown("---")
    st.info("👇 다른 건을 추가로 제출하시려면 아래 버튼을 눌러주세요.")
    
    # [추가 지급신청하기] 버튼
    if st.button("➕ 추가 지급신청하기 (새로운 건 작성)", type="primary"):
        # 상태 초기화 및 폼 ID 증가 (새로운 입력창 생성 효과)
        st.session_state.is_submitted = False
        st.session_state.form_id += 1
        st.rerun()

# -------------------------------------------------------
# 입력 폼 화면 (아직 제출하지 않은 경우)
# -------------------------------------------------------
else:
    # 현재 폼 ID (초기화 시마다 변경됨)
    fid = st.session_state.form_id

    # [STEP 1] 결제 정보
    st.subheader("1. 결제 정보 입력")

    corp_projects = [
        "2E33943 / 계산과학 및 AI 기반 에너지 저장 및 변환 소재 기술 개발 / 류승호",
        "2E33944 / 설치가 용이한 고밀착부착형 태양전지 기술 개발 / 이필립",
        "2E33951 / e-Chemical 제조 기술 / 이동기",
        "2E33961 / Carbon to Liquid 공정 실증기술 개발(응용) / 이웅",
        "2E33962 / (신규선임) 전기화학적 질소-탄소 결합 화합물 생산 기술 개발 / 김찬솔",
        "2E33963 / (신규선임) 생성형 AI를 활용한 이산화탄소 동시 포집-전환 아민 합성 플랫폼 개발 / 김창수(선임)",
        "2G13240 / 신개념 에너지기술 확보를 위한 실증 플랜트 구축 / 오형석",
        "2I25710 / 이산화탄소 활용 청정 기초소재 합성반응의 대용량셀 평가 및 분석 / 오형석",
        "2MRE760 / CO2 및 환원제 활용 온실가스 감축형 메탄올 합성기술 / 정광덕",
        "2MRF640 / 48V급 발열 내구성을 갖는 투명한 금속 박막코팅 복합재 개발 / 김상우",
        "2N47580 / 이산화탄소 환원 메탄올 생산을 위한 혁신적 촉매개발 / 정광덕",
        "2V10563 / 플라스틱 전기개질 기술개발 / 이동기",
        "2V10792 / Air to SAF 개발 계획 / 하정명"
    ]

    research_projects = [
        "2N47780 / 전기화학적 환원 반응 활용 금속 산화물 재활용 기술 개발 / 김찬솔",
        "2N78490 / 고농도 C2+ 액체 산물 생산용 *H/*CO 중간체 제어 나노촉매 및 전해 시스템 개발 / 원다혜",
        "2N78700 / 전기화학적 CO2 전환 에틸렌 생산 핵심 기술 개발 및 실증 연구 / 오형석",
        "2N78970 / 공기 중 이산화탄소 동시 포집-전환 원천기술개발 / 이현주",
        "2N79010 / 카본 네거티브 소재-응용 넥서스 / 오형석",
        "2N79060 / 목질계 바이오매스의 통합 e-Biorefinery 기술개발 / 이동기",
        "2N79510 / 소비자 가치 및 수용성이 고려된 CO2 전환 에탄올 생산 촉매 소재 및 시스템 개발 / 이동기",
        "2N79860 / 직접 공기 포집 및 전기화학적 전환을 통한 유용화합물 생산 기술 개발 / 원다혜",
        "2N80000 / 능동학습법을 활용한 CO2 동시 포집-전환 메탄올 저온 제조기술개발 / 이웅",
        "2N80390 / 청정수소 생산을 위한 요소 재순환 소재-응용 넥서스 / 오형석",
        "2N82060 / 기술 수출을 위한 배출원 맞춤형 저비용 CO2 포집 기술개발 / 이웅",
        "2N82360 / 전기화학 전환(e-플라스틱 원료(CO/PO)) / 오형석",
        "2N82910 / 초임계 환경 전기화학적 CO2 전환 환원 전극 소재 및 반응기 개발 / 오형석"
    ]

    col1, col2 = st.columns(2)
    with col1:
        # Key에 fid를 추가하여 초기화 시 새로운 위젯으로 인식하게 함
        payment_method = st.radio(
            "결제 수단을 선택하세요", 
            ["법인카드", "연구비카드", "세금계산서"],
            key=f"payment_method_radio_{fid}",
            on_change=reset_amount_check
        )

    with col2:
        if payment_method == "법인카드":
            base_list = corp_projects
        elif payment_method == "연구비카드":
            base_list = research_projects
        else: # 세금계산서
            base_list = corp_projects + research_projects
        
        final_options = ["➕ 직접 입력 (목록에 없는 계정)"] + base_list
        project_selection = st.selectbox(f"사용할 과제 계정", final_options, key=f"project_select_{fid}")

    # 과제 선택 로직
    final_project_name = ""
    if project_selection == "➕ 직접 입력 (목록에 없는 계정)":
        manual_input = st.text_input("과제명 직접 입력 (⚠️ 숫자와 영문만 입력 가능)", 
                                     placeholder="예: 2X00000 New Project",
                                     key=f"manual_input_{fid}")
        if manual_input:
            if not re.match(r'^[a-zA-Z0-9\s]+$', manual_input):
                st.error("🚫 한글이나 특수문자는 입력할 수 없습니다. 숫자와 영문만 입력해주세요.")
                st.stop()
            else:
                final_project_name = f"[직접입력] {manual_input}"
        else:
            st.info("👈 위 입력창에 과제 정보를 입력해주세요.")
            st.stop()
    else:
        final_project_name = project_selection

    project = final_project_name

    # [STEP 2] 고액 결제 확인
    st.divider()
    st.subheader("2. 고액 결제 여부")

    amount_check = st.radio(
        "100만 원 이상입니까?", 
        ["아니오 (100만 원 미만)", "네 (100만 원 이상)"], 
        horizontal=True,
        key=f"amount_radio_key_{fid}" 
    )

    uploaded_files = {} 
    is_high_price_checked = True 
    
    # [설정] 허용 파일 확장자: pdf, jpg (jpeg 제외)
    file_types = ['pdf', 'jpg']

    if amount_check == "네 (100만 원 이상)":
        st.error("💰 고액 건: 사전 검수 내역 필수")
        uploaded_files['audit_proof'] = st.file_uploader("★ 검수 완료 캡처 [필수]", type=file_types, key=f"audit_proof_{fid}")
        if not uploaded_files.get('audit_proof'): is_high_price_checked = False

    # [STEP 3] 상세 항목
    st.divider()
    st.subheader("3. 지출 항목 및 증빙")
    if not is_high_price_checked:
        st.warning("👆 고액 검수 증빙을 먼저 올리세요.")
        st.stop()

    expense_types = ["재료비", "연구실 환경 유지비", "사무기기 및 SW", "학회/세미나 등록비", "인쇄비 (포스터/책)", "논문 게재료"]
    if payment_method != "세금계산서": expense_types.append("연구실 운영비 (식대/다과)")

    category = st.selectbox("지출 항목 선택", expense_types, key=f"category_{fid}")
    st.markdown(f"**[{category}]** 선택함 - 필수 서류를 제출하세요.")

    c1, c2 = st.columns(2)
    with c1:
        if "카드" in payment_method: st.success("💳 카드는 거래명세서만 제출")
        else: uploaded_files['tax_invoice'] = st.file_uploader("1. 세금계산서 [필수]", type=file_types, key=f"tax_{fid}")
    with c2:
        uploaded_files['statement'] = st.file_uploader("2. 거래명세서 [필수]", type=file_types, key=f"stmt_{fid}")

    extra_requirements_met = False 
    reason_text = ""
    
    def check_is_online(): return st.checkbox("인터넷 주문입니까? (쿠팡 등)", value=True, key=f"is_online_{fid}")

    # 로직 시작 (각 위젯 key에도 fid 추가)
    if category == "재료비":
        extra_requirements_met = True
    elif category == "연구실 환경 유지비":
        if payment_method == "세금계산서":
            reason_text = st.text_input("4. 필요 사유 [필수]", key=f"reason_{fid}")
            if reason_text: extra_requirements_met = True
        else:
            is_online = check_is_online()
            if is_online:
                uploaded_files['order_capture'] = st.file_uploader("3. 인터넷 주문내역 캡처", type=file_types, key=f"order_{fid}")
            else:
                uploaded_files['detail_receipt'] = st.file_uploader("3. 상세 영수증 (품목 확인용)", type=file_types, key=f"detail_{fid}")
            
            reason_text = st.text_input("4. 필요 사유 [필수]", key=f"reason_{fid}")
            
            has_file = uploaded_files.get('order_capture') or uploaded_files.get('detail_receipt')
            if has_file and reason_text: extra_requirements_met = True
            
    elif category == "사무기기 및 SW":
        is_online = False
        if payment_method != "세금계산서": is_online = check_is_online()
        if is_online: uploaded_files['order_capture'] = st.file_uploader("3. 인터넷 주문내역", type=file_types, key=f"order_{fid}")
        reason_text = st.text_input("4. 사유 [필수]", key=f"reason_{fid}")
        if reason_text:
            if is_online and not uploaded_files.get('order_capture'): extra_requirements_met = False
            else: extra_requirements_met = True
    elif category == "학회/세미나 등록비":
        c_a, c_b, c_c = st.columns(3)
        uploaded_files['conf_reg'] = c_a.file_uploader("3. 학회등록증", type=file_types, key=f"conf_reg_{fid}")
        uploaded_files['conf_info'] = c_b.file_uploader("4. 일시/장소", type=file_types, key=f"conf_info_{fid}")
        uploaded_files['conf_fee'] = c_c.file_uploader("5. 등록비 기준표", type=file_types, key=f"conf_fee_{fid}")
        if uploaded_files.get('conf_reg') and uploaded_files.get('conf_info') and uploaded_files.get('conf_fee'): extra_requirements_met = True
    elif category == "인쇄비 (포스터/책)":
        print_type = st.radio("인쇄 종류", ["포스터", "책"], key=f"print_type_{fid}")
        if print_type == "포스터":
            uploaded_files['poster_file'] = st.file_uploader("3. 포스터 원본", type=file_types, key=f"poster_{fid}")
            if uploaded_files.get('poster_file'): extra_requirements_met = True
        else:
            uploaded_files['book_cover'] = st.file_uploader("3. 책 앞표지", type=file_types, key=f"book_{fid}")
            if uploaded_files.get('book_cover'): extra_requirements_met = True
    elif category == "논문 게재료":
        paper_type = st.radio("비용 종류", ["게재/교정료", "삽화"], key=f"paper_type_{fid}")
        if paper_type == "게재/교정료":
            uploaded_files['paper_cover'] = st.file_uploader("3. 논문 표지", type=file_types, key=f"paper_cover_{fid}")
            if uploaded_files.get('paper_cover'): extra_requirements_met = True
        else:
            uploaded_files['figure_file'] = st.file_uploader("3. 그림 파일", type=file_types, key=f"fig_{fid}")
            if uploaded_files.get('figure_file'): extra_requirements_met = True
    elif category == "연구실 운영비 (식대/다과)":
        is_under_100k = st.checkbox("10만 원 미만입니까?", value=False, key=f"under_100k_{fid}")
        if not is_under_100k:
            st.error("🚫 10만 원 미만만 청구 가능")
            extra_requirements_met = False
        else:
            buy_route = st.radio("구매 경로", ["인터넷 주문", "오프라인 매장"], key=f"buy_route_{fid}")
            if buy_route == "인터넷 주문":
                uploaded_files['order_capture'] = st.file_uploader("3. 주문내역 캡처", type=file_types, key=f"order_{fid}")
                if uploaded_files.get('order_capture'): extra_requirements_met = True
            else:
                uploaded_files['detail_receipt'] = st.file_uploader("3. 상세 영수증", type=file_types, key=f"detail_{fid}")
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
        if st.button("제출하기 (Submit)", type="primary", key=f"submit_btn_{fid}"):
            status_box = st.empty()
            status_box.info("⏳ 메일 발송 중입니다... (SendGrid 엔진 가동 🏎️)")
            
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
                # 성공 시 세션 상태 변경 후 리런
                st.session_state.is_submitted = True
                st.rerun()
            else:
                status_box.error("메일 발송에 실패했습니다.")
    else:
        st.error("🚫 필수 서류 누락")
        st.button("제출 불가", disabled=True, key=f"disabled_btn_{fid}")
