from flask import Flask, render_template, request
import yfinance as yf
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.models import DatetimeAxis
from bokeh.models import NumeralTickFormatter
from pymongo import MongoClient
import pandas as pd

app = Flask(__name__)

client = MongoClient('mongodb+srv://admin:Trader!1@cluster0.i8va7ol.mongodb.net/?retryWrites=true&w=majority')
db = client['stock_data']
collection = db['stock_prices']

@app.route('/')
def index():
    # Gather data from Yahoo Finance API
    ticker = 'AAPL'  # Apple Inc.
    data = yf.Ticker(ticker)
    df = data.history(period="1y")

    # Create a Bokeh plot for the ticker
    p = figure(title=f'{ticker} Stock Price', x_axis_label='Date', y_axis_label='Price', x_axis_type='datetime')
    p.line(df.index, df['Close'], legend_label='Close', line_width=2)
    # Format y-axis labels as currency
    p.yaxis.formatter = NumeralTickFormatter(format='$0,0.00')

    script, div = components(p)

    return render_template('index.html', script=script, div=div)

@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    if request.method == 'POST':
        # Get the selected stock tickers from the form input
        selected_tickers = request.form.get('stock_tickers')
        selected_period = request.form.get('stock_period')
        tickers = [ticker.strip() for ticker in selected_tickers.split(',')]

        # Create a list to store Bokeh plot components
        bokeh_plots = []

        # Loop through each selected ticker
        for ticker in tickers:
            # Check if data for the ticker already exists in the database
            existing_data = collection.find_one({'ticker': ticker, 'period': selected_period})
        
            if not existing_data:
                # If data doesn't exist, retrieve it and store it in the database
                print('Reading/Writing new data')
                data = yf.Ticker(ticker)
                df = data.history(period=selected_period)
        
                # Store data in MongoDB
                document = {
                    'ticker': ticker,
                    'period': selected_period,
                    'date': df.index.tolist(),
                    'close_price': df['Close'].tolist()
                }
                collection.insert_one(document)
            else:
                # If data already exists, you can choose to skip or update it as needed
                print('Reading data that already exists')
                df = pd.DataFrame({'Close': existing_data['close_price']}, index=existing_data['date'])
                pass
            
            # Create a Bokeh plot for the ticker as before
            p = figure(title=f'{ticker} Stock Price', x_axis_label='Date', y_axis_label='Price', x_axis_type='datetime')
            p.line(df.index, df['Close'], legend_label='Close', line_width=2)
            # Format y-axis labels as currency (e.g., $1,000.00)
            p.yaxis.formatter = NumeralTickFormatter(format='$0,0.00')
        
            # Generate Bokeh plot components
            script, div = components(p)
            bokeh_plots.append((script, div))
        

        # Render a template with the results and Bokeh plots
        return render_template('results.html', bokeh_plots=bokeh_plots)

    # Handle cases where the request method is not POST (e.g., GET request)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
