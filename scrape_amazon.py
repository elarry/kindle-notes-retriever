# -*- coding: utf-8 -*-
"""Extracts Amazon kindle notes from the web and saves notes for each book
in directory ~/html_files/. Files named in format "Author - Title"
"""

from unidecode import unidecode
from bs4 import BeautifulSoup
import mechanize
import getpass
import cookielib
import os
import re


def scrape_amazon_notes():
    """Scrapes Amazon Kindle notes and saves them as html files
    in directory "~/html_files/". File names given in the form
    *integer*.html starting with the most recent recorded notes.

    :inputs: Function prompts to give your Amazon username and
             password to log into your Amazon Kindle account.

    ToDo: Find out how secure it is to use user id and pw with mechanize

    """

    USERNAME = raw_input('Enter your Amazon username: ')
    PASSWORD = getpass.getpass('Enter your Amazon password: ')
    COUNTER = int(raw_input("How many notes do you wish to download?"))
    amazon = 'https://kindle.amazon.com/your_highlights'
    if not os.path.exists("html_files"):  # Create folder for scraped html files
        os.makedirs("html_files")

    br = mechanize.Browser()
    cj = cookielib.CookieJar()
    br.set_cookiejar(cj)
    br.set_handle_robots(False)  # Ignore robots.txt.
    br.addheaders = [('user-agent', 'Firefox')]  # Use mechanize as browser

    sign_in = br.open(amazon)
    sign_in.set_data(re.sub('<!DOCTYPE(.*)>', '', sign_in.get_data()))
    br.set_response(sign_in)
    br.select_form(name="signIn")
    br["email"] = str(USERNAME)
    br["password"] = str(PASSWORD)
    response = br.submit()
    print('Logging on to Amazon...')

    for k in range(COUNTER):
        try:
            html = response.read()
            note_name = "html_files/{:03d}.html".format(k)
            print "Saving note: ", note_name

            with open(note_name, "w") as f:
                f.write(html)

            try:
                response = br.follow_link(text='Next Book')
            except:
                "Unable to find more notes"
                break
        except:
            print "Something went wrong..."


def rename_html_files(max_char=50):
    """Rename all the files in folder "/html_files" according to
    the books author and title

    :param max_char: Maximum number of characters in the title
    :return: "Author(s) -- Title"
    """

    for filename in os.listdir("html_files/."):
        if os.path.isdir("html_files/" + filename):
            print "Skipping directory: ", filename
            continue
        print("Extracting information from title {}...", filename)
        source_html = "html_files/" + filename
        author_title = extract_author_title(source_html, max_char)
        filename_new = "html_files/" + author_title[0] + " - " + author_title[2] + ".html"
        filename_old = "html_files/" + filename
        os.rename(filename_old, filename_new)


def extract_author_title(source_html, max_char=50):
    """Extract the authors and titles from the raw html files
    which contain Amazon Kindle notes.

    :param source_html: Saved Amazon notes html file
    :param max_char: The maximum number of characters for truncated titles
                     to be used in naming html files
    :return: [Authors, Title, Truncated Title]
    """

    try:
        soup = BeautifulSoup(open(source_html))
        soup_title, soup_author = soup.find_all('span', attrs={'class': ["author", "title"]})
    except ValueError:
        print "The following file had no author or title: ", source_html
        print "It will be renamed as 'ERROR'"
        return ["ERROR", "", ""]

    title = unidecode(soup_title.string)
    author = unidecode(soup_author.string)

    # Clean string
    author = author.replace("by", "", 1)
    author = author.lstrip()
    author = author.rstrip()
    author = author.title()

    # Clean title
    title = title.title()
    title = title.replace("'S ", "'s ")
    title = title.replace("'T ", "'t ")

    title_truncated = title
    title_truncated = title_truncated.replace(":", " --")  # Avoid filename error
    title_truncated = title_truncated.replace("?", "")
    if len(title_truncated) > max_char:  # Truncate long book titles
        title_truncated = title_truncated.split(" --", 1)[0]
        title_truncated = title_truncated.split(" (", 1)[0]
        if len(title_truncated) > max_char:
            title_truncated = " ".join(title_truncated.split()[:5])
    title_truncated = re.sub("[^A-Za-z0-9_.]+$", "", title_truncated)

    return [author, title, title_truncated]
