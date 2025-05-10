from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from io import StringIO
import pandas as pd
import time

driver=webdriver.Chrome()
# các liên kết đến các bảng dữ liệu
links = {
    "Standard": ("https://fbref.com/en/comps/9/stats/Premier-League-Stats", "stats_standard"),
    "Goalkeeping": ("https://fbref.com/en/comps/9/keepers/Premier-League-Stats", "stats_keeper"),
    "Shooting": ("https://fbref.com/en/comps/9/shooting/Premier-League-Stats", "stats_shooting"),
    "Passing": ("https://fbref.com/en/comps/9/passing/Premier-League-Stats", "stats_passing"),
    "GnS Creation": ("https://fbref.com/en/comps/9/gca/Premier-League-Stats", "stats_gca"),
    "Defensive act": ("https://fbref.com/en/comps/9/defense/Premier-League-Stats", "stats_defense"),
    "Possession": ("https://fbref.com/en/comps/9/possession/Premier-League-Stats", "stats_possession"),
    "Misc": ("https://fbref.com/en/comps/9/misc/Premier-League-Stats", "stats_misc")
}

dfs=[]
# Hàm để lấy dữ liệu từ các bảng
def scraping(url, table_id):
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    table = soup.find("table", {"id": table_id})
    df = pd.read_html(StringIO(str(table)), header=1)[0]
    df=df[~df["Rk"].str.contains("Rk", na=False)]
    df = df[df.apply(lambda row: not any(row.astype(str) == row.name), axis=1)]
    return df
all_df = None
# Duyệt qua từng liên kết và lấy dữ liệu, sau đó gộp lại
for name, (url, table_id) in links.items():
    df = scraping(url, table_id)
    if all_df is None:
        all_df = df
    else:
        all_df = pd.merge(all_df, df, on=["Player", "Squad"], how="outer", suffixes=("", f"_{name}"))
        print(f"Gộp với {name} xong, kích thước all_df: {all_df.shape}")
# Các cột cần giữ lại trong DataFrame
columns_to_keep = [
    # Thông tin cơ bản
    "Player", "Squad", "Nation", "Pos", "Age",
    # Thời gian thi đấu
    "MP", "Starts", "Min",
    # Hiệu suất thi đấu
    "Gls", "Ast", "CrdY", "CrdR",
    # Chỉ số kỳ vọng
    "xG", "xAG",
    # Tiến triển bóng
    "PrgC", "PrgP", "PrgR",
    # Thống kê theo 90 phút
    "Gls.1", "Ast.1", "xG.1", "xAG.1",
    # Thủ môn - Performance
    "GA90", "Save%", "CS%",
    # Thủ môn - Penalty
    "PKsv",
    # Dứt điểm - Standard
    "SoT%", "SoT/90", "G/Sh", "Dist",
    # Chuyền bóng - Tổng
    "Cmp", "Cmp%", "TotDist",
    # Chuyền bóng - Ngắn / Trung bình / Dài
    "Cmp%.1", "Cmp%.2", "Cmp%.3",
    # Chuyền bóng - Kỳ vọng & sáng tạo
    "KP", "1/3", "PPA", "CrsPA", "PrgP_Passing",
    # Kiến tạo và tạo cơ hội ghi bàn
    "SCA", "SCA90", "GCA", "GCA90",
    # Phòng ngự - Tắc bóng & tranh chấp
    "Tkl", "TklW", "Att_Defensive act", "Lost",
    # Phòng ngự - Chặn bóng
    "Blocks", "Sh_Defensive act", "Pass", "Int",
    # Kiểm soát bóng - Chạm bóng
    "Touches", "Def Pen", "Def 3rd_Possession",
    "Mid 3rd_Possession", "Att 3rd_Possession", "Att Pen",
    # Kiểm soát bóng - Đi bóng
    "Att_Possession", "Succ%", "Tkld%",
    # Kiểm soát bóng - Carry
    "Carries", "PrgDist_Possession", "PrgC_Possession",
    "1/3_Possession", "CPA", "Mis", "Dis",
    # Nhận bóng
    "Rec", "PrgR_Possession",
    # Thống kê khác - Hiệu suất
    "Fls", "Fld_Misc", "Off", "Crs", "Recov",
    # Không chiến
    "Won", "Lost_Misc", "Won%"
]

if "Min" in all_df.columns:
    all_df["Min"] = pd.to_numeric(all_df["Min"], errors="coerce")
    all_df = all_df[all_df["Min"] > 90]

# Thay thế giá trị NaN bằng "N/a"
all_df.fillna("N/a", inplace=True)
#  Thay thế giá trị "N/a" bằng NaN
all_df["First_name"] = all_df["Player"].apply(lambda x: x.split()[0] if isinstance(x, str) else "N/a")

# Sắp xếp DataFrame theo First_name
all_df = all_df.sort_values(by="First_name")

# Lọc các cột cần thiết
all_df = all_df[[col for col in columns_to_keep if col in all_df.columns]]
# Replace missing values with "N/a"
all_df.fillna("N/a", inplace=True)

# Lưu DataFrame vào file CSV
all_df.to_csv("results.csv", index=False, encoding="utf-8-sig")
print("Dữ liệu đã được lưu vào file results.csv.")