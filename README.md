# slash_refunds_tendermint

The purpose of this script is to create a json file to refund users from a slash event.

Usage:
```
git clone https://github.com/LavenderFive/slash_refunds_tendermint.git
cd slash_refunds_tendermint
python3 src/slash_refund.py --denom {denom} --daemon {denom} --c {chain_id} -e {rpc_endpoint} -vc {valcons_address} -v {valoper_address} -s {send_address}

# example:
python3 src/slash_refund.py --denom uatom --daemon gaiad --c cosmoshub-4 -e http://65.21.132.124:10657 -vc cosmosvalcons1c5e86exd7jsyhcfqdejltdsagjfrvv8xv22368 -v cosmosvaloper140l6y2gp3gxvay6qtn70re7z2s0gn57zfd832j -s cosmos15s9vggt9d0xumzqeq89scy4lku4k6qlzvvv2lz -m "With 💜 from Lavender.Five Nodes 🐝"
```

This will output `/tmp/dist.json`

### Previous Attempts

You may be tempted to believe the best way forward is to query against a node for addresses using block height, a la: 
```
{daemon} q staking delegations-to {valoper_address} --height {block_height} --page {page} --output json --limit {page_limit} --node {endpoint} --chain-id {chain_id}
```

And with under 1500 delegators, you would be correct. Anything above that, and 10 load-balanced nodes was insufficient. 