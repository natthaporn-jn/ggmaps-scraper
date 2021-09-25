import streamlit as st
from selenium import webdriver
import time
import io
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common import keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome import options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import re
import urllib.parse
import base64
import datetime
import os
import json
import html

@st.cache(allow_output_mutation=True)
class Scaper:
    def __init__(self, input_URL, max_reviews=None):
        self.PAGE_URL = input_URL
        self.MAX_NUM_REVIEW = max_reviews

    def split_translated_text(self, text_list, original_arg='(ต้นฉบับ)', translated_arg='(แปลโดย Google)'):
        original_text = []
        translated_text = []
        for text in text_list:
            text = str(text).replace('\n', ' ')
            try:
                if text.startswith(translated_arg):
                    splited = text.split(original_arg)
                    translated_text.append(splited[0].replace(translated_arg, '').lstrip(' '))
                    original_text.append(splited[1].lstrip(' '))
                elif text.startswith(original_arg):
                    splited = text.split(translated_arg)
                    original_text.append(splited[0].replace(original_arg, '').lstrip(' '))
                    translated_text.append(splited[1].lstrip(' '))
            except Exception as e:
                print(e)
        print("Number of Original text: {}".format(len(original_text)))
        print("Number of Translated text: {}".format(len(translated_text)))
        return original_text, translated_text

    def scraper(self):
        #load chrome driver
        option = webdriver.ChromeOptions()
        option.add_argument('headless')
        option.add_argument('--incognito')
        browser = webdriver.Chrome(options=option,
                                    executable_path="/home/appuser/.conda/bin/geckodriver")
        browser.get(self.PAGE_URL)
        actions = ActionChains(browser)
        browser.maximize_window()
        time.sleep(3)

        #get total number of reviews on page
        num_reviews = browser.find_element_by_css_selector('button.widget-pane-link')
        max_num_review = int(re.findall(r'\d+', num_reviews.text)[0])
        if self.MAX_NUM_REVIEW == None:
            self.MAX_NUM_REVIEW = max_num_review
        #go to all reviews page
        num_reviews.click()
        time.sleep(2)

        #scrape all the reviews
        reviews = []
        div = browser.find_element_by_xpath('//div[contains(@class, "section-scrollbox")]')
        for i in range(max_num_review):
            print(i)
            browser.execute_script("arguments[0].scrollBy(0, 500)", div)
            time.sleep(2)

        print(len(browser.find_elements_by_xpath('//span[contains(@class, "text")]')))

        jsl_tags = browser.find_elements_by_xpath('//button[@aria-label="ดูเพิ่มเติม"]')
        # jsl_tags = browser.find_elements_by_css_selector('button.ODSEW-KoToPc-ShBeI.gXqMYb-hSRGPd')
        for tag in jsl_tags:
            tag.click()

        time.sleep(3)

        reviews.extend([review.get_attribute('innerHTML') for review in browser.find_elements_by_xpath('//span[contains(@class, "text")]')])
        # this_page_review = [review.get_attribute('innerHTML') for review in browser.find_elements_by_xpath('.//span[@class="ODSEW-ShBeI-text"]')]
        print(len(reviews))

        #clean reviews 
        reviews = list(map(lambda x: html.unescape(str(x).replace('\n', ' ')), reviews))

        #split original text from translated one
        self.ORIGINAL_TEXT, self.TRANSLATED_TEXT = self.split_translated_text(reviews)

        self.REVIEW = reviews
        return self.REVIEW
    
    def writer(self, type='csv', reviews='all'):
        self.dir = '/tmp/'
        if type == 'txt':
            if reviews == 'all':
                with open(self.dir+'/data.txt', 'w') as file:
                    for line in self.REVIEW:
                        file.write(line)
                        file.write('\n')
            elif reviews == 'original':
                with open(self.dir+'/original_data.txt', 'w') as file:
                    for line in self.ORIGINAL_TEXT:
                        file.write(line)
                        file.write('\n')
            elif reviews == 'translated':
                with open(self.dir+'/translated_data.txt', 'w') as file:
                    for line in self.TRANSLATED_TEXT:
                        file.write(line)
                        file.write('\n')
        elif type == 'csv':
            if reviews == 'all':
                review_to_write = pd.DataFrame()
                review_to_write['reviews'] = self.REVIEW
                return review_to_write.to_csv('data.csv')
            elif reviews == 'original':
                review_to_write = pd.DataFrame()
                review_to_write['reviews'] =self.ORIGINAL_TEXT
                return review_to_write.to_csv('original_data.csv')
            elif reviews == 'translated':
                review_to_write = pd.DataFrame()
                review_to_write['reviews'] =self.ORIGINAL_TEXT
                return review_to_write.to_csv('translated_data.csv')
            
                


### build streamlit app ###
st.set_page_config(
    page_icon='📺',
    page_title='''what's on your google maps'''
)
st.write("# Extract Reviews from Google Maps")
input_url = st.text_input("insert url of google maps page here", key="url")
if st.button("start"):
    with st.spinner('proceeding ..'):

        #remove all previous files in data directory
        try:
            dir = '/tmp/'
            for file in os.listdir(dir):
                if file != 'docs.txt':
                    os.remove(os.path.join(dir, file))
        except Exception as e:
            print(e)

        #extract title and spatial location
        url_elements = st.session_state.url.split('/')
        place_title = urllib.parse.unquote_plus(url_elements[5])
        gps_location = url_elements[6].split(',')

        st.write("scraping " + place_title)
        
        scr = Scaper(st.session_state.url)
        this_review = scr.scraper()

    st.success("found "+ str(len(this_review)) + " reviews")

    st.write('select your choice of data to download')
    if len(scr.ORIGINAL_TEXT) > 0:
        st.download_button(label='ALL REVIEWS',
                            data=scr.writer(type='csv', reviews='all'),
                            file_name=f"reviews_data_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                            mime='text/csv')
        st.download_button(label='ORIGINAL REVIEWS',
                            data=scr.writer(type='csv', reviews='original'),
                            file_name=f"original_reviews_data_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                            mime='text/csv')
        st.download_button(label='TRANSLATED  REVIEWS',
                            data=scr.writer(type='csv', reviews='translated'),
                            file_name=f"translaterd_reviews_data_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                            mime='text/csv')

       