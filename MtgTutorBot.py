#Bot to tutor magic cards

from uuid import uuid4

from telegram.utils.helpers import escape_markdown

from telegram import InlineQueryResultArticle, InlineQueryResultPhoto, ParseMode, InputTextMessageContent
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, run_async

#Other imports
import json, os, time, requests, logging, re

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    update.message.reply_text('Hiya and thank you for using the MtgTutorBot. To get started type @mtgtutorbot <card name>.\nThen you can select to send the card\'s picture, text, buy link, or price.\nAdd an <&> with the 3/4 character set code to grab a specific printing of a card.\nPut an <!> in front of the card name to tutor a card by its exact name. Useful for cards with common words for names like Sleep and Shock.')

def help(bot, update):
    update.message.reply_text('*Tosses inflatable* Type /start to see how I work. Otherwise contact us at https://gitlab.com/zefrof/mtgtutorbot with bug reports and other issues')

#Searches Scyfall API for cards and returns them
def cardTutor(searchTerm, type):
    if len(searchTerm) < 2:
        return

    url = "https://api.scryfall.com/cards/search?q="
    searchSplit = searchTerm.split('&')

    #print(searchSplit[0].replace(" ", "-"))
    if("!" in searchSplit[0]):
        encodedTerm = searchSplit[0].replace(" ", "-")
    else:
        encodedTerm = searchSplit[0]

    if("&" in searchTerm):
            req = requests.get(url=url + encodedTerm + "e:" + searchSplit[1])
            tutorData = json.loads(req.content.decode('utf-8'))
    else:        
        req = requests.get(url=url + encodedTerm)
        tutorData = json.loads(req.content.decode('utf-8'))

    #Delay so Scryfall doesn't get mad
    time.sleep(0.1)

    if(req.status_code == 404):
        return

    if type == "photo":
        if(tutorData['data'][0]['layout'] == "transform"):
            index = 0 
            tsfm = re.sub(r'[^\w\s]', '', tutorData['data'][0]['card_faces'][1]['name'].lower())
            search = re.sub(r'[^\w\s]', '', searchSplit[0].lower())
            if(search in tsfm):
                index = 1
            return tutorData['data'][0]['card_faces'][index]['image_uris']['large']


        return tutorData['data'][0]['image_uris']['large']
    elif type == "text":
        if(tutorData['data'][0]['layout'] == "split"):
            text = ""
            for index in range(len(tutorData['data'][0]['card_faces'])):
                text += tutorData['data'][0]['card_faces'][index]['name'] + " " + tutorData['data'][0]['mana_cost'] + '\n' + tutorData['data'][0]['card_faces'][index]['type_line'] + '\n' + tutorData['data'][0]['card_faces'][index]['oracle_text'] + '\n\n'
            return text
        elif(tutorData['data'][0]['layout'] == "transform" or tutorData['data'][0]['layout'] == "flip"):
            index = 0 
            tsfm = re.sub(r'[^\w\s]', '', tutorData['data'][0]['card_faces'][1]['name'].lower())
            search = re.sub(r'[^\w\s]', '', searchSplit[0].lower())
            if(search in tsfm):
                index = 1
            if "Planeswalker" in tutorData['data'][0]['card_faces'][index]['type_line']:
                addl = '\n' + tutorData['data'][0]['card_faces'][index]['loyalty']
            elif "Creature" in tutorData['data'][0]['card_faces'][index]['type_line']:
                addl = '\n' + tutorData['data'][0]['card_faces'][index]['power'] + '/' + tutorData['data'][0]['card_faces'][index]['toughness']
            else:
                addl = ""  
                                                                                        
            return tutorData['data'][0]['card_faces'][index]['name'] + " " + tutorData['data'][0]['card_faces'][index]['mana_cost'] + '\n' + tutorData['data'][0]['card_faces'][index]['type_line'] + '\n' + tutorData['data'][0]['card_faces'][index]['oracle_text'] + addl

        else:
            if "Planeswalker" in tutorData['data'][0]['type_line']:
                addl = '\n' + tutorData['data'][0]['loyalty']
            elif "Creature" in tutorData['data'][0]['type_line']:
                addl = '\n' + tutorData['data'][0]['power'] + '/' + tutorData['data'][0]['toughness']
            else:
                addl = ""  
                                                                                        
            return tutorData['data'][0]['name'] + " " + tutorData['data'][0]['mana_cost'] + '\n' + tutorData['data'][0]['type_line'] + '\n' + tutorData['data'][0]['oracle_text'] + addl
    elif type == "price":
        try:
            if tutorData['data'][0]['foil'] == True and tutorData['data'][0]['nonfoil'] == True:
                addl = tutorData['data'][0]['name'] + " from " + tutorData['data'][0]['set_name'] + " costs an average of \nNon-Foil: " + tutorData['data'][0]['prices']['usd'] + "$" + "\nFoil: " + tutorData['data'][0]['prices']['usd_foil'] + "$"
            elif(tutorData['data'][0]['nonfoil'] == True):
                addl = tutorData['data'][0]['name'] + " from " + tutorData['data'][0]['set_name'] + " costs an average of \nNon-Foil: " +  tutorData['data'][0]['prices']['usd'] + "$"
            elif(tutorData['data'][0]['foil'] == True):
                addl = tutorData['data'][0]['name'] + " from " + tutorData['data'][0]['set_name'] + " costs an average of \nFoil: " +  tutorData['data'][0]['prices']['usd_foil'] + "$"
            else:
                addl = ""

            return addl
        except:
            return "No USD price data available for this card. Try another printing."
    elif type == "buy":
        buyLink = tutorData['data'][0]['purchase_uris']['tcgplayer'].replace("Scryfall", "mtgtutorbot")
        buyLink = buyLink.replace("scryfall", "mtgtutorbot")
        return buyLink    

def inlinequery(bot, update):
    query = update.inline_query.query

    results = [
        InlineQueryResultArticle(
            id=uuid4(),
            title="Price",
            thumb_url="https://img.scryfall.com/cards/art_crop/en/me3/17.jpg?1517813031",
            input_message_content=InputTextMessageContent(cardTutor(query, "price"))),
        InlineQueryResultArticle(
            id=uuid4(),
            title="Text",
            thumb_url="https://img.scryfall.com/cards/art_crop/en/ust/41a.jpg?1522206097",
            input_message_content=InputTextMessageContent(cardTutor(query, "text"))),
        InlineQueryResultArticle(
            id=uuid4(),
            title="Buy",
            thumb_url="https://img.scryfall.com/cards/art_crop/en/gtc/26.jpg?1517813031",
            input_message_content=InputTextMessageContent(cardTutor(query, "buy"))),
        InlineQueryResultPhoto(
            id=uuid4(),
            title="Photo",
            type='photo',
            photo_url=cardTutor(query, "photo"),
            thumb_url=cardTutor(query, "photo"))
    ]

    update.inline_query.answer(results)

def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    # Create the Updater and pass it your bot's token.
    token = os.environ.get('TOKEN') or open('token.txt').read().strip()
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(InlineQueryHandler(inlinequery))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
