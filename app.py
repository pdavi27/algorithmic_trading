from flask import Flask, render_template, request
import yfinance as yf
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.models import NumeralTickFormatter
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import pandas as pd
from fastdtw import fastdtw
import numpy as np
import faiss
from scipy.spatial.distance import euclidean

app = Flask(__name__)

<<<<<<< HEAD
uri = "mongodb+srv://admin2:Trades123@testingcluster.45vrcox.mongodb.net/?retryWrites=true&w=majority"
=======
uri = "[mongoDB_URL]"
>>>>>>> 86dc6afb7592c4a6e4589e7669ccdce3b211d44d

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
                # add code here to add new data to existing
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

def clean_data(data):
    # Removing NaN or infinite values by mean imputation
    clean_data = np.where(np.isnan(data) | np.isinf(data), np.nan, data)
    nan_indices = np.where(np.isnan(clean_data))
    
    for ind in nan_indices:
        if ind != 0 and ind != len(clean_data)-1:  # Avoid endpoints
            clean_data[ind] = (clean_data[ind-1] + clean_data[ind+1]) / 2
        elif ind == 0:
            clean_data[ind] = clean_data[ind+1]
        else:
            clean_data[ind] = clean_data[ind-1]
    
    return clean_data

def preprocess_ticker_data(ticker_data, ticker_dates):
    # Determine the length of the longest sequence
    max_length = max(len(sublist) for sublist in ticker_data)
    
    # Pad shorter sequences with np.nan
    for sublist in ticker_data:
        while len(sublist) < max_length:
            sublist.append(np.nan)
    
    return ticker_data

def find_similar_tickers(entered_tickers, selected_period):
    all_tickers_data_cursor = collection.find({'period': selected_period})
    all_tickers_data_list = list(all_tickers_data_cursor)

    ticker_names = []
    ticker_data = []

    for data in all_tickers_data_list:
        if data['close_price']:
            ticker_names.append(data['ticker'])
            ticker_data.append(data['close_price'])

    print(f"Ticker names from DB: {ticker_names}")  # Debugging line

    if len(ticker_data) < 2:
        return []

    ticker_data = [clean_data(np.array(data)) for data in ticker_data]
    ticker_data = [data for data in ticker_data if len(data) > 0]

    index = faiss.IndexFlatL2(len(ticker_data[0]))
    index.add(np.array(ticker_data).astype(np.float32))

    similar_tickers = []

    for entered_ticker in entered_tickers:
        if entered_ticker not in ticker_names:
            print(f"Ticker not found: {entered_ticker}")  # Debugging line
            continue

        entered_ticker_index = ticker_names.index(entered_ticker)

        try:
            _, I = index.search(np.array([ticker_data[entered_ticker_index]]).astype(np.float32), 6)
        except IndexError:
            print(f"IndexError encountered for {entered_ticker}")  # Debugging line
            continue

        similar_tickers_for_this = set()
        for i in I[0]:
            if i != entered_ticker_index and i < len(ticker_names):
                similar_tickers_for_this.add(ticker_names[i])

                if len(similar_tickers_for_this) >= 5:
                    break

        similar_tickers.append(list(similar_tickers_for_this))

    return similar_tickers



if __name__ == '__main__':
    app.run(debug=True)
