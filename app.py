import streamlit as st
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import re
import pandas as pd

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
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# [기능 0] 상태 관리 (서버 메모리 사용)
# ==========================================
if 'form_id' not in st.session_state:
    st.session_state.form_id = 0
if 'is_submitted' not in st.session_state:
    st.session_state.is_submitted = False

# ★ 서버 메모리에 로그 저장
@st.cache_resource
def get_shared_log():
    return []

mail_history = get_shared_log()

def reset_amount_check():
    key_name = f"amount_radio_key_{st.session_state.form_id}"
    if key_name in st.session_state:
        st.session_state[key_name] = "아니오 (100만 원 미만)"

# ==========================================
# [UI - 사이드바] 로그 항상 표시
# ==========================================
with st.sidebar:
    st.title("📋 전송 내역 (Log)")
    st.markdown("---")
    st.caption("※ 서버가 재부팅되기 전까지 기록이 유지됩니다.")
    
    if mail_history:
        df_log = pd.DataFrame(mail_history)
        df_log = df_log.iloc[::-1]
        
        st.dataframe(
            df_log[['성명', '항목', '전송상태', '제출일시']], 
            use_container_width=True, 
            hide_index=True
        )
        st.caption(f"총 {len(df_log)}건의 제출 내역이 있습니다.")
    else:
        st.info("아직 제출된 내역이 없습니다.")

# ==========================================
# [기능 1] 이메일 발송 함수
# ==========================================
def send_email_via_gmail(data_summary, files_dict):
    try:
        sender_email = st.secrets["email"]["sender_address"]
        sender_pass = st.secrets["email"]["sender_password"]
        receiver_email = st.secrets["email"]["receiver_address"]

        msg = MIMEMultipart()
        msg['Subject'] = f"[연구비제출] {data_summary['성명']} - {data_summary['항목']} ({data_summary['날짜']})"
        msg['From'] = sender_email
        msg['To'] = receiver_email

        body = f"""
        <h3>🧾 연구비 증빙 서류 제출 알림</h3>
        <p>연구비 지출 증빙 서류가 접수되었습니다.</p>
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

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(sender_email, sender_pass)
            server.send_message(msg)
            
        record = {
            "제출일시": data_summary['날짜'],
            "성명": data_summary['성명'],
            "과제명": data_summary['과제'],
            "항목": data_summary['항목'],
            "결제수단": data_summary['결제수단'],
            "전송상태": "✅ 성공"
        }
        mail_history.append(record)
        return True

    except Exception as e:
        record = {
            "제출일시": data_summary['날짜'],
            "성명": data_summary['성명'],
            "과제명": data_summary['과제'],
            "항목": data_summary['항목'],
            "결제수단": data_summary['결제수단'],
            "전송상태": "❌ 실패"
        }
        mail_history.append(record)
        st.error(f"메일 발송 실패: {e}")
        return False


# ==========================================
# [UI] 메인 화면 구성
# ==========================================
st.title("🧾 연구비 지출 증빙 제출 시스템")
st.markdown("### 🚨 안내: 작성된 내용은 안희영 연구행정원에게 메일로 전송됩니다.")
st.divider()

st.subheader("0. 신청자 정보")
user_name = st.text_input("신청자 성명", placeholder="성명을 직접 입력하세요")

if not user_name.strip():
    st.info("👈 성명을 먼저 입력해주세요.")
    st.stop()

if st.session_state.is_submitted:
    st.success(f"✅ **{user_name}**님의 증빙 서류가 성공적으로 전송되었습니다.")
    st.balloons()
    
    st.markdown("---")
    if st.button("➕ 추가 지급신청하기 (새로운 건 작성)", type="primary"):
        st.session_state.is_submitted = False
        st.session_state.form_id += 1
        st.rerun()

else:
    fid = st.session_state.form_id
    st.subheader("1. 결제 정보 입력")

    corp_projects = ["2E33943 / 계산과학 및 AI 기반 에너지 저장 및 변환 소재 기술 개발 / 류승호", "2E33944 / 설치가 용이한 고밀착부착형 태양전지 기술 개발 / 이필립", "2E33951 / e-Chemical 제조 기술 / 이동기", "2E33961 / Carbon to Liquid 공정 실증기술 개발(응용) / 이웅", "2E33962 / (신규선임) 전기화학적 질소-탄소 결합 화합물 생산 기술 개발 / 김찬솔", "2E33963 / (신규선임) 생성형 AI를 활용한 이산화탄소 동시 포집-전환 아민 합성 플랫폼 개발 / 김창수(선임)", "2G13240 / 신개념 에너지기술 확보를 위한 실증 플랜트 구축 / 오형석", "2I25710 / 이산화탄소 활용 청정 기초소재 합성반응의 대용량셀 평가 및 분석 / 오형석", "2MRE760 / CO2 및 환원제 활용 온실가스 감축형 메탄올 합성기술 / 정광덕", "2MRF640 / 48V급 발열 내구성을 갖는 투명한 금속 박막코팅 복합재 개발 / 김상우", "2N47580 / 이산화탄소 환원 메탄올 생산을 위한 혁신적 촉매개발 / 정광덕", "2V10563 / 플라스틱 전기개질 기술개발 / 이동기", "2V10792 / Air to SAF 개발 계획 / 하정명"]
    research_projects = ["2N47780 / 전기화학적 환원 반응 활용 금속 산화물 재활용 기술 개발 / 김찬솔", "2N78490 / 고농도 C2+ 액체 산물 생산용 *H/*CO 중간체 제어 나노촉매 및 전해 시스템 개발 / 원다혜", "2N78700 / 전기화학적 CO2 전환 에틸렌 생산 핵심 기술 개발 및 실증 연구 / 오형석", "2N78970 / 공기 중 이산화탄소 동시 포집-전환 원천기술개발 / 이현주", "2N79010 / 카본 네거티브 소재-응용 넥서스 / 오형석", "2N79060 / 목질계 바이오매스의 통합 e-Biorefinery 기술개발 / 이동기", "2N79510 / 소비자 가치 및 수용성이 고려된 CO2 전환 에탄올 생산 촉매 소재 및 시스템 개발 / 이동기", "2N79860 / 직접 공기 포집 및 전기화학적 전환을 통한 유용화합물 생산 기술 개발 / 원다혜", "2N80000 / 능동학습법을 활용한 CO2 동시 포집-전환 메탄올 저온 제조기술개발 / 이웅", "2N80390 / 청정수소 생산을 위한 요소 재순환 소재-응용 넥서스 / 오형석", "2N82060 / 기술 수출을 위한 배출원 맞춤형 저비용 CO2 포집 기술개발 / 이웅", "2N82360 / 전기화학 전환(e-플라스틱 원료(CO/PO)) / 오형석", "2N82910 / 초임계 환경 전기화학적 CO2 전환 환원 전극 소재 및 반응기 개발 / 오형석"]

    c1, c2 = st.columns(2)
    with c1:
        payment_method = st.radio("결제 수단을 선택하세요", ["법인카드", "연구비카드", "세금계산서"], key=f"pay_{fid}", on_change=reset_amount_check)
    with c2:
        base_list = corp_projects if payment_method == "법인카드" else (research_projects if payment_method == "연구비카드" else corp_projects + research_projects)
        project_sel = st.selectbox(f"사용할 과제 계정", ["➕ 직접 입력"] + base_list, key=f"proj_{fid}")

    project = ""
    if project_sel == "➕ 직접 입력":
        manual = st.text_input("과제명 직접 입력", key=f"man_{fid}")
        if manual:
            if not re.match(r'^[a-zA-Z0-9\s]+$', manual):
                st.error("🚫 숫자와 영문만 입력 가능")
                st.stop()
            project = f"[직접입력] {manual}"
        else:
            pass
    else:
        project = project_sel

    st.divider()
    st.subheader("2. 고액 결제 여부")
    amount_check = st.radio("100만 원 이상입니까?", ["아니오 (100만 원 미만)", "네 (100만 원 이상)"], horizontal=True, key=f"amt_{fid}")
    
    uploaded_files = {}
    is_high_price_checked = True
    file_types = ['pdf', 'jpg']

    if amount_check == "네 (100만 원 이상)":
        st.error("💰 고액 건: 사전 검수 내역 필수")
        uploaded_files['audit_proof'] = st.file_uploader("★ 검수 완료 캡처", type=file_types, key=f"audit_{fid}")
        if not uploaded_files.get('audit_proof'): is_high_price_checked = False

    st.divider()
    st.subheader("3. 지출 항목 및 증빙")
    
    expense_types = ["재료비", "연구실 환경 유지비", "사무기기 및 SW", "학회/세미나 등록비", "인쇄비 (포스터/책)", "논문 게재료"]
    if payment_method != "세금계산서": expense_types.append("연구실 운영비 (식대/다과)")
    category = st.selectbox("지출 항목 선택", expense_types, key=f"cat_{fid}")

    d1, d2 = st.columns(2)
    with d1:
        if "카드" in payment_method: st.success("💳 카드는 거래명세서만 제출")
        else: uploaded_files['tax_invoice'] = st.file_uploader("1. 세금계산서", type=file_types, key=f"tax_{fid}")
    with d2:
        uploaded_files['statement'] = st.file_uploader("2. 거래명세서", type=file_types, key=f"stmt_{fid}")

    extra_met = False
    reason = ""
    
    # 인터넷 주문 체크박스 함수
    def check_online(): return st.checkbox("인터넷 주문입니까?", value=True, key=f"online_{fid}")

    # --- [로직 수정 시작] ---
    if category == "재료비": 
        extra_met = True
        
    elif category == "연구실 환경 유지비":
        if payment_method == "세금계산서":
            reason = st.text_input("4. 필요 사유", key=f"r_{fid}")
            if reason.strip(): extra_met = True
        else:
            # 온라인/오프라인 체크
            is_online = check_online()
            
            if is_online:
                uploaded_files['order'] = st.file_uploader("3. 인터넷 주문내역 캡처", type=file_types, key=f"ord_{fid}")
                has_evidence = uploaded_files.get('order') is not None
            else:
                # 오프라인의 경우: 거래명세서(기본서류)가 있으므로 추가 영수증 불필요
                st.info("✅ 오프라인 결제는 '거래명세서'로 증빙을 갈음합니다.")
                has_evidence = True 
            
            reason = st.text_input("4. 필요 사유", key=f"r_{fid}")
            
            if has_evidence and reason.strip(): 
                extra_met = True

    elif category == "사무기기 및 SW":
        is_online = False
        if payment_method != "세금계산서": is_online = check_online()
        
        if is_online: 
            uploaded_files['order'] = st.file_uploader("3. 주문내역", type=file_types, key=f"ord_{fid}")
            has_evidence = uploaded_files.get('order') is not None
        else:
            has_evidence = True 
            
        reason = st.text_input("4. 사유", key=f"r_{fid}")
        
        if reason.strip():
            if is_online and not has_evidence: extra_met = False
            else: extra_met = True
                
    elif category == "학회/세미나 등록비":
        c1,c2,c3 = st.columns(3)
        uploaded_files['reg'] = c1.file_uploader("3. 등록증", type=file_types, key=f"creg_{fid}")
        uploaded_files['info'] = c2.file_uploader("4. 개요", type=file_types, key=f"cinfo_{fid}")
        uploaded_files['fee'] = c3.file_uploader("5. 등록비표", type=file_types, key=f"cfee_{fid}")
        if uploaded_files.get('reg') and uploaded_files.get('info') and uploaded_files.get('fee'): extra_met = True
        
    elif category == "인쇄비 (포스터/책)":
        ptype = st.radio("종류", ["포스터", "책"], key=f"pt_{fid}")
        if ptype=="포스터": 
            uploaded_files['poster'] = st.file_uploader("3. 포스터", type=file_types, key=f"post_{fid}")
            if uploaded_files.get('poster'): extra_met = True
        else:
            uploaded_files['book'] = st.file_uploader("3. 표지", type=file_types, key=f"book_{fid}")
            if uploaded_files.get('book'): extra_met = True
            
    elif category == "논문 게재료":
        ptype = st.radio("종류", ["게재료", "삽화"], key=f"pp_{fid}")
        if ptype=="게재료":
            uploaded_files['paper'] = st.file_uploader("3. 논문표지", type=file_types, key=f"pcover_{fid}")
            if uploaded_files.get('paper'): extra_met = True
        else:
            uploaded_files['fig'] = st.file_uploader("3. 그림", type=file_types, key=f"pfig_{fid}")
            if uploaded_files.get('fig'): extra_met = True
            
    elif category == "연구실 운영비 (식대/다과)":
        if not st.checkbox("10만 원 미만입니까?", key=f"u100_{fid}"): st.error("10만원 미만만 가능"); extra_met=False
        else:
            route = st.radio("경로", ["인터넷", "오프라인"], key=f"pr_{fid}")
            if route=="인터넷": 
                uploaded_files['order'] = st.file_uploader("3. 주문내역", type=file_types, key=f"ord_{fid}")
                if uploaded_files.get('order'): extra_met = True
            else:
                uploaded_files['receipt'] = st.file_uploader("3. 영수증", type=file_types, key=f"rec_{fid}")
                if uploaded_files.get('receipt'): extra_met = True
    # --- [로직 수정 끝] ---

    st.divider()
    basic_ok = False
    if "카드" in payment_method: 
        if uploaded_files.get('statement'): basic_ok = True
    else: 
        if uploaded_files.get('tax_invoice') and uploaded_files.get('statement'): basic_ok = True
    
    if is_high_price_checked and basic_ok and extra_met and project != "":
        if st.button("제출하기 (Submit)", type="primary", key=f"sub_{fid}"):
            with st.spinner("🚀 메일 전송 중..."):
                kst = datetime.timezone(datetime.timedelta(hours=9))
                now = datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
                
                summary = {
                    "성명": user_name, "과제": project, "항목": category,
                    "결제수단": payment_method, "고액": amount_check,
                    "사유": reason if reason else "-", "날짜": now
                }
                
                if send_email_via_gmail(summary, uploaded_files):
                    st.session_state.is_submitted = True
                    st.rerun()
    else:
        err_msg = []
        if not is_high_price_checked: err_msg.append("고액결제 검수내역")
        if not basic_ok: err_msg.append("기본서류(거래명세서/계산서)")
        if not extra_met: err_msg.append("항목별 필수증빙 또는 사유")
        if project == "": err_msg.append("과제명")
        
        st.error(f"🚫 필수 정보 누락: {', '.join(err_msg)}")
        st.button("제출 불가", disabled=True)
