import os
import re
from os import path
from anki.storage import Collection
from PitchSearcher import findPitch
import configparser
import Pronunciation


def deleteRepeats(somelist):
    final = []
    for x in somelist:
        if final.count(x) == 0:
            final.append(x)
        else:
            final.append('!REPEAT!')
    return final


def kana(text: str):
    """
    Заменяет иероглифы на их чтения, указанные в "[]".\n
    :param text: строка формата "*текст* иероглиф[его чтение]*текст*".
    :return: кана, без иероглифов.
    """
    try:
        # Нахождение иероглифов с их чтениями
        kanjiAndFurigana = re.findall(r'(\w+\[(\w*)])', text, flags=re.UNICODE)
        # Замена иероглифов на их фуригану
        for i in range(len(kanjiAndFurigana)):
            text = text.replace(kanjiAndFurigana[i][0], kanjiAndFurigana[i][1]).replace(' ', '')

        allReadings = deleteRepeats(text.split(','))
        if len(allReadings) == 1:
            text = allReadings[0]
        else:
            text = allReadings
        return text
    except Exception as exception:
        print('Не получилось извлечь кану из-за неизвестной ошибки.', exception, sep='\n')


# constants
redFlagID: int = 1
blueFlagID: int = 4
considerNotFilled = ['', 'null']

globalSettingsFileName: str = 'settings.ini'
if path.exists(globalSettingsFileName):
    config = configparser.ConfigParser()
    config.read(filenames=globalSettingsFileName, encoding="utf8")
else:
    raise FileNotFoundError(f'Файл настроек \"{globalSettingsFileName}\" не был найден.')

# Путь к профилю Anki
profilePath: str = os.getenv('APPDATA') + '\\' + config['InitialSettings']['profileRelativePath']
# Название колоды
deckName: str = config['InitialSettings']['deckName']
# Название типа записей
noteType: str = config['InitialSettings']['noteType']
# Поля
kanjiField: str = config['InitialSettings']['kanjiField']
kanaField: str = config['InitialSettings']['kanaField']
pronunciationField: str = config['InitialSettings']['pronunciationField']
onlyKanjiField: str = config['InitialSettings']['onlyKanjiField']

searchForPronunciation: bool = bool(config['ModeSettings']['searchForPronunciation'])
searchForPitch: bool = bool(config['ModeSettings']['searchForPitch'])
col: Collection = None

try:
    if not path.exists(profilePath):
        raise FileNotFoundError(f'Заданный путь профиля \"{profilePath}\" не существует.')
    # Образуем путь до файла с базой Anki
    cpath = path.join(profilePath, 'collection.anki2')

    # Загружаем коллекцию
    col = Collection(cpath)

    # Сразу после "deck:" пишется путь к колоде, пробелы заменяются на "_"
    deck = col.find_notes('deck:' + deckName.replace(' ', '_'))
    if not deck:
        raise ValueError(f'По заданному имени колоды \"{deckName}\" ничего не нашлось.')

    for noteId in deck:
        note = col.get_note(noteId)
        if note.note_type()['name'] == noteType:
            print('Смотрим на「{}」'.format(note[onlyKanjiField]), end='…\n')  # DEBUG
            if searchForPitch:
                # Если в карточке ещё не указаны тональности, то записываем, если же есть, то не трогаем
                if note[kanaField] in considerNotFilled:
                    buf = findPitch(note[onlyKanjiField], kana(note[kanjiField]))  # Преобразуем
                    if buf != 'NOT FOUND':
                        note[kanaField] = buf
                    # всё поле в кану и записываем на карточку
                    # col.set_user_flag_for_cards(blueFlagID, cids=[note.cards()[0].id, ])  # Ставим на карточку синий флажок
                    if buf == 'NOT FOUND':
                        col.set_user_flag_for_cards(redFlagID,
                                                    cids=[note.cards()[0].id, ])  # Ставим на карточку красный флажок
                    # ↑ берём карточки по id [0], потому что в этом типе записей только одна карточка
                    col.update_note(note)  # Сохраняем изменения в карточке
                    print(note[kanjiField], note[kanaField], sep=" ———→ ")  # DEBUG
            if searchForPronunciation:
                if note[pronunciationField] in considerNotFilled:
                    print("Поиск произношений", end='…\n')  # DEBUG
                    pronunciationURL = Pronunciation.getPronunciationURL(word=note[onlyKanjiField])
                    if pronunciationURL != 'NOT FOUND':
                        print("Произношение было найдено. Ссылка: " + pronunciationURL)  # DEBUG
                        soundFileName = f'{note[onlyKanjiField]}.mp3'
                        Pronunciation.download_pronunciation(pronunciationURL, profilePath, soundFileName)
                        note[pronunciationField] = f'[sound:{soundFileName}]'
                    else:
                        print("Произношение не найдено.")  # DEBUG
                        col.set_user_flag_for_cards(redFlagID,
                                                    cids=[note.cards()[0].id, ])  # Ставим на карточку красный флажок
                    col.update_note(note)  # Сохраняем изменения в карточке
            print('—' * 40)  # DEBUG

    print('Изменения были записаны в базу.')
except ValueError as e:
    print(e, sep='\n')
except FileNotFoundError as e:
    print(e, sep='\n')
except Exception as e:
    print('Произошла неизвестная ошибка.', e, sep='\n')
finally:
    if col != None:
        col.close(downgrade=False)
    input("Нажмите любую клавишу, чтобы закончить работу.")
