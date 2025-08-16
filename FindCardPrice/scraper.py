# -*- coding: utf-8 -*-
"""
Created on Thu Mar  6 13:32:09 2025

@author: Victor
"""
import csv
import re
import time
import sqlite3
import subprocess
import sys

required_packages = ['selenium', 'beautifulsoup4']
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        print(f"Package '{package}' is not installed. Installing now...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        print(f"Package '{package}' has been installed successfully.")

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

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
options.page_load_strategy = 'none'
options.add_argument("--headless");
options.add_argument("disable-infobars")
options.add_argument("--disable-extensions")

# === Sqlite Functions ===
def initialize_database():
    with sqlite3.connect('card_prices.sqlite') as connection:
        cursor = connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_name TEXT NOT NULL,
                lowest_price REAL NOT NULL,
                card_set TEXT NOT NULL,
                url TEXT NOT NULL,
                date_added DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        connection.commit()

def insert_or_update_card_data(card_name, lowest_price, card_set, url):
    with sqlite3.connect('card_prices.sqlite') as connection:
        cursor = connection.cursor()
        cursor.execute('''
            SELECT id FROM cards
            WHERE card_name = ? AND date_added < DATETIME('now', '-1 day')
        ''', (card_name,))
        result = cursor.fetchone()
        if result:
            cursor.execute('''
                UPDATE cards
                SET lowest_price = ?, card_set = ?, url = ?, date_added = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (lowest_price, card_set, url, result[0]))
        else:
            cursor.execute('''
                INSERT INTO cards (card_name, lowest_price, card_set, url)
                VALUES (?, ?, ?, ?)
            ''', (card_name, lowest_price, card_set, url))
        connection.commit()

def card_exists_recently(connection, card_name):
    cursor = connection.cursor()
    cursor.execute('''
        SELECT card_name, lowest_price, card_set, url
        FROM cards
        WHERE card_name = ? AND date_added >= DATETIME('now', '-1 day')
    ''', (card_name,))
    result = cursor.fetchone()
    return result

# === Data Extraction Functions ===
def extract_lowest_price_and_set_from_page_f2f(driver, url, name):
    lowest_price = None
    corresponding_set = None
    corresponding_url = None
    try:
        card_elements = driver.find_elements(By.CSS_SELECTOR, "div.bb-card-wrapper")
        for card_element in card_elements:
            name_element = card_element.find_element(By.CSS_SELECTOR, "div.bb-card-title")
            set_element = card_element.find_element(By.CSS_SELECTOR, "div.bb-card-vendor span")
            price_element = card_element.find_element(By.CSS_SELECTOR, "div.price__regular span.price-item--regular span:nth-child(3)")
            name_text = name_element.text.strip().lower()
            set_text = set_element.text.strip().lower()
            price_text = price_element.text.strip()
            if (price_text and "art series" not in set_text and (name_text == name or re.match(rf"^{re.escape(name)}(?:\s[-(]|$)", name_text))):
                    numeric_price = float(re.sub(r'[^\d.]', '', price_text))
                    if (lowest_price is None or numeric_price < lowest_price):
                        lowest_price = numeric_price
                        corresponding_set = set_text
                        url_element = card_element.find_element(By.CSS_SELECTOR, "div.bb-card-img a")
                        corresponding_url = url_element.get_attribute('href')
        return (lowest_price, corresponding_set, corresponding_url)
    except Exception as e:
        print(f"Error on page {url}: {e}")
        return (lowest_price, corresponding_set, corresponding_url)

def extract_lowest_price_and_set_from_page_401(driver, url, name):
    lowest_price = None
    corresponding_set = None
    corresponding_url = None
    try:
        shadow_host = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div#fast-simon-serp-app"))
        )
        shadow_root = driver.execute_script('return arguments[0].shadowRoot', shadow_host)
        card_elements = shadow_root.find_elements(By.CSS_SELECTOR, "div.product-card.fs-results-product-card.fs-product-card")
        for card_element in card_elements:
            name_element = card_element.find_element(By.CSS_SELECTOR, "span.title.fs-product-title.fs-result-page-mihllj")
            set_element = card_element.find_element(By.CSS_SELECTOR, "div.vendor.fs-product-vendor")
            price_element = card_element.find_element(By.CSS_SELECTOR, "div.price.fs-result-page-1a37dw5")
            name_text = name_element.get_attribute('aria-label').strip().lower()
            set_text = set_element.text.strip().lower()
            price_text = price_element.text.strip()
            if (price_text and "art series" not in set_text and (name_text == name or re.match(rf"^{re.escape(name)}(?:\s[-(]|$)", name_text))):
                numeric_price = float(re.sub(r'[^\d.]', '', price_text))
                if (lowest_price is None or numeric_price < lowest_price):
                    lowest_price = numeric_price
                    corresponding_set = set_text
                    url_element = card_element.find_element(By.CSS_SELECTOR, "a.fs-product-main-image-wrapper ")
                    corresponding_url = url_element.get_attribute('href')
        return (lowest_price, corresponding_set, corresponding_url)
    except Exception as e:
        print(f"Error on page {url}: {e}")
        return (lowest_price, corresponding_set, corresponding_url)

def extract_lowest_price_and_set_from_page_fg(driver, url, name):
    lowest_price = None
    corresponding_set = None
    corresponding_url = None
    try:
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        card_elements = soup.select('div.collectionGrid div.productCard__card[data-producttype="MTG Single"]')
        for card_element in card_elements:
            if not card_element.select(".productCard__button--outOfStock"):
                set_element = card_element.select_one("div.productCard__lower p.productCard__setName")
                name_element = card_element.select_one("div.productCard__lower p.productCard__title")
                price_element = card_element.select_one("div.productCard__lower p.productCard__price span.money")
                if not set_element or not name_element or not price_element:
                    continue
                price_text = price_element.text.strip()
                set_text = set_element.text.strip().lower()
                name_text = name_element.text.strip().lower()
                if (price_text and (name_text == name or re.match(rf"^{re.escape(name)}(?:\s[-(]|$)", name_text))):
                        numeric_price = float(re.sub(r'[^\d.]', '', price_text))
                        if lowest_price is None or numeric_price < lowest_price:
                            lowest_price = numeric_price
                            corresponding_set = set_text
                            url_element = card_element.find('a', href=True)
                            url_link = url_element.get("href")
                            corresponding_url = f"https://fusiongamingonline.com{url_link}"
        return (lowest_price, corresponding_set, corresponding_url)
    except Exception as e:
        print(f"Error on page {url}: {e}")
        return (lowest_price, corresponding_set, corresponding_url)
    
def extract_lowest_price_and_set_from_page_firstplayer(driver, url, name):
    lowest_price = None
    corresponding_set = None
    corresponding_url = None
    try:
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        card_elements = soup.select('div.products-container li.product.enable-msrp')
        for card_element in card_elements:
            form_element = card_element.find('form', class_='add-to-cart-form')
            if form_element:
                url_element = card_element.find('a', href=True)
                url_link = url_element.get("href")
                if(url_link[9:14] == "magic"):
                    name_text = form_element.get('data-name', '').strip().lower()
                    price_text = form_element.get('data-price', '').strip()
                    set_text = form_element.get('data-category', '').strip().lower()
                    if (price_text and "art series" not in set_text and (name_text == name or re.match(rf"^{re.escape(name)}(?:\s[-(]|$)", name_text))):
                            numeric_price = float(re.sub(r'[^\d.]', '', price_text))
                            if (lowest_price is None or numeric_price < lowest_price):
                                corresponding_url = f"https://www.firstplayer.ca{url_link}"
                                lowest_price = numeric_price
                                corresponding_set = set_text        
        return (lowest_price, corresponding_set, corresponding_url)
    except Exception as e:
        print(f"Error on page {url}: {e}")
        return (lowest_price, corresponding_set, corresponding_url)

def extract_lowest_price_and_set_from_page_comichunter(driver, url, name):
    lowest_price = None
    corresponding_set = None
    corresponding_url = None
    try:
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        card_elements = soup.select('div.products-container li.product.enable-msrp')
        for card_element in card_elements:
            form_element = card_element.find('form', class_='add-to-cart-form')
            if form_element:
                url_element = card_element.find('a', href=True)
                url_link = url_element.get("href")
                if(url_link[9:14] == "magic"):
                    name_text = form_element.get('data-name', '').strip().lower()
                    price_text = form_element.get('data-price', '').strip()
                    set_text = form_element.get('data-category', '').strip().lower()
                    if (price_text and "art series" not in set_text and (name_text == name or re.match(rf"^{re.escape(name)}(?:\s[-(]|$)", name_text))):
                            numeric_price = float(re.sub(r'[^\d.]', '', price_text))
                            if (lowest_price is None or numeric_price < lowest_price):
                                corresponding_url = f"https://comichunter.crystalcommerce.com{url_link}"
                                lowest_price = numeric_price
                                corresponding_set = set_text
        return (lowest_price, corresponding_set, corresponding_url)
    except Exception as e:
        print(f"Error on page {url}: {e}")
        return (lowest_price, corresponding_set, corresponding_url)

def extract_lowest_price_and_set_from_page_gauntletgames(driver, url, name):
    lowest_price = None
    corresponding_set = None
    corresponding_url = None
    try:
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        card_elements = soup.select('div.products-container li.product.enable-msrp')
        for card_element in card_elements:
            not_in_stock = card_element.find('div', class_='variant-row no-stock')
            not_in_stock2 = card_element.find('div', class_='variant-row row no-stock')
            if not not_in_stock and not not_in_stock2:
                form_element = card_element.find('form', class_='add-to-cart-form')
                if form_element:
                    url_element = card_element.find('a', href=True)
                    url_link = url_element.get("href")
                    if(url_link[9:14] == "magic"):
                        name_text = form_element.get('data-name', '').strip().lower()
                        price_text = form_element.get('data-price', '').strip()
                        set_text = form_element.get('data-category', '').strip().lower()
                        if (price_text and "art series" not in set_text and (name_text == name or re.match(rf"^{re.escape(name)}(?:\s[-(]|$)", name_text))):
                                numeric_price = float(re.sub(r'[^\d.]', '', price_text))
                                if (lowest_price is None or numeric_price < lowest_price):
                                    corresponding_url = f"https://www.gauntletgamesvictoria.ca{url_link}"
                                    lowest_price = numeric_price
                                    corresponding_set = set_text
        return (lowest_price, corresponding_set, corresponding_url)
    except Exception as e:
        print(f"Error on page {url}: {e}")
        return (lowest_price, corresponding_set, corresponding_url)

def extract_lowest_price_and_set_from_page_fanofthesport(driver, url, name):
    lowest_price = None
    corresponding_set = None
    corresponding_url = None
    try:
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        card_elements = soup.select('div.collectionGrid div.productCard__card[data-producttype="MTG Single"]')
        for card_element in card_elements:
            if not card_element.select(".productCard__button--outOfStock"):
                set_element = card_element.select_one("div.productCard__lower p.productCard__setName")
                name_element = card_element.select_one("div.productCard__lower p.productCard__title")
                price_element = card_element.select_one("div.productCard__lower p.productCard__price")
                if not set_element or not name_element or not price_element:
                    continue
                price_text = price_element.text.strip()
                set_text = set_element.text.strip().lower()
                name_text = name_element.text.strip().lower()
                if (price_text and (name_text == name or re.match(rf"^{re.escape(name)}(?:\s[-(]|$)", name_text))):
                        numeric_price = float(re.sub(r'[^\d.]', '', price_text))
                        if lowest_price is None or numeric_price < lowest_price:
                            lowest_price = numeric_price
                            corresponding_set = set_text
                            url_element = card_element.find('a', href=True)
                            url_link = url_element.get("href")
                            corresponding_url = f"https://fanofthesport.com{url_link}"
        return (lowest_price, corresponding_set, corresponding_url)
    except Exception as e:
        print(f"Error on page {url}: {e}")
        return (lowest_price, corresponding_set, corresponding_url)

def extract_lowest_price_and_set_from_page_trinityhobby(driver, url, name):
    lowest_price = None
    corresponding_set = None
    corresponding_url = None
    try:
        try:
            shadow_host = driver.find_element(By.CSS_SELECTOR, "form-embed#app-embed-container-226716")
            if shadow_host:
                shadow_root = driver.execute_script('return arguments[0].shadowRoot', shadow_host)
                button = shadow_root.find_element(By.CSS_SELECTOR, "span._formCloseButton_1684x_4")
                if button:
                    button.click()
        except Exception:
            pass
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        card_elements = soup.select('div.usf-results.usf-clear.usf-grid div.usf-sr-product.usf-grid__item')
        for card_element in card_elements:
            name_element = card_element.select_one("div.usf-title a")
            price_element = card_element.select_one("div.usf-price-wrapper span.usf-price")
            if not name_element or not price_element:
                continue
            full_text = name_element.text
            if "[" in full_text and "]" in full_text:
                set_text = full_text[full_text.index("[") + 1:full_text.index("]")].strip().lower()
                name_part = full_text[:full_text.index("[")].strip()
                name_text = name_part.split("(")[0].strip().lower()
            else:
                name_text = full_text.strip().lower()
                set_text = None
            price_text = price_element.text.strip()
            if (price_text and (name_text == name or re.match(rf"^{re.escape(name)}(?:\s[-(]|$)", name_text))):
                    numeric_price = float(re.sub(r'[^\d.]', '', price_text))
                    if lowest_price is None or numeric_price < lowest_price:
                        lowest_price = numeric_price
                        corresponding_set = set_text
                        url_element = card_element.find('a', href=True)
                        url_link = url_element.get("href")
                        corresponding_url = f"https://trinityhobby.com{url_link}"
        return (lowest_price, corresponding_set, corresponding_url)
    except Exception as e:
        print(f"Error on page {url}: {e}")
        return (lowest_price, corresponding_set, corresponding_url)

def extract_lowest_price_and_set_from_page_legendarycollectables(driver, url, name):
    lowest_price = None
    corresponding_set = None
    corresponding_url = None
    try:
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        card_elements = soup.select('div.productgrid--items div.productgrid--item')
        for card_element in card_elements:
            name_element = card_element.select_one("h2.productitem--title a")
            price_element = card_element.select_one("div.price__current span.money[data-price-max]")
            if not name_element or not price_element:
                continue
            full_text = name_element.text
            if "[" in full_text and "]" in full_text:
                set_text = full_text[full_text.index("[") + 1:full_text.index("]")].strip().lower()
                name_part = full_text[:full_text.index("[")].strip()
                name_text = name_part.split("(")[0].strip().lower()
            else:
                name_text = full_text.strip().lower()
                set_text = None
            price_text = price_element.text.strip()
            if (price_text and (name_text == name or re.match(rf"^{re.escape(name)}(?:\s[-(]|$)", name_text))):
                    numeric_price = float(re.sub(r'[^\d.]', '', price_text))
                    if lowest_price is None or numeric_price < lowest_price:
                        lowest_price = numeric_price
                        corresponding_set = set_text
                        url_link = name_element.get("href")
                        corresponding_url = f"https://legendarycollectables.com{url_link}"
        return (lowest_price, corresponding_set, corresponding_url)
    except Exception as e:
        print(f"Error on page {url}: {e}")
        return (lowest_price, corresponding_set, corresponding_url)
    
# === URL Construction Functions ===
def construct_url_f2f(card_name):
    base_url = "https://facetofacegames.com/search?q="
    formatted_name = card_name.replace("'", '%27').replace(',', '%2C').replace(' ', '+')
    return f"{base_url}{formatted_name}&filter__Product+Type=Singles&filter__Game=Magic%3A+The+Gathering&filter__Availability=In+Stock&sort_by=best"

def construct_url_fg(card_name):
    base_url = "https://fusiongamingonline.com/search?page=1&q=%2A"
    formatted_name = card_name.replace(
        '/', '%2F').replace("'", '%27').replace(',', '%2C').replace(' ', '%20')
    return f"{base_url}{formatted_name}%2A"
    
def construct_url_401(card_name):
    base_url = "https://store.401games.ca/pages/search-results?q="
    formatted_name = card_name.replace("'", '%27').replace(' ', '+')
    return f"{base_url}{formatted_name}&filters=In+Stock,True,Category,Magic:+The+Gathering+Singles&search={formatted_name}"

def construct_url_firstplayer(card_name):
    base_url = "https://www.firstplayer.ca/products/search?q="
    formatted_name = card_name.replace("'", '%27').replace(',', '%2C').replace(' ', '+')
    return f"{base_url}{formatted_name}"

def construct_url_comichunter(card_name):
    base_url = "https://comichunter.crystalcommerce.com/products/search?q="
    formatted_name = card_name.replace("'", '%27').replace(',', '%2C').replace(' ', '+')
    return f"{base_url}{formatted_name}&c=1"

def construct_url_gauntletgames(card_name):
    base_url = "https://www.gauntletgamesvictoria.ca/products/search?q="
    formatted_name = card_name.replace("'", '%27').replace(',', '%2C').replace(' ', '+')
    return f"{base_url}{formatted_name}&c=1"

def construct_url_fanofthesport(card_name):
    base_url = "https://fanofthesport.com/search?page=1&q=%2A"
    formatted_name = card_name.replace(
        '/', '%2F').replace("'", '%27').replace(',', '%2C').replace(' ', '%20')
    return f"{base_url}{formatted_name}%2A"

def construct_url_trinityhobby(card_name):
    base_url = "https://trinityhobby.com/search?options%5Bprefix%5D=last&q="
    formatted_name = card_name.replace(
        '/', '%2F').replace("'", '%27').replace(',', '%2C').replace(' ', '%20')
    return f"{base_url}{formatted_name}&uff_68z6r3_stockStatus=1&uff_ej1dei_vendor=Magic%3A%20The%20Gathering&uff_tdso15_productType=MTG%20Single&usf_sort=price"

def construct_url_legendarycollectables(card_name):
    base_url = "https://legendarycollectables.com/search?filter.v.availability=1&q="
    formatted_name = card_name.replace("'", '%27').replace(',', '%2C').replace(' ', '+')
    return f"{base_url}{formatted_name}"

# === CSV Functions ===
def read_card_names(csv_file):
    card_names = []
    with open(csv_file, mode='r', newline='') as file:
        reader = csv.reader(file)
        for row in reader:
            if row:
                for x in range(9):
                    val = f"{x+1} "
                    if row[0][:2] == val:
                        row[0] = row[0][2:]
                        break
                card_names.append(row[0].lower())
    return card_names

def write_lowest_price(card_name, lowest_price, set_name, url, csv_file):
    with open(csv_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([card_name, lowest_price, set_name, url])

# === Main Function ===
def main():
    initialize_database()
    driver = webdriver.Chrome(options=options)
    cards_csv_file = 'card_names.csv'
    output_csv_file = 'card_lowest_prices.csv'
    card_names = read_card_names(cards_csv_file)
    sites = {
        1: (construct_url_fanofthesport, extract_lowest_price_and_set_from_page_fanofthesport), #FanofTheSport
        2: (construct_url_f2f, extract_lowest_price_and_set_from_page_f2f), #FacetoFaceGames
        3: (construct_url_fg, extract_lowest_price_and_set_from_page_fg), #FusionGaming 
        4: (construct_url_comichunter, extract_lowest_price_and_set_from_page_comichunter), #ComicHunter
        5: (construct_url_gauntletgames, extract_lowest_price_and_set_from_page_gauntletgames), #GauntletGames
        6: (construct_url_legendarycollectables, extract_lowest_price_and_set_from_page_legendarycollectables), #LegendaryCollectables
        7: (construct_url_trinityhobby, extract_lowest_price_and_set_from_page_trinityhobby), #TrinityHobby
        8: (construct_url_firstplayer, extract_lowest_price_and_set_from_page_firstplayer), #FirstPlayer
        9: (construct_url_401, extract_lowest_price_and_set_from_page_401) #401Games
    }
    with open(output_csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Card Name", "Lowest Price", "Set", "URL"])
    try:
        connection = sqlite3.connect('card_prices.sqlite')
        for card_name in card_names:
            recent_card = card_exists_recently(connection, card_name)
            if recent_card:
                print(f"{card_name} already in database")
                write_lowest_price(*recent_card, output_csv_file)
                continue
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
            time.sleep(1)
            for site, (_, extract_info) in sites.items():
                driver.switch_to.window(handles[site][0])
                price, set_name, url = extract_info(driver, handles[site][1], card_name)
                print(f"INFO:{card_name}, {price}, {url}")
                if price is not None and (lowest_price is None or price < lowest_price):
                    lowest_price = price
                    corresponding_set = set_name
                    corresponding_url = url
            if lowest_price is not None:
                insert_or_update_card_data(card_name, lowest_price, corresponding_set, corresponding_url)
                write_lowest_price(card_name, lowest_price, corresponding_set, corresponding_url, output_csv_file)
                print(f"{card_name}, {lowest_price}, {corresponding_url}")
            for handle in list(handles.values())[:-1]:
                driver.switch_to.window(handle[0])
                driver.close()
            driver.switch_to.window(driver.window_handles[-1])
    finally:
        driver.quit()
        connection.close()
    
if __name__ == '__main__':
    main()
    print("Done!")