from requests import get
from json import load, loads, dump
from discord_webhook import DiscordWebhook, DiscordEmbed
from random import choice

import threading
import time
import sys
import os


def get_settings():  # Get all the data that is stored in settings.json
    with open('settings.json', 'r') as file:
        settings = load(file)
        file.close()

    return settings


def get_skus():  # Get all the skus in skus.txt
    file = open('skus.txt', 'r')
    skus = [sku.strip() for sku in file.readlines()]
    file.close()
    return skus


def get_data():  # Gets the data from data.json
    with open('data.json', 'r') as file:
        # Reading from json file
        stored_data = load(file)
        file.close()

    return stored_data


def get_proxies():  # Gets all proxy in the proxy file and makes a list from them
    with open('proxies.txt', 'r') as proxy_file:
        proxy_list = [proxy.strip() for proxy in proxy_file.readlines()]
        proxy_file.close()

    # Chooses a random proxy from proxy_list
    if proxy_list != []:
        proxy_url = choice(proxy_list)

        # Splits user:pass:ip:port up
        proxy_items = proxy_url.split(':')

        username = proxy_items[2]
        password = proxy_items[3]
        ip = proxy_items[0]
        port = proxy_items[1]

        proxy = {
            'http': f'http://{username}:{password}@{ip}:{port}/',
        }
        return proxy
    else:
        return {}


def get_product_info(sku):  # Gets all the other relavent information on the product
    url = f'https://www.adidas.co.uk/api/products/{sku}'

    response = get(url=url, headers=headers)
    content = loads(s=response.content)

    name = content['name']
    product_url = f"https:{content['meta_data']['canonical']}"
    image_url = content['view_list'][0]['image_url']
    price = content['pricing_information']['currentPrice']
    site_name = content['meta_data']['site_name']
    model_number = content['model_number']

    return name, product_url, image_url, price, site_name, model_number


def send_update(sku, package, info=True):  # Sends the information to discord
    # This is if new_data has variation_list in it
    if info:
        name, product_url, image_url, price, site_name, model_number = get_product_info(
            sku=sku)
        price = currency+str(price)

        description = f'**Model Number:** {model_number}'

        if package['Info'] == True:
            webhook = DiscordWebhook(url=webhook_urls)

            data = package['Data']

            sizes = '\n'.join(
                [f"{size_prefix}  {variation['size']}" for variation in data])
            availability = '\n'.join(
                [str(variation['availability']) for variation in data])

            total_stock = sum([int(variation['availability'])
                               for variation in data])

            embed = DiscordEmbed(
                title=name,
                description=description,
                url=product_url
            )

            embed.set_thumbnail(url=image_url)

            embed.add_embed_field(name='SKU', value=sku, inline=True)
            embed.add_embed_field(name='Price', value=price, inline=True)
            embed.add_embed_field(
                name='Site Name', value=site_name, inline=True)

            embed.add_embed_field(name='Sizes', value=sizes, inline=True)
            embed.add_embed_field(name='Availability',
                                  value=availability, inline=True)
            embed.add_embed_field(name='Total Stock',
                                  value=total_stock, inline=True)

            webhook.add_embed(embed)
            webhook.execute()
            time.sleep(3)


def update_stored_data(sku, content):  # Updates data.json
    with open('data.json', "r") as file:
        data = load(file)
        file.close()

    data[sku] = content

    with open('data.json', 'w') as file:
        dump(data, file, indent=4)
        file.close()


def compare_data(sku, new_data):  # Compares the new_data and the stored_data

    # If stored_data actually holds data about sizes
    if 'variation_list' in stored_data[sku].keys():
        # If stored_data has variation_list and new_data has variation_list
        # This doesn't have an else as no update is sent if new_data doesn't have variation_list
        if 'variation_list' in new_data.keys():
            stored_variation_list = stored_data[sku]['variation_list']
            new_variation_list = new_data['variation_list']

            try:  # This try-except block is to break out of both for loops
                for variation in new_variation_list:
                    for stored_variation in stored_variation_list:
                        if variation['sku'] == stored_variation['sku']:
                            if variation['availability'] != stored_variation['availability']:
                                raise StopIteration

            except StopIteration:
                update_package = {
                    'Data': new_data['variation_list'],
                    'Info': True
                }
                send_update(sku=sku, package=update_package)

    else:
        # If stored_data doesn't have variation list but new_data does
        if 'variation_list' in new_data.keys():
            update_package = {
                'Data': new_data['variation_list'],
                'Info': True
            }
            send_update(sku=sku, package=update_package)

    update_stored_data(sku=sku, content=new_data)


def main():  # Loops through the skus and runs the appropriate functions
    for sku in skus:
        url = f'https://www.adidas.co.uk/api/products/{sku}/availability'

        response = get(url=url, headers=headers, proxies=proxies)
        content = loads(s=response.content)

        if sku in stored_data.keys():
            compare_data(sku=sku, new_data=content)
        else:
            # If sku not in data.json then add it
            update_stored_data(sku=sku, content=content)


if __name__ == '__main__':
    skus = get_skus()
    settings = get_settings()
    proxies = get_proxies()

    delay = settings['Delay']
    webhook_urls = settings['Webhook Urls']
    headers = {'User-Agent': settings['User-Agent']}
    size_prefix = settings['Size Prefix']
    currency = settings['Currency']
    currency = currency.replace('Â', '')

    while True:
        stored_data = get_data()

        def loadingAnimation(process):
            while process.is_alive():
                chars = ['.', '..', '...', '   ']
                for char in chars:
                    sys.stdout.write('\r'+'Program Running'+char)
                    time.sleep(0.4)
                    sys.stdout.flush()

        try:
            loading_process = threading.Thread(target=main)
            loading_process.start()

            loadingAnimation(loading_process)
            loading_process.join()

        except Exception as error:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)