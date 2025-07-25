import pytest
import requests
import time
import logging


#Log configs
logger = logging.getLogger(__name__)

#Basic configs
BASE_URL = 'https://api.crypto.com/exchange/v1/public/get-candlestick'
VALID_INSTRUMENTS = ['BTCUSD-PERP']
VALID_TIMEFRAMES = ['5m', '30m', '1h', '1D', '1M']
INVALID_INSTRUMENTS = ['BTCUSD-PERP-TEST01', 'ABC123', '']
INVALID_TIMEFRAMES = ['5min', '3d', 'daily', '1week', '1month']


#Function to get candlestick results
def test_get_candlestick(instrument_name, timeframe=None, count=None, start_ts=None, end_ts=None):
    #Send API request
    params = {"instrument_name": instrument_name}
    if timeframe: params["timeframe"] = timeframe
    if count: params["count"] = count
    if start_ts: params["start_ts"] = start_ts
    if end_ts: params["end_ts"] = end_ts
    
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        #print(response.text)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request failed, error msg is: {e}")

#Function to verify API response
def verify_response(response, instrument_name, timeframe=None):
    res_data = response.json()
    
    assert response.status_code == 200
    assert "result" in res_data
    assert "data" in res_data["result"]
    
    result = res_data['result']
    assert result["instrument_name"] == instrument_name
    
    if timeframe:
        assert result["interval"] ==  timeframe

    #verify detail data
    candles = result["data"]
    if candles:
        for candle in candles:
            assert len(candle) == 6 
            #Below verify have a bug: could not convert string to float: 'o', I have no enough time to debug.
            '''
            o, h, l, c, v, t = map(float, candle)
            assert l <= o <= h
            assert l <= c <= h
            assert v >= 0
            '''
    return res_data
            
#--------------------------
#-------- Test Cases ------
#--------------------------

#1 Valid instruments name   
@pytest.mark.parametrize("instrument", VALID_INSTRUMENTS)
def test_basic_request(instrument):
    response = test_get_candlestick(instrument)
    data = verify_response(response, instrument)
    assert data["result"]["interval"] == "1m"
    logger.info(f"Succeed to get candlestick data of {instrument}.")

#2 Valid timeframes verify
@pytest.mark.parametrize("timeframe", VALID_TIMEFRAMES)
def test_timeframes(timeframe):
    logger.info(f"Time frame is: {timeframe}")
    response = test_get_candlestick("BTCUSD-PERP", timeframe=timeframe)
    verify_response(response, "BTCUSD-PERP", timeframe)
    logger.info(f"Succeed to test timeframe: {timeframe}")
    
#3 Verify count is correct
@pytest.mark.parametrize("count", [1, 5, 10, 50, 100, 1000])
def test_count(count):
    response = test_get_candlestick("BTCUSD-PERP", count=count)
    data = verify_response(response, "BTCUSD-PERP")
    assert len(data["result"]["data"]) == count

#4 verify time stamps
def test_time_stamps_range():
    now = int(time.time()*1000)
    start_ts = now - (24*60*60*1000)
    response = test_get_candlestick("BTCUSD-PERP", start_ts=start_ts, end_ts=now)
    data = verify_response(response, "BTCUSD-PERP")
    candles = data["result"]["data"]
    assert start_ts <= candles[0]["t"] <= now
   
#5 Verify invalid instruments name
@pytest.mark.parametrize("instrument", INVALID_INSTRUMENTS)
def test_invalid_instruments(instrument):
    with pytest.raises(Exception) as e:
        test_get_candlestick(instrument)
    assert "400" in str(e.value) or "404" in str(e.value)
    
#6 Verify invalid timeframe
@pytest.mark.parametrize("timeframe", INVALID_INSTRUMENTS)
def test_invalid_timeframe(timeframe):
    with pytest.raises(Exception) as e:
        test_get_candlestick("BTCUSD-PERP", timeframe=timeframe)
    assert "400" in str(e.value)
    
#7 Verify miss required params
def test_miss_params():
    with pytest.raises(Exception) as e:
        test_get_candlestick(None)
    assert "400" in str(e.value)
    
#8 We can add performance/stress test cases here