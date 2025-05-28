# 🔥 C2C Panel - Flask-based Command & Control Interface

Panel web ini berfungsi sebagai pusat kendali untuk menerima informasi dari client, menampilkan lokasi perangkat, menyimpan file log, serta mengirimkan perintah ke client.

## 🚀 Fitur

- Deteksi lokasi perangkat berdasarkan IP atau koordinat GPS
- Upload & manajemen file dari client
- Tampilan keylogger log
- Panel berbasis Web dengan peta interaktif (Leaflet)
- Komunikasi real-time via WebSocket (Flask-SocketIO)
- Kirim perintah eksekusi jarak jauh ke client

## 🛠️ Instalasi

1. **Clone repo ini**

```bash
git clone https://github.com/yourusername/yourrepo.git
cd yourrepo
```

2. **Install dependencies**

Pastikan kamu sudah menggunakan Python 3.8+.

```bash
pip install -r requirements.txt
```

3. **Siapkan file konfigurasi**

Buat file `config.py` di root project dengan isi seperti:

```python
API_TOKEN = "your-secret-token"
```

4. **Jalankan server**

```bash
python app.py
```

Aplikasi akan berjalan di: [http://localhost:5000](http://localhost:5000)

## 🔐 Autentikasi

Semua endpoint penting menggunakan `API_TOKEN`. Pastikan setiap request dari client menyertakan header:

```
Authorization: Bearer your-secret-token
```

## 📂 Struktur Folder

- `uploads/` : Folder penyimpanan file dari client
- `logs/` : File log perangkat dan aktivitas
- `GeoLite2-City.mmdb` : Database geolokasi (diperlukan)

## 🗺️ Lokasi & Map

Peta ditampilkan menggunakan Leaflet dengan dukungan data dari `ipinfo.io`. Untuk meningkatkan akurasi, pengguna dapat mengizinkan lokasi GPS via browser.

## 📦 Dependencies

- Flask
- Flask-SocketIO
- Eventlet
- Requests
- GeoIP2
- Pynput

## 📜 Lisensi

MIT License.
