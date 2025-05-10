import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import time
from rapidfuzz import process, fuzz

# --- Cấu hình Toàn cục ---
# URL và Scraping
BASE_URL_SCRAPING = "https://www.footballtransfers.com/us/values/players/most-valuable-soccer-players/playing-in-uk-premier-league"
NUMBER_OF_PAGES_TO_SCRAPE = 22 

# Tệp CSV
INPUT_STATS_CSV_PATH = "results.csv"
OUTPUT_FINAL_CSV_PATH = "players_900mins_transfer_values.csv"

# Lọc và So khớp
MINIMUM_PLAYING_TIME_MINS = 900
FUZZY_MATCH_SIMILARITY_THRESHOLD_PERCENT = 80
COLUMNS_TO_KEEP_FROM_STATS_FILE = ["Player", "Nation", "Pos", "Squad", "Age", "Min"]

# --- Bước 1: Hàm Thu Thập Dữ Liệu từ Web ---
def scrape_player_values(base_url: str, num_pages: int) -> pd.DataFrame:
    """
    Quét tên cầu thủ, đội bóng và giá trị chuyển nhượng từ footballtransfers.com.
    """
    players_data = []
    print("Đang khởi tạo WebDriver cho việc scraping...")
    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
        print("WebDriver đã khởi tạo thành công.")
    except Exception as e:
        print(f"Lỗi nghiêm trọng khi khởi tạo WebDriver: {e}")
        return pd.DataFrame(players_data)

    print(f"Bắt đầu quét {num_pages} trang từ {base_url}...")
    for i in range(1, num_pages + 1):
        url_to_scrape = base_url
        if i != 1:
            url_to_scrape += "/" + str(i)
        print(f"  Đang xử lý trang {i}: {url_to_scrape}")
        try:
            driver.get(url_to_scrape)
            time.sleep(3) # Chờ trang tải - có thể cần điều chỉnh hoặc dùng WebDriverWait
            html_source = driver.page_source
            soup = BeautifulSoup(html_source, "html.parser")
            player_table = soup.find("table", class_="table table-hover no-cursor table-striped leaguetable mvp-table mb-0")

            if player_table:
                table_rows = player_table.find_all("tr")
                for row_index, row in enumerate(table_rows):
                    if row_index == 0: continue
                    columns = row.find_all("td")
                    if columns and len(columns) > 4:
                        try:
                            player_name_tag = columns[2].find("a")
                            player_name = player_name_tag.text.strip() if player_name_tag else "N/A"
                            team_tag = columns[4].find("span", class_="td-team__teamname")
                            team_name = team_tag.text.strip() if team_tag else "N/A"
                            player_value = columns[-1].text.strip()
                            if player_name != "N/A":
                                players_data.append({"Player": player_name, "Team": team_name, "Value_Scraped": player_value})
                        except (IndexError, AttributeError) as e_parse:
                             print(f"    Lỗi nhỏ khi phân tích hàng {row_index} ở trang {i}: {e_parse}")
            else:
                print(f"    Không tìm thấy bảng dữ liệu trên trang {i}.")
        except Exception as e_page:
            print(f"    Lỗi không mong muốn khi xử lý trang {i}: {e_page}")

    print("Quá trình quét dữ liệu từ web đã hoàn tất.")
    if driver:
        driver.quit()
        print("WebDriver đã được đóng.")
    if not players_data:
        print("CẢNH BÁO: Không thu thập được dữ liệu cầu thủ nào từ web.")
    return pd.DataFrame(players_data)

# --- Bước 2: Hàm Đọc và Lọc Dữ liệu Thống kê Cầu thủ ---
def read_and_filter_player_stats(stats_csv_path: str, min_playing_time: int, columns_to_keep: list) -> pd.DataFrame:
    """
    Đọc tệp CSV thống kê, lọc theo phút thi đấu và giữ lại các cột chỉ định.
    """
    print(f"\nĐang đọc dữ liệu thống kê từ tệp: {stats_csv_path}...")
    try:
        df_stats = pd.read_csv(stats_csv_path)
        print("Đọc tệp CSV thống kê thành công.")
    except FileNotFoundError:
        print(f"LỖI: Không tìm thấy tệp '{stats_csv_path}'.")
        return pd.DataFrame()
    except Exception as e:
        print(f"LỖI: Đã xảy ra sự cố khi đọc tệp '{stats_csv_path}': {e}")
        return pd.DataFrame()

    required_cols_stats = ["Player", "Min"]
    for col in required_cols_stats:
        if col not in df_stats.columns:
            print(f"LỖI: Cột bắt buộc '{col}' không tìm thấy trong '{stats_csv_path}'.")
            return pd.DataFrame()

    if df_stats['Min'].dtype == 'object': # Xử lý cột 'Min' nếu là dạng chuỗi (ví dụ: '1,234')
        df_stats['Min'] = df_stats['Min'].astype(str).str.replace(',', '', regex=False)
        df_stats['Min'] = pd.to_numeric(df_stats['Min'], errors='coerce')
        df_stats.dropna(subset=['Min'], inplace=True)

    filtered_players_df = df_stats[df_stats["Min"] > min_playing_time].copy()
    if filtered_players_df.empty:
        print(f"Không tìm thấy cầu thủ nào có số phút thi đấu > {min_playing_time} phút.")
        return pd.DataFrame()
    print(f"Tìm thấy {len(filtered_players_df)} cầu thủ có số phút thi đấu > {min_playing_time} phút.")
    
    valid_columns_to_keep = [col for col in columns_to_keep if col in filtered_players_df.columns]
    final_df = filtered_players_df[valid_columns_to_keep].reset_index(drop=True)
    print(f"Đã chọn các cột từ file stats: {valid_columns_to_keep}")
    return final_df

# --- Bước 3: Hàm Kết hợp Dữ liệu và Thêm Giá Trị ---
def combine_data_and_add_values(
    df_filtered_stats: pd.DataFrame,
    df_scraped_values: pd.DataFrame,
    similarity_threshold: int
) -> pd.DataFrame:
    """
    Kết hợp DataFrame thống kê đã lọc với DataFrame giá trị từ web.
    """
    if df_filtered_stats.empty:
        print("LỖI: DataFrame thống kê cầu thủ đã lọc trống khi kết hợp.")
        return pd.DataFrame()
    if df_scraped_values.empty:
        print("CẢNH BÁO: DataFrame giá trị từ web trống khi kết hợp. Sẽ trả về DataFrame thống kê chưa có giá trị.")
        df_filtered_stats['Transfer_Value'] = None
        df_filtered_stats['Match_Score'] = None
        return df_filtered_stats

    print("\nBắt đầu quá trình kết hợp dữ liệu và thêm giá trị chuyển nhượng...")
    df_combined = df_filtered_stats.copy()
    df_combined["Transfer_Value"] = None

    if 'Player' not in df_scraped_values.columns or 'Value_Scraped' not in df_scraped_values.columns:
        print("LỖI: DataFrame từ web thiếu cột 'Player' hoặc 'Value_Scraped'.")
        return df_combined # Trả về với cột giá trị rỗng

    scraped_player_names = df_scraped_values['Player'].dropna().astype(str).tolist()
    if not scraped_player_names:
        print("CẢNH BÁO: Không có tên cầu thủ nào trong DataFrame từ web để so khớp.")
        return df_combined

    print(f"Thực hiện so khớp tên cho {len(df_combined)} cầu thủ đã lọc...")
    matched_count = 0
    for index, row in df_combined.iterrows():
        player_name_to_match = str(row["Player"])
        match_result = process.extractOne(
            player_name_to_match,
            scraped_player_names,
            scorer=fuzz.token_sort_ratio
        )
        if match_result:
            best_match_name, score, _ = match_result
            if score >= similarity_threshold:
                value_series = df_scraped_values.loc[df_scraped_values["Player"] == best_match_name, "Value_Scraped"]
                if not value_series.empty:
                    df_combined.at[index, "Transfer_Value"] = value_series.iloc[0]
                    df_combined.at[index, "Match_Score"] = score
                    matched_count += 1
            
    print(f"Hoàn tất so khớp. Đã tìm thấy và gán giá trị cho {matched_count} cầu thủ.")
    
    # Xóa các cầu thủ không tìm được giá trị chuyển nhượng
    # Điều này đảm bảo rằng tất cả các cầu thủ trong tệp cuối cùng đều có giá trị.
    # Nếu bạn muốn giữ lại cả những cầu thủ không có giá trị, hãy bỏ qua dòng này.
    df_combined.dropna(subset=['Transfer_Value'], inplace=True)
    print(f"Số cầu thủ còn lại sau khi loại bỏ những người không có giá trị chuyển nhượng: {len(df_combined)}")
    
    return df_combined.reset_index(drop=True)

# --- Bước 4: Hàm Chính (Main Function) ---
def main():
    """
    Hàm chính điều phối toàn bộ quy trình:
    1. Thu thập dữ liệu giá trị cầu thủ từ web.
    2. Đọc và lọc dữ liệu thống kê cầu thủ từ tệp CSV.
    3. Kết hợp hai bộ dữ liệu.
    4. Lưu kết quả cuối cùng ra tệp CSV.
    """
    print("--- BẮT ĐẦU QUY TRÌNH THU THẬP DỮ LIỆU CHUYỂN NHƯỢNG CẦU THỦ ---")

    # 1. Thu thập dữ liệu từ web
    df_scraped = scrape_player_values(BASE_URL_SCRAPING, NUMBER_OF_PAGES_TO_SCRAPE)
    if df_scraped.empty:
        print("Không thể thu thập dữ liệu từ web. Kết thúc quy trình.")
        return
    print(f"\nĐã thu thập {len(df_scraped)} mục giá trị cầu thủ từ web.")
    # print("5 dòng đầu dữ liệu từ web:\n", df_scraped.head())


    # 2. Đọc và lọc dữ liệu thống kê
    # Tạo tệp results.csv giả để thử nghiệm nếu chưa có
    try:
        with open(INPUT_STATS_CSV_PATH, 'r') as f:
            pass # Tệp tồn tại
    except FileNotFoundError:
        print(f"\nCẢNH BÁO: Tệp '{INPUT_STATS_CSV_PATH}' không tìm thấy. Tạo tệp mẫu...")
        sample_data_stats = {
            'Player': ['Robert Lewandowski', 'Kylian Mbappe', 'Erling Haaland', 'Mohamed Salah', 'Lionel Messi Jr.', 'Kevin De Bruyne', 'Sadio Mane'],
            'Nation': ['POL', 'FRA', 'NOR', 'EGY', 'ARG', 'BEL', 'SEN'],
            'Pos': ['FW', 'FW', 'FW', 'FW', 'FW', 'MF', 'FW'],
            'Squad': ['Barcelona', 'PSG', 'Man City', 'Liverpool', 'Inter Miami', 'Man City', 'Al-Nassr'],
            'Age': [35, 25, 23, 31, 36, 32, 31],
            'Min': [3000, 2800, 2500, 3200, 850, 2700, 700], # Một số < 900
        }
        pd.DataFrame(sample_data_stats).to_csv(INPUT_STATS_CSV_PATH, index=False)
        print(f"Tệp mẫu '{INPUT_STATS_CSV_PATH}' đã được tạo. Vui lòng kiểm tra và cập nhật nếu cần.")

    df_stats_filtered = read_and_filter_player_stats(
        INPUT_STATS_CSV_PATH,
        MINIMUM_PLAYING_TIME_MINS,
        COLUMNS_TO_KEEP_FROM_STATS_FILE
    )
    if df_stats_filtered.empty:
        print("Không có dữ liệu thống kê nào sau khi lọc. Kết thúc quy trình.")
        return
    # print("\n5 dòng đầu dữ liệu thống kê đã lọc:\n", df_stats_filtered.head())

    # 3. Kết hợp dữ liệu
    df_final_output = combine_data_and_add_values(
        df_stats_filtered,
        df_scraped,
        FUZZY_MATCH_SIMILARITY_THRESHOLD_PERCENT
    )

    if df_final_output.empty:
        print("\nKhông có dữ liệu nào sau khi kết hợp. Kết thúc quy trình.")
        return
    
    print(f"\nTổng số cầu thủ trong kết quả cuối cùng: {len(df_final_output)}")
    print("\n5 dòng đầu của dữ liệu kết hợp cuối cùng:")
    print(df_final_output.head())

    # 4. Lưu kết quả
    try:
        df_final_output.to_csv(OUTPUT_FINAL_CSV_PATH, index=False, encoding='utf-8-sig') # utf-8-sig để Excel mở tiếng Việt tốt hơn
        print(f"\n--- DỮ LIỆU CUỐI CÙNG ĐÃ ĐƯỢC LƯU VÀO TỆP: {OUTPUT_FINAL_CSV_PATH} ---")
    except Exception as e:
        print(f"LỖI: Không thể lưu kết quả vào tệp CSV. Lỗi: {e}")

    print("\n--- KẾT THÚC QUY TRÌNH ---")

if __name__ == "__main__":
    main()
