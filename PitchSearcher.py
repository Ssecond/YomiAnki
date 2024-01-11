import requests
from bs4 import BeautifulSoup
from bs4 import element

# constants
startHigh = '<span class="pitch high">'
startHighConst = '<span class="pitch high" style="border-right: none">'
startLow = '<span class="pitch low">'
startLowConst = '<span class="pitch low" style="border-right: none">'
endTag = '</span>'

KATAKANA_HIRGANA_SHIFT = 0x30a1 - 0x3041  # KATAKANA LETTER A - HIRAGANA A


def shift_chars_prefix(text, amount, condition):
    output = ''

    for last_index, char in enumerate(text):
        if not condition(char):
            if lambda c: '\u3040' < char < '\u3097':
                output += char
            else:
                break
        else:
            output += chr(ord(char) + amount)

    return output


def katakana_to_hiragana(text):
    return shift_chars_prefix(text, -KATAKANA_HIRGANA_SHIFT, lambda c: '\u30a0' < c < '\u30f7')


def hiragana_to_katakana(text):
    return shift_chars_prefix(text, KATAKANA_HIRGANA_SHIFT, lambda c: '\u3040' < c < '\u3097')


def findPitch(word: str, readingkanji) -> str:
    """
    Находит тональность для слова, используя онлайн-словарь.
    :param word: слово, записанное, как его обычно пишут.
    :param readingkanji: чтение слова, которому находим тональность.
    :return: Строка, содержащая тональность в HTML формате.
    """
    try:
        if type(readingkanji) == str:
            return findPitchStr(word, readingkanji)
        elif type(readingkanji) == list:
            return findPitchList(word.split(','), readingkanji)

    except ConnectionError as e:
        print(e)
    except Exception as e:
        print('Неизвестная ошибка при поиске в словаре.', e, sep='\n')


def findPitchList(word: list, readingkanji: list) -> str:
    finalStr = ''
    for i in range(len(readingkanji)):
        if readingkanji[i] != '!REPEAT!':
            if i < len(readingkanji) - 1 and readingkanji[i + 1] != '!REPEAT!':
                finalStr += findPitchStr(word[i], readingkanji[i]) + ', '
            else:
                finalStr += findPitchStr(word[i], readingkanji[i])
    return finalStr


def findPitchStr(word: str, readingkanji) -> str:
    # Делаем запрос
    response = requests.get(f'https://www.wadoku.de/search/{word}')
    if response.status_code != 200:
        raise ConnectionError(f'Не удалось подключиться к сайту.\nОшибка {response.status_code}.')

    # Создаём объект BeautifulSoup из html-кода, полученного выше
    soup = BeautifulSoup(response.text, 'html.parser')
    # Находим места, где хранятся чтения иероглифов в коде
    for link in soup.find_all('div', class_='reading'):
        # Спускаемся до ноды, которая содержит span'ы с произношением
        buffReadings = link.find('span', {'class': 'pron accent', 'data-accent-id': '1'})
        if buffReadings is not None:
            reading = ''
            clearTextReading = ''
            index = 1
            for partReading in buffReadings:
                if type(partReading) != element.NavigableString:
                    buffPartsOfReading = partReading.get('class')
                    # Если это последний элемент, мы используем другие константы
                    if index != len(buffReadings):
                        # Если тон высокий
                        if 't' in buffPartsOfReading:
                            reading += startHigh + partReading.text.replace('~', '').replace('￨', '') + endTag
                        # Тон низкий
                        elif 'b' in buffPartsOfReading:
                            reading += startLow + partReading.text.replace('~', '').replace('￨', '') + endTag
                    else:
                        # Если тональность содержит правую границу (возвышается/понижается)
                        if 'r' not in buffPartsOfReading:
                            if 't' in buffPartsOfReading:
                                reading += startHighConst + partReading.text.replace('~', '').replace('￨', '').replace('･', '') + endTag
                            elif 'b' in buffPartsOfReading:
                                reading += startLowConst + partReading.text.replace('~', '').replace('￨', '').replace('･', '') + endTag
                        else:
                            if 't' in buffPartsOfReading:
                                reading += startHigh + partReading.text.replace('~', '').replace('￨', '').replace('･', '') + endTag
                            elif 'b' in buffPartsOfReading:
                                reading += startLow + partReading.text.replace('~', '').replace('￨', '').replace('･', '') + endTag
                    # Просто чтение, без нагромождения в виде HTML
                    clearTextReading += partReading.text.replace('~', '').replace('￨', '').replace('･', '')
                    index += 1
                    if clearTextReading == readingkanji or clearTextReading == katakana_to_hiragana(readingkanji):
                        return reading
    return 'NOT FOUND'

