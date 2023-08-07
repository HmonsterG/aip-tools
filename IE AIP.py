import requests, os
from multiprocessing.pool import ThreadPool
from bs4 import BeautifulSoup

AIP_URL = "https://www.airnav.ie/air-traffic-management/aeronautical-information-management/aip-package/"
CHARTS_PAGES = []
CHARTS = []
PDFS = []

#1. Get Aerodrome Charts Table Page 
soup = BeautifulSoup(requests.get(AIP_URL).content, "html.parser")
for tag in soup.find_all("a", {
    "href": lambda x:
            x and "/air-traffic-management/aeronautical-information-management/aip-package/" in x and x.endswith("-chart-information")
}):
    CHARTS_PAGES.append(AIP_URL + tag['href'].rsplit("/", 1)[1])

#2. Get Aerodrome Charts Name/ URL from Table 
chartsToKeep = ["AERODROME", "APPROACH", "PARKING", "DEPARTURE", "ARRIVAL", "ALTITUDE"]

for page in CHARTS_PAGES:
    soup = BeautifulSoup(requests.get(page).content, "html.parser")
    
    table = soup.find("table")
    rows = list()
    for row in table.find_all("tr"):
        rows.append(row)

    names = []
    for row in rows:
        for tag in row.find_all("span"):
            names.append(tag.getText())
            break
    
    del names[0]
         
    urls = soup.find_all("a", {"href": lambda x: x and "/getattachment/" in x})
    for i in range(len(names)):
        #Names already processed above
        urls[i] = "https://www.airnav.ie" + urls[i]['href']
        
        if not any(chart in names[i].upper() for chart in chartsToKeep):
            names[i] = None
            urls[i] = None
    
    names = [x.replace("/", "-") for x in names if x is not None]
    urls = [x for x in urls if x is not None]
    result = [list(a) for a in zip(names, urls)]
    result.insert(0, soup.find("a", {"name": lambda x: x and "_2.24" in x})['name'][:4])
    CHARTS.append(result)



#3. Download Charts to Relevant Directory Hierarchy
for aerodrome in CHARTS:
    basePath = os.path.join(os.path.join(os.getcwd(), "IE Charts"), aerodrome[0])
    os.makedirs(basePath, exist_ok=True)
    for data in aerodrome:
        if "AERODROME" in data[0].upper():
            p = os.path.join(basePath, "Aerodrome Charts/")
            os.makedirs(p, exist_ok=True)
            data[0] = p + data[0] + ".pdf"
        elif "PARKING" in data[0].upper():
            p = os.path.join(basePath, "Ground Charts/") 
            os.makedirs(p, exist_ok=True)
            data[0] = p + data[0] + ".pdf"
        elif "ALTITUDE" in data[0].upper():
            p = os.path.join(basePath, "Altitude Charts/")
            os.makedirs(p, exist_ok=True)
            data[0] = p + data[0] + ".pdf"
        elif "APPROACH" in data[0].upper():
            p = os.path.join(basePath, "Approach Charts/")
            os.makedirs(p, exist_ok=True)
            data[0] = p + data[0] + ".pdf"
        elif "ARRIVAL" in data[0].upper():
            p = os.path.join(basePath, "Approach Charts/")
            os.makedirs(p, exist_ok=True)
            data[0] = p + data[0] + ".pdf"
        elif "DEPARTURE" in data[0].upper():
            p = os.path.join(basePath, "Departure Charts/")
            os.makedirs(p, exist_ok=True)
            data[0] = p + data[0] + ".pdf"

    del aerodrome[0]

MAX_THREADS = 20
TOTAL_LENGTH = 0
DOWNLOADED = 0

for a in CHARTS:
    TOTAL_LENGTH = TOTAL_LENGTH + len(a)

def download(data):
    global DOWNLOADED
    print(f"Downloading {data[0]}")
    with open(str(data[0]), 'wb') as f:
        response = requests.get(data[1])
        f.write(response.content)
    DOWNLOADED = DOWNLOADED + 1
    print(f"Downloaded {data[0]} ({DOWNLOADED}/{TOTAL_LENGTH})")


with ThreadPool(MAX_THREADS) as p:
    for chartset in CHARTS:
        p.map(download, chartset)

