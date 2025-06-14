import os
import re
import asyncio
import aiohttp
from fastapi import FastAPI, BackgroundTasks, HTTPException
from bs4 import BeautifulSoup
from openai import AsyncOpenAI  # Use OpenAI client for DeepSeek
import pdfplumber
from io import BytesIO
import json
from datetime import datetime
import hashlib
from typing import List, Dict

app = FastAPI(title="ClimateSense AI", version="1.0.0")

# Initialize DeepSeek client using OpenAI SDK
client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"  # DeepSeek API endpoint
)

# In-memory storage for demo
reports_store = []
summaries_store = {}

def get_report_hash(title: str) -> str:
    return hashlib.md5(title.encode()).hexdigest()

async def fetch_url(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

async def fetch_pdf(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.read()

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
        print(f"PDF extraction error: {str(e)}")
    return text

def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\bPage \d+\b', '', text)
    return text.strip()

async def summarize_text(text: str, report_title: str) -> Dict:
    try:
        # Use OpenAI-compatible API call
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
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
            response_format={"type": "json_object"},
            max_tokens=1000
        )
        
        # Extract JSON content
        summary_str = response.choices[0].message.content
        return json.loads(summary_str)
    except Exception as e:
        print(f"Summarization error: {str(e)}")
        return {
            "key_findings": ["Summary not available"],
            "risks": ["Summary not available"],
            "mitigation_options": ["Summary not available"],
            "confidence_level": "Unknown"
        }

async def process_ipcc_report(report_url: str):
    try:
        print(f"Processing report: {report_url}")
        report_html = await fetch_url(report_url)
        soup = BeautifulSoup(report_html, 'html.parser')
        
        # Extract report details
        title = soup.select_one('h1.page-header__title')
        if not title:
            print(f"No title found for {report_url}")
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
            print(f"Downloading PDF: {pdf_links[0]}")
            pdf_bytes = await fetch_pdf(pdf_links[0])
            pdf_text = extract_text_from_pdf(pdf_bytes)
            clean_pdf_text = clean_text(pdf_text)
            
            print(f"Generating summary for: {title}")
            summary = await summarize_text(clean_pdf_text, title)
            summaries_store[report_data["id"]] = summary
            report_data["summary_available"] = True
            
        return report_data
    except Exception as e:
        print(f"Error processing report: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

async def scrape_ipcc_reports(limit: int = 3):
    base_url = "https://www.ipcc.ch"
    reports_url = f"{base_url}/reports/"
    
    try:
        html_content = await fetch_url(reports_url)
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
        print(f"Scraping error: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

@app.post("/scrape")
async def start_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(scrape_ipcc_reports)
    return {
        "status": "success",
        "message": "Scraping started in background. Check /reports endpoint in a few minutes."
    }

@app.get("/reports")
async def list_reports():
    return {
        "count": len(reports_store),
        "reports": reports_store
    }

@app.get("/report/{report_id}")
async def get_report(report_id: str):
    report = next((r for r in reports_store if r["id"] == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    summary = summaries_store.get(report_id, {})
    return {
        "report": report,
        "summary": summary
    }

@app.get("/")
async def home():
    return {
        "name": "ClimateSense AI",
        "description": "IPCC Report Summarizer",
        "endpoints": {
            "scrape_reports": "POST /scrape",
            "list_reports": "GET /reports",
            "get_report": "GET /report/{id}"
        },
        "note": "Free tier limitations: Processes first 3 reports, 10 pages per PDF"
    }

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
