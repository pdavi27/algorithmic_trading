from flask import Flask, render_template, request
import yfinance as yf
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.models import DatetimeAxis
from bokeh.models import NumeralTickFormatter

app = Flask(__name__)

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
            # Gather data for the ticker
            data = yf.Ticker(ticker)
            df = data.history(period=selected_period)

            # Create a Bokeh plot for the ticker
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
