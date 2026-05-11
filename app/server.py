import time
import psutil
import subprocess
import json
import threading
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

docker_cache = {"containers": [], "last_update": 0}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
)

def get_cpu_metrics():
    cpu_percent = psutil.cpu_percent(interval=0.5)
    cpu_per_core = psutil.cpu_percent(interval=0.5, percpu=True)
    cpu_freq = psutil.cpu_freq()
    cpu_count = psutil.cpu_count()
    cpu_count_logical = psutil.cpu_count(logical=True)
    load_avg = psutil.getloadavg()
    return {
        "percent": cpu_percent,
        "per_core": cpu_per_core,
        "cores_physical": cpu_count,
        "cores_logical": cpu_count_logical,
        "frequency_mhz": round(cpu_freq.current, 1) if cpu_freq else None,
        "load_avg_1": round(load_avg[0], 2),
        "load_avg_5": round(load_avg[1], 2),
        "load_avg_15": round(load_avg[2], 2),
    }

def get_ram_metrics():
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        "total_gb": round(vm.total / 1e9, 2),
        "used_gb": round(vm.used / 1e9, 2),
        "available_gb": round(vm.available / 1e9, 2),
        "percent": vm.percent,
        "swap_total_gb": round(swap.total / 1e9, 2),
        "swap_used_gb": round(swap.used / 1e9, 2),
        "swap_percent": swap.percent,
    }

def get_disk_metrics():
    partitions = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            partitions.append({
                "mountpoint": part.mountpoint,
                "device": part.device,
                "fstype": part.fstype,
                "total_gb": round(usage.total / 1e9, 2),
                "used_gb": round(usage.used / 1e9, 2),
                "free_gb": round(usage.free / 1e9, 2),
                "percent": usage.percent,
            })
        except PermissionError:
            continue
    io = psutil.disk_io_counters()
    return {
        "partitions": partitions,
        "read_mb": round(io.read_bytes / 1e6, 1) if io else 0,
        "write_mb": round(io.write_bytes / 1e6, 1) if io else 0,
    }

def get_network_metrics():
    net = psutil.net_io_counters()
    return {
        "bytes_sent_mb": round(net.bytes_sent / 1e6, 1),
        "bytes_recv_mb": round(net.bytes_recv / 1e6, 1),
        "packets_sent": net.packets_sent,
        "packets_recv": net.packets_recv,
        "errors_in": net.errin,
        "errors_out": net.errout,
    }

def get_top_processes(n=8):
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    procs.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
    return procs[:n]

def get_system_info():
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time
    uptime_days = int(uptime_seconds // 86400)
    uptime_hours = int((uptime_seconds % 86400) // 3600)
    uptime_minutes = int((uptime_seconds % 3600) // 60)
    users = psutil.users()
    return {
        "boot_time": datetime.fromtimestamp(boot_time).strftime("%Y-%m-%d %H:%M:%S"),
        "uptime": f"{uptime_days}j {uptime_hours}h {uptime_minutes}m",
        "uptime_seconds": int(uptime_seconds),
        "users_connected": len(users),
        "process_count": len(psutil.pids()),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

def update_docker_metrics():
    global docker_cache
    try:
        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            containers = [json.loads(line) for line in result.stdout.strip().split('\n') if line]
            docker_cache["containers"] = containers
            docker_cache["last_update"] = time.time()
    except Exception:
        pass

def get_docker_metrics():
    return docker_cache.get("containers", [])

def docker_refresh_worker():
    while True:
        time.sleep(10)
        update_docker_metrics()

@app.get("/api/metrics")
def metrics():
    return {
        "cpu": get_cpu_metrics(),
        "ram": get_ram_metrics(),
        "disk": get_disk_metrics(),
        "network": get_network_metrics(),
        "processes": get_top_processes(),
        "system": get_system_info(),
        "docker": get_docker_metrics(),
    }

@app.on_event("startup")
async def startup():
    update_docker_metrics()
    thread = threading.Thread(target=docker_refresh_worker, daemon=True)
    thread.start()

app.mount("/", StaticFiles(directory="/app/static", html=True), name="static")
