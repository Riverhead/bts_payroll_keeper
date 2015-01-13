#!/usr/bin/env python
# coding=utf8

# This is a watchdog script which connects to a delegate periodically to verify that it is up and running,
# and to do some basic maintenance tasks if the delegate is not ready to sign blocks and report if it is
# unhealthy

import requests
import sys
import os
import json
import getpass
import time
import datetime
from pprint import pprint
from dateutil import parser

BTS_PRECISION = 100000

config_data = open('config.json')
config = json.load(config_data)
config_data.close()

auth = (config["bts_rpc"]["username"], config["bts_rpc"]["password"])
url = config["bts_rpc"]["url"]

WALLET_NAME = config["wallet_name"]

DELEGATE_NAME = config["delegate_name"]
PAYTO = config["payto_account"]
THRESH = float(config["balance_threshold"])
SALARY = float(config["salary"])
PAYCHECK_TO = config["paycheck_to"]

MARKETUSD = "USD"
MARKETBTS = "BTS"

def parse_date(date):
  return datetime.datetime.strptime(date, "%Y%m%dT%H%M")

def call(method, params=[]):
  headers = {'content-type': 'application/json'}
  request = {
          "method": method,
          "params": params,
          "jsonrpc": "2.0",
          "id": 1
          }

  while True:
    try:
      response = requests.post(url, data=json.dumps(request), headers=headers, auth=auth)
      result = json.loads(vars(response)["_content"])
      #print "Method:", method
      #print "Result:", result
      return result
    except:
      print "Warnning: rpc call error, retry 5 seconds later"
      time.sleep(5)
      continue
    break  
  return None

while True:
  try:
    os.system("clear")
    print("\nRunning Balance Keeper")
 
    response = call("wallet_get_account", [DELEGATE_NAME] )
    if "error" in response:
      print("FATAL: Failed to get info:")
      print(result["error"])
      exit(1)
    response = response["result"]

    balance = float(response["delegate_info"]["pay_balance"] / BTS_PRECISION)

    print ("Balance for %s is currently: %s BTS" % (DELEGATE_NAME, balance))

    if balance > (SALARY+THRESH+1):
       response = call("wallet_delegate_withdraw_pay", [DELEGATE_NAME, PAYTO, THRESH])

    with open('last_pay.dat', 'r') as f :
      last_pay_date_dat = f.read()
    f.close()

    last_pay_date_dat = last_pay_date_dat.rstrip()

    print ("Last pay date: %s" % last_pay_date_dat)

    last_pay_date = parser.parse(last_pay_date_dat)
    next_pay_date = last_pay_date + datetime.timedelta(days=14)
    now = datetime.datetime.now()
    print ("Next pay date: %s" % next_pay_date)

    rec_pay_date = str((datetime.datetime.now() + datetime.timedelta(hours=-5)))

    if now > next_pay_date :
      print("Paying a salary of %s to %s" % (SALARY, PAYCHECK_TO))
      response = call("wallet_delegate_withdraw_pay", [DELEGATE_NAME, PAYCHECK_TO, SALARY])
      if "error" in response:
        print ("Something went wrong")
      else:
        response = call("blockchain_market_status", [MARKETUSD, MARKETBTS])
        if "error" in response:
          print("FATAL: Failed to get market info:")
          print(result["error"])
          exit(1)
        response = response["result"]
        print(response)
        feed_price = float(response["current_feed_price"])
        print(feed_price)
        bitUSD = SALARY * feed_price
        print(bitUSD)

        print("Times up!")

        response = call("wallet_account_transaction_history", [DELEGATE_NAME])
        if "error" in response:
          print("FATAL: Failed to get account history info:")
          print(result["error"])
          exit(1)
        response = response["result"]
        print(response)
        k = 0
        for i in response:
          k = k + 1
        xTrxId = response[k-1]["trx_id"]
        timeStamp = response[k-1]["timestamp"]

        with open('transactions.txt', 'a') as f :
          f.write("%s, %s, %s, %s, %s\n" % (timeStamp, SALARY, bitUSD, PAYCHECK_TO, xTrxId))
        f.close()

        with open('last_pay.dat', 'w') as f :
          f.write(rec_pay_date)
        f.close()

    print ("Last Checked: %s\n" % (rec_pay_date))  
    
    time.sleep(300)
  except:
    time.sleep(300)
