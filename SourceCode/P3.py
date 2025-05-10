import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

# Đọc dữ liệu
df = pd.read_csv("results.csv")

# Bỏ các cột định danh không dùng cho phân cụm
cols_to_drop = ["Player", "Squad", "Nation", "Pos", "Age"]
df_clean = df.drop(columns=cols_to_drop, errors='ignore')

# Làm sạch và chuyển đổi sang kiểu số (loại bỏ % nếu có)
def clean_numeric(col):
    return pd.to_numeric(col.astype(str).str.replace('%', '', regex=False), errors='coerce')

df_clean = df_clean.apply(clean_numeric)

# Sử dụng SimpleImputer để điền giá trị NaN bằng trung bình của cột
imputer = SimpleImputer(strategy="mean")
df_clean_imputed = imputer.fit_transform(df_clean)

# Chuẩn hóa dữ liệu
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df_clean_imputed)

# Áp dụng phương pháp Elbow để tìm số cụm tối ưu
inertia = []
K_range = range(1, 30)

for k in K_range:
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(X_scaled)
    inertia.append(kmeans.inertia_)

# Tính toán số K tối ưu từ sự thay đổi lớn nhất trong inertia
# Tìm sự thay đổi lớn nhất giữa các inertia liên tiếp
inertia_diff = [inertia[i] - inertia[i+1] for i in range(len(inertia)-1)]
optimal_K = inertia_diff.index(max(inertia_diff)) + 2
print(f"Số K tối ưu là {optimal_K}, vì từ K={optimal_K-1} tới K={optimal_K} ta nhận thấy giá trị của Inertia (quán tính) giảm mạnh nhất, và từ đó các sự thay đổi trở nên ít đi, tức là đã đạt đến điểm elbow")

# Vẽ biểu đồ Elbow
plt.figure(figsize=(8, 5))
plt.plot(K_range, inertia, 'bo-', markersize=8)
plt.xlabel('Số cụm (k)')
plt.ylabel('Inertia')
plt.title('Phương pháp Elbow để chọn số cụm K')
plt.grid(True)
plt.tight_layout()
plt.show()

# Áp dụng K-means phân cụm với số K tối ưu
kmeans_optimal = KMeans(n_clusters=optimal_K, random_state=42, n_init=10)
df_clean['Cluster'] = kmeans_optimal.fit_predict(X_scaled)

# Giảm chiều dữ liệu xuống 2D với PCA
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)

# Trực quan hóa kết quả phân cụm
plt.figure(figsize=(8, 5))
plt.scatter(X_pca[:, 0], X_pca[:, 1], c=df_clean['Cluster'], cmap='viridis', s=50)
plt.title('Phân cụm K-means với số K tối ưu (PCA 2D)')
plt.xlabel('PC 1')
plt.ylabel('PC 2')
plt.colorbar(label='Cluster')
plt.show()
