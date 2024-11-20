:: Runs the data pipeline to get latest price history and updata trend analysis data

set "current_path=%cd%"

cd ..\historical-price-updater
call venv\Scripts\activate
python .\scripts\update_historical_price.py

cd ..\price-trend-analysis
call venv\Scripts\activate
python .\scripts\analyze_price.py

cd "%current_path%"
call venv\Scripts\activate