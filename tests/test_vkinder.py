import json
import os
import unittest
from unittest.mock import patch
import Vkinder


class TestVkinder(unittest.TestCase):
    def setUp(self) -> None:
        with patch('Vkinder.input') as in_mock:
            in_mock.side_effect = ['1', '1', '1', '1', 0, 'q']

    def test_user_id(self):
        user_id = Vkinder.user_get('r1zzzon')['response'][0]['id']
        self.assertEqual(user_id, 35014969)

    def test_find_interests(self):
        users_dict = {}
        current_path = str(os.path.dirname(os.path.abspath(__file__)))
        f_users_interests = os.path.join(current_path, 'fixtures/users_interests.json')
        with open(f_users_interests, 'r', encoding='utf-8') as out_docs:
            users_interests = json.load(out_docs)
        user_match_interests = Vkinder.find_interest(['футбол', 'воллейбол', 'стихи'], users_interests, 'interests', 3, users_dict)
        self.assertEqual(set(user_match_interests), {1, 6})

    def test_find_top10(self):
        current_path = str(os.path.dirname(os.path.abspath(__file__)))
        f_interests_dict = os.path.join(current_path, 'fixtures/interests_dict.json')
        with open(f_interests_dict, 'r', encoding='utf-8') as out_docs:
            interests_dict = json.load(out_docs)
        top10users = Vkinder.find_top10(interests_dict)
        compare_top10users = [('12', 12), ('14', 11), ('7', 10), ('2', 9), ('3', 9), ('13', 8), ('1', 6), ('15', 5), ('5', 3), ('8', 3)]
        self.assertEqual(top10users, compare_top10users)

    def test_find_photos(self):
        current_path = str(os.path.dirname(os.path.abspath(__file__)))
        f_top3photos = os.path.join(current_path, 'fixtures/top3photo.json')
        with open(f_top3photos, 'r', encoding='utf-8') as out_docs:
            top3photos = json.load(out_docs)
        compare_top3photos = Vkinder.find_photos([('35014969', 10)])
        self.assertEqual(compare_top3photos, top3photos)






