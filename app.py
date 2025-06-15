from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
import os

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

# Chat endpoint
@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        # Process chat request here
        return JSONResponse({"response": "This is a sample chat response"})
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
    # Add your actual scraping logic here
    logger.info("Scraping IP data started...")
    # Simulate work
    import time
    time.sleep(5)
    logger.info("Scraping completed!")
