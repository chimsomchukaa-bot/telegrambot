from config.catalogue import PAYMENT_USD, PAYMENT_GBP


def format_usd_instructions() -> str:
    p = PAYMENT_USD
    return (
        "Please make a bank transfer using the following USD details:\n\n"
        f"Account Holder: {p['account_holder']}\n"
        f"Account Number: {p['account_number']}\n"
        f"Bank Name: {p['bank_name']}\n"
        f"ACH Routing: {p['ach_routing']}\n"
        f"Wire Routing: {p['wire_routing']}\n"
        f"Account Type: {p['account_type']}\n"
        f"Bank Address: {p['bank_address']}\n\n"
        "After completing the transfer, please send a clear screenshot of the transaction "
        "for verification. Your order will remain in Pending Verification until our team reviews it."
    )


def format_gbp_instructions() -> str:
    p = PAYMENT_GBP
    return (
        "Please make a bank transfer using the following GBP details:\n\n"
        f"Account Holder: {p['account_holder']}\n"
        f"Account Number: {p['account_number']}\n"
        f"Bank Name: {p['bank_name']}\n"
        f"Sort Code: {p['sort_code']}\n"
        f"Swift Code: {p['swift_code']}\n"
        f"IBAN: {p['iban']}\n"
        f"Bank Address: {p['bank_address']}\n\n"
        "After completing the transfer, please send a clear screenshot of the transaction "
        "for verification. Your order will remain in Pending Verification until our team reviews it."
    )


def format_both_payment_options() -> str:
    return (
        "We accept bank transfers in USD or GBP.\n\n"
        "——— USD ——–\n"
        f"{format_usd_instructions()}\n\n"
        "——— GBP ——–\n"
        f"{format_gbp_instructions()}"
    )
