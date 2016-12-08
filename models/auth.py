"""Django models for the queryforce app"""
import os
import requests
import datetime
from pydoc import locate
from django.db import models
from django.utils import timezone as dtz


def proxies():
    """Gets proxys from environmental variables if they exist"""
    proxd = {}
    try:
        proxd['http'] = os.environ['HTTP_PROXY']
        proxd['https'] = os.environ['HTTPS_PROXY']
    except KeyError:
        proxd = None
    return proxd


class ForceAPI(models.Model):
    """Credentials and methods for Salesforce REST API connection"""
    user_id = models.EmailField(max_length=80)
    password = models.CharField(max_length=80)
    user_token = models.CharField(max_length=80)
    consumer_key = models.CharField(max_length=120)
    consumer_secret = models.CharField(max_length=120)
    request_token_url = models.CharField(
        max_length=255,
        default='https://login.salesforce.com/services/oauth2/token')
    access_token_url = models.CharField(
        max_length=255,
        default='https://login.salesforce.com/services/oauth2/token')
    conn = None

    def __str__(self):
        return self.user_id

    def create_connection(self):
        """Creates API Connection"""
        data = {
            'grant_type': 'password',
            'client_id': self.consumer_key,
            'client_secret': self.consumer_secret,
            'username': self.user_id,
            'password': self.password
        }
        headers = {
            'content-type': 'application/x-www-form-urlencoded'
        }
        if proxies():
            req = requests.post(
                self.access_token_url,
                data=data,
                headers=headers,
                proxies=proxies())
        else:
            req = requests.post(
                self.access_token_url,
                data=data,
                headers=headers)

        self.conn = req.json()
        return req.json()

    def test_connection(self):
        """tests if connection is still working"""
        if self.conn:
            tsthdr = {
                'Authorization': 'Bearer ' + self.conn['access_token']
            }
            tsturl = self.conn['instance_url']
            tsturl = tsturl + '/services/data/v37.0/sobjects'
            tst = requests.get(tsturl, headers=tsthdr, proxies=proxies())
            return tst.status_code == 200

        return False

    def get_connection(self):
        """gets a live connection to the REST API"""
        if not self.test_connection():
            return self.create_connection()
        else:
            return self.conn

    def get_data(self, apifunction):
        """gets data defined in the apifunction"""
        cnn = self.get_connection()
        hdr = {
            'Authorization': 'Bearer ' + cnn['access_token']
        }
        url = cnn['instance_url'] + '/services/data/v37.0/' + apifunction
        grs = requests.get(url, headers=hdr, proxies=proxies())
        return grs.json()
