
import sys
import os
import time
import yaml
import logging
from dotenv import load_dotenv
from web3 import Web3

#todo estimate gas
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
        min_hoes_stake = cfg['min_hoes_stake']
        min_mooDrugsGuns_stake = cfg['min_mooDrugsGuns_stake']
        web3_endpoint = cfg['web3_endpoint']
        og_contract_abi = cfg['og_contract_abi']
        og_contract_address = cfg['og_contract_address']
        sg_contract_abi = cfg['sgangster_contract_abi']
        sg_contract_address = cfg['sgangster_contract_address']
        mooDrugsGuns_contract_address = cfg['mooDrugsGuns_contract_address']
        mooDrugsGuns_contract_abi = cfg['mooDrugsGuns_contract_abi']
        drugs_token_abi = cfg['drugs_token_abi']
        drugs_token_address = cfg['drugs_token_address']
        hoes_token_abi = cfg['hoes_token_abi']
        hoes_token_address = cfg['hoes_token_address']
        enable_hoes = cfg['enable_hoes']
        enable_mooDrugsGuns = cfg['enable_mooDrugsGuns']
    except yaml.YAMLError as err:
        logging.critical(err)
        sys.exit()

#construct contracts
if og_contract_abi and og_contract_address:
    w3=Web3(Web3.HTTPProvider(web3_endpoint))
    og_contract = w3.eth.contract(address=og_contract_address,abi=og_contract_abi)
    sg_contract = w3.eth.contract(address=sg_contract_address,abi=sg_contract_abi)
    drugs_contract = w3.eth.contract(address=drugs_token_address,abi=drugs_token_abi)
    hoes_contract = w3.eth.contract(address=hoes_token_address,abi=hoes_token_abi)
    mooDrugsGuns_contract = w3.eth.contract(address=mooDrugsGuns_contract_address,abi=mooDrugsGuns_contract_abi)
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

def ensureMooDrugsGunsAllowance():
    logging.info('enter moo allowance')
    mooDrugsGunsAllowance = drugs_contract.functions.allowance(account_address,mooDrugsGuns_contract_address).call()
    logging.info(f'mooDrugsGunsAllowance={mooDrugsGunsAllowance}')
    assert(mooDrugsGunsAllowance > 0)

def stakeDrugs():
    logging.info('staking Drugs...')
    drugs_balance_wei = drugs_contract.functions.balanceOf(account_address).call()
    drugs_balance_eth = w3.fromWei(drugs_balance_wei,'ether')
    logging.info(f'\tdrugs_balance={drugs_balance_eth}')
    if drugs_balance_eth > min_drug_stake:
        tx_data = getTransactionData()
        tx = og_contract.functions.enterStaking(drugs_balance_wei).buildTransaction(tx_data)
        signAndSendTransaction(tx)
    else:
        logging.info('insufficient drugs to stake')

def stakeHoes():
    logging.info('staking Hoes...')
    hoes_balance_wei = hoes_contract.functions.balanceOf(account_address).call()
    hoes_balance_eth = w3.fromWei(hoes_balance_wei,'ether')
    logging.info(f'\thoes_balance={hoes_balance_eth}')
    if hoes_balance_eth > min_hoes_stake:
        tx_data = getTransactionData()
        tx = sg_contract.functions.deposit(hoes_balance_wei).buildTransaction(tx_data)
        signAndSendTransaction(tx)
    else:
        logging.info('insufficient hoes to stake...')

def stakeMooDrugsGuns():
    logging.info('staking mooDrugsGuns at Beefy...')
    mooDrugsGuns_balance_wei = drugs_contract.functions.balanceOf(account_address).call()
    mooDrugsGuns_balance_eth = w3.fromWei(mooDrugsGuns_balance_wei,'ether')
    logging.info(f'\tmooDrugsGuns_balance={mooDrugsGuns_balance_eth}')
    if mooDrugsGuns_balance_eth > min_mooDrugsGuns_stake:
        tx_data = getTransactionData()
        tx = mooDrugsGuns_contract.functions.depositAll().buildTransaction(tx_data)
        signAndSendTransaction(tx)
    else:
        logging.info('insufficient mooDrugsGuns to stake...')

def getTransactionData():
    return {'nonce' : w3.eth.getTransactionCount(account_address),
            'gas' : 800000,
            'gasPrice' : w3.toWei(20, 'gwei')}

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
    logging.info('Starting Drugs and Hoes staking script...')
    logging.info(f'Min pool harvest: {min_pool_harvest}')
    logging.info(f'Min Drug stake: {min_drug_stake}')
    logging.info(f'Min hoes stake: {min_hoes_stake}')
    logging.info(f'Min mooDrugsGuns stake: {min_mooDrugsGuns_stake}')
    ensureDrugsAllowance()
    if enable_mooDrugsGuns == True:
        logging.info('mooDrugsGuns staking enabled')
        ensureMooDrugsGunsAllowance()
    while True:
        logging.info('Starting new round [................]')
        harvest()
        if enable_mooDrugsGuns == True:
            logging.info('Sleep for 5 seconds to wait for blockchain to catch up')
            time.sleep(5)    
            stakeMooDrugsGuns()
        else:
            stakeDrugs()
            if enable_hoes == True:
                stakeHoes()
        logging.info(f'sleeping for {sleep_time_seconds}s')
        logging.info('Round done [................]')
        logging.info('')
        time.sleep(sleep_time_seconds)
