import requests
import time
import datetime
import math
import json
from urllib.parse import urlencode
import psycopg2 as pg
import re

APP_ID = int(input('Введите APP_ID: '))
OUTH_URL = 'https://oauth.vk.com/authorize'
OUTH_PARAMS = {
    'client_id': APP_ID,
    'display': 'page',
    'scope': 'friends, groups, photos',
    'response_type': 'token',
    'v': '5.52'
}
print('Перейдите по ссылке ниже, скопируйте access_token и вставьте: ')
print('?'.join((OUTH_URL, urlencode(OUTH_PARAMS))))
token = input()

def vkinder_start():
    dbname = input('Введите название базы данных: ')
    user = input('Введите логин: ')
    password = input('Введите пароль: ')
    with pg.connect(dbname=dbname,
                    user=user,
                    password=password
                    ) as conn:

        cur = conn.cursor()
    while True:
        uid = input('Введите ID (Nickname) пользователя')
        with timer() as t:
            user1 = User(uid)
            interests_dict = user1.get_mutual_groups_friends()
            print('Выбор топ 10 пользователей')
            top10 = find_top10(interests_dict)
            print('Поиск 3 самых популярных фотографий среди пользователей')
            photo_dict = find_photos(top10)
            create_db(cur)
            add_user(user1.uid, photo_dict, cur)
            conn.commit()
            if user1.uid is None:
                continue
            with open('photos.json', 'w', encoding='utf-8') as f:
                json.dump(photo_dict, f, ensure_ascii=False, indent=2)
                print('Файл успешно записан')
                print()
                print(f'Пользователь с id - {uid} обработан за {t.work_time()} секунд')
                t.cancel_time()
            print()
            next_step = input('Нажмите: \n'
                              'y - для повторного запуска\n'
                              'q - для выхода из программы\n')

            if next_step == 'y':
                continue
            elif next_step == 'q':
                break

def create_db(cur):
    cur.execute("""
            CREATE TABLE if not exists match_users(
                id serial PRIMARY KEY,
                input_user_id varchar(100) not NULL,
                match_user_id varchar(100) not NULL,
                rate numeric(10, 0) not NULL,
                photo_url varchar(100) not NULL,
                likes numeric(10, 0) not NULL
            );
            """)

def add_user(user_id, photo_dict,cur):
    for keys, values in photo_dict.items():
        for value in values[1]:
            cur.execute(f"insert into match_users (input_user_id, match_user_id, rate, photo_url, likes) values"
                        " (%s,%s,%s,%s,%s)", (user_id, keys, values[0]['rate'],value['photo_id'], value['likes']))


def user_get(uid):
    url = 'https://api.vk.com/method/users.get'
    params = {
        'v': 5.52,
        'access_token': token,
        'fields': 'bdate, sex, city, interests, music, movies, tv, books, games',
        'user_ids': uid
    }
    try:
        response = requests.get(url, params=params)
        if 'error' in response.json() and 'error_code' in response.json()['error'] and response.json()['error']['error_code'] == 113:
            raise InvalidUserID()
    except InvalidUserID:
        print(f'Неправильно введен ID {uid} пользователя')
        pass
    else:
        return response.json()

def find_interest(interests, result, key, w, interests_dict):
    interests_list = []
    for interest in interests:
        pattern = re.compile(r'{}'.format(interest), re.IGNORECASE)
        for i in result:
            if key in i.keys() and i[key] != '' and pattern.findall(i[key]) != []:
                if 'relation' in i.keys() and 'last_seen' in i.keys() and i['last_seen']['time'] > 1588291200:
                    if i['relation'] == 1 or i['relation'] == 6 or i['relation'] == 0:
                        if i['id'] not in interests_dict.keys():
                            interests_dict[i['id']] = list()
                        interests_dict[i['id']].append(len(pattern.findall(i[key])) * w)
                        interests_list.append(i['id'])
                elif 'relation' not in i.keys() and 'last_seen' in i.keys() and \
                        i['last_seen']['time'] > 1588291200:
                    if i['id'] not in interests_dict.keys():
                        interests_dict[i['id']] = list()
                    interests_dict[i['id']].append(len(pattern.findall(i[key])) * w)
                    interests_list.append(i['id'])
    return interests_list

def find_photos(top10):
    top_interests_dict = dict(top10)
    photo_dict = {}
    for key,value in top_interests_dict.items():
        photo_dict.setdefault(key, list())
        photo_dict[key].append({'rate': value})
    for key, value in photo_dict.items():
        time.sleep(0.34)
        dic = {'owner_id': key, 'album_id': 'profile'}
        url = 'https://api.vk.com/method/photos.get'
        params = {
            'v': 5.52,
            'access_token': token,
            'fields': 'bdate, sex, city, interests, music, movies, tv, books, games',
            'owner_id': key,
            'album_id': 'profile',
            'count': 1000,
            'extended': 1
        }
        repeat = True
        while repeat:
            response = requests.get(url, params=params)
            if 'error' in response.json() and 'error_code' in response.json()['error'] and response.json()['error'][
                'error_code'] == 6:
                time.sleep(0.34)
            else:
                repeat = False
        photos = response.json()['response']['items']
        photo_list = []
        for photo in photos:
            if 'photo_2560' in photo.keys():
                photo_list.append({'likes': photo['likes']['count'], 'photo_id': photo['photo_2560']})
            elif 'photo_1280' in photo.keys():
                photo_list.append({'likes': photo['likes']['count'], 'photo_id': photo['photo_1280']})
            elif 'photo_807' in photo.keys():
                photo_list.append({'likes': photo['likes']['count'], 'photo_id': photo['photo_807']})
            elif 'photo_604' in photo.keys():
                photo_list.append({'likes': photo['likes']['count'], 'photo_id': photo['photo_604']})
        photo_dict[key].append(photo_list)
    for keys, values in photo_dict.items():
        values[1].sort(key=lambda x: x['likes'], reverse=True)
        values[1] = values[1][:3]
    return photo_dict

def find_top10(interests_dict):
    total = 0
    for keys, values in interests_dict.items():
        for j in values:
            total += int(j)
            interests_dict[keys] = total
        total = 0
    top_10 = list(interests_dict.items())
    top_10.sort(key=lambda i: i[1], reverse=True)
    top_10 = top_10[:10]
    return top_10

class User:
    def __init__(self, uid):
        self.user_info = user_get(uid)
        self.uid = self.user_info['response'][0]['id']
        self.id = 'id'+str(self.uid)
        self.link = 'https://vk.com/id' + str(self.uid)
        self.groups_list = []

    def get_users_on_interests(self):
        w_interests = 3
        w_games = 1
        w_music = 2
        w_books = 1
        interests_dict = {}
        url = 'https://api.vk.com/method/users.search'
        match_uid_list = []
        try:
            interests = self.user_info['response'][0]['interests'].split(', ')
            interests = [el for el in interests if el and el.strip()]
        except KeyError:
            interests = []
        try:
            music = self.user_info['response'][0]['music'].split(', ')
            music = [el for el in music if el and el.strip()]
        except KeyError:
            music = []
        try:
            books = self.user_info['response'][0]['books'].split(', ')
            books = [el for el in books if el and el.strip()]
        except KeyError:
            books = []
        try:
            games = self.user_info['response'][0]['games'].split(', ')
            games = [el for el in games if el and el.strip()]
        except KeyError:
            games = []
        try:
            bdate_years = math.floor((datetime.datetime.today() - datetime.datetime.strptime(self.user_info['response'][0]['bdate'], '%d.%m.%Y')).days/365)
            city = self.user_info['response'][0]['city']['id']
        except KeyError:
            bdate_years = int(input('Введите ваш возраст'))
        except ValueError:
            bdate_years = int(input('Введите ваш возраст'))
        finally:
            del_age = int(input('Введите разницу возраста для поиска'))
        try:
            city = self.user_info['response'][0]['city']['id']
        except KeyError:
            city = input('Введите идентификатор вашего города')
        if self.user_info['response'][0]['sex'] == 1:
            sex = 2
        elif self.user_info['response'][0]['sex'] == 2:
            sex =1
        params = {
            'v': 5.89,
            'access_token': token,
            'city': city,
            'age_from': bdate_years-del_age,
            'age_to': bdate_years+del_age,
            'sex': sex,
            'fields': 'interests, music, books, games, relation, last_seen',
            'count': 1000
        }
        try:
            response = requests.get(url, params=params)
            if 'error' in response.json() and 'error_code' in response.json()['error'] and response.json()['error']['error_code'] == 18:
                raise DeletedUser()
            if 'error' in response.json() and 'error_code' in response.json()['error'] and response.json()['error']['error_code'] == 15:
                raise PrivateUserProfile()
        except DeletedUser:
            print(f'Пользователь с ID {self.uid} удален или забанен')
            pass
        except PrivateUserProfile:
            print(f'Пользователь с ID {self.uid} запретил доступ к профилю')
            pass
        else:
            result = response.json()['response']['items']
            match_uid_list += find_interest(interests, result, 'interests', w_interests, interests_dict)
            match_uid_list += find_interest(books, result, 'books', w_books, interests_dict)
            match_uid_list += find_interest(music, result, 'music', w_music, interests_dict)
            match_uid_list += find_interest(games, result, 'games', w_games, interests_dict)
            if match_uid_list == []:
                for i in result:
                    if 'relation' in i.keys() and 'last_seen' in i.keys() and i['last_seen']['time'] > 1588291200:
                        if i['relation'] == 1 or i['relation'] == 6 or i['relation'] == 0:
                            match_uid_list.append(i['id'])
                    elif 'relation' not in i.keys() and 'last_seen' in i.keys() and i['last_seen']['time'] > 1588291200:
                        match_uid_list.append(i['id'])
            return set(match_uid_list), interests_dict

    def get_mutual_groups_friends(self):
        w_friends = 3
        w_groups = 2
        user_group = set(self.get_groups(self.uid))
        user_ids, interests_dict = self.get_users_on_interests()
        user_ids = list(user_ids)
        if len(user_ids) > 328:
            user_ids = user_ids[:328]
        user_count = len(user_ids)
        print(f'Найдено {user_count} совпадений по интересам')
        print('Поиск пользователей, имеющих общие группы и общих друзей')
        for user_id in user_ids:
            friend_group = self.get_groups(user_id)
            if friend_group is None:
                pass
            else:
                friend_group = set(friend_group)
                if (user_group & friend_group) != set():
                    if user_id not in interests_dict.keys():
                        interests_dict[user_id] = list()
                    interests_dict[user_id].append(w_groups)
            url = 'https://api.vk.com/method/friends.getMutual'
            params = {
                'v': 5.52,
                'access_token': token,
                'source_uid': self.uid,
                'target_uid': user_id
            }
            repeat = True
            try:
                while repeat:
                    response = requests.get(url, params=params)
                    if 'error' in response.json() and 'error_code' in response.json()['error'] and response.json()['error']['error_code'] == 6:
                        time.sleep(0.34)
                    else:
                        repeat = False
                if 'error' in response.json() and 'error_code' in response.json()['error'] and response.json()['error'][
                    'error_code'] == 18:
                    raise DeletedUser()
                if 'error' in response.json() and 'error_code' in response.json()['error'] and response.json()['error'][
                    'error_code'] == 15:
                    raise PrivateUserProfile()
            except DeletedUser:
                print(f'Пользователь с ID {user_id} удален или забанен')
                pass
            except PrivateUserProfile:
                print(f'Пользователь с ID {user_id} запретил доступ к профилю')
                pass
            else:
                if response.json()['response'] != []:
                    if user_id not in interests_dict.keys():
                        interests_dict[user_id] = list()
                    interests_dict[user_id].append(w_friends)
            user_count -= 1
            print(f'Осталось обработать {user_count+1} пользователей')
        return interests_dict

    def get_groups(self, user_id):
        url = 'https://api.vk.com/method/groups.get'
        params = {
            'v': 5.52,
            'access_token': token,
            'user_id': user_id
        }
        repeat = True
        try:
            while repeat:
                response = requests.get(url, params=params)
                if 'error' in response.json() and 'error_code' in response.json()['error'] and response.json()['error'][
                    'error_code'] == 6:
                    time.sleep(0.34)
                else:
                    repeat = False
            if 'error' in response.json() and 'error_code' in response.json()['error'] and response.json()['error']['error_code'] == 18:
                raise DeletedUser()
            if 'error' in response.json() and 'error_code' in response.json()['error'] and response.json()['error']['error_code'] == 15:
                raise PrivateUserProfile()
        except DeletedUser:
            print(f'Пользователь с ID {self.uid} удален или забанен')
            pass
        except PrivateUserProfile:
            print(f'Пользователь с ID {self.uid} запретил доступ к профилю')
            pass
        else:
            return response.json()['response']['items']


class timer():
    def __init__(self):
        self.start = time.time()
        self.work = time.time()
        self.start_time = datetime.datetime.now()
        print(f'Время начала работы программы: {self.start_time}')

    def current_time(self):
        return round(time.time() - self.start, 2)

    def work_time(self):
        return round(time.time() - self.work, 2)

    def cancel_time(self):
        self.work = time.time()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.datetime.now()
        print(f'Программа завершилась в: {self.end_time}')
        print(f'Затрачено времени {self.current_time()} секунд')

class DeletedUser(Exception):
    pass

class GroupAccessDenied(Exception):
    pass

class PrivateUserProfile(Exception):
    pass

class InvalidUserID(Exception):
    pass

if __name__ == '__main__':
    vkinder_start()
