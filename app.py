from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
import os
import time
import random

# Initialize app
app = FastAPI()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Serve static files
static_dir = os.path.join(current_dir, "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Setup templates
templates_dir = os.path.join(current_dir, "templates")
templates = Jinja2Templates(directory=templates_dir)

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Reports endpoint
@app.get("/reports", response_class=HTMLResponse)
async def reports(request: Request):
    return templates.TemplateResponse("reports.html", {"request": request})

# Scrape endpoint
@app.post("/scrape")
async def scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(scrape_ip_jiguang)
    return {"status": "Scraping started"}

# IPCC Crawler endpoint
@app.post("/crawl-ipcc")
async def crawl_ipcc(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_ipcc_crawler)
    return {"status": "IPCC crawler started"}

# Chat endpoint
@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        user_message = data.get("message", "").lower()
        
        # Simulate AI processing time
        time.sleep(1)
        
        # Generate response
        ai_response = generate_ai_response(user_message)
        
        return JSONResponse({
            "response": ai_response,
            "timestamp": time.strftime("%I:%M %p")
        })
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return JSONResponse({"error": "Invalid request"}, status_code=400)

# Favicon endpoint
@app.get("/favicon.ico")
async def favicon():
    return FileResponse(os.path.join(static_dir, "favicon.ico"))

# Error handler
@app.exception_handler(404)
async def not_found(request: Request, exc: HTTPException):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

# Background task function
async def scrape_ip_jiguang():
    logger.info("Scraping IP data started...")
    # Simulate work
    time.sleep(5)
    logger.info("Scraping completed!")

# IPCC Crawler function
async def run_ipcc_crawler():
    logger.info("IPCC crawler started...")
    # Simulate crawling work
    time.sleep(8)
    logger.info("IPCC crawler completed!")
    # In a real implementation, this would:
    # 1. Crawl IPCC reports
    # 2. Process and store data
    # 3. Update the knowledge base

# AI response generation with IPCC/DeepSeek logic
def generate_ai_response(user_message):
    # IPCC-related keywords
    ipcc_keywords = [
        "ipcc", "climate change", "global warming", "ar6", 
        "mitigation", "adaptation", "carbon", "ghg", "co2",
        "temperature rise", "climate report", "summary for policymakers"
    ]
    
    # Check if question is IPCC-related
    is_ipcc_question = any(keyword in user_message for keyword in ipcc_keywords)
    
    # 70% chance of IPCC response for IPCC questions
    # 10% chance of IPCC response for other questions (out of scope)
    use_ipcc = (is_ipcc_question and random.random() < 0.7) or \
               (not is_ipcc_question and random.random() < 0.1)
    
    if use_ipcc:
        # IPCC responses
        ipcc_responses = [
            "According to the IPCC AR6 report, human activities have unequivocally caused global warming...",
            "The IPCC states that global surface temperature has increased faster since 1970 than in any other 50-year period...",
            "IPCC findings show that climate change is already affecting every region on Earth...",
            "The IPCC projects that global warming will exceed 1.5°C during the 21st century unless deep reductions in CO2 occur...",
            "Per IPCC AR6, climate-related risks to health, livelihoods, and ecosystems are projected to increase with global warming...",
            "IPCC models indicate that limiting global warming requires reaching at least net zero CO2 emissions..."
        ]
        return random.choice(ipcc_responses)
    else:
        # Default DeepSeek responses
        responses = {
            "hello": "Hello! How can I assist you with climate data today?",
            "hi": "Hi there! What climate information are you looking for?",
            "weather": "I can provide weather forecasts and climate patterns. Please specify a location.",
            "report": "You can find detailed climate reports in the Reports section.",
            "help": "I can help with: weather forecasts, climate reports, IPCC summaries, and environmental data analysis.",
            "": "I'm ClimateSense AI, your assistant for climate data analysis. How can I help you today?"
        }
        
        for keyword in responses:
            if keyword in user_message:
                return responses[keyword]
        
        return "I'm still learning about climate science. Could you rephrase your question?"
