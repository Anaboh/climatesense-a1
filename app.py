import os
import re
import asyncio
import aiohttp
import logging
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from bs4 import BeautifulSoup
import pdfplumber
from io import BytesIO
import json
from datetime import datetime
import hashlib
from typing import List, Dict
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ClimateSense AI", version="2.0.0")

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (index.html)
app.mount("/", StaticFiles(directory="/app", html=True), name="static")

# In-memory storage
reports_store = []
conversations = {}
user_sessions = {}

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
            report_data["summary"] = summary
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
        background_tasks.add_task(scrape_ip极光
        return {
            "status": "success",
            "message": "Scraping started in background. Reports will be available soon."
        }
    except Exception as e:
        logger.error(f"Error starting scrape: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Internal server error"}
        )

@app.get("/reports")
async def list_reports():
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

@app.get("/report/{report_id}")
async def report_data(report_id: str):
    try:
        report = next((r for r in reports_store if r["id"] == report_id), None)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        return report
    except Exception as e:
        logger.error(f"Error getting report data: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )

@app.post("/chat")
async def chat_with_agent(request: dict):
    try:
        session_id = request.get("session_id", str(uuid.uuid4()))
        message = request["message"]
        
        # Initialize session if new
        if session_id not in conversations:
            conversations[session_id] = []
            user_sessions[session_id] = {
                "created_at": datetime.now().isoformat(),
                "report_context": None
            }
        
        # Add user message to conversation
        conversations[session_id].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Prepare system prompt based on context
        system_prompt = (
            "You are ClimateSense AI, an expert in IPCC climate reports. "
            "Your purpose is to help users understand complex climate science. "
        )
        
        if user_sessions[session_id]["report_context"]:
            system_prompt += (
                f"\nYou're currently discussing the report: '{user_sessions[session_id]['report_context']['title']}'"
            )
        
        # Build messages array
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversations[session_id][-5:])  # Last 5 messages
        
        # Get response from DeepSeek
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(DEEPSEEK_API_URL, headers=headers, json=payload) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"DeepSeek API error: {response.status} - {error}")
                    return {
                        "error": f"API error: {response.status}"
                    }
                
                result = await response.json()
                ai_message = result['choices'][0]['message']['content']
        
        # Add AI response to conversation
        conversations[session_id].append({
            "role": "assistant",
            "content": ai_message,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "session_id": session_id,
            "response": ai_message,
            "conversation": conversations[session_id]
        }
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )

@app.post("/set-context")
async def set_report_context(request: dict):
    try:
        session_id = request["session_id"]
        report_id = request["report_id"]
        
        if session_id not in conversations:
            return {"error": "Invalid session ID"}
        
        report = next((r for r in reports_store if r["id"] == report_id), None)
        if not report:
            return {"error": "Report not found"}
        
        user_sessions[session_id]["report_context"] = report
        
        # Add context to conversation
        conversations[session_id].append({
            "role": "system",
            "content": f"User has selected the report: {report['title']}",
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "status": "success",
            "report": report["title"],
            "summary_available": report["summary_available"]
        }
        
    except Exception as e:
        logger.error(f"Context error: {极光}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )
