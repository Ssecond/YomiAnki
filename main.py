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


globalSettingsFilename: str = 'settings.ini'

if path.exists(globalSettingsFilename):
    config = configparser.ConfigParser()
    config.read(filenames=globalSettingsFilename, encoding="utf8")
else:
    raise FileNotFoundError(f'Файл настроек \"{globalSettingsFilename}\" не был найден.')

# Путь к профилю Anki
profilePath = os.getenv('APPDATA') + '\\' + config['GlobalSettings']['profileRelativePath']
# Название колоды
deckName = config['GlobalSettings']['deckName']
# Название типа записей
noteType = config['GlobalSettings']['noteType']
# Поля
kanjiField = config['GlobalSettings']['kanjiField']
kanaField = config['GlobalSettings']['kanaField']
pronunciationField = config['GlobalSettings']['pronunciationField']
onlyKanjiField = config['GlobalSettings']['onlyKanjiField']

isHereSmthToChange = False

col: Collection = None

try:
    if not path.exists(profilePath):
        raise FileNotFoundError(f'Заданный путь профиля \"{profilePath}\" не существует.')
    # Образуем путь до файла с базой Anki
    cpath = path.join(profilePath, 'collection.anki2')

    # Загружаем коллекцию
    col = Collection(cpath)  # Entry point to the API

    # Сразу после "deck:" пишется путь к колоде, пробелы заменяются на "_"
    deck = col.find_notes('deck:' + deckName.replace(' ', '_'))
    if not deck:
        raise ValueError(f'По заданному имени колоды \"{deckName}\" ничего не нашлось.')

    for noteId in deck:
        note = col.get_note(noteId)
        if note.note_type()['name'] == noteType:
            # Если в карточке ещё не указаны тональности, то записываем, если же есть, то не трогаем
            if note[kanaField] == 'null' or note[kanaField] == '':
                print('Происходит работа с「{}」'.format(note[onlyKanjiField]), end='…\n')  # DEBUG
                buf = findPitch(note[onlyKanjiField], kana(note[kanjiField]))  # Преобразуем
                # if buf != 'NOT FOUND':
                note[kanaField] = buf
                # всё поле в кану и записываем на карточку
                # col.set_user_flag_for_cards(4, cids=[note.cards()[0].id, ])  # Ставим на карточку синий флажок
                if buf == 'NOT FOUND':
                    col.set_user_flag_for_cards(1, cids=[note.cards()[0].id, ])  # Ставим на карточку красный флажок
                # ↑ берём карточки по id [0], потому что в этом типе записей только одна карточка
                if note[pronunciationField] == 'null' or note[pronunciationField] == '':
                    print("Поиск произношений", end='…\n')  # DEBUG
                    pronunciationURL = Pronunciation.getPronunciationURL(word=note[onlyKanjiField])
                    print("Произношение было найдено. Ссылка: " + pronunciationURL)  # DEBUG
                    soundFileName = f'{note[onlyKanjiField]}.mp3'
                    Pronunciation.download_pronunciation(pronunciationURL, profilePath, soundFileName)
                    note[pronunciationField] = f'[sound:{soundFileName}]'
                col.update_note(note)  # Обновляем базу данных
                isHereSmthToChange = True  # Записываем факт того, что мы что-то изменили, и есть что сохранить
                print(note[kanjiField], note[kanaField], sep=" ———→ ")  # DEBUG
                print('—' * 40)  # DEBUG

    ###### Now changes saves automatically
    # if isHereSmthToChange:
    #     # Защита от дурочка :)
    #     answer = input('Сохранить изменения в базу?\nВнимание! Их нельзя будет обратить! (Да(Yes)/Нет(No))\n').lower()
    #     if answer == 'да' or answer == 'yes':
    #         col.save()  # Сохраняем и синхронизируем
    #         print('Изменения были записаны в базу.')
    #     else:
    #         print('Изменения не сохранены.')
    # else:
    #     print('Нечего сохранять, никаких изменений не было произведено.')
    print('Изменения были записаны в базу.')
except ValueError as e:
    print(e, sep='\n')
except FileNotFoundError as e:
    print(e, sep='\n')
except Exception as e:
    print('Произошла неизвестная ошибка.', e, sep='\n')
# finally:
#     if col != None:
#         col.close(save=False, downgrade=False)
input("Нажмите любую клавишу, чтобы закончить работу.")
