import streamlit as st
import os
import requests
from io import BytesIO
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from deep_translator import GoogleTranslator

# ==========================================
# 1. 網頁介面設定
# ==========================================
st.set_page_config(page_title="AAC 圖卡自動生成系統", page_icon="📇")
st.title("📇 AAC 溝通圖卡自動生成系統")
st.markdown("輸入您需要的圖卡詞彙，系統將自動搜尋 ARASAAC 圖庫並排版成可列印的 5x5cm PECS 標準圖卡。")

# ==========================================
# 2. 字型下載與註冊函數
# ==========================================
@st.cache_resource # 讓 Streamlit 記住字型，不用每次按按鈕都重新下載
def load_font():
    FONT_PATH = "LXGWWenKai.ttf"
    if not os.path.exists(FONT_PATH) or os.path.getsize(FONT_PATH) < 1000000:
        font_url = "https://github.com/lxgw/LxgwWenKai/releases/download/v1.522/LXGWWenKai-Regular.ttf"
        r = requests.get(font_url, headers={'User-Agent': 'Mozilla/5.0'}, stream=True)
        if r.status_code == 200:
            with open(FONT_PATH, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    pdfmetrics.registerFont(TTFont('CustomFont', FONT_PATH))

# ==========================================
# 3. 圖片抓取與翻譯函數
# ==========================================
def fetch_arasaac_image(keyword):
    translator_cn = GoogleTranslator(source='auto', target='zh-CN')
    translator_en = GoogleTranslator(source='auto', target='en')
    
    search_strategies = [
        ('zh', keyword),
        ('zh', translator_cn.translate(keyword)),
        ('en', translator_en.translate(keyword))
    ]
    
    for lang, query_term in search_strategies:
        if not query_term: continue
        search_url = f"https://api.arasaac.org/api/pictograms/{lang}/search/{query_term}"
        try:
            response = requests.get(search_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    img_response = requests.get(f"https://api.arasaac.org/api/pictograms/{data[0]['_id']}", timeout=5)
                    if img_response.status_code == 200:
                        img = Image.open(BytesIO(img_response.content))
                        return img.convert('RGB') if img.mode in ('RGBA', 'P') else img
        except:
            continue
    return None

# ==========================================
# 4. 使用者輸入區塊
# ==========================================
user_input = st.text_area(
    "📝 請輸入需要的圖卡名稱（可使用逗號、空格或換行來分隔）：", 
    "蘋果, 香蕉, 喝水, 謝謝, 高興, 生氣, 洗手, 睡覺"
)

# ==========================================
# 5. 生成 PDF 邏輯
# ==========================================
if st.button("🚀 開始生成 PDF 圖卡"):
    if not user_input.strip():
        st.warning("請先輸入至少一個詞彙喔！")
    else:
        with st.spinner('正在智慧搜尋圖片並排版中，請稍候...'):
            load_font()
            
            # 清理與分割使用者輸入的字詞
            raw_words = user_input.replace('\n', ',').replace(' ', ',').split(',')
            card_list = [w.strip() for w in raw_words if w.strip()]
            
            # PDF 設定
            output_pdf = "PECS_Cards.pdf"
            PAGE_WIDTH, PAGE_HEIGHT = A4
            CM = 28.3465
            CARD_SIZE = 5.0 * CM  
            COLS, ROWS = 4, 5
            MARGIN_X = (PAGE_WIDTH - (COLS * CARD_SIZE)) / 2
            MARGIN_Y = (PAGE_HEIGHT - (ROWS * CARD_SIZE)) / 2
            
            c = canvas.Canvas(output_pdf, pagesize=A4)
            current_idx = 0
            
            # 建立進度條
            progress_bar = st.progress(0)
            
            while current_idx < len(card_list):
                for row in range(ROWS):
                    for col in range(COLS):
                        if current_idx >= len(card_list): break
                            
                        word = card_list[current_idx]
                        x = MARGIN_X + (col * CARD_SIZE)
                        y = PAGE_HEIGHT - MARGIN_Y - ((row + 1) * CARD_SIZE)
                        
                        c.setStrokeColorRGB(0.5, 0.5, 0.5) 
                        c.rect(x, y, CARD_SIZE, CARD_SIZE, stroke=1, fill=0)
                        
                        img = fetch_arasaac_image(word)
                        if img:
                            img_size = CARD_SIZE * 0.75
                            img_x = x + (CARD_SIZE - img_size) / 2
                            img_y = y + (CARD_SIZE - img_size) - (0.2 * CM)
                            temp_path = f"temp_{current_idx}.jpg"
                            img.save(temp_path, "JPEG")
                            c.drawImage(temp_path, img_x, img_y, width=img_size, height=img_size)
                            os.remove(temp_path) 
                        
                        c.setFillColorRGB(0, 0, 0)
                        c.setFont('CustomFont', 14) 
                        text_width = c.stringWidth(word, 'CustomFont', 14)
                        c.drawString(x + (CARD_SIZE - text_width)/2, y + (0.4 * CM), word)
                        
                        current_idx += 1
                        progress_bar.progress(current_idx / len(card_list))
                        
                c.showPage() 
            c.save()
            
            # 提供下載按鈕
            with open(output_pdf, "rb") as pdf_file:
                st.success("✅ 圖卡生成完畢！請點擊下方按鈕下載：")
                st.download_button(
                    label="📥 下載 PDF 檔案",
                    data=pdf_file,
                    file_name="AAC_PECS_Cards.pdf",
                    mime="application/pdf"
                )
