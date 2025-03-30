# Using a scheduler like APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

def schedule_jobs():
    scheduler = BackgroundScheduler(timezone=pytz.utc)
    
    # Schedule market data collection (during market hours)
    scheduler.add_job(collect_market_data, 'cron', 
                     day_of_week='mon-fri', hour='13-20', minute='*/15')
    
    # Schedule end-of-day analysis
    scheduler.add_job(run_daily_analysis, 'cron', 
                     day_of_week='mon-fri', hour=21, minute=0)
    
    # Update stock universe weekly
    scheduler.add_job(update_stock_universe, 'cron', 
                     day_of_week='sun', hour=12, minute=0)
    
    scheduler.start()