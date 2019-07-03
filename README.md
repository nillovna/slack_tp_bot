Slack TP Bot
========================
Slack Bot to create UserStories in TargetProcess

### Описание работы с ботом
Бот работает только в публичных каналах
1) В **треде** написать сообщение с обращением к боту `@<Bot Name> <UserStory Name>`
    * `<UserStory Name>` может быть пустым, тогда будет использовано дефолтное значение
2) Придет меню с выбором параметров для UserStory:
    * Параметры можно оставить пустыми, тогда будут использованы дефолтные значения
    * **Cancel** - отменить создание таски
    * **Create UserStory** - подтвердить создание таски
3) По итогам будет создана задача и ссылка придет в тред

#### Дефолтные значения:
* **Name** - `[Bot] <DATE> Created from <requesters_name> request`
* **Description** - Отправитель и текст сообщения, от которого рос тред
* **State** - ToDo
* **Priority** - Critical
* **Owner** - Призвавший бота
* **Developer** - omit
* **PlannedEndDate** - omit

### Requirments
```
apt install python3 python3-pip
pip3 install -r requirments.txt
```

### Run
```
python3 ./main.py
```
