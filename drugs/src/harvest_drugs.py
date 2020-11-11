
import sys
import os
import time
import yaml
import logging
from dotenv import load_dotenv
from web3 import Web3

#get price from AMMs

load_dotenv()

sleep_time_seconds = None
min_pool_harvest = None
min_drug_stake = None
web3_endpoint = None
account_address = None
account_pk = None
og_contract_address = None
og_contract_abi = None
og_contract = None
drugs_token_address = None
drugs_token_abi = None
drugs_contract = None
w3 = None
log_format = '%(levelname)s:%(asctime)s: %(message)s'

logging.basicConfig(level=logging.INFO,format=log_format)

#read configs
with open('./drugs.yaml') as cfg_stream:
    logging.info('reading config')
    try:
        account_address = os.getenv("ACCOUNT_ADDRESS")#env variable
        account_pk = os.getenv("ACCOUNT_PRIVATE_KEY")#env variable
        cfg = yaml.safe_load(cfg_stream)
        sleep_time_seconds = cfg['sleep_time_seconds']
        min_pool_harvest = cfg['min_pool_harvest']
        min_drug_stake = cfg['min_drug_stake']
        web3_endpoint = cfg['web3_endpoint']
        og_contract_abi = cfg['og_contract_abi']
        og_contract_address = cfg['og_contract_address']
        drugs_token_abi = cfg['drugs_token_abi']
        drugs_token_address = cfg['drugs_token_address']
    except yaml.YAMLError as err:
        logging.critical(err)
        sys.exit()

#construct contracts
if og_contract_abi and og_contract_address:
    w3=Web3(Web3.HTTPProvider(web3_endpoint))
    og_contract = w3.eth.contract(address=og_contract_address,abi=og_contract_abi)
    drugs_contract = w3.eth.contract(address=drugs_token_address,abi=drugs_token_abi)
else:
    logging.info('terminal error - no contract/abi')
    sys.exit()

def harvest():
    for pid in range(og_contract.functions.poolLength().call()):
        pending_rewards_wei = og_contract.functions.pendingDrugs(pid, account_address).call()
        pending_rewards_ether = w3.fromWei(pending_rewards_wei,"ether")
        logging.info(f'pool {pid} pending DRUGS = {pending_rewards_ether}')
        if pending_rewards_ether > min_pool_harvest:
            logging.info(f'processing pool {pid}')
            if pid == 0:
                logging.info("harvesting DRUGS from HOES staking (poolid = 0)")
                stx = og_contract.functions.leaveStaking(0).buildTransaction(getTransactionData())
                signAndSendTransaction(stx)
            else:
                logging.info(f'\tharvesting from pool {pid}')
                tx_data = getTransactionData()
                tx = og_contract.functions.deposit(pid,0).buildTransaction(tx_data)
                signAndSendTransaction(tx)

def ensureDrugsAllowance():
    drugsAllowance = drugs_contract.functions.allowance(account_address,og_contract_address).call()
    logging.info(f'drugsAllowance={drugsAllowance}')
    assert(drugsAllowance > 0)

def stakeDrugs():
    logging.info('staking')
    drugs_balance_wei = drugs_contract.functions.balanceOf(account_address).call()
    drugs_balance_eth = w3.fromWei(drugs_balance_wei,'ether')
    logging.info(f'\tdrugs_balance={drugs_balance_eth}')
    if drugs_balance_eth > min_drug_stake:
        tx_data = getTransactionData()
        tx = og_contract.functions.enterStaking(drugs_balance_wei).buildTransaction(tx_data)
        signAndSendTransaction(tx)
    else:
        logging.info('insufficient drugs to stake')

def getTransactionData():
    return {'nonce' : w3.eth.getTransactionCount(account_address),
            'gas' : 200000,
            'gasPrice' : w3.eth.generateGasPrice()
            }

def signAndSendTransaction(tx):
    logging.info(f'signing and sending tx{tx}')
    signed_tx = w3.eth.account.signTransaction(tx, account_pk)
    tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)
    logging.info(f'tx_hash={w3.toHex(tx_hash)}')
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    status=tx_receipt['status']
    gasUsed=w3.fromWei(tx_receipt["gasUsed"],'ether')
    blockHash=w3.toHex(tx_receipt['blockHash'])
    logging.info(f'\tstatus={status}, blockNumber={tx_receipt["blockNumber"]}, gasUsed={gasUsed}, blockHash={blockHash}')

if __name__ == "__main__":
    ensureDrugsAllowance()
    while True:
        harvest()
        stakeDrugs()
        logging.info(f'sleeping for {sleep_time_seconds}s')
        time.sleep(sleep_time_seconds)
