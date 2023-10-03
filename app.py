from flask import Flask, render_template, request
import yfinance as yf
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.models import NumeralTickFormatter
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import pandas as pd
from fastdtw import fastdtw
import numpy as np

app = Flask(__name__)

uri = "[mongoDB_URL]"

client = MongoClient(uri, server_api=ServerApi('1'))
db = client['stock_data']
collection = db['stock_prices']

@app.route('/')
def index():
    return render_template('index.html')

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
            
            # Create a Bokeh plot for the ticker as before
            p = figure(title=f'{ticker} Stock Price', x_axis_label='Date', y_axis_label='Price', x_axis_type='datetime')
            p.line(df.index, df['Close'], legend_label='Close', line_width=2)
            # Format y-axis labels as currency (e.g., $1,000.00)
            p.yaxis.formatter = NumeralTickFormatter(format='$0,0.00')
        
            # Generate Bokeh plot components
            script, div = components(p)
            bokeh_plots.append((script, div))
        
        # Calculate similarity between tickers and retrieve the 5 most similar ones
        similar_tickers = find_similar_tickers(tickers, selected_period)
        
        # Render a template with the results, Bokeh plots, and similar tickers
        return render_template('results.html', bokeh_plots=bokeh_plots, similar_tickers=similar_tickers)

    # Handle cases where the request method is not POST (e.g., GET request)
    return render_template('index.html')

def find_similar_tickers(entered_tickers, selected_period):
    # Retrieve data from MongoDB for all tickers in the database for the selected period
    all_tickers_data = collection.find({'period': selected_period})

    # Extract ticker names and close price data from the database
    ticker_names = []
    ticker_data = []
    for data in all_tickers_data:
        ticker_names.append(data['ticker'])
        ticker_data.append(data['close_price'])

    if len(ticker_data) < 2:
        return []  # Not enough data in the database to calculate similarity

    # Initialize a list to store similar tickers for each entered ticker
    similar_tickers = []

    for entered_ticker in entered_tickers:
        # Find the index of the entered ticker in the list of ticker names
        entered_ticker_index = ticker_names.index(entered_ticker)

        # Calculate DTW distance between the entered ticker and all other tickers
        distances = []
        for i, data in enumerate(ticker_data):
            if i != entered_ticker_index:
                # Use fastdtw to calculate DTW distance
                distance, _ = fastdtw(np.array(ticker_data[entered_ticker_index]), np.array(data))
                distances.append((ticker_names[i], distance))

        # Sort by DTW distance and get the top 5 most similar tickers
        distances.sort(key=lambda x: x[1])
        similar_tickers.append([ticker[0] for ticker in distances[:5]])

    return similar_tickers

if __name__ == '__main__':
    app.run(debug=True)
