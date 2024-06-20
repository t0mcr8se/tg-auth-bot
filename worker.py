
import sqlite3
import telebot
from dotenv import load_dotenv
import os
from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
import time
load_dotenv()
# Constants for the RPC URL and contract details
def send_tokens(to_address):
    RPC_URL = 'https://sepolia.rpc.metisdevops.link/'
    CONTRACT_ADDRESS = '0x4E6D07bCF5586BC1eC0d3F066D1F795aFd26bD96'
    TO_ADDRESS = to_address  # Adjust the to address 

    # Replace with your private key
    private_key = os.environ.get("PRIVATE_KEY")

    # Check if the private key is provided
    if not private_key:
        raise ValueError("Private key not provided.")

    # Create a Web3 instance connected to the specified RPC URL
    w3 = Web3(Web3.HTTPProvider(RPC_URL))

    # Inject PoA middleware for networks using Proof of Authority consensus
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    # Check for connection to the Ethereum network
    if not w3.is_connected():
        raise ConnectionError("Failed to connect to HTTPProvider")

    # Load the contract ABI from a file
    with open('abi.json') as abi_file:
        contract_abi = json.load(abi_file)

    # Create a contract object
    contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

    # Get the nonce for the transaction
    nonce = w3.eth.get_transaction_count(w3.eth.account.from_key(private_key).address)


    print(w3.eth.accounts)
    # Build the transaction
    transaction = contract.functions.distributeToAddresses([TO_ADDRESS]).build_transaction({
        'chainId': w3.eth.chain_id,
        'gas': 500000,  # Adjust the gas limit as needed
        'gasPrice': Web3.to_wei(0.06,'gwei'),
        'nonce': nonce,
    })
    # Sign the transaction with the private key
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key)

    # Attempt to send the transaction
    try:
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction sent! Hash: {tx_hash.hex()}")
        return tx_receipt
    except Exception as e:
        print(f"Error sending transaction: {e}")
        return None

BOT_TOKEN = os.environ.get('BOT_TOKEN')
POLLING_TIMEOUT = None

bot = telebot.TeleBot(BOT_TOKEN)

while True:
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    # Retrieve non-visited records sorted by creation time
    cursor.execute('SELECT * FROM users WHERE visited = 0 ORDER BY created_at ASC LIMIT 5')
    non_visited_records = cursor.fetchall()

    for record in non_visited_records:

        # Update the record as visited
        cursor.execute('UPDATE users SET visited = 1 WHERE id = ?', (record[0],))
        conn.commit()

        # Send a message to the user that the request is in progress
        bot.send_message(record[2], 'Your request is in progress!')


        try:
            # Send tokens to the new tester
            tx_receipt = send_tokens(record[1])
            if tx_receipt is None or not tx_receipt['status'] or not tx_receipt['transactionHash']:
                raise Exception("Transaction failed")
            tx_hash = tx_receipt['transactionHash'].hex()
            # Mark the record as completed

            cursor.execute('UPDATE users SET completed = 1 WHERE id = ?', (record[0],))
            conn.commit()

            # Send a message to the user that the transaction is completed
            bot.send_message(record[2], f'tokens were sent successfully to wallet {record[1]}')
            bot.send_message(record[2], f'https://sepolia.explorer.metisdevops.link/tx/{tx_hash}')
            
        except Exception as e:
            # Handle any exceptions (e.g., transaction failure)
            print(e)
            bot.send_message(record[2], f'sorry, there was a problem while processing your request. ')
            bot.send_message(record[2], f'we will get back to you soon')
            
    time.sleep(1)

    conn.close()