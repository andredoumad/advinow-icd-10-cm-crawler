
import os
import time
import unittest
import re
from datetime import datetime, timedelta
import platform
from selenium import webdriver
from fake_useragent import UserAgent
from pathlib import Path
from standalone_tools import eventlog
from bs4 import BeautifulSoup

print(f"os.path.join(str(Path.cwd()),'chromedriver'): {os.path.join(str(Path.cwd()),'chromedriver')}")
print(f"platform.system(): {platform.system()}")

class Crawler(object):
    def __init__(self, job_name):
        self.job_name = job_name
        self.timestamp = self._get_timestamp()
        self.path_job_root = self.make_job_paths(self.job_name)
        self.webpage_load_interval = 1.5
        self.driver = None
        self.home_url = None

    def _get_timestamp(self) -> str:
        """
        Gets a timestamp in the correct format that is current UTC.
        returns timestamp
        """
        time_string = float(datetime.utcnow().strftime('%y%m%d%H%M%S.%f'))
        time_string = str(round(time_string, 3))
        time_string = time_string.replace(".", "")
        while len(time_string) < 15:
            time_string += "0"
        return time_string


    def generate_icd10data(self):
        self.home_url = "https://www.icd10data.com/ICD10CM/Codes"
        self.driver = self.make_web_browser()
        self.visit_web_page(self.home_url)
        self.download_source()
        
        
        
        self.shutdown()

    def make_web_browser(self):
        # LOGGER.setLevel(logging.WARNING)
        # logging.getLogger("urllib3").setLevel(logging.WARNING)
        chrome_options = webdriver.ChromeOptions()
        #https://cs.chromium.org/chromium/src/chrome/common/pref_names.cc
        prefs = {
            "profile.managed_default_content_settings.images":2,
            "download.default_directory": "NUL", 
            "download.prompt_for_download": False,
            "download_restrictions":3,
            
        }
        
        chrome_options.accept_untrusted_certs = True
        chrome_options.assume_untrusted_cert_issuer = True
        # chrome_options.add_argument('--headless')
        chrome_options.add_argument("--window-size=1400,900")
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument("--disable-impl-side-painting")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-seccomp-filter-sandbox")
        chrome_options.add_argument("--disable-breakpad")
        chrome_options.add_argument("--disable-client-side-phishing-detection")
        chrome_options.add_argument("--disable-cast")
        chrome_options.add_argument("--disable-cast-streaming-hw-encoding")
        chrome_options.add_argument("--disable-cloud-import")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-session-crashed-bubble")
        chrome_options.add_argument("--disable-ipv6")
        chrome_options.add_argument("--allow-http-screen-capture")
        chrome_options.add_argument("--start-maximized")
        

        ua = UserAgent()
        userAgent = ua.random
        chrome_options.add_argument(f'user-agent={userAgent}')
        chrome_options.add_experimental_option("prefs", prefs)
        if platform.system() != "Windows":
            # assuming linux - also make sure that the chromedriver version is right before using it on linux
            self.driver = webdriver.Chrome(os.path.join(str(Path.cwd()), 'chromedriver'), chrome_options=chrome_options)
        else:
            self.driver = webdriver.Chrome(os.path.join(str(Path.cwd()), 'chromedriver_88.exe'), chrome_options=chrome_options)
        time.sleep(1)
        return self.driver

    # loads web page.
    def visit_web_page(self, url):
        self.driver.get(url)
        time.sleep(self.webpage_load_interval)

    # creates path based on job name in database folder
    def make_job_paths(self, name):
        path = str(os.path.join(os.getcwd(), 'DATABASE', self.timestamp, 'JOBS', str(name)))
        if not os.path.exists( path ):
            #shutil.rmtree( str(os.getcwd() + '/DATABASE/JOBS/' + str(job_name)))
            os.makedirs( path)
        return path

    # creates path based on current url and job name in database folder
    def compute_save_directory(self):
        print("computing save directory")
        directory_key = None
        eventlog(f"job_name: {self.job_name}")
        eventlog(f"job root path: {self.path_job_root}")
        fp_url = ""
        previous_ch = ""
        for ch in str(self.driver.current_url):
            regex = re.compile('[@_!#$%^&*()<>?/\|}{~:;],.')
            if regex.search(ch) == None and ch != ' ':
                if ch == '/' and previous_ch != '/':
                    if platform.system() != "Windows":
                        fp_url += ch
                    else:
                        fp_url += "\\"
                elif ch.isdigit() == True:
                    fp_url += ch
                elif ch.isalpha() == True:
                    fp_url += ch
            previous_ch = ch

        eventlog(f"fp_url: {fp_url}")
        temp_string = "".join([c for c in str(self.driver.current_url) if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        string = temp_string.replace(" ", "")
        eventlog(f"string: {string}")

        if len(string) > 60:
            directory_key = str('{:.60}'.format(str(string)))
        else:
            directory_key = string

        eventlog(f"directory_key: {directory_key}")

        path = os.path.join(self.path_job_root, 'web', str(fp_url))
        if not os.path.exists(path):
            os.makedirs(path)

        eventlog(f"compute_save_directory path is: {path}")
        return path
        # iresult = 0
        # dp_google_results = os.path.join(website_root_path, "web", fp_url)
        # matrix_name = str(directory_key)

        # pathStart = os.path.join(website_root_path, "web", fp_url)
        # pathEnd = "_index.html"

    # writes source.html into appropriate database directory
    def download_source(self):
        raw = self.driver.page_source
        fp_raw = os.path.join(self.compute_save_directory(), "source.html")
        fp_pretty_list = os.path.join(self.compute_save_directory(), "source_pretty.html")
        with open(fp_raw, "w+") as f:
            f.write(raw)
        self.soup = BeautifulSoup(str(raw), 'html.parser')
        self.prettify_soup = ''
        self.prettify_soup = self.soup.prettify()
        list_pretty = self.prettify_soup.split('\n')
        with open(fp_pretty_list, "w+") as f:
            for line in list_pretty:
                f.write(line + "\n")

    # teardown anything we need to
    def shutdown(self):
        self.driver.quit()

class test_unittest(unittest.TestCase):
    def test_crawler(self):
        crawler = Crawler("test_crawler")
        crawler.generate_icd10data()


if __name__ == "__main__":
    unittest.main()