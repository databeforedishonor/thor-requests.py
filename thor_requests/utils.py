"""
These functions are portable.

read: only reading.
build: put parts in to a whole.
calc: transforming or reform.
is: boolean functions.
"""

import json
import secrets
from typing import List, Union

from thor_devkit import abi, cry, transaction
from thor_devkit.cry import address, secp256k1

from .contract import Contract
from .wallet import Wallet


def build_url(base: str, tail: str) -> str:
    """Build a proper URL, base + tail"""
    return base.rstrip("/") + "/" + tail.lstrip("/")


def build_params(types: List, args: List) -> bytes:
    """ABI encode params according to types"""
    return abi.Coder.encode_list(types, args)


def calc_address(priv: bytes) -> str:
    """Calculate an address from a given private key"""
    public_key = secp256k1.derive_publicKey(priv)
    _address_bytes = cry.public_key_to_address(public_key)
    address = "0x" + _address_bytes.hex()
    return address


def calc_nonce() -> int:
    """Calculate a random number for nonce"""
    return int(secrets.token_hex(8), 16)


def calc_blockRef(block_id: str) -> str:
    """Calculate a blockRef from a given block_id, id should starts with 0x"""
    if not block_id.startswith("0x"):
        raise Exception("block_id should start with 0x")
    return block_id[0:18]


def calc_chaintag(hex_str: str) -> int:
    """hex_str can be both like '0x4a' or just '4a'"""
    return int(hex_str, 16)


def calc_gas(vm_gas: int, intrinsic_gas: int) -> int:
    """Calculate recommended (safe) gas"""
    return vm_gas + intrinsic_gas + 15000


def calc_vtho(gas: int, coef: 0) -> int:
    """Calculate extimated vtho from gas"""
    if coef > 255 or coef < 0:
        raise Exception("coef: [0~255]")
    return gas * (1 + coef / 255)


def any_emulate_failed(emulate_responses: List) -> bool:
    """Check the emulate response, if any tx reverted then it is a fail"""
    results = [each["reverted"] for each in emulate_responses]
    return any(results)


def is_emulate_failed(emulate_response) -> bool:
    """If a single clause emulation is failed"""
    return emulate_response["reverted"]


def read_vm_gases(emulated_responses: List) -> List[int]:
    """Extract vm gases from a batch of emulated executions."""
    results = [int(each["gasUsed"]) for each in emulated_responses]
    return results


def build_tx_body(
    clauses: List,
    chainTag: int,
    blockRef: str,
    nonce: int,
    expiration: int = 32,
    gasPriceCoef: int = 0,
    gas: int = 0,
    dependsOn=None,
) -> dict:
    """Build a Tx body.

    Clause should confine to "thor_devkit.transaction.CLAUSE" schema. {to, value, data}
    Tx body shall confine to "thor_devkit.transaction.BODY" schema.
    """
    body = {
        "chainTag": chainTag,
        "blockRef": blockRef,
        "expiration": expiration,
        "clauses": clauses,
        "gasPriceCoef": gasPriceCoef,
        "gas": str(gas),
        "dependsOn": dependsOn,
        "nonce": nonce,
    }

    # Raise Exception if format check cannot pass.
    transaction.Transaction(body)

    return body


def calc_emulate_tx_body(caller: str, tx_body: dict) -> dict:
    """Rip an emulated tx body from a normal tx body."""
    # Raise Exception if format check cannot pass.
    transaction.Transaction(tx_body)
    # Check if caller is correct format.
    if not address.is_address(caller):
        raise Exception(f"{caller} is not an address")

    e_tx_body = {
        "caller": caller,
        "blockRef": tx_body["blockRef"],
        "expiration": tx_body["expiration"],
        "clauses": tx_body["clauses"],
    }

    # Set gas field only when the tx_body set it.
    if int(tx_body["gas"]) > 0:
        e_tx_body["gas"] = int(tx_body["gas"])

    return e_tx_body


def calc_tx_unsigned(
    tx_body: dict, encode=False
) -> Union[transaction.Transaction, str]:
    """Build unsigned transaction from tx body"""
    tx = transaction.Transaction(tx_body)
    if encode:
        return "0x" + tx.encode().hex()
    else:
        return tx


def calc_tx_signed(
    wallet: Wallet, tx_body: dict, encode=False
) -> Union[transaction.Transaction, str]:
    """Build signed transaction from tx body"""
    tx = calc_tx_unsigned(tx_body, encode=False)
    message_hash = tx.get_signing_hash()
    signature = wallet.sign(message_hash)
    tx.set_signature(signature)
    if encode:
        return "0x" + tx.encode().hex()
    else:
        return tx


def is_readonly(abi_dict: dict):
    """Check the abi, see if the function is read-only"""
    # Check the shape of input data
    abi.FUNCTION(abi_dict)

    return (
        abi_dict["stateMutability"] == "view" or abi_dict["stateMutability"] == "pure"
    )


def calc_revertReason(data: str) -> str:
    """
    Extract revert reason from data

    Parameters
    ----------
    data : str
        "0x...." string of data

    Returns
    -------
    str
        revert reason in string

    Raises
    ------
    Exception
        If the revert reason data is not in good shape
    """
    if not data.startswith("0x08c379a0"):  # abi encoded of "Error(string)"
        raise Exception(f"{data.hex()} is not a valid error message")

    message = abi.Coder.decode_single(
        "string", bytes.fromhex(data.replace("0x08c379a0", ""))
    )
    return message


def inject_decoded_event(
    event_dict: dict, contract: Contract, target_address: str = None
) -> dict:
    """
    Inject 'decoded' and 'name' into event

    Each event is:
    {
        "address": "0x...",
        "topics": [
            "0x...",
            "0x...",
            ...
        ],
        "data": "0x..."
    }
    """
    # target_address doesn't compily with event address
    if target_address and (event_dict["address"].lower() != target_address.lower()):
        return event_dict

    e_obj = contract.get_event_by_signature(bytes.fromhex(event_dict["topics"][0][2:]))
    if not e_obj:  # oops, event not found, cannot decode
        return event_dict
    # otherwise can be decoded
    event_dict["decoded"] = e_obj.decode(
        bytes.fromhex(event_dict["data"][2:]),
        [bytes.fromhex(x[2:]) for x in event_dict["topics"]],
    )
    event_dict["name"] = e_obj.get_name()
    return event_dict


def inject_decoded_return(e_response: dict, contract: Contract, func_name: str) -> dict:
    """Inject 'decoded' return value into a emulate response"""
    if e_response["reverted"] == True:
        return e_response

    if (not e_response["data"]) or (e_response["data"] == "0x"):
        return e_response

    function_obj = contract.get_function_by_name(func_name, True)
    e_response["decoded"] = function_obj.decode(
        bytes.fromhex(e_response["data"][2:])  # Remove '0x'
    )

    return e_response


def inject_revert_reason(e_response: dict) -> dict:
    """Inject ['decoded''revertReason'] if the emulate response failed"""
    if e_response["reverted"] == True and e_response["data"] != "0x":
        e_response["decoded"] = {"revertReason": calc_revertReason(e_response["data"])}

    return e_response


def is_reverted(receipt: dict) -> bool:
    """Check receipt to see if tx is reverted"""
    return receipt["reverted"]


def read_created_contracts(receipt: dict) -> list:
    """Read receipt and return a list of contract addresses created"""
    a = [x.get("contractAddress") for x in receipt["outputs"]]
    b = [x for x in a if x != None]
    return b


def is_contract(account: dict) -> bool:
    """Check if the address online is a contract"""
    return account["hasCode"]
