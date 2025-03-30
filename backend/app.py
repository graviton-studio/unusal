from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging

from fetch_data import (
    get_unusual_options_activity,
    get_ticker_options,
    get_bullish_bearish_breakdown,
    run_daily_analysis
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Unusual Options Activity API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Unusual Options Activity API using Polygon.io"}

@app.get("/api-status")
async def get_api_status():
    """Get API status"""
    from fetch_data import cache, last_api_call
    
    # Calculate time since last API call
    seconds_since_call = (datetime.now() - last_api_call).total_seconds()
    
    return {
        "status": "operational",
        "last_updated": cache['last_updated'].strftime("%Y-%m-%d %H:%M:%S") if cache['last_updated'] else None,
        "cached_options_count": len(cache['unusual_options']),
        "cached_tickers_count": len(cache['ticker_data']),
        "last_api_call": last_api_call.strftime("%Y-%m-%d %H:%M:%S"),
        "seconds_since_last_call": round(seconds_since_call, 1)
    }

@app.get("/unusual-options")
async def get_unusual_options(limit: int = 20):
    """Get unusual options activity"""
    try:
        unusual_options = get_unusual_options_activity()
        return unusual_options[:limit]
    except Exception as e:
        logger.error(f"Error getting unusual options: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bullish-bearish")
async def get_bullish_bearish():
    """Get breakdown of bullish vs bearish unusual activity"""
    try:
        return get_bullish_bearish_breakdown()
    except Exception as e:
        logger.error(f"Error getting bullish-bearish breakdown: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ticker/{ticker}")
async def get_ticker_activity(ticker: str):
    """Get unusual options activity for a specific ticker"""
    try:
        return get_ticker_options(ticker.upper())
    except Exception as e:
        logger.error(f"Error getting ticker activity for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run-analysis")
async def trigger_analysis():
    """Manually trigger data refresh"""
    try:
        results = run_daily_analysis()
        return {
            "message": "Analysis completed",
            "results_count": len(results)
        }
    except Exception as e:
        logger.error(f"Error running analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)