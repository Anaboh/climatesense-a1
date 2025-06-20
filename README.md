# ClimateSense AI - IPCC Report Summarizer

This application automatically scrapes IPCC climate reports, processes them, and generates AI-powered summaries using DeepSeek.

## Features
- Automated scraping of IPCC reports
- PDF text extraction
- AI-powered summarization of key findings
- Web API for accessing reports and summaries

## Deployment to Render

1. **Create GitHub Repository**  
   Upload these files to a new GitHub repository

2. **Sign up on Render**  
   Go to [render.com](https://render.com) and sign up with GitHub

3. **Create Web Service**  
   - Click "New +" > "Web Service"
   - Connect your GitHub repository
   - Configure settings:
     - **Name:** climatesense-ai
     - **Region:** Choose closest (e.g., Ohio)
     - **Branch:** main
     - **Runtime:** Docker
     - **Plan Type:** Free
     - **Port:** 10000
   - Add environment variable:
     - `DEEPSEEK_API_KEY` - Your DeepSeek API key

4. **Deploy**  
   Render will automatically build and deploy your application

5. **Trigger Scraping**  
   After deployment, trigger scraping:
   ```bash
   curl -X POST https://your-service.onrender.com/scrape
   ```

6. **Access Reports**
   - List reports: GET /reports
   - Get report details: GET /report/{id}

**Usage**
   - Web Interface: https://your-service.onrender.com
   - API Documentation: Built-in with FastAPI (add /docs to URL)

**Mobile Access**
   - The API is mobile-friendly. Use any HTTP client to access endpoints.

**Note**
   - Free tier limitations:
   - Limited to 5 reports
   - Processes first 20 pages of PDFs
   - May have cold start delays
