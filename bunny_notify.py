# -*- coding: utf-8 -*-
from web3 import Web3, WebsocketProvider, HTTPProvider
import asyncio

import telegram

import os
from os.path import join, dirname
from dotenv import load_dotenv
import json

import requests
from cairosvg import svg2png

import datetime

import logging

CHAT_ID = "@bunnies_notification"
# CHAT_ID = "@r3n_test_channel"
bot = None
nftkey_cont = None
# w3 = Web3(WebsocketProvider("wss://bsc-ws-node.nariox.org:443"))
w3 = Web3(HTTPProvider("https://bsc-dataseed.binance.org/"))

MD_ESCAPE = {
    '_': '\_', '*': '\*', '[': '\[', ']': '\]',
    '(': '\(', ')': '\)', '~': '\~', '`': '\~',
    '>': '\>', '#': '\#', '+': '\+', '-': '\-',
    '=': '\=', '|': '\|', '{': '\{', '}': '\}',
    '.': '\.', '!': '\!'
}


def md_escape(text: str):
    return text.translate(str.maketrans(MD_ESCAPE))


def getPngByte(bnny_id: int):
    svg_url = "https://storage.googleapis.com/bunniesassets/{}.svg".format(
        bnny_id)
    response = requests.get(svg_url)

    return svg2png(bytestring=response.content,
                   write_to=None, dpi=300)


def fetch(bnny_id: int):
    if bnny_id == 1:
        return open(
            join(dirname(__file__), "media", "bunny_1.png"),
            "rb").read()

    return getPngByte(bnny_id)


def notifyEvent(event):
    eventName = event["event"]
    args = event["args"]
    tokenId = args["tokenId"]
    txHash = Web3.toHex(event["transactionHash"])
    tx = w3.eth.get_transaction(txHash)
    funcInput = nftkey_cont.decode_function_input(tx.input)[1]

    text = ""
    image = None

    if eventName == "TokenListed":
        """ with image
        🏷New Listing!
          🐰Bunny #123
          🥕Price: 1.23 BNB
          🥕Expiration: ???
          🛒https://nftkey.app/collections/bnbbunnies/bunny-details/?tokenId=123
          🔎https://bscscan.com/tx/{txHash}?
        """
        price = args["minValue"] / 1000000000000000000
        price = str(price).replace(".", "\.")
        expiration = datetime.datetime.utcfromtimestamp(
            funcInput["expireTimestamp"])

        text = "🏷*New Listing\!*\n"\
               "  🐰Bunny \#{}\n"\
               "  🥕Price: {} BNB\n"\
               "  🥕Expiration: {} \(UTC\)\n"\
               "  🛒[*__NFTKEY Marketplace__*](https://nftkey.app/collections/bnbbunnies/bunny-details/?tokenId={})\n"\
               "  🔎[__Tx at bscscan__](https://bscscan.com/tx/{}?)".format(
                   tokenId,
                   price,
                   md_escape(str(expiration)),
                   tokenId,
                   txHash)
        image = fetch(tokenId)

    # elif eventName == "TokenDelisted":
    #     """ text only
    #     🚫Cancel Listing!
    #       🐰Bunny #123
    #     """
    #     text = "🚫*Cancel Listing\!*\n"\
    #            "  🐰Bunny \#{}".format(
    #                tokenId
    #            )
    elif eventName == "TokenBought":
        """ with image
        💰Bunny Sold!
          🐰Bunny #123
          🥕Price: 1.23 BNB!
          🔎https://bscscan.com/tx/{txHash}?
        """

        price = args["value"] / 1000000000000000000
        price = str(price).replace(".", "\.")

        text = "💰*Bunny Sold\!*\n"\
               "  🐰Bunny \#{}\n"\
               "  🥕Price: {} BNB\n"\
               "  🔎[__Tx at bscscan__](https://bscscan.com/tx/{}?)".format(
                   tokenId, price, txHash)
        image = fetch(tokenId)

    # elif eventName == "TokenBidAccepted":
    # elif eventName == "TokenBidEntered":
    # elif eventName == "TokenBidWithdrawn"

    # sold at original marketplace
    # if eventName == "Transfar":

    if text != "":
        if image is None:
            bot.send_message(
                chat_id=CHAT_ID,
                text=text,
                parse_mode="MarkdownV2"
            )
        else:
            bot.send_photo(
                chat_id=CHAT_ID,
                photo=image,
                caption=text,
                parse_mode="MarkdownV2"
            )


async def log_loop(event_filter, poll_interval):
    while True:
        for event in event_filter.get_new_entries():
            notifyEvent(event)
        await asyncio.sleep(poll_interval)


def main(bnny_cont_addr_1, bnny_cont_addr_2, nftkey_cont_addr, telegram_bot_token):
    logging.basicConfig(level=logging.INFO)
    logging.info("BunniesNotificator Start.")
    logging.info("Endpoint connected: {}".format(w3.isConnected()))

    bnny_abi_1 = json.loads(
        open(join(dirname(__file__), "bnny_abi_1.json")).read())
    bnny_abi_2 = json.loads(
        open(join(dirname(__file__), "bnny_abi_2.json")).read())
    nftkey_abi = json.loads(
        open(join(dirname(__file__), "nftkey_abi.json")).read())

    # bnny_cont_1 = w3.eth.contract(address=bnny_cont_addr_1, abi=bnny_abi_1)
    # bnny_cont_2 = w3.eth.contract(address=bnny_cont_addr_2, abi=bnny_abi_2)

    global nftkey_cont
    nftkey_cont = w3.eth.contract(address=nftkey_cont_addr, abi=nftkey_abi)

    # nftkey
    """
    TokenListed()
    args : tokenId - int
           fromAddress - address (str)
           minValue - int
    """
    nftkey_list = nftkey_cont.events.TokenListed.createFilter(
        fromBlock="latest")
    """
    TokenDelisted()
    args: tokenId - int
          fromAddress - address (str)
    """
    # nftkey_delist = nftkey_cont.events.TokenDelisted.createFilter(
    #     fromBlock="latest")
    """
    TokenBought()
    args: tokenId - int
          fromAddress - ddress (str)
          toAddress - address (str)
          total - int
          value - int
          fees - int
    total = value + fees
    """
    nftkey_sold = nftkey_cont.events.TokenBought.createFilter(
        fromBlock="latest")
    """
    TokenBidAccepted()
    args: tokenId - int
          owner - address (str)
          bidder - address (str)
          total - int
          value - int
          fees - int
    """
    # nftkey_bid_accepted = nftkey_cont.events.TokenBidAccepted.createFilter(
    #     fromBlock="latest")
    """
    TokenBidEntered()
    args: tokenId - int
          fromAddress - address (str)
          value - int
    """
    # nftkey_bid_entered = nftkey_cont.events.TokenBidEntered.createFilter(
    #     fromBlock="latest")
    """
    TokenBidWithdrawn()
    args: tokenId - int
          fromAddress - address (str)
          value - int
    """
    # nftkey_bid_withdrawn = nftkey_cont.events.TokenBidWithdrawn.createFilter(
    #     fromBlock="latest")

    # tx = w3.eth.get_transaction(
    #     "0x4e1f4b306233788c4bd9cc2e3799e97a17cbf50644162643162d728047a6abd7")
    # print(tx)
    # funcInput = bnny_cont_1.decode_function_input(tx.input)
    # print(funcInput)
    # print(type(funcInput[0]))
    # print(isinstance(type(funcInput[0]), type(bnny_cont_1.get_function_by_name(
    #     "buyAnimalsFromUser"))))
    # return

    global bot
    bot = telegram.Bot(token=telegram_bot_token)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            asyncio.gather(
                log_loop(nftkey_list, 30),
                # log_loop(nftkey_delist, 60),
                log_loop(nftkey_sold, 30),
                # log_loop(nftkey_bid_accepted, 30),
                # log_loop(nftkey_bid_entered, 30),
                # log_loop(nftkey_bid_withdrawn, 30)
            )
        )
    finally:
        loop.close()


def load_env():
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)

    bnny_cont_addr_1 = os.environ.get("BNNY_CONTRACT_1")
    bnny_cont_addr_2 = os.environ.get("BNNY_CONTRACT_2")
    nftkey_cont_addr = os.environ.get("NFTKEY_CONTRACT")
    telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")

    return bnny_cont_addr_1, bnny_cont_addr_2, nftkey_cont_addr, telegram_bot_token


if __name__ == '__main__':
    bnny_cont_addr_1, bnny_cont_addr_2, nftkey_cont_addr, telegram_bot_token = load_env()
    main(bnny_cont_addr_1, bnny_cont_addr_2,
         nftkey_cont_addr, telegram_bot_token)
