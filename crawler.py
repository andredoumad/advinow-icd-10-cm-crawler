
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
import openpyxl

print(f"os.path.join(str(Path.cwd()),'chromedriver'): {os.path.join(str(Path.cwd()),'chromedriver')}")
print(f"platform.system(): {platform.system()}")

class Crawler(object):
    def __init__(self, job_name):
        self.job_name = job_name
        self.timestamp = self._get_timestamp()
        self.path_job_root = self.make_get_job_paths(self.job_name)
        self.webpage_load_interval = 0.5
        self.driver = None
        self.home_url = None
        self.links_icd10cm_codes = []
        self.links_visited = []
        self.diagnosis_codes = []


        # xlsx setup
        self.wb_out = openpyxl.Workbook()
        self.ws_out = self.wb_out.active

        self.ws_out["A1"] = "Code"
        self.ws_out["A1"].fill = openpyxl.styles.PatternFill("solid", fgColor="0000CCFF")
        self.ws_out.column_dimensions['A'].width = 15

        self.ws_out["B1"] = "Description"
        self.ws_out["B1"].fill = openpyxl.styles.PatternFill("solid", fgColor="0000CCFF")
        self.ws_out.column_dimensions['B'].width = 100

        self.ws_out["C1"] = "URL"
        self.ws_out["C1"].fill = openpyxl.styles.PatternFill("solid", fgColor="0000CCFF")
        self.ws_out.column_dimensions['C'].width = 120

        self.ws_index = 2

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

    def generate_pretty_source(self, url):
        self.home_url = url
        self.driver = self.make_web_browser()
        self.crawl_url(self.home_url)
        self.shutdown()

    def generate_icd10data(self):
        self.home_url = "https://www.icd10data.com/ICD10CM/Codes"
        self.driver = self.make_web_browser()
        self.crawl_url(self.home_url)
        prev_length_icd10cm_codes = 0

        while len(self.links_icd10cm_codes) != prev_length_icd10cm_codes:
            for url in self.links_icd10cm_codes:
                if url not in self.links_visited:
                    self.crawl_url(url)
            prev_length_icd10cm_codes = len(self.links_icd10cm_codes)


        self.write_all_icd10cm_codes_to_job_root()
        self.write_all_links_visited()
        
        self.shutdown()

    def crawl_url(self, url):
        self.links_visited.append(url)
        self.visit_web_page(url)
        pretty_list = self.download_source_return_source_pretty_list()
        self.extract_icd10_code_given_pretty_list(pretty_list)
        self.update_icd10cm_urls(pretty_list)

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
    def make_get_job_paths(self, name):
        path = str(os.path.join(os.getcwd(), 'DATABASE', self.timestamp, 'JOBS', str(name)))
        if not os.path.exists( path ):
            #shutil.rmtree( str(os.getcwd() + '/DATABASE/JOBS/' + str(job_name)))
            os.makedirs( path)
        return path

    # creates path based on current url and job name in database folder
    def compute_save_directory(self):
        # print("computing save directory")
        directory_key = None
        # eventlog(f"job_name: {self.job_name}")
        # eventlog(f"job root path: {self.path_job_root}")
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

        # eventlog(f"fp_url: {fp_url}")
        temp_string = "".join([c for c in str(self.driver.current_url) if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        string = temp_string.replace(" ", "")
        # eventlog(f"string: {string}")

        if len(string) > 60:
            directory_key = str('{:.60}'.format(str(string)))
        else:
            directory_key = string

        # eventlog(f"directory_key: {directory_key}")

        path = os.path.join(self.path_job_root, 'web', str(fp_url))
        if not os.path.exists(path):
            os.makedirs(path)

        # eventlog(f"compute_save_directory path is: {path}")
        return path
        # iresult = 0
        # dp_google_results = os.path.join(website_root_path, "web", fp_url)
        # matrix_name = str(directory_key)

        # pathStart = os.path.join(website_root_path, "web", fp_url)
        # pathEnd = "_index.html"

    # writes source.html into appropriate database directory
    def download_source_return_source_pretty_list(self):
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

        return list_pretty
    
    def update_icd10cm_urls(self, pretty_list):
        for line in pretty_list:
            if line.find("/ICD10CM/Codes/") != -1:
                found = False
                start_index = line.index("/ICD10CM/Codes/")
                icd10cm_end = ""
                end_index = start_index + 30
                while end_index > len(line) -1:
                    end_index -= 1
                extracting = True
                i = start_index
                while extracting and i < end_index:
                    if line[i] != '"':
                        found = True
                        icd10cm_end += line[i]
                    else:
                        extracting = False
                    i += 1
                
                if found and icd10cm_end.find("-") != -1:
                    link = f"https://www.icd10data.com{icd10cm_end}"
                    # append to master list of icd 10 code links
                    if link not in self.links_icd10cm_codes:
                        self.links_icd10cm_codes.append(link)

                    # write links to source directory
                    fp_links_icd10cm_codes = os.path.join(self.compute_save_directory(), "source_icd10cm_list.txt")
                    with open(fp_links_icd10cm_codes, "a+") as f:
                        f.write(link + "\n")

    def write_all_icd10cm_codes_to_job_root(self):
        path_job_base = self.make_get_job_paths(self.job_name)

        dir_all_links_icd10cm_codes = os.path.join(path_job_base, "output")
        if not os.path.exists(dir_all_links_icd10cm_codes):
            os.makedirs(dir_all_links_icd10cm_codes)

        fp_all_links_icd10cm_codes = os.path.join(path_job_base, "output", "links_icd10cm.txt")
        with open(fp_all_links_icd10cm_codes, "w+") as f:
            for link in self.links_icd10cm_codes:
                # eventlog(f"found: {link}")
                f.write(link + "\n")

    def write_all_links_visited(self):
        path_job_base = self.make_get_job_paths(self.job_name)

        dir_all_links_visited = os.path.join(path_job_base, "output")
        if not os.path.exists(dir_all_links_visited):
            os.makedirs(dir_all_links_visited)

        fp_all_links_visited = os.path.join(path_job_base, "output", "links_visited.txt")
        with open(fp_all_links_visited, "w+") as f:
            for link in self.links_visited:
                # eventlog(f"found: {link}")
                f.write(link + "\n")

    def find_between(self, s, first, last ):
        try:
            start = s.index( first ) + len( first )
            end = s.index( last, start )
            return s[start:end]
        except ValueError:
            return ''

    def extract_icd10_code_given_pretty_list(self, pretty_list):

        for line in pretty_list:
            if line.find("Diagnosis Code") != -1:
                print(f"FOUND DIAGNOSIS CODE: {line}")
                self.diagnosis_codes.append(line)
                path_job_base = self.make_get_job_paths(self.job_name)
                dir_all_diagnosis_codes = os.path.join(path_job_base, "output")
                if not os.path.exists(dir_all_diagnosis_codes):
                    os.makedirs(dir_all_diagnosis_codes)
                fp_all_diagnosis_codes = os.path.join(path_job_base, "output", "All_diagnosis_codes.txt")
                with open(fp_all_diagnosis_codes, "a+") as f:
                    f.write(line + "\n")

                code = self.find_between(line, "Diagnosis Code ", ":")
                description = line.split(f"{code}: ")[-1]

                
                self.ws_out["A"+str(self.ws_index)] = f"{code}"
                self.ws_out["B"+str(self.ws_index)] = f"{description}"
                self.ws_out["C"+str(self.ws_index)] = f"{self.driver.current_url}"
                
                self.ws_index += 1
                fp_all_diagnosis_codes_xlsx = os.path.join(path_job_base, "output", "All_diagnosis_codes.xlsx")
                self.wb_out.save(fp_all_diagnosis_codes_xlsx)
                break
                

    # teardown anything we need to
    def shutdown(self):
        self.driver.quit()

class test_unittest(unittest.TestCase):
    
    # # do entire job
    def test_crawler(self):
        crawler = Crawler("test_crawler")
        crawler.generate_icd10data()

    # # pull just pretty source for review.
    # def test_dl_pretty_source(self):
    #     crawler = Crawler("dl_pretty_source")
    #     crawler.generate_pretty_source("https://www.icd10data.com/ICD10CM/Codes/A00-B99/A00-A09/A00-/A00.0")
    #     crawler.generate_pretty_source("https://www.icd10data.com/ICD10CM/Codes/C00-D49/C43-C44/C43-/C43.1")


if __name__ == "__main__":
    unittest.main()