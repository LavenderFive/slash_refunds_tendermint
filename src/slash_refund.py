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
    endpoints = [endpoint, "https://rpc-cosmoshub.blockapsis.com:443", "https://cosmoshub.validator.network:443", "https://rpc-cosmoshub.ecostake.com:443"]
    delegations = {}
    page = 1
    page_limit = 100
    more_pages = True

    while more_pages:
        endpoint_choice = (page % len(endpoints)) - 1
        result = run(
            f"/usr/local/go/bin/{daemon} q staking delegations-to {valoper_address} --height {block_height} --page {page} --output json --limit {page_limit} --node {endpoints[endpoint_choice]} --chain-id {chain_id}",
            shell=True,
            capture_output=True,
            text=True,
        )
        if result.returncode == 1:
            print(endpoints[endpoint_choice])
            raise ("No delegations returned")
        response = json.loads(result.stdout)

        for delegation in response["delegation_responses"]:
            delegator_address = delegation["delegation"]["delegator_address"]
            delegation_amount = delegation["balance"]["amount"]
            if delegator_address not in delegations:
                delegations[delegator_address] = delegation_amount
            else:
                print(delegator_address)
        page += 1
        sleep(5)
        if len(response["delegation_responses"]) < page_limit:
            more_pages = False
        print(len(delegations))




def calculateRefundAmounts(
    daemon: str, endpoint: str, chain_id: str, slash_block: int, valoper_address: str
):
    pre_slash_delegations = getDelegationAmounts(
        daemon, endpoint, chain_id, int(slash_block) - 1, valoper_address
    )
    post_slash_delegations = getDelegationAmounts(
        daemon, endpoint, chain_id, slash_block, valoper_address
    )


def main(daemon: str, endpoint: str, chain_id: str):
    pass


if __name__ == "__main__":
    daemon = "gaiad"
    chain_id = "cosmoshub-4"
    endpoint = "http://65.21.132.124:10657"
    valcons_address = "cosmosvalcons1c5e86exd7jsyhcfqdejltdsagjfrvv8xv22368"
    valoper_address = "cosmosvaloper140l6y2gp3gxvay6qtn70re7z2s0gn57zfd832j"

    slash_block = getSlashBlock(endpoint, valcons_address)
    calculateRefundAmounts(daemon, endpoint, chain_id, slash_block, valoper_address)
    # main(daemon, endpoint, chain_id)
