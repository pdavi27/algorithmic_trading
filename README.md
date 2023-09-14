# Stock Analysis Web Application


This web application allows you to visualize stock price data using Flask and Bokeh. You can also analyze multiple stock tickers and time periods simultaneously.

## Prerequisites

Before running this application, make sure you have the following prerequisites installed on your system:

- Python 3.x
- Flask
- yfinance
- Bokeh

You can install the required Python packages using `pip`:

```bash
pip install Flask yfinance bokeh
```

## Getting Started

Follow these steps to run the application:

1. Clone the repository to your local machine:

```bash
git clone https://github.com/pdavi27/algorithmic_trading.git
cd algorithmic_trading
```

1. Run the Flask application:

```bash
python app.py
```

3. Open your web browser and go to `http://localhost:5000` to access the application.

## Usage

### Home Page

- The home page displays the stock price visualization for a default stock ticker (AAPL).
- You can view stock price data for the past year.

### Analyze Page

- Click the "Analyze" link in the navigation bar to access the analyze page.
- Enter one or more stock tickers separated by commas (e.g., AAPL, MSFT).
- Choose a time period from the dropdown menu.
- Click the "Analyze" button to view visualizations for the selected stocks.

## Troubleshooting

- If you encounter any issues or errors, please check your internet connection and verify that the required packages are installed.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
