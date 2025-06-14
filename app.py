import os
import re
import asyncio
import aiohttp
import logging
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from bs4 import BeautifulSoup
import pdfplumber
from io import BytesIO
import json
from datetime import datetime
import hashlib
from typing import List, Dict
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ClimateSense AI", version="1.0.0")

# Get current directory
BASE_DIR = Path(__file__).resolve().parent

# Define paths
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
CSS_DIR = STATIC_DIR / "css"
JS_DIR = STATIC_DIR / "js"

# Create directories if they don't exist
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(CSS_DIR, exist_ok=True)
os.makedirs(JS_DIR, exist_ok=True)

# Embedded template content
TEMPLATES = {
    "base.html": """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ClimateSense AI - IPCC Report Summarizer</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#2c3e50">
    <style>
        /* Base styles */
        :root {
            --primary: #2c3e50;
            --secondary: #3498db;
            --success: #27ae60;
            --warning: #f39c12;
            --danger: #e74c3c;
            --light: #ecf0f1;
            --dark: #2c3e50;
            --text: #34495e;
            --bg: #f8f9fa;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--text);
            background-color: var(--bg);
        }
        
        .container {
            width: 100%;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* Header */
        header {
            background: linear-gradient(135deg, var(--primary), #1a2530);
            color: white;
            padding: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        header h1 {
            font-size: 1.8rem;
            margin-bottom: 5px;
        }
        
        header p {
            opacity: 0.9;
        }
        
        /* Buttons */
        .btn-primary {
            background-color: var(--secondary);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-primary:hover {
            background-color: #2980b9;
            transform: translateY(-2px);
        }
        
        .btn-secondary {
            background-color: var(--light);
            color: var(--text);
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-secondary:hover {
            background-color: #d5dbdb;
        }
        
        .btn-small {
            background-color: var(--light);
            color: var(--text);
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 0.8rem;
            cursor: pointer;
        }
        
        /* Cards */
        .report-card, .feature-card {
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            padding: 20px;
            margin-bottom: 20px;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .report-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.1);
        }
        
        .report-card h3 {
            margin-bottom: 10px;
            font-size: 1.2rem;
        }
        
        .meta {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            font-size: 0.9rem;
        }
        
        .date {
            color: #7f8c8d;
        }
        
        .badge {
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        
        .badge.success {
            background-color: rgba(39, 174, 96, 0.1);
            color: var(--success);
        }
        
        .badge.warning {
            background-color: rgba(243, 156, 18, 0.1);
            color: var(--warning);
        }
        
        /* Hero section */
        .hero {
            background: linear-gradient(rgba(44, 62, 80, 0.8), rgba(44, 62, 80, 0.9)), 
                        url('https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?ixlib=rb-4.0.3&auto=format&fit=crop&w=2000&q=80');
            background-size: cover;
            background-position: center;
            color: white;
            text-align: center;
            padding: 60px 20px;
            border-radius: 10px;
            margin: 20px 0;
        }
        
        .hero-content h2 {
            font-size: 2rem;
            margin-bottom: 15px;
        }
        
        .hero-content p {
            font-size: 1.2rem;
            margin-bottom: 25px;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
        }
        
        /* Features */
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 40px 0;
        }
        
        .feature-card {
            text-align: center;
            padding: 30px 20px;
        }
        
        .feature-card h3 {
            font-size: 1.3rem;
            margin-bottom: 15px;
        }
        
        /* Summary view */
        .report-summary {
            background: white;
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            margin: 20px 0;
        }
        
        .summary-section {
            margin-bottom: 25px;
        }
        
        .summary-section h3 {
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .summary-section ul {
            padding-left: 20px;
        }
        
        .summary-section li {
            margin-bottom: 8px;
            line-height: 1.5;
        }
        
        .confidence-level {
            padding: 10px 15px;
            background-color: #f8f9fa;
            border-radius: 8px;
            margin-top: 20px;
            font-weight: bold;
        }
        
        .confidence-high {
            color: var(--success);
        }
        
        .confidence-medium {
            color: var(--warning);
        }
        
        .confidence-low {
            color: var(--danger);
        }
        
        /* Related reports */
        .related-reports {
            margin: 30px 0;
        }
        
        .related-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .related-card {
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        /* Search box */
        .search-box {
            display: flex;
            margin: 20px 0;
        }
        
        .search-box input {
            flex: 1;
            padding: 12px 15px;
            border: 1px solid #ddd;
            border-radius: 8px 0 0 8px;
            font-size: 1rem;
        }
        
        .search-box button {
            background: var(--secondary);
            color: white;
            border: none;
            padding: 0 20px;
            border-radius: 0 8px 8px 0;
            cursor: pointer;
            font-size: 1.2rem;
        }
        
        /* Footer */
        footer {
            margin-top: 40px;
            padding: 20px 0;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9rem;
        }
        
        /* Loaders and empty states */
        .loader, .empty-state {
            text-align: center;
            padding: 30px;
        }
        
        .loader::after {
            content: "";
            display: inline-block;
            width: 24px;
            height: 24px;
            border: 3px solid rgba(52, 152, 219, 0.3);
            border-radius: 50%;
            border-top-color: var(--secondary);
            animation: spin 1s linear infinite;
            margin-left: 10px;
            vertical-align: middle;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .error {
            background-color: #fdecea;
            border: 1px solid #f5c6cb;
            border-radius: 8px;
            padding: 20px;
            color: #721c24;
            margin: 20px 0;
        }
        
        /* Mobile adjustments */
        @media (max-width: 768px) {
            .hero-content h2 {
                font-size: 1.6rem;
            }
            
            .hero-content p {
                font-size: 1rem;
            }
            
            .features {
                grid-template-columns: 1fr;
            }
            
            .report-card {
                padding: 15px;
            }
            
            .container {
                padding: 15px;
            }
        }
        
        /* PWA install prompt */
        .pwa-install {
            margin-top: 15px;
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>ClimateSense AI</h1>
            <p>IPCC Report Insights & Summaries</p>
        </div>
    </header>

    <main class="container">
        {% block content %}{% endblock %}
    </main>

    <footer>
        <div class="container">
            <p>Powered by DeepSeek AI • IPCC Climate Reports</p>
            <div class="pwa-install" id="installContainer" style="display: none;">
                <button id="installBtn">Install App</button>
            </div>
        </div>
    </footer>

    <script>
        // Fallback JavaScript
        // Progressive Web App functionality
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/service-worker.js')
                    .then(registration => {
                        console.log('Service Worker registered:', registration);
                    })
                    .catch(error => {
                        console.log('Service Worker registration failed:', error);
                    });
            });
        }

        // Handle PWA install prompt
        let deferredPrompt;
        const installContainer = document.getElementById('installContainer');
        const installBtn = document.getElementById('installBtn');

        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            if (installContainer) installContainer.style.display = 'block';
        });

        if (installBtn) {
            installBtn.addEventListener('click', () => {
                if (deferredPrompt) {
                    deferredPrompt.prompt();
                    deferredPrompt.userChoice.then(choiceResult => {
                        if (choiceResult.outcome === 'accepted') {
                            console.log('User accepted install');
                        } else {
                            console.log('User dismissed install');
                        }
                        deferredPrompt = null;
                        if (installContainer) installContainer.style.display = 'none';
                    });
                }
            });
        }

        // Check if app is running in standalone mode
        window.addEventListener('load', () => {
            if (window.matchMedia('(display-mode: standalone)').matches && installContainer) {
                installContainer.style.display = 'none';
            }
        });
    </script>
    {% block scripts %}{% endblock %}
</body>
</html>
    """,
    "index.html": """
{% extends "templates/base.html" %}

{% block content %}
<section class="hero">
    <div class="hero-content">
        <h2>AI-Powered IPCC Report Analysis</h2>
        <p>Instant summaries and key insights from complex climate reports</p>
        <button id="scrapeBtn" class="btn-primary">Get Latest Reports</button>
    </div>
</section>

<section class="features">
    <div class="feature-card">
        <h3>📚 Comprehensive</h3>
        <p>Processes full IPCC reports with scientific accuracy</p>
    </div>
    <div class="feature-card">
        <h3>⚡️ Fast Summaries</h3>
        <p>Get executive summaries in seconds, not hours</p>
    </div>
    <div class="feature-card">
        <h3>🌍 Actionable Insights</h3>
        <p>Key findings, risks, and mitigation strategies</p>
    </div>
</section>

<section class="demo">
    <h2>How It Works</h2>
    <ol>
        <li>Automatically retrieves latest IPCC reports</li>
        <li>Extracts and processes content using AI</li>
        <li>Generates concise summaries and insights</li>
        <li>Delivers results to web or mobile</li>
    </ol>
</section>
{% endblock %}

{% block scripts %}
<script>
    document.getElementById('scrapeBtn').addEventListener('click', async () => {
        const btn = document.getElementById('scrapeBtn');
        btn.disabled = true;
        btn.textContent = "Processing...";
        
        try {
            const response = await fetch('/scrape', { method: 'POST' });
            const data = await response.json();
            
            if(data.status === 'success') {
                setTimeout(() => {
                    window.location.href = '/reports';
                }, 2000);
            } else {
                alert('Error: ' + data.message);
                btn.disabled = false;
                btn.textContent = "Get Latest Reports";
            }
        } catch (error) {
            alert('Connection error: ' + error.message);
            btn.disabled = false;
            btn.textContent = "Get Latest Reports";
        }
    });
</script>
{% endblock %}
    """,
    "reports.html": """
{% extends "templates/base.html" %}

{% block content %}
<section class="reports-header">
    <h2>IPCC Reports</h2>
    <p>Click any report to see AI-generated summary</p>
    <div class="search-box">
        <input type="text" id="searchInput" placeholder="Search reports...">
        <button id="searchBtn">🔍</button>
    </div>
</section>

<section class="reports-list" id="reportsList">
    <div class="loader">Loading reports...</div>
</section>
{% endblock %}

{% block scripts %}
<script>
    document.addEventListener('DOMContentLoaded', async () => {
        const reportsList = document.getElementById('reportsList');
        reportsList.innerHTML = '<div class="loader">Loading reports...</div>';
        
        try {
            const response = await fetch('/reports/data');
            const data = await response.json();
            
            if(data.count === 0) {
                reportsList.innerHTML = `
                    <div class="empty-state">
                        <p>No reports found.</p>
                        <a href="/" class="btn-primary">Scrape Reports</a>
                    </div>
                `;
                return;
            }
            
            let html = '';
            data.reports.forEach(report => {
                html += `
                <div class="report-card" data-id="${report.id}">
                    <h3>${report.title}</h3>
                    <div class="meta">
                        <span class="date">${report.date}</span>
                        ${report.summary_available ? 
                          '<span class="badge success">Summary Available</span>' : 
                          '<span class="badge warning">Processing</span>'}
                    </div>
                    <div class="actions">
                        <button class="btn-secondary view-summary">View Summary</button>
                    </div>
                </div>
                `;
            });
            
            reportsList.innerHTML = html;
            
            document.querySelectorAll('.view-summary').forEach(button => {
                button.addEventListener('click', (e) => {
                    const card = e.target.closest('.report-card');
                    const reportId = card.getAttribute('data-id');
                    window.location.href = `/report/${reportId}`;
                });
            });
            
            document.getElementById('searchBtn').addEventListener('click', filterReports);
            document.getElementById('searchInput').addEventListener('keyup', filterReports);
            
        } catch (error) {
            reportsList.innerHTML = `
                <div class="error">
                    <p>Error loading reports: ${error.message}</p>
                    <button class="btn-primary" onclick="location.reload()">Try Again</button>
                </div>
            `;
        }
    });
    
    function filterReports() {
        const searchTerm = document.getElementById('searchInput').value.toLowerCase();
        const cards = document.querySelectorAll('.report-card');
        
        cards.forEach(card => {
            const title = card.querySelector('h3').textContent.toLowerCase();
            if(title.includes(searchTerm)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    }
</script>
{% endblock %}
    """,
    "report.html": """
{% extends "templates/base.html" %}

{% block content %}
<section class="report-header">
    <a href="/reports" class="back-link">← Back to Reports</a>
    <h2 id="reportTitle">Report Summary</h2>
    <p id="reportDate"></p>
</section>

<section class="report-summary">
    <div class="summary-container" id="summaryContainer">
        <div class="loader">Generating summary...</div>
    </div>
    
    <div class="summary-actions">
        <button id="downloadBtn" class="btn-primary">Download Summary</button>
        <button id="shareBtn" class="btn-secondary">Share</button>
    </div>
</section>

<section class="related-reports">
    <h3>Other Reports</h3>
    <div class="related-list" id="relatedReports"></div>
</section>
{% endblock %}

{% block scripts %}
<script>
    document.addEventListener('DOMContentLoaded', async () => {
        const reportId = window.location.pathname.split('/').pop();
        const titleEl = document.getElementById('reportTitle');
        const dateEl = document.getElementById('reportDate');
        const summaryContainer = document.getElementById('summaryContainer');
        
        try {
            const response = await fetch(`/report/${reportId}/data`);
            const data = await response.json();
            
            titleEl.textContent = data.report.title;
            dateEl.textContent = `Published: ${data.report.date}`;
            
            const summary = data.summary;
            let html = '';
            
            if(summary.error) {
                html = `<div class="error"><p>${summary.error}</p></div>`;
            } else {
                html = `
                <div class="summary-section">
                    <h3>🔑 Key Findings</h3>
                    <ul>
                        ${summary.key_findings.map(f => `<li>${f}</li>`).join('')}
                    </ul>
                </div>
                
                <div class="summary-section">
                    <h3>⚠️ Risks</h3>
                    <ul>
                        ${summary.risks.map(r => `<li>${r}</li>`).join('')}
                    </ul>
                </div>
                
                <div class="summary-section">
                    <h3>🛠 Mitigation Options</h3>
                    <ul>
                        ${summary.mitigation_options.map(m => `<li>${m}</li>`).join('')}
                    </ul>
                </div>
                
                <div class="confidence-level">
                    <strong>Confidence Level:</strong> 
                    <span class="confidence-${summary.confidence_level.toLowerCase()}">
                        ${summary.confidence_level}
                    </span>
                </div>
                `;
            }
            
            summaryContainer.innerHTML = html;
            loadRelatedReports(reportId);
            
            document.getElementById('downloadBtn').addEventListener('click', () => {
                downloadSummary(data.report.title, html);
            });
            
            document.getElementById('shareBtn').addEventListener('click', () => {
                shareSummary(data.report.title);
            });
            
        } catch (error) {
            summaryContainer.innerHTML = `
                <div class="error">
                    <p>Error loading report: ${error.message}</p>
                    <button class="btn-primary" onclick="location.reload()">Try Again</button>
                </div>
            `;
        }
    });
    
    async function loadRelatedReports(currentId) {
        const container = document.getElementById('relatedReports');
        container.innerHTML = '<div class="loader">Loading related reports...</div>';
        
        try {
            const response = await fetch('/reports/data');
            const data = await response.json();
            
            const otherReports = data.reports.filter(r => r.id !== currentId).slice(0, 3);
            
            if(otherReports.length === 0) {
                container.innerHTML = '<p>No other reports available</p>';
                return;
            }
            
            let html = '';
            otherReports.forEach(report => {
                html += `
                <div class="related-card" data-id="${report.id}">
                    <h4>${report.title}</h4>
                    <span class="date">${report.date}</span>
                    <button class="btn-small">View</button>
                </div>
                `;
            });
            
            container.innerHTML = html;
            
            document.querySelectorAll('.related-card button').forEach(button => {
                button.addEventListener('click', (e) => {
                    const card = e.target.closest('.related-card');
                    const reportId = card.getAttribute('data-id');
                    window.location.href = `/report/${reportId}`;
                });
            });
            
        } catch (error) {
            container.innerHTML = `<p>Error loading related reports: ${error.message}</p>`;
        }
    }
    
    function downloadSummary(title, content) {
        const blob = new Blob([`
            <!DOCTYPE html>
            <html>
            <head>
                <title>${title} - Summary</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; }
                    h1, h2, h3 { color: #2c3e50; }
                    ul { padding-left: 20px; }
                    li { margin-bottom: 8px; }
                </style>
            </head>
            <body>
                <h1>${title}</h1>
                <div>${content}</div>
            </body>
            </html>
        `], { type: 'text/html' });
        
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `${title.replace(/[^a-z0-9]/gi, '_')}_summary.html`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }
    
    function shareSummary(title) {
        if(navigator.share) {
            navigator.share({
                title: `IPCC Summary: ${title}`,
                text: 'Check out this AI-generated summary of an IPCC climate report',
                url: window.location.href
            }).catch(error => {
                console.log('Sharing failed:', error);
                alert('Sharing not supported. Copy the URL to share.');
            });
        } else {
            alert('Sharing not supported. Copy the URL to share.');
        }
    }
</script>
{% endblock %}
    """
}

# Create templates if they don't exist
for filename, content in TEMPLATES.items():
    filepath = TEMPLATES_DIR / filename
    if not filepath.exists():
        with open(filepath, "w") as f:
            f.write(content)
        logger.info(f"Created template: {filepath}")

# Create static files if they don't exist
if not (CSS_DIR / "style.css").exists():
    with open(CSS_DIR / "style.css", "w") as f:
        f.write("/* CSS is embedded in base.html */")
    logger.info(f"Created CSS placeholder: {CSS_DIR / 'style.css'}")

if not (JS_DIR / "app.js").exists():
    with open(JS_DIR / "app.js", "w") as f:
        f.write("// JavaScript is embedded in base.html")
    logger.info(f"Created JS placeholder: {JS_DIR / 'app.js'}")

# Mount static files and templates
try:
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    templates = Jinja2Templates(directory=TEMPLATES_DIR)
    logger.info(f"Static files mounted from: {STATIC_DIR}")
    logger.info(f"Templates mounted from: {TEMPLATES_DIR}")
except Exception as e:
    logger.error(f"Error mounting static/templates: {str(e)}")

# In-memory storage for demo
reports_store = []
summaries_store = {}

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    logger.warning("DEEPSEEK_API_KEY environment variable is not set!")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def get_report_hash(title: str) -> str:
    return hashlib.md5(title.encode()).hexdigest()

async def fetch_url(url: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.text()
    except Exception as e:
        logger.error(f"Error fetching URL {url}: {str(e)}")
        return None

async def fetch_pdf(url: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.read()
    except Exception as e:
        logger.error(f"Error fetching PDF {url}: {str(e)}")
        return None

def extract_text_from_pdf(pdf_bytes: bytes, max_pages: int = 10) -> str:
    text = ""
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                if i >= max_pages:
                    break
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
    except Exception as e:
        logger.error(f"PDF extraction error: {str(e)}")
    return text

def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\bPage \d+\b', '', text)
    return text.strip()

async def summarize_text(text: str, report_title: str) -> Dict:
    if not DEEPSEEK_API_KEY:
        logger.error("DeepSeek API key is not set!")
        return {
            "key_findings": ["API key not configured"],
            "risks": ["API key not configured"],
            "mitigation_options": ["API key not configured"],
            "confidence_level": "Unknown"
        }
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "You are a climate science expert summarizing IPCC reports. Return output in JSON format."
            },
            {
                "role": "user",
                "content": (
                    f"Create a structured summary with these keys: "
                    f"key_findings (list), risks (list), mitigation_options (list), confidence_level (string). "
                    f"Report Title: {report_title}\n\n"
                    f"Text: {text[:5000]}"
                )
            }
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": 1000
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(DEEPSEEK_API_URL, headers=headers, json=payload) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"DeepSeek API error: {response.status} - {error}")
                    return {
                        "error": f"API error: {response.status}"
                    }
                
                result = await response.json()
                summary_str = result['choices'][0]['message']['content']
                return json.loads(summary_str)
    except Exception as e:
        logger.error(f"Summarization error: {str(e)}")
        return {
            "key_findings": ["Summary not available"],
            "risks": ["Summary not available"],
            "mitigation_options": ["Summary not available"],
            "confidence_level": "Unknown"
        }

async def process_ipcc_report(report_url: str):
    try:
        logger.info(f"Processing report: {report_url}")
        report_html = await fetch_url(report_url)
        if not report_html:
            logger.error(f"Failed to fetch report HTML: {report_url}")
            return None
            
        soup = BeautifulSoup(report_html, 'html.parser')
        
        # Extract report details
        title = soup.select_one('h1.page-header__title')
        if not title:
            logger.error(f"No title found for {report_url}")
            return None
            
        title = title.text.strip()
        date_tag = soup.select_one('.date--publication meta')
        date = date_tag['content'] if date_tag else datetime.now().strftime("%Y-%m-%d")
        
        # Find PDF links
        pdf_links = []
        for link in soup.select('a[href$=".pdf"]'):
            href = link['href']
            if "fullreport" in href.lower():
                full_url = f"https://www.ipcc.ch{href}" if href.startswith('/') else href
                pdf_links.append(full_url)
        
        report_data = {
            "id": get_report_hash(title),
            "title": title,
            "date": date,
            "url": report_url,
            "pdf_urls": pdf_links,
            "summary_available": False
        }
        
        # Store report
        reports_store.append(report_data)
        
        # Process first PDF only for demo
        if pdf_links:
            logger.info(f"Downloading PDF: {pdf_links[0]}")
            pdf_bytes = await fetch_pdf(pdf_links[0])
            if not pdf_bytes:
                logger.error(f"Failed to download PDF: {pdf_links[0]}")
                return report_data
                
            pdf_text = extract_text_from_pdf(pdf_bytes)
            clean_pdf_text = clean_text(pdf_text)
            
            logger.info(f"Generating summary for: {title}")
            summary = await summarize_text(clean_pdf_text, title)
            summaries_store[report_data["id"]] = summary
            report_data["summary_available"] = True
            
        return report_data
    except Exception as e:
        logger.error(f"Error processing report: {str(e)}", exc_info=True)
        return None

async def scrape_ipcc_reports(limit: int = 3):
    base_url = "https://www.ipcc.ch"
    reports_url = f"{base_url}/reports/"
    
    try:
        html_content = await fetch_url(reports_url)
        if not html_content:
            logger.error("Failed to fetch IPCC reports page")
            return []
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get report links
        report_links = []
        for card in soup.select('.card-item__content'):
            link = card.select_one('.card-item__link')
            if link and link.has_attr('href'):
                href = link['href']
                full_url = f"{base_url}{href}" if href.startswith('/') else href
                report_links.append(full_url)
        
        # Process reports concurrently
        tasks = [process_ipcc_report(url) for url in report_links[:limit]]
        results = await asyncio.gather(*tasks)
        
        return [r for r in results if r is not None]
    except Exception as e:
        logger.error(f"Scraping error: {str(e)}", exc_info=True)
        return []

@app.post("/scrape")
async def start_scrape(background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(scrape_ipcc_reports)
        return {
            "status": "success",
            "message": "Scraping started in background. Check /reports endpoint in a few minutes."
        }
    except Exception as e:
        logger.error(f"Error starting scrape: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Internal server error"}
        )

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering home: {str(e)}", exc_info=True)
        return HTMLResponse("<h1>ClimateSense AI</h1><p>Error loading page. Template system is working.</p>")

@app.get("/reports", response_class=HTMLResponse)
async def list_reports(request: Request):
    try:
        return templates.TemplateResponse("reports.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering reports: {str(e)}", exc_info=True)
        return HTMLResponse("<h1>IPCC Reports</h1><p>Error loading reports. Template system is working.</p>")

@app.get("/reports/data")
async def reports_data():
    try:
        return {
            "count": len(reports_store),
            "reports": reports_store
        }
    except Exception as e:
        logger.error(f"Error getting reports data: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )

@app.get("/report/{report_id}", response_class=HTMLResponse)
async def get_report(request: Request, report_id: str):
    try:
        return templates.TemplateResponse("report.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering report: {str(e)}", exc_info=True)
        return HTMLResponse("<h1>Report Summary</h1><p>Error loading report. Template system is working.</p>")

@app.get("/report/{report_id}/data")
async def report_data(report_id: str):
    try:
        report = next((r for r in reports_store if r["id"] == report_id), None)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        summary = summaries_store.get(report_id, {})
        return {
            "report": report,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Error getting report data: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/debug/dirs")
async def debug_dirs():
    return {
        "base_dir": str(BASE_DIR),
        "static_exists": STATIC_DIR.exists(),
        "static_files": [str(f) for f in STATIC_DIR.glob("**/*") if f.is_file()],
        "templates_exists": TEMPLATES_DIR.exists(),
        "template_files": [str(f) for f in TEMPLATES_DIR.glob("*")]
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )
