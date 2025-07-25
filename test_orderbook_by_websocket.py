import pytest
import json
import websockets
import time
import asyncio
import logging


#Log configs
logger = logging.getLogger(__name__)

WS_MARKET_URL = "wss://stream.crypto.com/exchange/v1/market"
INSTRUMENT = "BTCUSD-PERP"
DEPTHS = 10
SUBSCRIPTION_DELTA = "SNAPSHOT_AND_UPDATE"
SNAPSHOT_FREQS = [100, 500]
DELTA_FREQS = [10, 100]

#Support function to send subscribe
async def subscribe(ws, instrument=INSTRUMENT, depth=DEPTHS):
    sub_id = int (time.time()*1000)
    await ws.send(json.dumps({
            "id": sub_id,
            "method": "subscribe",
            "params": {
                "channels": [f"book.{instrument}.{depth}"],
                "book_subscription_type": SUBSCRIPTION_DELTA,
                "book_update_frequency": 100
            }
    }))
    
    await ws.recv()


#Test_case_1: Basic subscribe functional test
@pytest.mark.asyncio
async def test_basci_subscription():
    async with websockets.connect(WS_MARKET_URL) as ws:
        sub_id = int (time.time()*1000)
        await ws.send(json.dumps({
            "id": sub_id,
            "method": "subscribe",
            "params": {
                "channels": [f"book.{INSTRUMENT}.{DEPTHS}"],
                "book_subscription_type": SUBSCRIPTION_DELTA,
                "book_update_frequency": 100
            }
        }))

        #Verify basic subscribe response
        response = json.loads(await ws.recv())
        #logger.info(f"response: {response}")
        assert response["id"] == sub_id
        assert response["code"] == 0
        
        #Verify initial snapshot
        snapshot = json.loads(await ws.recv())
        assert snapshot["result"]["channel"] == "book"
        assert len(snapshot["result"]["data"][0]["asks"]) == DEPTHS
        assert len(snapshot["result"]["data"][0]["bids"]) == DEPTHS
        last_u = snapshot["result"]["data"][0]["u"]
        
        #Verify delta update
        delta = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))
        assert delta["result"]["channel"] == "book.update"
        assert delta["result"]["data"][0]["pu"] == last_u
        assert delta["result"]["data"][0]["u"] > last_u

#Test_case_2: Verify sequence number is continuity
@pytest.mark.asyncio
async def test_sequence_continuity():
    async with websockets.connect(WS_MARKET_URL) as ws:
        await subscribe(ws)
        await ws.recv() #skip subscribe
        snapshot = json.loads(await ws.recv())
        last_u = snapshot["result"]["data"][0]["u"]
        
        #Verify more new and update sequence number
        for _ in range(3):
            delta = json.loads(await ws.recv())
            data = delta["result"]["data"][0]
            assert data["pu"] == last_u
            last_u = data["u"]        

#Test_case_3: Empty heart beat handling. #TODO: Failed, need to debug.
@pytest.mark.asyncio
async def test_empty_heartbeat():
    async with websockets.connect(WS_MARKET_URL) as ws:
        await subscribe(ws)
        await ws.recv() #skip subscribe
        await ws.recv() #skip initial snapshot
        
        start_time = time.time()
        while time.time() - start_time < 6:
            delta = json.loads(await asyncio.wait_for(ws.recv(), timeout=6))
            if delta["result"]["channel"] == "book.update":
                #check empty updte
                if "update" not in delta["result"]["data"][0] or(
                    not delta["result"]["data"][0]["update"].get("bids") and
                    not delta["result"]["data"][0]["update"].get("asks")):
                    assert ["result"]["data"][0]["u"] > ["result"]["data"][0]["pu"]
                    return
        pytest.fail("Did not receive empty heartbeat within 6 secs")
        
#Test_case_4: Invalid params handling
@pytest.mark.asyncio
async def test_invalid_parameters():
    async with websockets.connect(WS_MARKET_URL) as ws:
        sub_id = int(time.time()*1000)
        await ws.send(json.dumps({
        "id": sub_id,
        "method": "subscribe",
        "params": {
            "channels": [f"book.{INSTRUMENT}.5"], #Invalid depth
            }
        }))
        response = json.loads(await ws.recv())
        assert response["code"] != 0

#Test_case_5: Verify data with 10 and 50 depths
    #1) Subscribe separatly with 10 and 50 depths
    #2) Verify the depth amount from response
    #3) Verify the asks and bids sequence  
        
#Test_case_6: Verify send snapshot every 500ms even no any update
    #1) Subscribe initial snapshot
    #2) Verify snapshot
    #3) Collect more snapshots and verify 500ms interval

#Test_case_7: Verify delta update merged to book
    #1) Create book with the initial snapshot
    #2) Apply for delta update
    #3) Verify the merged book structure

#Test_case_8: Verify restore logic if sequence number not consistent
    #1) Skip delta update to simulate sequence number not consistent
    #2) Verify it can get new snapshot after re-subscribe
    #3) Verify new sequence number is consistent

#Test_case_9: Verify stability with 10ms update
    #1) Set update frequency to 10ms
    #2) Collect response data and message within 5 seconds
    #3) Verify the miss message less than one number, like 10%

    