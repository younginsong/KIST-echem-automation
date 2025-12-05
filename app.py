import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.cloud import storage
import datetime

# ==========================================
# [설정] 구글 클라우드 스토리지 버킷 이름
# ==========================================
# ★ 중요: 방금 만든 버킷(창고) 이름을 정확히 넣으세요!
BUCKET_NAME = "kist-echem-automation"  # 예: "kist-lab-receipts-2025-ahy"


# ==========================================
# [기능 1] 구글 클라우드 스토리지(GCS) 업로드
# ==========================================
def upload_to_gcs(file_obj, filename):
    try:
        # 1. Secrets에서 인증 정보로 클라이언트 생성
        creds_dict = dict(st.secrets["gcp_service_account"])
        client = storage.Client.from_service_account_info(creds_dict)
        
        # 2. 버킷 선택 및 파일 업로드
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        
        # 파일 포인터를 처음으로 되돌림 (중요)
        file_obj.seek(0)
        blob.upload_from_file(file_obj, content_type=file_obj.type)
        
        # 3. 접근 가능한 링크 생성 (인증된 사용자용 링크)
        # 이 링크는 권한이 있는 사람(안희영님)만 열 수 있습니다.
        link = f"https://storage.cloud.google.com/{BUCKET_NAME}/{filename}"
        return link

    except Exception as e:
        st.error(f"창고 저장 실패: {e}")
        return None

# ==========================================
# [기능 2] 구글 시트 저장 함수
# ==========================================
def save_to_google_sheets(data):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open("log_sheet").sheet1 
        sheet.append_row(data)
        return True
    except Exception as e:
        st.error(f"엑셀 저장 실패: {e}")
        return False

# ==========================================
# [UI] 화면 구성 (이전과 동일)
# ==========================================
st.set_page_config(page_title="연구비 증빙 제출 시스템", page_icon="🧾", layout="wide")
st.title("🧾 연구비 지출 증빙 제출 시스템")
st.markdown("### 🚨 안내: 파일은 구글 클라우드 창고(GCS)에 저장됩니다.")
st.divider()

# [STEP 1] 결제 정보
st.subheader("1. 결제 정보 입력")
col1, col2 = st.columns(2)
with col1:
    payment_method = st.radio("결제 수단을 선택하세요", ["법인카드", "연구비카드", "세금계산서"])
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
amount_check = st.radio("100만 원 이상입니까?", ["아니오", "네 (100만 원 이상)"], horizontal=True)
uploaded_files = {} 
is_high_price_checked = True 

if amount_check == "네 (100만 원 이상)":
    st.error("💰 고액 건: 사전 검수 내역 필수")
    uploaded_files['audit_proof'] = st.file_uploader("★ 검수 완료 캡처 [필수]", type=['png', 'pdf'])
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
    else: uploaded_files['tax_invoice'] = st.file_uploader("1. 세금계산서 [필수]", type=['pdf', 'xml', 'png'])
with c2:
    uploaded_files['statement'] = st.file_uploader("2. 거래명세서 [필수]", type=['png', 'pdf'])

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
        uploaded_files['order_capture'] = st.file_uploader("3. 주문내역 캡처", type=['png', 'pdf'])
        reason_text = st.text_input("4. 필요 사유 [필수]")
        if uploaded_files.get('order_capture') and reason_text: extra_requirements_met = True
elif category == "사무기기 및 SW":
    is_online = False
    if payment_method != "세금계산서": is_online = check_is_online()
    if is_online: uploaded_files['order_capture'] = st.file_uploader("3. 인터넷 주문내역", type=['png', 'pdf'])
    reason_text = st.text_input("4. 사유 [필수]")
    if reason_text:
        if is_online and not uploaded_files.get('order_capture'): extra_requirements_met = False
        else: extra_requirements_met = True
elif category == "학회/세미나 등록비":
    c_a, c_b, c_c = st.columns(3)
    uploaded_files['conf_reg'] = c_a.file_uploader("3. 학회등록증", type=['pdf', 'png'])
    uploaded_files['conf_info'] = c_b.file_uploader("4. 일시/장소", type=['png', 'pdf'])
    uploaded_files['conf_fee'] = c_c.file_uploader("5. 등록비 기준표", type=['png', 'pdf'])
    if uploaded_files.get('conf_reg') and uploaded_files.get('conf_info') and uploaded_files.get('conf_fee'): extra_requirements_met = True
elif category == "인쇄비 (포스터/책)":
    print_type = st.radio("인쇄 종류", ["포스터", "책"])
    if print_type == "포스터":
        uploaded_files['poster_file'] = st.file_uploader("3. 포스터 원본", type=['pdf'])
        if uploaded_files.get('poster_file'): extra_requirements_met = True
    else:
        uploaded_files['book_cover'] = st.file_uploader("3. 책 앞표지", type=['png', 'pdf'])
        if uploaded_files.get('book_cover'): extra_requirements_met = True
elif category == "논문 게재료":
    paper_type = st.radio("비용 종류", ["게재/교정료", "삽화"])
    if paper_type == "게재/교정료":
        uploaded_files['paper_cover'] = st.file_uploader("3. 논문 표지", type=['pdf', 'png'])
        if uploaded_files.get('paper_cover'): extra_requirements_met = True
    else:
        uploaded_files['figure_file'] = st.file_uploader("3. 그림 파일", type=['png', 'pdf'])
        if uploaded_files.get('figure_file'): extra_requirements_met = True
elif category == "연구실 운영비 (식대/다과)":
    is_under_100k = st.checkbox("10만 원 미만입니까?", value=False)
    if not is_under_100k:
        st.error("🚫 10만 원 미만만 청구 가능")
        extra_requirements_met = False
    else:
        buy_route = st.radio("구매 경로", ["인터넷 주문", "오프라인 매장"])
        if buy_route == "인터넷 주문":
            uploaded_files['order_capture'] = st.file_uploader("3. 주문내역 캡처", type=['png', 'pdf'])
            if uploaded_files.get('order_capture'): extra_requirements_met = True
        else:
            uploaded_files['detail_receipt'] = st.file_uploader("3. 상세 영수증", type=['png', 'pdf'])
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
    if st.button("제출하기 (Submit)", type="primary"):
        progress_text = st.empty()
        progress_text.text("⏳ GCS 창고에 안전하게 저장 중입니다...")
        
        file_links = {}
        for key, file_obj in uploaded_files.items():
            if file_obj is not None:
                # 파일명: 날짜_항목_파일명
                safe_filename = f"{datetime.datetime.now().strftime('%Y%m%d')}_{category}_{file_obj.name}"
                link = upload_to_gcs(file_obj, safe_filename)
                file_links[key] = link if link else "업로드 실패"

        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        extra_link = "-"
        # 우선순위에 따라 추가 증빙 링크 하나 선택 (엑셀 칸 절약을 위해)
        for k in ['order_capture', 'conf_reg', 'poster_file', 'paper_cover', 'detail_receipt', 'book_cover', 'figure_file']:
             if file_links.get(k): extra_link = file_links[k]; break

        row_data = [
            current_time, payment_method, project, category, amount_check, reason_text,
            file_links.get('audit_proof', "-"),
            file_links.get('tax_invoice', "-"),
            file_links.get('statement', "-"),
            extra_link
        ]

        if save_to_google_sheets(row_data):
            progress_text.empty()
            st.balloons()
            st.success("✅ 제출 완료! 담당자가 곧 확인합니다.")
else:
    st.error("🚫 필수 서류 누락")
    st.button("제출 불가", disabled=True)
