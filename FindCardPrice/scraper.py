# -*- coding: utf-8 -*-
"""
Created on Thu Mar  6 13:32:09 2025

@author: Victor
"""
import csv
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

options = webdriver.ChromeOptions()
prefs = {'profile.default_content_setting_values': {'images': 2,  
                            'plugins': 2, 'popups': 2, 'geolocation': 2, 
                            'notifications': 2, 'auto_select_certificate': 2, 'fullscreen': 2, 
                            'mouselock': 2, 'mixed_script': 2, 'media_stream': 2, 
                            'media_stream_mic': 2, 'media_stream_camera': 2, 'protocol_handlers': 2, 
                            'ppapi_broker': 2, 'automatic_downloads': 2, 'midi_sysex': 2, 
                            'push_messaging': 2, 'ssl_cert_decisions': 2, 'metro_switch_to_desktop': 2, 
                            'protected_media_identifier': 2, 'app_banner': 2, 'site_engagement': 2, 
                            'durable_storage': 2}}
options.add_experimental_option("prefs", prefs)
#options.add_argument("--headless");
options.add_argument("disable-infobars")
options.add_argument("--disable-extensions")

def expand_shadow_element(driver, element):
    return driver.execute_script('return arguments[0].shadowRoot', element)

# === Data Extraction Functions ===
def extract_lowest_price_and_set_from_page_f2f(driver, url, name):
    try:
        name_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CLASS_NAME, "hawk-results__hawk-contentTitle"))
        )
        set_elements = WebDriverWait(driver, 2).until(
            EC.presence_of_all_elements_located(
                (By.CLASS_NAME, "hawk-results__hawk-contentSubtitle"))
        )
        price_elements = WebDriverWait(driver, 2).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//div[contains(@class, 'hawk-results__price')]//div[contains(@class, 'price-container')]//span[not(contains(@style, 'display: none'))]"))
        )
        lowest_price = None
        corresponding_set = None
        for name_element, set_element, price_element in zip(name_elements, set_elements, price_elements):  
            price_text = price_element.text.strip()
            set_text = set_element.text.strip()
            name_text = name_element.text.strip().lower()
            if price_text and set_text and name_text:
                numeric_price = float(re.sub(r'[^\d.]', '', price_text))
                if (lowest_price is None or numeric_price < lowest_price) and name_text == name:
                    lowest_price = numeric_price
                    corresponding_set = set_text
        return (lowest_price, corresponding_set)
    except Exception as e:
        print(f"Error on page {url}: {e}")
        return (None, None)

def extract_lowest_price_and_set_from_page_401(driver, url, name):
    try:
        shadow_host = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div#fast-simon-serp-app"))
        )
        shadow_root = expand_shadow_element(driver, shadow_host)
        root = shadow_root.find_element(By.CSS_SELECTOR, "#fs-serp-page")
        filters_grid_wrapper = root.find_element(By.CSS_SELECTOR, "div.fs-result-page-1401w5l.filters-grid-wrapper")
        products_grid = filters_grid_wrapper.find_element(By.CSS_SELECTOR, "#products-grid")
        product_cards = products_grid.find_elements(By.CSS_SELECTOR, "div.product-card.fs-results-product-card.fs-product-card.fs-result-page-nxn4j1.product-card-border-hover.fs-product-has-compare-price")
        lowest_price = None
        corresponding_set = None
        for card in product_cards:
            name_element = card.find_element(By.CSS_SELECTOR, "span.product-title-search-term")
            set_element = card.find_element(By.CSS_SELECTOR, "div.vendor.fs-product-vendor")
            price_element = card.find_element(By.CSS_SELECTOR, "div.price.fs-result-page-1a37dw5")
            if name_element and set_element and price_element:
                name_text = name_element.text.strip().lower()
                set_text = set_element.text.strip()
                price_text = price_element.text.strip()
                if "art series" not in set_text.lower():
                    numeric_price = float(re.sub(r'[^\d.]', '', price_text))
                    if (lowest_price is None or numeric_price < lowest_price) and name_text == name:
                        lowest_price = numeric_price
                        corresponding_set = set_text
        return (lowest_price, corresponding_set)
    except Exception as e:
        print(f"Error on page {url}: {e}")
        return (None, None)

def extract_lowest_price_and_set_from_page_fg(driver, url, name):
    try:
        card_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CLASS_NAME, "productCard__card"))
        )
        lowest_price = None
        corresponding_set = None
        name_length = len(name)
        for card_element in card_elements:
            name_element = card_element.find_element(By.CLASS_NAME, "productCard__title")
            set_element = card_element.find_element(By.CLASS_NAME, "productCard__setName")
            price_element = card_element.find_element(By.CLASS_NAME, "money")
            price_text = price_element.text.strip()
            set_text = set_element.text.strip()
            name_text = name_element.text.strip().lower()
            name_prefix = name_text[:name_length]
            out_of_stock_elements = name_element.find_elements(By.XPATH, "../following-sibling::div[contains(@class, 'productCard__button--outOfStock')]")
            add_to_cart_elements = name_element.find_elements(By.XPATH, "../following-sibling::form[contains(@class, 'product-item__action-list')]")
            is_out_of_stock = any(out_of_stock_element.is_displayed() for out_of_stock_element in out_of_stock_elements)
            is_in_stock = any(add_to_cart_element.is_displayed() for add_to_cart_element in add_to_cart_elements)
            if price_text and set_text and name_text and name_prefix == name and not is_out_of_stock and is_in_stock:
                product_type = card_element.get_attribute("data-producttype")
                if product_type != "Yugioh Single":
                    numeric_price = float(re.sub(r'[^\d.]', '', price_text))
                    if lowest_price is None or numeric_price < lowest_price:
                        lowest_price = numeric_price
                        corresponding_set = set_text
        return (lowest_price, corresponding_set)
    except Exception as e:
        print(f"Error on page {url}: {e}")
        return (None, None)
    
def extract_lowest_price_and_set_from_page_firstplayer(driver, url, name):
    try:
        card_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CLASS_NAME, "variant-row row"))
        
        )
    except Exception as e:
        print(f"Error on page {url}: {e}")
        return (None, None)
    
# === URL Construction Functions ===
def construct_url_f2f(card_name):
    base_url = "https://www.facetofacegames.com/search/?keyword="
    formatted_name = card_name.replace(
        '/', '%2F').replace("'", '%27').replace(',', '%2C').replace(' ', '%20')
    return f"{base_url}{formatted_name}&sort=priceasc&pg=1&child_inventory_level=1&general%20brand=Magic%3A%20The%20Gathering"

def construct_url_fg(card_name):
    base_url = "https://fusiongamingonline.com/search?page=1&q=%2A"
    formatted_name = card_name.replace(
        '/', '%2F').replace("'", '%27').replace(',', '%2C').replace(' ', '%20')
    return f"{base_url}{formatted_name}%2A"
    
def construct_url_401(card_name):
    base_url = "https://store.401games.ca/pages/search-results?q="
    formatted_name = card_name.replace("'", '%27').replace(' ', '+')
    return f"{base_url}{formatted_name}&filters=In+Stock,True,Category,Magic:+The+Gathering+Singles&search={formatted_name}"

def construct_url_FirstPlayer(card_name):
    base_url = "https://www.firstplayer.ca/products/search?q="
    formatted_name = card_name.replace("'", '%27').replace(' ', '+')
    return f"{base_url}{formatted_name}"

# === CSV Functions ===
def read_card_names(csv_file):
    card_names = []
    with open(csv_file, mode='r', newline='') as file:
        reader = csv.reader(file)
        for row in reader:
            if row:
                card_names.append(row[0].replace('1 ', '').lower())
    return card_names


def write_lowest_price(card_name, lowest_price, set_name, url, csv_file):
    with open(csv_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([card_name, lowest_price, set_name, url])

# === Main Function ===
def main():
    cards_csv_file = 'card_names.csv'
    output_csv_file = 'card_lowest_prices.csv'
    card_names = read_card_names(cards_csv_file)
    sites = {
        1: (construct_url_f2f, extract_lowest_price_and_set_from_page_f2f), #FacetoFaceGames
        2: (construct_url_fg, extract_lowest_price_and_set_from_page_fg), #FusionGaming
        3: (construct_url_401, extract_lowest_price_and_set_from_page_401) #401Games
    }
    with open(output_csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Card Name", "Lowest Price", "Set", "URL"])
    driver = webdriver.Chrome(options=options)
    for card_name in card_names:
        lowest_price = None
        corresponding_set = None
        corresponding_url = None
        handles = {}
        for site, (construct_url, _) in sorted(sites.items(), reverse=True):
            url = construct_url(card_name)
            if not handles:
                driver.get(url)
                handles[site] = (driver.current_window_handle, url)
            else:
                driver.execute_script("window.open('');")
                driver.switch_to.window(driver.window_handles[-1])
                handles[site] = (driver.current_window_handle, url)
                driver.get(url)
        time.sleep(0.5)
        for site, (_, extract_info) in sites.items():
            driver.switch_to.window(handles[site][0])
            price, set_name = extract_info(driver, handles[site][1], card_name)
            if price is not None and (lowest_price is None or price < lowest_price):
                lowest_price = price
                corresponding_set = set_name
                corresponding_url = handles[site][1]
        write_lowest_price(card_name, lowest_price, corresponding_set, corresponding_url, output_csv_file)
        for handle in list(handles.values())[:-1]:
            driver.switch_to.window(handle[0])
            driver.close()
        driver.switch_to.window(driver.window_handles[-1])
    driver.quit()
    
if __name__ == '__main__':
    main()