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
import requests
from bs4 import BeautifulSoup
from transformers import pipeline
from datetime import datetime
from dateutil.parser import parse
import math

app = Flask(__name__)

uri = "[MongoDB_URL]"

client = MongoClient(uri, server_api=ServerApi('1'))

db = client['stock_data']
collection = db['stock_prices_2']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    avgVolume = 0
    minLow = 0
    maxHigh = 0
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

                avgVolume = sum(df['Volume']) / len(df['Volume'])
                maxHigh = max(df['High'])
                minLow = min(df['Low'])

                # Store data in MongoDB
                document = {
                    'ticker': ticker,
                    'period': selected_period,
                    'date': df.index.tolist(),
                    'close_price': df['Close'].tolist(),
                    'volume': df['Volume'].tolist(),
                    'high': df['High'].tolist(),
                    'low': df['Low'].tolist()
                }
                collection.insert_one(document)  
            else:
                print('Fetching only new data')
                # Convert the existing date strings to datetime objects
                existing_dates = [pd.to_datetime(date) for date in existing_data['date']]
                last_date_in_db = max(existing_dates)

                # Define a start date for new data as one day after the last date in the db
                start_date_for_new_data = last_date_in_db + pd.Timedelta(days=1)

                # Make sure start_date_for_new_data is less than today's date to avoid the error
                today_date = datetime.now().date()
                if start_date_for_new_data.date() < today_date:
                    # Fetch new data starting from the day after the last date in the db
                    new_df = yf.download(ticker, start=start_date_for_new_data)
                    new_df.index = pd.to_datetime(new_df.index)

                    avgVolume = sum(new_df['Volume']) / len(new_df['Volume'])
                    maxHigh = max(new_df['High'])
                    minLow = min(new_df['Low'])

                    # If new data is fetched, process and merge
                    if not new_df.empty:
                        new_df.reset_index(inplace=True)
                        new_df['Date'] = new_df['Date'].dt.tz_localize(None)  # Remove timezone info

                        # Create the existing dataframe
                        existing_df = pd.DataFrame({
                            'Date': existing_dates,
                            'Close': existing_data['close_price']
                        })

                        merged_df = pd.merge(existing_df, new_df, how='outer', on='Date', suffixes=('_existing', '_new'))
                        merged_df['Close'] = merged_df['Close_new'].combine_first(merged_df['Close_existing'])
                        df = merged_df[['Date', 'Close', 'Volume', 'High', 'Low']].dropna()
                        df.set_index('Date', inplace=True)
                        df = df.sort_index()

                        # Update MongoDB with the new merged data
                        collection.update_one(
                            {'ticker': ticker, 'period': selected_period},
                            {'$set': {
                                'date': df.index.tolist(),
                                'close_price': df['Close'].tolist(),
                                'volume': df['Volume'].tolist(),
                                'low': df['Low'].tolist(),
                                'high': df['High'].tolist()
                            }}
                        )
                    else:
                        # If no new data was fetched, use the existing data as a dataframe
                        df = pd.DataFrame({
                            'Date': existing_dates,
                            'Close': existing_data['close_price']
                        }).set_index('Date')
                        df = df.sort_index()
                else:
                    print("No new data to fetch. The last date in DB is already the current date or later.")
                    # Use existing data if no new data needs to be fetched
                    df = pd.DataFrame({
                        'Date': existing_dates,
                        'Close': existing_data['close_price'],
                        'Volume': existing_data['volume'],
                        'High': existing_data['high'],
                        'Low': existing_data['low']
                    }).set_index('Date')
                    df = df.sort_index()

                    avgVolume = sum(df['Volume']) / len(df['Volume'])
                    maxHigh = max(df['High'])
                    minLow = min(df['Low'])

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

        # Fetch and display news articles
        news_articles, sentiment_rating = get_news_articles(ticker)
        
        # Render a template with the results, Bokeh plots, and similar tickers
        return render_template('results.html', 
                               bokeh_plots=bokeh_plots, 
                               similar_tickers=similar_tickers, 
                               news_articles=news_articles, 
                               sentiment_rating=sentiment_rating,
                               avgVolume=avgVolume, minLow=minLow, maxHigh=maxHigh)

    # Handle cases where the request method is not POST (e.g., GET request)
    return render_template('index.html')

# Function to get news articles related to the stock tickers
def get_news_articles(ticker):
    url = f"https://finviz.com/quote.ashx?t={ticker}&p=d"
    # Send an HTTP GET request to the URL
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to retrieve the webpage. Status code: {response.status_code}")
        return
    
    soup = BeautifulSoup(response.text, 'html.parser')
    news_rows = soup.find_all('tr', class_='cursor-pointer has-label')

    news_data = []
    
    def get_standardized_datetime(date_time_str, last_known_date):
        try:
            has_time = 'AM' in date_time_str or 'PM' in date_time_str
            time_part = date_time_str[-7:] if has_time else "00:00"

            if date_time_str.startswith('Today'):
                date_part = datetime.now().strftime("%Y-%m-%d")
                last_known_date = date_part
            elif '-' in date_time_str:
                # If the string contains a full date and time
                date_part_raw = date_time_str[:-7]  # Exclude the time part
                date_object = parse(date_part_raw, fuzzy=True).date()
                date_part = date_object.strftime("%Y-%m-%d")
                last_known_date = date_part
            else:
                # If only time is provided
                date_part = last_known_date

            return f"{date_part} {time_part}", last_known_date
        except ValueError:
            # Handle cases where parsing fails
            return None, last_known_date

    last_known_date = None
    for row in news_rows:
        columns = row.find_all('td')
        date_time_str = columns[0].get_text(strip=True)
        standardized_datetime, last_known_date = get_standardized_datetime(date_time_str, last_known_date)

        if standardized_datetime:
            headline_container = columns[1].find('a', class_='tab-link-news')
            headline = headline_container.get_text(strip=True)
            link = headline_container['href']

            news_data.append({
                'date_time': standardized_datetime,
                'headline': headline,
                'link': link
            })

    classification = pipeline('sentiment-analysis', model='ProsusAI/FinBERT')
    batch_size = 10  # Adjust based on token limit
    batches = [news_data[i:i + batch_size] for i in range(0, len(news_data), batch_size)]
    ratings = []

    for batch in batches:
        headlines = '. '.join([item['headline'] for item in batch])
        rating = classification(headlines)
        ratings.extend(rating)

    # Convert labels to numerical values: negative -> -1, neutral -> 0, positive -> 1
    label_to_num = {'negative': -1, 'neutral': 0, 'positive': 1}

    # Calculate weighted score
    weighted_scores = [label_to_num[item['label']] * item['score'] for item in ratings]

    # Calculate average
    average_rating = sum(weighted_scores) / len(weighted_scores)
    average_rating_percentage = (average_rating + 1) / 2 * 100

    if average_rating > 0:
        formatted_result = f"{average_rating_percentage:.2f}% Positive"
    elif average_rating < 0:
        formatted_result = f"{average_rating_percentage:.2f}% Negative"
    else:
        formatted_result = "Neutral"

    return news_data, formatted_result
        

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
                try:
                    distance, _ = fastdtw(np.array(ticker_data[entered_ticker_index]), np.array(data))
                    distances.append((ticker_names[i], distance))
                except IndexError as e:
                    print(f"An error occurred with ticker {ticker_names[i]}: {e}")
                    # Continuing to the next ticker
                    continue

        # Sort by DTW distance and get the top 5 most similar tickers
        distances.sort(key=lambda x: x[1])
        similar_tickers.append([ticker[0] for ticker in distances[:5]])

    return similar_tickers



if __name__ == '__main__':
    app.run(debug=True)
