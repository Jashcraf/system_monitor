#!/usr/bin/env python3
"""
Multi-User System Usage Monitor Server
Serves a web interface showing real-time CPU/GPU usage per user for VPN users
"""

import json
import time
import psutil
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify
from collections import defaultdict
import GPUtil
import subprocess
import re

app = Flask(__name__)

# Store the HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-User System Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background-color: #4CAF50;
            margin-left: 10px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-5px);
        }
        
        .metric-title {
            font-size: 1.3em;
            margin-bottom: 20px;
            text-align: center;
            font-weight: bold;
        }
        
        .usage-bar {
            width: 100%;
            height: 30px;
            background-color: rgba(255, 255, 255, 0.2);
            border-radius: 15px;
            overflow: hidden;
            margin-bottom: 10px;
            position: relative;
        }
        
        .usage-fill {
            height: 100%;
            border-radius: 15px;
            transition: width 0.5s ease;
            background: linear-gradient(90deg, #4CAF50 0%, #FFC107 70%, #F44336 100%);
        }
        
        .usage-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-weight: bold;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.7);
        }
        
        .chart-container {
            height: 200px;
            margin-top: 20px;
            position: relative;
        }
        
        .chart {
            width: 100%;
            height: 100%;
        }
        
        .users-section {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            margin-bottom: 20px;
        }
        
        .section-title {
            font-size: 1.4em;
            margin-bottom: 20px;
            text-align: center;
            font-weight: bold;
        }
        
        .users-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .user-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .user-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .user-name {
            font-size: 1.1em;
            font-weight: bold;
        }
        
        .user-status {
            font-size: 0.9em;
            padding: 3px 8px;
            border-radius: 10px;
            background-color: rgba(76, 175, 80, 0.3);
        }
        
        .user-inactive {
            background-color: rgba(158, 158, 158, 0.3);
        }
        
        .user-metrics {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        
        .user-metric {
            text-align: center;
        }
        
        .user-metric-label {
            font-size: 0.8em;
            opacity: 0.8;
            margin-bottom: 5px;
        }
        
        .user-metric-value {
            font-size: 1.1em;
            font-weight: bold;
        }
        
        .process-list {
            margin-top: 15px;
            max-height: 120px;
            overflow-y: auto;
        }
        
        .process-item {
            background: rgba(255, 255, 255, 0.05);
            margin-bottom: 5px;
            padding: 8px;
            border-radius: 5px;
            font-size: 0.85em;
        }
        
        .process-name {
            font-weight: bold;
            margin-bottom: 2px;
        }
        
        .process-stats {
            opacity: 0.8;
        }
        
        .info-section {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        
        .info-item {
            text-align: center;
        }
        
        .info-label {
            font-size: 0.9em;
            opacity: 0.8;
            margin-bottom: 5px;
        }
        
        .info-value {
            font-size: 1.2em;
            font-weight: bold;
        }
        
        .last-updated {
            text-align: center;
            margin-top: 20px;
            opacity: 0.7;
            font-size: 0.9em;
        }
        
        .scrollable {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .scrollable::-webkit-scrollbar {
            width: 8px;
        }
        
        .scrollable::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }
        
        .scrollable::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.3);
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ hostname }} Multi-User Monitor <span class="status-indicator"></span></h1>
            <p>Real-time CPU and GPU monitoring by user</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-title">Total CPU Usage</div>
                <div class="usage-bar">
                    <div class="usage-fill" id="cpu-fill"></div>
                    <div class="usage-text" id="cpu-text">0%</div>
                </div>
                <canvas class="chart" id="cpu-chart"></canvas>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">Total GPU Usage</div>
                <div class="usage-bar">
                    <div class="usage-fill" id="gpu-fill"></div>
                    <div class="usage-text" id="gpu-text">0%</div>
                </div>
                <canvas class="chart" id="gpu-chart"></canvas>
            </div>
        </div>
        
        <div class="users-section">
            <div class="section-title">User Activity</div>
            <div class="users-grid scrollable" id="users-grid">
                <!-- User cards will be populated here -->
            </div>
        </div>
        
        <div class="info-section">
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">CPU Temperature</div>
                    <div class="info-value" id="cpu-temp">--°C</div>
                </div>
                <div class="info-item">
                    <div class="info-label">GPU Temperature</div>
                    <div class="info-value" id="gpu-temp">--°C</div>
                </div>
                <div class="info-item">
                    <div class="info-label">RAM Usage</div>
                    <div class="info-value" id="ram-usage">-- GB</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Active Users</div>
                    <div class="info-value" id="active-users">--</div>
                </div>
            </div>
            <div class="last-updated" id="last-updated">
                Last updated: Never
            </div>
        </div>
    </div>

    <script>
        class SystemMonitor {
            constructor() {
                this.cpuHistory = [];
                this.gpuHistory = [];
                this.maxHistoryPoints = 60;
                
                this.initCharts();
                this.startMonitoring();
            }
            
            initCharts() {
                this.cpuChart = document.getElementById('cpu-chart');
                this.cpuCtx = this.cpuChart.getContext('2d');
                this.cpuChart.width = this.cpuChart.offsetWidth;
                this.cpuChart.height = this.cpuChart.offsetHeight;
                
                this.gpuChart = document.getElementById('gpu-chart');
                this.gpuCtx = this.gpuChart.getContext('2d');
                this.gpuChart.width = this.gpuChart.offsetWidth;
                this.gpuChart.height = this.gpuChart.offsetHeight;
            }
            
            async fetchSystemData() {
                try {
                    const response = await fetch('/api/system-data');
                    return await response.json();
                } catch (error) {
                    console.error('Failed to fetch system data:', error);
                    return null;
                }
            }
            
            updateUI(data) {
                if (!data) return;
                
                // Update total CPU
                const cpuFill = document.getElementById('cpu-fill');
                const cpuText = document.getElementById('cpu-text');
                cpuFill.style.width = `${data.cpu.usage}%`;
                cpuText.textContent = `${Math.round(data.cpu.usage)}%`;
                
                // Update total GPU
                const gpuFill = document.getElementById('gpu-fill');
                const gpuText = document.getElementById('gpu-text');
                gpuFill.style.width = `${data.gpu.usage}%`;
                gpuText.textContent = `${Math.round(data.gpu.usage)}%`;
                
                // Update users
                this.updateUsersGrid(data.users);
                
                // Update additional info
                document.getElementById('cpu-temp').textContent = data.cpu.temperature;
                document.getElementById('gpu-temp').textContent = data.gpu.temperature;
                document.getElementById('ram-usage').textContent = data.memory.display;
                document.getElementById('active-users').textContent = data.active_user_count;
                
                // Update timestamp
                document.getElementById('last-updated').textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
                
                // Update history
                this.cpuHistory.push(data.cpu.usage);
                this.gpuHistory.push(data.gpu.usage);
                
                if (this.cpuHistory.length > this.maxHistoryPoints) {
                    this.cpuHistory.shift();
                    this.gpuHistory.shift();
                }
                
                this.drawCharts();
            }
            
            updateUsersGrid(users) {
                const grid = document.getElementById('users-grid');
                grid.innerHTML = '';
                
                users.forEach(user => {
                    const userCard = document.createElement('div');
                    userCard.className = 'user-card';
                    
                    const isActive = user.cpu_usage > 5 || user.processes.length > 0;
                    const statusClass = isActive ? '' : 'user-inactive';
                    const statusText = isActive ? 'Active' : 'Idle';
                    
                    let processesHtml = '';
                    if (user.processes.length > 0) {
                        processesHtml = `
                            <div class="process-list">
                                ${user.processes.slice(0, 3).map(proc => `
                                    <div class="process-item">
                                        <div class="process-name">${proc.name}</div>
                                        <div class="process-stats">CPU: ${proc.cpu_percent}% | RAM: ${proc.memory_mb}MB</div>
                                    </div>
                                `).join('')}
                                ${user.processes.length > 3 ? `<div class="process-item" style="text-align: center; opacity: 0.6;">+${user.processes.length - 3} more processes...</div>` : ''}
                            </div>
                        `;
                    }
                    
                    userCard.innerHTML = `
                        <div class="user-header">
                            <div class="user-name">${user.username}</div>
                            <div class="user-status ${statusClass}">${statusText}</div>
                        </div>
                        <div class="user-metrics">
                            <div class="user-metric">
                                <div class="user-metric-label">CPU Usage</div>
                                <div class="user-metric-value">${user.cpu_usage.toFixed(1)}%</div>
                            </div>
                            <div class="user-metric">
                                <div class="user-metric-label">RAM Usage</div>
                                <div class="user-metric-value">${user.memory_usage.toFixed(1)}%</div>
                            </div>
                        </div>
                        ${processesHtml}
                    `;
                    
                    grid.appendChild(userCard);
                });
                
                if (users.length === 0) {
                    grid.innerHTML = '<div style="text-align: center; opacity: 0.6; padding: 20px;">No active users detected</div>';
                }
            }
            
            drawCharts() {
                this.drawChart(this.cpuCtx, this.cpuHistory, '#4CAF50');
                this.drawChart(this.gpuCtx, this.gpuHistory, '#FF9800');
            }
            
            drawChart(ctx, data, color) {
                const canvas = ctx.canvas;
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                if (data.length < 2) return;
                
                const padding = 20;
                const width = canvas.width - padding * 2;
                const height = canvas.height - padding * 2;
                
                // Draw grid
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
                ctx.lineWidth = 1;
                
                for (let i = 0; i <= 4; i++) {
                    const y = padding + (height / 4) * i;
                    ctx.beginPath();
                    ctx.moveTo(padding, y);
                    ctx.lineTo(canvas.width - padding, y);
                    ctx.stroke();
                }
                
                // Draw data line
                ctx.strokeStyle = color;
                ctx.lineWidth = 2;
                ctx.beginPath();
                
                for (let i = 0; i < data.length; i++) {
                    const x = padding + (width / (data.length - 1)) * i;
                    const y = padding + height - (data[i] / 100) * height;
                    
                    if (i === 0) {
                        ctx.moveTo(x, y);
                    } else {
                        ctx.lineTo(x, y);
                    }
                }
                
                ctx.stroke();
                
                // Fill area under curve
                ctx.lineTo(canvas.width - padding, canvas.height - padding);
                ctx.lineTo(padding, canvas.height - padding);
                ctx.closePath();
                
                const gradient = ctx.createLinearGradient(0, padding, 0, canvas.height - padding);
                gradient.addColorStop(0, color + '40');
                gradient.addColorStop(1, color + '10');
                
                ctx.fillStyle = gradient;
                ctx.fill();
            }
            
            startMonitoring() {
                const updateData = async () => {
                    const data = await this.fetchSystemData();
                    this.updateUI(data);
                };
                
                updateData();
                setInterval(updateData, 3000); // Update every 3 seconds for user data
            }
        }
        
        window.addEventListener('load', () => {
            new SystemMonitor();
        });
        
        window.addEventListener('resize', () => {
            const monitor = new SystemMonitor();
        });
    </script>
</body>
</html>
"""

def get_cpu_temperature():
    """Get CPU temperature if available"""
    try:
        temps = psutil.sensors_temperatures()
        if 'coretemp' in temps:
            return f"{temps['coretemp'][0].current:.1f}°C"
        elif 'cpu_thermal' in temps:
            return f"{temps['cpu_thermal'][0].current:.1f}°C"
        else:
            return "N/A"
    except:
        return "N/A"

def get_gpu_info():
    """Get GPU usage and temperature"""
    try:
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]  # Use first GPU
            return {
                'usage': gpu.load * 100,
                'temperature': f"{gpu.temperature}°C" if gpu.temperature else "N/A"
            }
        else:
            return {'usage': 0, 'temperature': "N/A"}
    except:
        return {'usage': 0, 'temperature': "N/A"}

def get_gpu_processes_nvidia():
    """Get GPU processes using nvidia-smi"""
    try:
        result = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,process_name,used_memory', 
                               '--format=csv,noheader,nounits'], 
                               capture_output=True, text=True, timeout=5)
        
        gpu_processes = {}
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split(', ')
                    if len(parts) >= 3:
                        pid = int(parts[0])
                        gpu_processes[pid] = {
                            'name': parts[1],
                            'gpu_memory': int(parts[2]) if parts[2].isdigit() else 0
                        }
        return gpu_processes
    except:
        return {}

def get_user_processes():
    """Get processes organized by user with resource usage"""
    user_data = defaultdict(lambda: {
        'cpu_usage': 0.0,
        'memory_usage': 0.0,
        'processes': []
    })
    
    gpu_processes = get_gpu_processes_nvidia()
    total_memory = psutil.virtual_memory().total
    
    try:
        # Get all processes
        for proc in psutil.process_iter(['pid', 'username', 'name', 'cpu_percent', 'memory_info']):
            try:
                proc_info = proc.info
                username = proc_info['username']
                
                if username and proc_info['cpu_percent'] is not None:
                    cpu_percent = proc_info['cpu_percent']
                    memory_bytes = proc_info['memory_info'].rss if proc_info['memory_info'] else 0
                    memory_mb = memory_bytes / (1024 * 1024)
                    memory_percent = (memory_bytes / total_memory) * 100
                    
                    # Only include processes with significant resource usage
                    if cpu_percent > 1.0 or memory_mb > 50:
                        user_data[username]['cpu_usage'] += cpu_percent
                        user_data[username]['memory_usage'] += memory_percent
                        
                        # Check if this process is using GPU
                        gpu_info = ""
                        if proc_info['pid'] in gpu_processes:
                            gpu_mem = gpu_processes[proc_info['pid']]['gpu_memory']
                            gpu_info = f" (GPU: {gpu_mem}MB)"
                        
                        user_data[username]['processes'].append({
                            'pid': proc_info['pid'],
                            'name': proc_info['name'] + gpu_info,
                            'cpu_percent': round(cpu_percent, 1),
                            'memory_mb': round(memory_mb, 1)
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as e:
        print(f"Error getting user processes: {e}")
    
    # Sort processes by CPU usage for each user
    for username in user_data:
        user_data[username]['processes'].sort(key=lambda x: x['cpu_percent'], reverse=True)
    
    # Convert to list and sort by total CPU usage
    users_list = []
    for username, data in user_data.items():
        users_list.append({
            'username': username,
            'cpu_usage': data['cpu_usage'],
            'memory_usage': data['memory_usage'],
            'processes': data['processes']
        })
    
    users_list.sort(key=lambda x: x['cpu_usage'], reverse=True)
    return users_list

def format_uptime():
    """Format system uptime"""
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    else:
        return f"{hours}h {minutes}m"

@app.route('/')
def index():
    """Serve the main monitoring page"""
    import socket
    hostname = socket.gethostname()
    return render_template_string(HTML_TEMPLATE, hostname=hostname)

@app.route('/api/system-data')
def system_data():
    """API endpoint for system data"""
    try:
        # CPU usage
        cpu_usage = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_used_gb = memory.used / (1024**3)
        memory_total_gb = memory.total / (1024**3)
        
        # GPU info
        gpu_info = get_gpu_info()
        
        # User processes
        users = get_user_processes()
        active_users = sum(1 for user in users if user['cpu_usage'] > 5 or len(user['processes']) > 0)
        
        # System info
        data = {
            'cpu': {
                'usage': cpu_usage,
                'temperature': get_cpu_temperature()
            },
            'gpu': {
                'usage': gpu_info['usage'],
                'temperature': gpu_info['temperature']
            },
            'memory': {
                'used': memory_used_gb,
                'total': memory_total_gb,
                'display': f"{memory_used_gb:.1f} / {memory_total_gb:.1f} GB"
            },
            'users': users,
            'active_user_count': active_users,
            'uptime': format_uptime(),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(data)
        
    except Exception as e:
        print(f"Error in system_data: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import socket
    
    # Get local IP address
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
    except:
        local_ip = '127.0.0.1'
    finally:
        s.close()
    
    print(f"Starting Multi-User System Monitor Server...")
    print(f"Local access: http://localhost:5000")
    print(f"VPN access: http://{local_ip}:5000")
    print("Press Ctrl+C to stop the server")
    print("\nFeatures:")
    print("- Real-time CPU/GPU monitoring")
    print("- Per-user resource usage tracking")
    print("- Process-level details")
    print("- GPU process detection (NVIDIA)")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
