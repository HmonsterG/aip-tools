import requests, re, os
from multiprocessing.pool import ThreadPool
from bs4 import BeautifulSoup


#0. Get available AIP options
url = "https://nats-uk.ead-it.com/cms-nats/opencms/en/Publications/AIP/"
soup = BeautifulSoup(requests.get(url).content, "html.parser")
urls = soup.find_all("a", {"href": lambda x: x and "www.aurora.nats.co.uk" in x})
del urls[::2] 
choice = int(input(f"Which AIP do you want to download?\n{[str(i+1) + '. ' + x.getText() for i, x in enumerate(urls)]}\n"))
url = urls[choice-1]['href'].rsplit('/', 1)[0] + "/eAIP/"


#1. Get Aerodrome Charts Table Page
#Baseline URL containing all site data

url = 'https://www.aurora.nats.co.uk/htmlAIP/Publications/2023-09-07-AIRAC/html/eAIP/'
#Get menu html menu containing aerodromes and other data
soup = BeautifulSoup(requests.get(url+"EG-menu-en-GB.html").content, "html.parser")

aerodromes = []

#Get list of aerodromes
for tag in soup.find("div", id="AD-2details"):
    #Get div of class 'Hx' for each aerodrome
    tag2 = tag.find("div", {"class":"Hx"}) 
    #Get first a-tag and its href for aerodrome site
    if tag2 != None:
        aerodromes.append(tag2.find("a")['href'])

#Remove ../eAIP/ from URL and fragment of URL
for i in range(len(aerodromes)):
    aerodromes[i] = url+aerodromes[i][8:].split("#", 1)[0]

#2. Get Aerodrome Charts Name/ URL from Table

print("Getting charts download links, may take ~30 seconds.")

charts = []

for aerodrome in aerodromes:

    soup = BeautifulSoup(requests.get(aerodrome).content, "html.parser")

    #Keeps aerodrome charts, ground movememnt, aircraft movement, altitude and approach charts
    chartsToKeep = ["AERODROME", "MOVEMENT", "ALTITUDE", "APPROACH", "DEPARTURE", "ARRIVAL"]

    #Find table of aerodrome charts within 2.24 section of div with wildcard search
    for tag in soup.find("div", id=lambda x: x and "-AD-2.24" in x).find("table"):
        #Find all chart names and relative URLs
        names = tag.find_all("p")
        urls = tag.find_all("a", {"href":lambda x: x and "graphics" in x})

        for i in range(len(names)):
            #Process names and URLs from raw HTML to the name and absolute URLs
            names[i] = names[i].getText()
            urls[i] = url[:-10] + urls[i]['href'][6:]

            #Set unwanted charts to None to purge in postprocessing
            if not any(chart in names[i].upper() for chart in chartsToKeep):
                names[i] = None
                urls[i] = None

        #Remove Nonetype data (Replace / to prevent filesystem issues)
        names = [x.replace("/", "-") for x in names if x is not None]
        urls = [x for x in urls if x is not None]
        
        #Generate list of list - not tuple, immutable 
        result = [list(a) for a in zip(names, urls)]
        #Add ICAO from aerodrome URL via regex match
        result.insert(0,re.search('EG-AD-2.(.*)-en-GB', aerodrome).group(1))
        charts.append(result)

#3. Download Charts to Relevant Directory Hierarchy

#A. Create directory hierarchy
for aerodrome in charts:
    #Create ICAO folder
    basePath = os.path.join(os.path.join(os.getcwd(), "UK Charts"), aerodrome[0]) 
    os.makedirs(basePath, exist_ok=True)
    #Create relevant folders for specific charts
    for data in aerodrome:
        #Instead of just making folders, also replace name with download path
        if "AERODROME" in data[0].upper():
            p = os.path.join(basePath, "Aerodrome Charts/")
            os.makedirs(p, exist_ok=True)
            data[0] = p + data[0] + ".pdf"
        elif "MOVEMENT" in data[0].upper():
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


    del aerodrome[0] #Remove ICAO for easier use in multithreading pool

#B. Download - multithreaded

MAX_THREADS = 20
TOTAL_LENGTH = 0
DOWNLOADED = 0

for a in charts:
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
    for chartset in charts:
        p.map(download, chartset)
