#!/usr/bin/env python3
"""scrap.py module

This module gets CESAs from LWN.net and official CentOS ML and generates yaml files


Todo:
    - make it more parallel
    - unit test
"""
import re
from concurrent.futures import ThreadPoolExecutor as PoolExecutor
import requests
from jinja2 import Template
from bs4 import BeautifulSoup


def get_it(url):
    """Get content of url

    Args:

        url (str): The url to reach

    """
    response = requests.get(url)
    return response.text


def clean_word(word):
    """Clean word from unwanted chars: [, ], '

    Args:

        word (str): The string to be cleaned

    """
    return word.replace('[', '').replace(']', '').replace("'", '')


def get_cesa_links_official():
    '''Returns a list: of CESA links to be processed from CentOS ML'''
    cesa_url = "http://centos-announce.2309468.n4.nabble.com/"
    cesa_pattern = ".*CESA.*"
    response = requests.get(cesa_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    cesa_links = []
    for single_link in soup.find_all('a', href=True):
        if re.match(cesa_pattern, single_link.text):
            cesa_links.append(
                'http://centos-announce.2309468.n4.nabble.com{}'.format(single_link['href']))
    return cesa_links


def get_cesa_links(max_link=80):
    """Returns a list: of CESA links to be processed from LWN

    Args:

        max_link (int): max number of links to consider
    """
    cesa_url = "https://lwn.net/Alerts/CentOS/?n={}".format(max_link)
    lwn_url = 'https://lwn.net'
    cesa_pattern = "CESA-*"
    response = requests.get(cesa_url)
    if response:
        soup = BeautifulSoup(response.text, "html.parser")
        cesas = [link['href'] for link in soup.findAll(
            'a', href=True) if re.match(cesa_pattern, link.text)]
    cesa_links = {}
    if cesas is None:
        print("No links found from LWN.net")
    else:
        for cesa in cesas:
            cesa_links[cesa.split("/")[2]] = lwn_url + cesa
    return cesa_links


def get_cesa_details(cesa_found, official=False):
    """Parse the CESAs and generates the yaml files for ATLAS

    Args:

        CESAs (dict): The CESAs dict generated by the getCESALinks() function.
        official (bool) : Flag for LWN/CentOS source
    """
    cesa_to_6_template = {}
    cesa_to_7_template = {}
    if isinstance(cesa_found, dict):
        cesas_links = list(cesa_found.values())
    else:
        cesas_links = list(cesa_found)
    responses = []
    with PoolExecutor(max_workers=16) as executor:
        for resp in executor.map(get_it, iter(cesas_links)):
            responses.append(resp)

    for resp in responses:
        response = resp
        prm_pattern = r"([0-9a-zA-Z\.\-_]*.rpm)"
        package_pattern = r"\([a-zA-Z0-9-.^\(^\)]*\)"
        centos_version_pattern = r"(CentOS\s[6-7])"
        cesa_number_pattern = r"(CESA\-[0-9]{4}\:[0-9]{4})"
        soup = BeautifulSoup(response, 'html.parser')
        cesa_number = str(re.findall(
            cesa_number_pattern, str(response))[0])
        cesa_title = clean_word(str(re.findall(package_pattern, str(soup.title))).replace(
            '(', '').replace(')', ''))
        cesa_os = str(re.findall(centos_version_pattern, str(response)))
        if official is True:
            if '6' in cesa_os:
                cesa_title = str(re.findall(
                    r"CentOS\s[0-9]\s(.*)\sSecurity", str(soup.title)))
                cesa_subject = cesa_title + "#" + cesa_number
                cesa_to_6_template[cesa_subject] = re.findall(
                    prm_pattern, str(soup.find('div', {"class": "message-text adbayes-content"})))
                rpms = sorted(cesa_to_6_template[cesa_subject])
                with open('templates/template6.yml') as file_:
                    template = Template(file_.read())
                    template.stream(cesa_number=cesa_number,
                                    package_name=str(clean_word(cesa_title)),
                                    rpms=rpms).dump('C6/'+cesa_number+'.yml')
            else:
                cesa_title = str(re.findall(
                    r"CentOS\s[0-9]\s(.*)\sSecurity", str(soup.title)))
                cesa_subject = cesa_title + "#" + cesa_number
                cesa_to_7_template[cesa_subject] = re.findall(
                    prm_pattern, str(soup.find('div', {"class": "message-text adbayes-content"})))
                rpms = sorted(cesa_to_7_template[cesa_subject])
                with open('templates/template7.yml') as file_:
                    template = Template(file_.read())
                    template.stream(cesa_number=cesa_number,
                                    package_name=str(clean_word(cesa_title)),
                                    rpms=rpms).dump('C7/'+cesa_number+'.yml')

        else:
            if '6' in cesa_os:
                cesa_subject = cesa_title + "#" + cesa_number
                cesa_to_6_template[cesa_subject] = re.findall(
                    prm_pattern, soup.find('p').text)
                rpms = sorted(cesa_to_6_template[cesa_subject])
                with open('templates/template6.yml') as file_:
                    template = Template(file_.read())
                    template.stream(cesa_number=cesa_number, package_name=cesa_title,
                                    rpms=rpms).dump('C6/'+cesa_number+'.yml')
            else:
                cesa_subject = cesa_title + "#" + cesa_number
                cesa_to_7_template[cesa_subject] = re.findall(
                    prm_pattern, soup.find('p').text)
                rpms = sorted(cesa_to_7_template[cesa_subject])
                with open('templates/template7.yml') as file_:
                    template = Template(file_.read())
                    template.stream(cesa_number=cesa_number, package_name=cesa_title,
                                    rpms=rpms).dump('C7/'+cesa_number+'.yml')


if __name__ == "__main__":
    # get_cesa_details(get_cesa_links(150))
    try:
        get_cesa_details(get_cesa_links(100))
    except IndexError:
        print("Error in finding content from LWN.net!")
