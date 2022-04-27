import argparse
import json
import requests

from subprocess import run
from time import sleep


def getResponse(end_point, query_field=None, query_msg=None):
    response = None

    try:
        if query_msg is not None and query_field is not None:
            response = requests.get(end_point, params={query_field: query_msg})
        else:
            response = requests.get(end_point, params={})
    except Exception as e:
        print(e)

    if response is not None and response.status_code == 200:
        return json.loads(response.text)
    else:
        if response is not None:
            print("Response Error")
            print(str(response.status_code))
            print(str(response.text))
        else:
            print("Response is None")

        return None


def getSlashBlock(url: str, val_address: str) -> int:
    endpoint = url + "/block_search?query=%22slash.address=%27" + val_address + "%27%22"
    data = getResponse(endpoint)
    latest_slash = len(data["result"]["blocks"]) - 1
    return data["result"]["blocks"][latest_slash]["block"]["header"]["height"]

def getDelegationAmounts(
    daemon: str, endpoint: str, chain_id: str, block_height: int, valoper_address: str
):
    endpoints = [endpoint, "https://rpc-cosmoshub.ecostake.com:443"]
    delegations = {}
    page = 1
    page_limit = 100
    more_pages = True

    while more_pages:
        endpoint_choice = (page % len(endpoints)) - 1
        result = run(
            f"/home/schultzie/go/bin/{daemon} q staking delegations-to {valoper_address} --height {block_height} --page {page} --output json --limit {page_limit} --node {endpoints[endpoint_choice]} --chain-id {chain_id}",
            shell=True,
            capture_output=True,
            text=True,
        )
        if result.returncode == 1:
            print(endpoints[endpoint_choice])
            continue
        response = json.loads(result.stdout)

        for delegation in response["delegation_responses"]:
            delegator_address = delegation["delegation"]["delegator_address"]
            delegation_amount = delegation["balance"]["amount"]
            if delegator_address not in delegations:
                delegations[delegator_address] = delegation_amount
            else:
                print(delegator_address)
        page += 1
        sleep(2)
        if len(response["delegation_responses"]) < page_limit:
            more_pages = False
    
    return delegations

def calculateRefundAmounts(
    daemon: str, endpoint: str, chain_id: str, slash_block: int, valoper_address: str
):
    pre_slack_block = int(slash_block) - 5
    refund_amounts = {}
    # pre_slash_delegations = getDelegationAmounts(
    #     daemon, endpoint, chain_id, pre_slack_block, valoper_address
    # )
    
    # post_slash_delegations = getDelegationAmounts(
    #     daemon, endpoint, chain_id, slash_block, valoper_address
    # )
    
    pre_slash_delegations = read_json(pre_slack_block)
    post_slash_delegations = read_json(slash_block)

    if len(pre_slash_delegations) != len(post_slash_delegations):
        raise ("Something went awry on delegation calcs")
    for delegation_address in pre_slash_delegations:
        refund_amount = int(
            pre_slash_delegations[delegation_address]
        ) - int(post_slash_delegations[delegation_address])
        if refund_amount > 10:
            refund_amounts[delegation_address] = refund_amount

    with open("/tmp/refund_amounts.json", "w+") as f:
        f.write(json.dumps(refund_amounts))
            
    return refund_amounts

def read_json(block_height):
    with open(f"/tmp/{block_height}.json") as f:
        return json.load(f)
        
def buildRefundJSON(
    refund_amounts: dict, send_address: str, denom: str, memo: str
) -> dict:
    data = {
        "body": {
            "messages": [],
            "memo": memo,
            "timeout_height": "0",
            "extension_options": [],
            "non_critical_extension_options": [],
        },
        "auth_info": {
            "signer_infos": [],
            "fee": {
                "amount": [{"denom": denom, "amount": "1000"}],
                "gas_limit": "1500000",
                "payer": "",
                "granter": "",
            },
        },
        "signatures": [],
    }
    message_list = []
    for refund_address in refund_amounts:
        message = {
            "@type": "/cosmos.bank.v1beta1.MsgSend",
            "from_address": send_address,
            "to_address": refund_address,
            "amount": [{"denom": denom, "amount": str(refund_amounts[refund_address])}],
        }
        message_list.append(message)
    data["body"]["messages"] = message_list
    return data


def buildRefundScript(refund_amounts: dict, send_address: str, denom: str, memo: str):
    refundJson = buildRefundJSON(refund_amounts, send_address, denom, memo)
    with open("/tmp/dist.json", "w+") as f:
        f.write(json.dumps(refundJson))


def parseArgs():
    parser = argparse.ArgumentParser(
        description="Create json file for refunding slashing to delegators"
    )
    parser.add_argument(
        "--denom",
        dest="denom",
        required=True,
        default="uatom",
        help="denom for refunds (ex. uatom)",
    )
    parser.add_argument(
        "--daemon",
        dest="daemon",
        required=True,
        default="gaiad",
        help="daemon for refunds (ex. gaiad)",
    )
    parser.add_argument(
        "-c",
        "--chain_id",
        dest="chain_id",
        required=True,
        default="cosmoshub-4",
        help="Chain ID (ex. cosmoshub-4)",
    )
    parser.add_argument(
        "-e",
        "--endpoint",
        dest="endpoint",
        required=True,
        help="RPC endpoint to node for gathering data",
    )
    parser.add_argument(
        "-vc",
        "--valcons_address",
        dest="valcons_address",
        required=True,
        help="Valcons address of validator (ex. cosmosvalcons1c5e86exd7jsyhcfqdejltdsagjfrvv8xv22368), you can get this by doing {daemon} tendermint show-address",
    )
    parser.add_argument(
        "-v",
        "--valoper_address",
        dest="valoper_address",
        required=True,
        help="Valoper address of validator (ex. cosmosvaloper140l6y2gp3gxvay6qtn70re7z2s0gn57zfd832j), you can get this by doing {daemon} keys show --bech=val -a {keyname}",
    )
    parser.add_argument(
        "-s",
        "--send_address",
        dest="send_address",
        required=True,
        help="Address to send funds from",
    )
    parser.add_argument(
        "-m",
        "--memo",
        dest="memo",
        help="Optional. Memo to send in each tx (ex. With 💜 from Lavender.Five Nodes 🐝",
    )
    return parser.parse_args()


def main():
    # args = parseArgs()
    # denom = args.denom
    # daemon = args.daemon
    # chain_id = args.chain_id
    # endpoint = args.endpoint
    # valcons_address = args.valcons_address
    # valoper_address = args.valoper_address
    # send_address = args.send_address
    # memo = args.memo
    
    denom = "uatom"
    daemon = "gaiad"
    chain_id = "cosmoshub-4"
    endpoint = "http://65.21.132.124:10657"
    valcons_address = "cosmosvalcons1c5e86exd7jsyhcfqdejltdsagjfrvv8xv22368"
    valoper_address = "cosmosvaloper140l6y2gp3gxvay6qtn70re7z2s0gn57zfd832j"
    send_address = "cosmos15s9vggt9d0xumzqeq89scy4lku4k6qlzvvv2lz"
    memo = "With 💜 from Lavender.Five Nodes 🐝"

    slash_block = getSlashBlock(endpoint, valcons_address)
    print(slash_block)
    refund_amounts = calculateRefundAmounts(
        daemon, endpoint, chain_id, slash_block, valoper_address
    )
    # buildRefundScript(refund_amounts, send_address, denom, memo)


if __name__ == "__main__":
    main()
# https://colab.research.google.com/github/dcmoura/spyql/blob/master/notebooks/json_benchmark.ipynb