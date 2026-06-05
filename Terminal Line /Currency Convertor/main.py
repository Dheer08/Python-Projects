# currency converter
# 1 USD = 0.85 EUR      
def convert_currency(amount, from_currency, to_currency):
    exchange_rates = {
        'USD': 1.0,
        'EUR': 0.85,
        'GBP': 0.75,
        'JPY': 110.0
    }
    
    if from_currency not in exchange_rates or to_currency not in exchange_rates:
        raise ValueError("Unsupported currency")
    
    # Convert the amount to USD first
    amount_in_usd = amount / exchange_rates[from_currency]
    
    # Then convert from USD to the target currency
    converted_amount = amount_in_usd * exchange_rates[to_currency]
    
    return converted_amount
# Example usage
if __name__ == "__main__":
    amount = float(input("Enter the amount to convert: "))
    from_currency = input("Enter the currency to convert from (USD, EUR, GBP, JPY): ")
    to_currency = input("Enter the currency to convert to (USD, EUR, GBP, JPY): ")
    
    try:
        result = convert_currency(amount, from_currency.upper(), to_currency.upper())
        print(f"{amount} {from_currency.upper()} is equal to {result:.2f} {to_currency.upper()}")
    except ValueError as e:
        print(e)