import base64
import re
from bs4 import BeautifulSoup, Tag
import urllib.request
import urllib.parse


def download_pronunciation(url: str, profilePath : str, filename: str):
    """Downloads the pronunciation using the pronunciation url in the pronunciation object, adds the audio to Anki's
    DB and stores the media id in the pronunciation object. """
    from http.client import HTTPResponse
    req = urllib.request.Request(url)
    dl_path = profilePath + '\\' + 'collection.media' + '\\' + filename
    with open(dl_path, 'wb') as f:
        res: HTTPResponse = urllib.request.urlopen(req)
        f.write(res.read())
        res.close()


def getPronunciationURL(word: str) -> str:
    search_url = "https://forvo.com/word/"
    download_url = "https://forvo.com/download/mp3/"

    language = 'ja'

    opener = urllib.request.build_opener()
    opener.addheaders = [('User-Agent',
                          'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/35.0.1916.47 Safari/537.36')]
    urllib.request.install_opener(opener)
    gg = search_url + urllib.parse.quote_plus(word)
    response: str
    try:
        response = urllib.request.urlopen(url=search_url + urllib.parse.quote_plus(word)).read()
    except Exception as e:
        # print(e)
        return 'NOT FOUND'

    html = BeautifulSoup(response, 'html.parser')

    available_langs_el = html.find_all(id=re.compile(r"language-container-\w{2,4}"))
    available_langs = [re.findall(r"language-container-(\w{2,4})", el.attrs["id"])[0] for el in available_langs_el]
    if language not in available_langs:
        return 'NOT FOUND'

    lang_container = [lang for lang in available_langs_el if
                      re.findall(r"language-container-(\w{2,4})", lang.attrs["id"])[0] == language][0]

    pronunciations: Tag = \
        lang_container.find_all(class_="pronunciations")[0].find_all(class_="pronunciations-list")[0].find_all("li")

    max_votes = -1
    finalPronunciationURL: str = 'NOT FOUND'
    pronunciation_dl: str

    for pronunciation in pronunciations:
        if len(pronunciation.find_all(class_="more")) == 0:
            continue

        pronunciation_dls = re.findall(r"Play\(\d+,'.+','.+',\w+,'([^']+)",
                                       pronunciation.find_all(id=re.compile(r"play_\d+"))[0].attrs["onclick"])
        if len(pronunciation_dls) == 0:
            """Fallback to .ogg file"""
            pronunciation_dl = re.findall(r"Play\(\d+,'[^']+','([^']+)",
                                          pronunciation.find_all(id=re.compile(r"play_\d+"))[0].attrs["onclick"])[0]
            dl_url = "https://audio00.forvo.com/ogg/" + str(base64.b64decode(pronunciation_dl), "utf-8")
        else:
            pronunciation_dl = pronunciation_dls[0]
            dl_url = "https://audio00.forvo.com/audios/mp3/" + str(base64.b64decode(pronunciation_dl), "utf-8")

        author_info = pronunciation.find_all(
            lambda el: bool(el.find_all(string=re.compile("Pronunciation by"))),
            class_="info",
        )[0]
        username = re.findall("Pronunciation by(.*)", author_info.get_text(" "), re.S)[0].strip()
        if username == 'strawberrybrown':
            finalPronunciationURL = dl_url
            break
        elif username == "kaoring":
            finalPronunciationURL = dl_url
            break
        else:
            vote_count = pronunciation.find_all(class_="more")[0].find_all(
                class_="main_actions")[0].find_all(
                id=re.compile(r"word_rate_\d+"))[0].find_all(class_="num_votes")[0]

            vote_count_inner_span = vote_count.find_all("span")
            if len(vote_count_inner_span) == 0:
                vote_count = 0
            else:
                vote_count = int(str(re.findall(r"(-?\d+).*", vote_count_inner_span[0].contents[0])[0]))

            if max_votes < vote_count:
                max_votes = vote_count
                finalPronunciationURL = dl_url
    return finalPronunciationURL