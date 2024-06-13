import telebot
from PIL import Image, ImageOps
import io
from telebot import types
import random

TOKEN = '7098930079:AAFCgP91O3mziu3sZFd0fj2X0CITS67kI7E'
bot = telebot.TeleBot(TOKEN)

user_states = {}  # тут будем хранить информацию о действиях пользователя

# набор символов из которых составляем изображение
ASCII_CHARS = '@%#*+=-:. '

# Список шуток
JOKES = [
    "Почему курица перешла дорогу? Чтобы попасть на другую сторону",
    "Что сказал один глаз другому? Между нами говоря, что-то не так",
]

# Список комплиментов
COMPLIMENTS = [
    "Ты выглядишь потрясающе сегодня!",
    "Ты очень умный!",
    "Ты очень талантлив!",
    "Ты заставляешь мир сиять!",
]

def resize_image(image, new_width=100):
    width, height = image.size
    ratio = height / width
    new_height = int(new_width * ratio)
    return image.resize((new_width, new_height))


def grayify(image):
    return image.convert("L")


def image_to_ascii(image_stream, new_width=40, custom_chars=None):
    # Переводим в оттенки серого
    image = Image.open(image_stream).convert('L')

    # меняем размер сохраняя отношение сторон
    width, height = image.size
    aspect_ratio = height / float(width)
    new_height = int(
        aspect_ratio * new_width * 0.55)
    img_resized = image.resize((new_width, new_height))

    img_str = pixels_to_ascii(img_resized, custom_chars)
    img_width = img_resized.width

    max_characters = 4000 - (new_width + 1)
    max_rows = max_characters // (new_width + 1)

    ascii_art = ""
    for i in range(0, min(max_rows * img_width, len(img_str)), img_width):
        ascii_art += img_str[i:i + img_width] + "\n"

    return ascii_art


def pixels_to_ascii(image, custom_chars=None):
    pixels = image.getdata()
    characters = ""
    chars = custom_chars if custom_chars else ASCII_CHARS
    for pixel in pixels:
        characters += chars[pixel * len(chars) // 256]
    return characters



def pixelate_image(image, pixel_size):
    image = image.resize(
        (image.size[0] // pixel_size, image.size[1] // pixel_size),
        Image.NEAREST
    )
    image = image.resize(
        (image.size[0] * pixel_size, image.size[1] * pixel_size),
        Image.NEAREST
    )
    return image


def invert_colors(image):
    return ImageOps.invert(image)


def mirror_image(image, direction):
    if direction == 'horizontal':
        return image.transpose(Image.FLIP_LEFT_RIGHT)
    elif direction == 'vertical':
        return image.transpose(Image.FLIP_TOP_BOTTOM)
    else:
        return image

def convert_to_heatmap(image):
    return ImageOps.colorize(image.convert('L'), black='blue', white='red')

def resize_for_sticker(image, max_size=512):
    width, height = image.size
    if width > max_size or height > max_size:
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        image = image.resize((new_width, new_height))
    return image

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Send me an image, and I'll provide options for you!",
                 reply_markup=get_options_keyboard())


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.reply_to(message, "I got your photo! Please choose what you'd like to do with it.",
                 reply_markup=get_options_keyboard())
    user_states[message.chat.id] = {'photo': message.photo[-1].file_id}

@bot.message_handler(commands=['RandomJoke'])
def send_random_joke(message):
    random_joke = random.choice(JOKES)
    bot.reply_to(message, random_joke)

@bot.message_handler(commands=['RandomCompliment'])
def send_random_compliment(message):
    random_compliment = random.choice(COMPLIMENTS)
    bot.reply_to(message, random_compliment)

def get_options_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    pixelate_btn = types.InlineKeyboardButton("Pixelate", callback_data="pixelate")
    ascii_btn = types.InlineKeyboardButton("ASCII Art", callback_data="ascii")
    invert_btn = types.InlineKeyboardButton("Invert Colors", callback_data="invert")
    heatmap_btn = types.InlineKeyboardButton("Heatmap", callback_data="heatmap")
    horizontal_mirror_btn = types.InlineKeyboardButton("Mirror Horizontally", callback_data="horizontal_mirror")
    vertical_mirror_btn = types.InlineKeyboardButton("Mirror Vertically", callback_data="vertical_mirror")
    sticker_btn = types.InlineKeyboardButton("Resize for Sticker", callback_data="sticker")
    keyboard.add(pixelate_btn, ascii_btn, invert_btn, heatmap_btn, horizontal_mirror_btn, vertical_mirror_btn, sticker_btn)
    return keyboard


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "pixelate":
        bot.answer_callback_query(call.id, "Pixelating your image...")
        pixelate_and_send(call.message)
    elif call.data == "ascii":
        bot.answer_callback_query(call.id, "Converting your image to ASCII art...")
        bot.send_message(call.message.chat.id, "Введите символы, которые вы хотели бы использовать для оформления в формате ASCII, разделив их пробелами.")
        user_states[call.message.chat.id]['state'] = 'waiting_for_ascii_chars'
    elif call.data == "invert":
        bot.answer_callback_query(call.id, "Inverting the colors of your image...")
        invert_and_send(call.message)
    elif call.data == "heatmap":
        bot.answer_callback_query(call.id, "Converting your image to a heatmap...")
        heatmap_and_send(call.message)
    elif call.data == "horizontal_mirror":
        bot.answer_callback_query(call.id, "Mirroring your image horizontally...")
        mirror_and_send(call.message, 'horizontal')
    elif call.data == "vertical_mirror":
        bot.answer_callback_query(call.id, "Mirroring your image vertically...")
        mirror_and_send(call.message, 'vertical')
    elif call.data == "sticker":  # Обработка стикера
        bot.answer_callback_query(call.id, "Resizing your image for a sticker...")
        sticker_and_send(call.message)

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get('state') == 'waiting_for_ascii_chars')
def handle_ascii_chars(message):
    user_states[message.chat.id]['ascii_chars'] = message.text.split()
    ascii_and_send(message)
    user_states[message.chat.id].pop('state', None)


def pixelate_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    pixelated = pixelate_image(image, 20)

    output_stream = io.BytesIO()
    pixelated.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)


def ascii_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    custom_chars = user_states[message.chat.id].get('ascii_chars')
    ascii_art = image_to_ascii(image_stream, custom_chars=custom_chars)
    bot.send_message(message.chat.id, f"```\n{ascii_art}\n```", parse_mode="MarkdownV2")


def invert_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    inverted = invert_colors(image)

    output_stream = io.BytesIO()
    inverted.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)

def heatmap_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    heatmap = convert_to_heatmap(image)

    output_stream = io.BytesIO()
    heatmap.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)

def mirror_and_send(message, direction):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    mirrored = mirror_image(image, direction)

    output_stream = io.BytesIO()
    mirrored.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)

def sticker_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    resized_image = resize_for_sticker(image)  # Изменение размера для стикера

    output_stream = io.BytesIO()
    resized_image.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)

@bot.message_handler(commands=['FlipACoin'])
def flip_coin(message):
    coin_sides = ["Решка", "Орел"]
    result = random.choice(coin_sides)
    bot.reply_to(message, f"Выпала {result}!")

bot.polling(none_stop=True)