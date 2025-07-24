import base64
import tempfile
import os


import streamlit as streamlit  #user interface library
import pandas as pd
from datetime import timedelta
import  yfinance as yf
import plotly.graph_objects as go
import openai


from dash import Dash, dcc, html



def main():
    #set streamline
    #https://docs.streamlit.io/develop/api-reference
    #to run streamlit run /Users/hcarrillo/PycharmProjects/InvestmentAIProject/main.py
    streamlit.set_page_config(layout="wide")
    streamlit.title("Investment AI - Technical Analysis Assistant")
    streamlit.sidebar.header("Analyzing fields")


    #Get user input
    ticker_symbol = streamlit.sidebar.text_input("Enter Stock Ticker Symbol (e.g AAPL): ", "AAPL")
    today_date_year_back = tomorrow_datetime = pd.Timestamp.today() + timedelta(days=-360)
    start_date = streamlit.sidebar.date_input("Start Date", value=today_date_year_back)
    tomorrow_datetime = pd.Timestamp.today() + timedelta(days=1)
    end_date = streamlit.sidebar.date_input("Start Date", value=pd.Timestamp(tomorrow_datetime))




    #fetch data uses yfinance library to retrieve financial data
    # https://ranaroussi.github.io/yfinance/

    if streamlit.sidebar.button("Retrieve Data"): #Fetch Data button is clicked
        streamlit.session_state["stock_data"] = yf.download(ticker_symbol,start=start_date, end=end_date,auto_adjust=True) #sets it to a dictionary
        print(streamlit.session_state["stock_data"])
        print(streamlit.session_state["stock_data"].columns)

        streamlit.session_state["stock_data"].columns = streamlit.session_state["stock_data"].columns.droplevel('Ticker')
        print(streamlit.session_state["stock_data"].columns)
        print(streamlit.session_state["stock_data"])
        streamlit.success("Stock Data retrival successful!")

    #populate data exists in the session
    if "stock_data" in streamlit.session_state:
        data = streamlit.session_state["stock_data"]

        #https: // plotly.com / python / candlestick - charts /
        #candlestick graph
        fig = go.Figure(data=[
            go.Candlestick(
                x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                name="Candlestick"
            )
        ])



        #technical indicators
        streamlit.sidebar.subheader("Technical Indicators")
        indicators = streamlit.sidebar.multiselect("Select Indicators: ",
                                                   ["20-Day SMA", "20-Day EMA", "20-Day Bollinger Bands", "VWAP"],
                                                   default = ["20-Day SMA"])


        streamlit.sidebar.subheader("Technical Indicator Selector")


        for indicator in indicators:
            add_technical_indicators_to_graph(indicator,fig,data)

        # uses Dash to add slider
        app = Dash()
        app.layout = html.Div([
            dcc.Checklist(
                id='toggle-rangeslider',
                options=[{'label': 'Include Rangeslider',
                          'value': 'slider'}],
                value=['slider']
            ),
            dcc.Graph(id="graph"),
        ])

        #plot on graph
        streamlit.plotly_chart(fig)

        ai_analysis(fig)

def add_technical_indicators_to_graph(indicator,fig,data):
    if (indicator == "20-Day SMA"):
        sma = data['Close'].rolling(20).mean()
        fig.add_trace(go.Scatter(x=data.index, y=sma,mode='lines', name='SMA (20-Day)'))
    elif (indicator == "20-Day EMA"):
        ema = data['Close'].ewm(span=20).mean() #exponentially weighted moving
        fig.add_trace(go.Scatter(x=data.index, y=ema,mode='lines', name='EMA (20-Day)'))
    elif (indicator =="20-Day Bollinger Bands"):
        sma = data['Close'].rolling(window=20).mean()
        std = data['Close'].rolling(window=20).std()
        bollinger_band_upper = sma + 2 * std
        bollinger_band_lower = sma - 2 * std
        fig.add_trace(go.Scatter(x=data.index, y=bollinger_band_upper,mode='lines', name='Bollinger Band Upper'))
        fig.add_trace(go.Scatter(x=data.index, y=bollinger_band_lower,mode='lines', name='Bollinger Band Upper'))
    elif (indicator == "VWAP"):
        data['VWAP'] = (data['Close'] * data['Volume']).cumsum() / data['Volume'].cumsum()
        fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'],mode='lines', name='VWAP'))


def ai_analysis(fig):
    token = streamlit.secrets["auth"]["openai-key"]
    #streamlit.write(f"My API Token: {token}")
    streamlit.subheader("AI Technical Stock Analysis")

    #when pressing the button run the AI model using the chart as a png
    if streamlit.button("Run AI Alpha Report"):
        with streamlit.spinner("Running Technical Analysis on the Chart, please wait..."):
            with tempfile.NamedTemporaryFile(suffix=".png",delete=False) as tmpfile:
                fig.write_image(tmpfile.name)
                tmpfile_path = tmpfile.name

            #Read Image and encode to Base64
            with open(tmpfile_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")

        openai.api_key = token

        # chat completion
        # https://platform.openai.com/docs/guides/text?api-mode=responses

        # role is the user
        # content is the prompt you are sending to chatgpt
        # other models gpt-4o or gpt-3.5-turbo

        ai_query = ("You are a stock trader specialist in Technical Analysis at a financial institution. "
                    + "Analyse the stock chart's technical indicators and provide a buy/hold/sell recommendation "
                    + " Base you recommendation only on the candlestick chart and the displayed technical indicators"
                    +  "First provided the recommendation, then, provide your detail reasoning. Can you list the technical indicators you see in the image")



        chat_completion = openai.chat.completions.create(
            model="gpt-4o",
            messages = [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text",
                                 "text": ai_query
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_data}"
                                    }
                                }
                            ]
                        }
                    ])

        response = chat_completion.choices[0].message.content
        streamlit.write("AI Analysis Results")
        streamlit.write(response)

        os.remove(tmpfile_path)


if __name__ == "__main__":
    main()