# -*- coding: utf-8 -*-
"""
Created on Tue Feb  9 10:14:05 2021

@author: spiro
"""

"""Resistance/Support Breakout Strategy"""



import numpy as np
import pandas as pd
import yfinance as yf
import datetime as dt
import matplotlib.pyplot as plt
import copy

def ATR(DF, n):
    df=DF.copy()
    df['H-L']=abs(df['High']-df['Low'])
    df['H-PC']=abs(df['High']-df['Adj Close'].shift(1))
    df['L-PC']=abs(df['Low']-df['Adj Close'].shift(1))
    df['TR']=df[['H-L','H-PC','L-PC']].max(axis=1,skipna= False)
    #You can add SMA here, but i prefer EMA
    df['ATR']=df['TR'].ewm(span=n,adjust=False,min_periods=n).mean()
    df2= df.drop(['H-L','H-PC','L-PC'],axis=1)
    return df2['ATR']

def CAGR(DF):
    "function to calculate the Cumulative Annual Growth Rate of a trading strategy"
    df = DF.copy()
    df["cum_return"] = (1 + df["ret"]).cumprod()
    n = len(df)/(252*78)
    CAGR = (df["cum_return"].tolist()[-1])**(1/n) - 1
    return CAGR

def vol(DF):
    df=DF.copy()
    vol=df['ret'].std() * np.sqrt((252*78))
    return vol

def sharpe(DF,rf): #rf= risk free rate
     df=DF.copy()
     sr= (CAGR(df)- rf)/vol(df)
     return sr
 
def max_dd(DF):
    df=DF.copy()
    df['cum returns']=(df['ret']+1).cumprod()
    df['cum_roll_max']= df['cum returns'].cummax()
    df['drawdown']= df['cum_roll_max']-df['cum returns']
    df['drawdown_pct']=df['drawdown']/df['cum_roll_max']
    max_dd=df['drawdown_pct'].max()
    return max_dd 


tickers=["PLTR","AAPL"]
start= dt.datetime.today()- dt.timedelta(59)
stop=dt.datetime.today()
ohlcv_intraday={}

for t in tickers:
    ohlcv_intraday[t]=yf.download(t,start,stop,interval="5m")
    ohlcv_intraday[t].dropna(inplace=True,how='all')
    
tickers = ohlcv_intraday.keys()    
    

####################### BackTesting ###############################

ohlc_dict=copy.deepcopy(ohlcv_intraday)
tickers_signal={}
tickers_ret={}
for t in tickers:
    print('calculating ATR for',t)
    ohlc_dict[t]['ATR']= ATR(ohlc_dict[t],20)
    ohlc_dict[t]['roll_max_cp']= ohlc_dict[t]['High'].rolling(20).max()
    ohlc_dict[t]['roll_min_cp']= ohlc_dict[t]['Low'].rolling(20).min()
    ohlc_dict[t]['roll_max_vol']=ohlc_dict[t]['Volume'].rolling(20).max()
    ohlc_dict[t].dropna(inplace=True)
    tickers_signal[t]=""
    ohlc_dict[t]["Signal"]=""
    tickers_ret[t]=[0]

for ticker in tickers:
    print("calculating returns for ",ticker)
    for i in range(1,len(ohlc_dict[ticker])):
        if tickers_signal[ticker] == "":
            tickers_ret[ticker].append(0)
            if ohlc_dict[ticker]["High"][i]>=ohlc_dict[ticker]["roll_max_cp"][i] and \
               ohlc_dict[ticker]["Volume"][i]>1.5*ohlc_dict[ticker]["roll_max_vol"][i-1]:
                tickers_signal[ticker] = "Buy"
                ohlc_dict[ticker]["Signal"][i]=tickers_signal[ticker]
            elif ohlc_dict[ticker]["Low"][i]<=ohlc_dict[ticker]["roll_min_cp"][i] and \
               ohlc_dict[ticker]["Volume"][i]>1.5*ohlc_dict[ticker]["roll_max_vol"][i-1]:
                tickers_signal[ticker]= "Sell"
                ohlc_dict[ticker]["Signal"][i]=tickers_signal[ticker]
        
        elif tickers_signal[ticker] == "Buy":
            if ohlc_dict[ticker]["Low"][i]<ohlc_dict[ticker]["Close"][i-1] - ohlc_dict[ticker]["ATR"][i-1]:
                tickers_signal[ticker] = ""
                ohlc_dict[ticker]["Signal"][i]="Stop Loss Triggered"
                tickers_ret[ticker].append(((ohlc_dict[ticker]["Close"][i-1] - ohlc_dict[ticker]["ATR"][i-1])/ohlc_dict[ticker]["Close"][i-1])-1)
            elif ohlc_dict[ticker]["Low"][i]<=ohlc_dict[ticker]["roll_min_cp"][i] and \
               ohlc_dict[ticker]["Volume"][i]>1.5*ohlc_dict[ticker]["roll_max_vol"][i-1]:
                tickers_signal[ticker] = "Sell"
                ohlc_dict[ticker]["Signal"][i]=tickers_signal[ticker]
                tickers_ret[ticker].append((ohlc_dict[ticker]["Close"][i]/ohlc_dict[ticker]["Close"][i-1])-1)
            else:
                tickers_ret[ticker].append((ohlc_dict[ticker]["Close"][i]/ohlc_dict[ticker]["Close"][i-1])-1)
                
        elif tickers_signal[ticker] == "Sell":
            if ohlc_dict[ticker]["High"][i]>ohlc_dict[ticker]["Close"][i-1] + ohlc_dict[ticker]["ATR"][i-1]:
                tickers_signal[ticker] = ""
                ohlc_dict[ticker]["Signal"][i]="Stop Loss Triggered"
                tickers_ret[ticker].append((ohlc_dict[ticker]["Close"][i-1]/(ohlc_dict[ticker]["Close"][i-1] + ohlc_dict[ticker]["ATR"][i-1]))-1)
            elif ohlc_dict[ticker]["High"][i]>=ohlc_dict[ticker]["roll_max_cp"][i] and \
               ohlc_dict[ticker]["Volume"][i]>1.5*ohlc_dict[ticker]["roll_max_vol"][i-1]:
                tickers_signal[ticker] = "Buy"
                ohlc_dict[ticker]["Signal"][i]=tickers_signal[ticker]
                tickers_ret[ticker].append((ohlc_dict[ticker]["Close"][i-1]/ohlc_dict[ticker]["Close"][i])-1)
            else:
                tickers_ret[ticker].append((ohlc_dict[ticker]["Close"][i-1]/ohlc_dict[ticker]["Close"][i])-1)
                
    ohlc_dict[ticker]["ret"] = np.array(tickers_ret[ticker])

      """KPI Comparison"""
      
strategy_df=pd.DataFrame()
for t in tickers:
    strategy_df[t]= ohlc_dict[t]["ret"]
strategy_df["ret"]=strategy_df.mean(axis=1)
CAGR(strategy_df)
sharpe(strategy_df,0.025)
max_dd(strategy_df)

#strategy return visualization 
(1+strategy_df['ret']).cumprod().plot()

cagr={}
sharpe_ratios={}
max_drawdown={}
for t in tickers:
    print('Calculating return for',t)
    cagr[t]=CAGR(ohlc_dict[t])
    sharpe_ratios[t]= sharpe(ohlc_dict[t],0.025)
    max_drawdown[t]= max_dd(ohlc_dict[t])

KPI_df=pd.DataFrame([cagr,sharpe_ratios,max_drawdown],index=['Return','Sharpe Ratio','Max Drawdown'])
KPI_df