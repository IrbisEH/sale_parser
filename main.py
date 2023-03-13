import copy

from bs4 import BeautifulSoup
import requests
from datetime import datetime
import time
import os
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv('.env')

DIR = os.path.abspath(os.path.dirname(__file__))

SLEEP = 60 * 60 * 6
# SLEEP = 15

USERS = {
    'USER_1': int(os.getenv('USER_1_ID')),
    'USER_2': int(os.getenv('USER_2_ID'))
}
main_dic = {
    'artur_orlov_all': 'https://liveclasses.ru/bundle/artur_orlov_all/'
}


def get_parse_courses_dic():
    courses_dic = copy.deepcopy(main_dic)
    page = requests.get(main_dic['artur_orlov_all'])
    soup = BeautifulSoup(page.text, "html.parser")
    links = soup.findAll('a', class_='workshop__link')
    for link in links:
        link = f'https://liveclasses.ru{link["href"]}'
        course_id = link.split('/')[-2]
        courses_dic[course_id] = link
    return courses_dic


def get_user_id(username):

    async def get_channel_id_by_name_from_dialogs(username):
        async for dialog in client.iter_dialogs():
            if username in dialog.name:
                return dialog.name, dialog.entity.id

    client = TelegramClient('session', int(os.getenv('API_ID')), str(os.getenv('API_HASH')))

    with client:
        return client.loop.run_until_complete(get_channel_id_by_name_from_dialogs(username))


def send_message(user, text):

    async def send(user, text):
        await client.send_message(user, text)

    client = TelegramClient('session', int(os.getenv('API_ID')), str(os.getenv('API_HASH')))

    with client:
        client.loop.run_until_complete(send(user, text))


class Course:
    def __init__(self, course_id, url):
        self.url = url
        self.course_id = course_id
        self.save_file_path = os.path.join(DIR, 'course_info', f'{self.course_id}.txt')
        self.soup = self.get_soup()
        self.title = self.get_title()
        self.start_time_sale = self.get_start_time()
        self.end_time_sale = self.get_end_time()
        self.price = self.get_current_price()

    def get_soup(self):
        try:
            page = requests.get(self.url)
            return BeautifulSoup(page.text, "html.parser")
        except Exception as e:
            date = datetime.now().strftime('%d-%m-%Y %H:%M')
            text = f'{date} - error -> {e}'
            print(text)
            send_message(USERS['USER_1'], text)
            return None

    def get_title(self):
        if self.soup is None:
            return None
        return self.soup.title.text

    def get_start_time(self):
        try:
            sale_time = self.soup.find('div', class_='countdown countdown_workshop')
            start_time = datetime.fromtimestamp(int(sale_time['data-start_timestamp']))
            return start_time.strftime('%d-%m-%Y %H:%M')
        except Exception:
            return None

    def get_end_time(self):
        try:
            sale_time = self.soup.find('div', class_='countdown countdown_workshop')
            end_time = datetime.fromtimestamp(int(sale_time['data-end_timestamp']))
            return end_time.strftime('%d-%m-%Y %H:%M')
        except Exception:
            return None

    def get_current_price(self):
        if self.soup is None:
            return None
        # price = self.soup.find('form', class_='js-metrika-basket')
        prices = self.soup.findAll('span', class_='rouble')
        price_min = None
        for price in prices:
            if price_min is None or int(price.text) < price_min:
                price_min = int(price.text)

        return price_min

    def print_self_info(self):
        print(f'course_id: {self.course_id}')
        print(f'save file path: {self.save_file_path}')
        print(f'title: {self.title}')
        print(f'start_time_sale: {self.start_time_sale}')
        print(f'end_time_sale: {self.end_time_sale}')
        print(f'price: {self.price}')

    def save_current_info(self):
        date = datetime.now().strftime('%d-%m-%Y %H:%M')
        with open(self.save_file_path, 'a') as file:
            save_text = f'{date};{self.course_id};{self.title};{self.start_time_sale};{self.end_time_sale};{self.price}\n'
            file.write(save_text)

    def get_message_text(self):
        text = 'ИЗМЕНЕНИЕ ЦЕНЫ\n'
        text += f'курс: {self.title}\n'
        text += f'цена: {self.price}\n'
        text += '____________\n'
        text += self.url
        return text

    def check_price(self):
        if self.price is None:
            date = datetime.now().strftime('%d-%m-%Y %H:%M')
            text = f'{date} - Not found price at {self.url}'
            send_message(USERS['USER_1'], text)
            return
        if os.path.isfile(self.save_file_path):
            with open(self.save_file_path, 'r') as file:
                last_price = int(file.read().splitlines()[-1].split(';')[-1])
            if self.price < last_price:
                for user in USERS.values():
                    send_message(user, self.get_message_text())
        self.save_current_info()


if __name__ == '__main__':
    while True:
        print('Start loop'.center(40, '-'))
        course_dic = get_parse_courses_dic()
        for course_id, url in course_dic.items():
            print(f'-> check {course_id}')
            print(url)
            course = Course(course_id, url)
            course.check_price()
        print('End loop'.center(40, '-'))
        time.sleep(SLEEP)
