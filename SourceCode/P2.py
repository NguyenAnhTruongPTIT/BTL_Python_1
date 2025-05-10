import pandas as pd
import numpy as np # Mặc dù không dùng trực tiếp, pandas cần numpy
import matplotlib.pyplot as plt
import os # Để làm việc với thư mục

def plot_histograms(df: pd.DataFrame, numeric_cols: list, grouped_by_squad=None): # Bỏ output_dir
    """
    Vẽ và hiển thị biểu đồ histogram cho mỗi cột thống kê số.
    Một biểu đồ cho toàn giải và một biểu đồ cho mỗi đội (nếu có).

    Args:
        df (pd.DataFrame): DataFrame chứa toàn bộ dữ liệu.
        numeric_cols (list): Danh sách các cột số cần vẽ histogram.
        grouped_by_squad (pd.core.groupby.generic.DataFrameGroupBy, optional):
            Đối tượng DataFrame đã được nhóm theo 'Squad'. Mặc định là None.
    """
    for col_stat in numeric_cols:
        data_for_hist = df[col_stat].dropna()
        # 1. Histogram cho toàn giải
        plt.figure(figsize=(10, 6))
        plt.hist(data_for_hist, bins='auto', color='skyblue', edgecolor='black')
        plt.title(f"Phân phối của {col_stat} - Toàn giải")
        plt.xlabel(col_stat)
        plt.ylabel("Số lượng cầu thủ")
        plt.grid(axis='y', alpha=0.75)
        plt.show() # Hiển thị biểu đồ
        
        # 2. Histogram cho từng đội (nếu có grouped_by_squad)
        if grouped_by_squad is not None:
            print(f"    Đang xử lý histogram theo đội cho cột: {col_stat}")
            for team_name, team_data_group in grouped_by_squad:
                team_stat_data = team_data_group[col_stat].dropna()
                
                if team_stat_data.empty:
                    continue

                plt.figure(figsize=(10, 6)) # Tạo figure mới cho mỗi biểu đồ của đội
                plt.hist(team_stat_data, bins='auto', color='lightcoral', edgecolor='black')
                plt.title(f"Phân phối của {col_stat} - Đội: {team_name}")
                plt.xlabel(col_stat)
                plt.ylabel("Số lượng cầu thủ")
                plt.grid(axis='y', alpha=0.75)
                plt.show() # Hiển thị biểu đồ của đội
            print(f"    Đã xử lý xong histogram theo đội cho cột: {col_stat}")
            
    print("Hoàn tất việc chuẩn bị hiển thị histogram. Các cửa sổ biểu đồ sẽ lần lượt xuất hiện.")


def main():
    # --- 1. Đọc dữ liệu ---
    df = pd.read_csv("results.csv", na_values='N/a')
    # --- 2. Xử lý giá trị bị thiếu ---
    numeric_cols = df.select_dtypes(include='number').columns.tolist() 
    df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
    print(f"Đã xử lý giá trị bị thiếu cho các cột số: {numeric_cols}.")
    required_text_cols = ['Player', 'Squad']
    missing_text_cols = [col for col in required_text_cols if col not in df.columns]
    # --- 3. Ghi file top_3.txt: Top 3 cao nhất và thấp nhất mỗi thống kê ---
    
    with open("top_3.txt", "w", encoding="utf-8") as f:
        for col_stat in numeric_cols: 
            f.write(f"----------- Thống kê: {col_stat} -----------\n")

            display_cols_for_top_bottom = []
            if 'Player' in df.columns:
                display_cols_for_top_bottom.append('Player')
            if 'Squad' in df.columns:
                display_cols_for_top_bottom.append('Squad')
            display_cols_for_top_bottom.append(col_stat)
            
            if df[col_stat].notna().any(): 
                top3 = df.nlargest(3, col_stat)[display_cols_for_top_bottom]
                bot3 = df.nsmallest(3, col_stat)[display_cols_for_top_bottom]
                    
                f.write(f"Top 3 CAO NHẤT theo {col_stat}:\n")
                f.write(top3.to_string(index=False) + "\n")
                f.write(f"Top 3 THẤP NHẤT theo {col_stat}:\n")
                f.write(bot3.to_string(index=False) + "\n\n")
            else:
                f.write(f"Cột {col_stat} không có dữ liệu hợp lệ để tìm top/bottom 3.\n\n")
    print("Ghi tệp 'top_3.txt' hoàn tất.")
    

    # --- 4. Nhóm dữ liệu theo đội ---
    grouped_by_squad = None 
    if 'Squad' in df.columns:
        grouped_by_squad = df.groupby('Squad')
    else:
        print("CẢNH BÁO: Không tìm thấy cột 'Squad'. Không thể nhóm theo đội.")

    # --- 5. Tính median, mean, std cho toàn giải ---
    all_league_stats = None
    if numeric_cols: 
        if not df[numeric_cols].empty:
            all_league_stats = df[numeric_cols].agg(['median', 'mean', 'std']).T 
            print("Đã tính toán median, mean, std cho toàn giải.")
        else:
            print("Không có dữ liệu số để tính thống kê toàn giải.")
    else:
        print("Không có cột số nào được xác định để tính thống kê toàn giải.")


    # --- 6. Chuẩn bị kết quả và tạo file results2.csv ---
    if numeric_cols and all_league_stats is not None and grouped_by_squad is not None:
        print("Đang chuẩn bị dữ liệu cho 'results2.csv'...")
        rows_for_results2 = []
        
        columns_for_results2 = ['Squad']
        for col_stat in numeric_cols:
            columns_for_results2.extend([f"Median của {col_stat}", f"Mean của {col_stat}", f"Std của {col_stat}"])

        all_league_values = []
        for col_stat in numeric_cols:
            if col_stat in all_league_stats.index:
                all_league_values.extend([
                    all_league_stats.loc[col_stat, 'median'],
                    all_league_stats.loc[col_stat, 'mean'],
                    all_league_stats.loc[col_stat, 'std']
                ])
            else: 
                all_league_values.extend([np.nan, np.nan, np.nan])

        rows_for_results2.append(['all'] + all_league_values)

        if not grouped_by_squad[numeric_cols].first().empty: # Kiểm tra nếu có dữ liệu số trong nhóm
            team_aggregated_stats = grouped_by_squad[numeric_cols].agg(['median', 'mean', 'std'])
            for team_name, team_specific_stats in team_aggregated_stats.iterrows():
                team_values = []
                for col_stat in numeric_cols:
                    team_values.extend([
                        team_specific_stats.get((col_stat, 'median'), np.nan), 
                        team_specific_stats.get((col_stat, 'mean'), np.nan),
                        team_specific_stats.get((col_stat, 'std'), np.nan)
                    ])
                rows_for_results2.append([team_name] + team_values)
        else:
            print("Cảnh báo: Không có dữ liệu số trong các nhóm đội để tổng hợp cho results2.csv.")


        results2_df = pd.DataFrame(rows_for_results2, columns=columns_for_results2)
        results2_df.to_csv('results2.csv', index=False, encoding='utf-8-sig') 
        print("Ghi tệp 'results2.csv' hoàn tất.")
        print("\n5 dòng đầu của 'results2.csv':")
        print(results2_df.head())
    else:
        print("Bỏ qua việc tạo 'results2.csv' do thiếu grouped_by_squad, all_league_stats hoặc numeric_cols.")

    # --- 7. Vẽ Histograms CHỈ CHO CÁC CỘT TẤN CÔNG VÀ PHÒNG NGỰ ĐƯỢC CHỈ ĐỊNH ---
    attack_cols_defined = ["Gls", "Ast", "Dist"]
    defense_cols_defined = ["Tkl", "TklW", "Att_Defensive act"]
    
    target_hist_cols = attack_cols_defined + defense_cols_defined
    
    cols_to_plot_actual = []
    for col_name in target_hist_cols:
        if col_name in df.columns: 
            if pd.api.types.is_numeric_dtype(df[col_name]): 
                cols_to_plot_actual.append(col_name)

    if cols_to_plot_actual: 
        print(f"\nSẽ vẽ histogram cho các cột: {', '.join(cols_to_plot_actual)}")
        plot_histograms(df, cols_to_plot_actual, grouped_by_squad)
    else:
        print("\nKhông có cột tấn công/phòng ngự hợp lệ nào được tìm thấy để vẽ histogram.")

if __name__ == '__main__':
    main()