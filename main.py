import asyncio
import logging
import math
import sys
from os import getenv
import types
from typing import Any, Dict
import random
import json

from aiogram import Bot, Dispatcher, F, Router, html
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import (
  KeyboardButton,
  Message,
  ReplyKeyboardMarkup,
  ReplyKeyboardRemove,
  CallbackQuery
)
import redis

REDIS_CLOUD_HOST = 'redis-19480.c281.us-east-1-2.ec2.cloud.redislabs.com'
REDIS_CLOUD_PORT = 19480
REDIS_CLOUD_PASSWORD = '08NuEqLAyE4Op15mVzwbZelJ4lJbsdpU'

TOKEN = "6892432453:AAE0IEeX0j3m_3wgH0-n2U0eeV4QyX41F1M"

logging.basicConfig(level=logging.INFO)

form_router = Router()
bot = Bot(token=TOKEN)
dp = Dispatcher()

class Form(StatesGroup):
  # User info
  name = State()
  phone = State()
  role = State()
  client_rating = State()
  driver_rating = State()

  # Ride details
  location = State()
  destination = State()
  # driver = State()

driverID = ""
userID = ""
locationUser = ""
historyStorage = {}

# Test Connection
async def check_redis_connection():
  try:
    redis_conn = redis.StrictRedis(
      host=REDIS_CLOUD_HOST,
      port=REDIS_CLOUD_PORT,
      password=REDIS_CLOUD_PASSWORD,
      decode_responses=True,
    )
    redis_conn.ping()
    return True
  except redis.exceptions.ConnectionError:
    return False


async def send_start_options(message: Message):
  await message.answer(
    "Hello there, please sign up or login",
    reply_markup=ReplyKeyboardMarkup(
      keyboard=[
        [
          KeyboardButton(text="Login"),
          KeyboardButton(text="Signup"),
        ]
      ],
      resize_keyboard=True,
    )
  )

@form_router.message(CommandStart())
async def start_message(message: Message, state: FSMContext):
  await send_start_options(message)

# Login user
@form_router.message(F.text.casefold() == "login")
async def login_user(message: Message, state: FSMContext):
  global userID

  user_id = f"user:{message.from_user.id}"
  # Establish connection to Redis
  redis_conn = redis.StrictRedis(
    host=REDIS_CLOUD_HOST,
    port=REDIS_CLOUD_PORT,
    password=REDIS_CLOUD_PASSWORD,
    decode_responses=True,
  )
  # redis_conn.delete("ry:639522660")
  # redis_conn.delete("ry:407320925")
  # redis_conn.delete("ry:639522660")
  # redis_conn.delete("ry:user:407320925")

  user_info = redis_conn.hgetall(user_id)
  if not user_info:
    await message.answer('User not found')
    await send_start_options(message)  # Send start options again
    print(user_info)
  else:
    await message.answer("User Found")
    user_role = user_info.get("role")

    userID = user_id
    if user_role == "Driver":
      await driver_dashboard(message=message)
    elif user_role == "Passenger":
      await passenger_dashboard(message=message)
    else:
      await message.answer("What?")


# Register new user
@form_router.message(F.text.casefold() == "signup")
async def accept_name(message: Message, state: FSMContext):
  await state.set_state(Form.phone)
  await message.answer(
            "Hello, I'm a bot that can help you to find a ride. Please, Share your contact so that we can start.",
            reply_markup=ReplyKeyboardMarkup(
                resize_keyboard=True,
                keyboard=[
                    [
                        KeyboardButton(text="Share Contact", request_contact=True, is_persistant=True)
                    ]
                ],
            ),
        )

@form_router.message(Form.name)
async def accept_phone_number(message: Message, state: FSMContext):
  await state.update_data(name=message.text)
  await state.set_state(Form.phone)
  await message.answer(
    "Please enter your phone number",
    reply_markup=ReplyKeyboardRemove(),
  )

@form_router.message(Form.phone)
async def accept_role(message: Message, state: FSMContext):
  contact = message.contact       
  await state.update_data(phone=contact.phone_number)
  await state.update_data(name=contact.first_name)
  await state.set_state(Form.role)
  await message.answer(
    "Please enter your role",
    reply_markup=ReplyKeyboardMarkup(
      keyboard=[
        [
          KeyboardButton(text="Passenger"),
          KeyboardButton(text="Driver"),
        ]
      ],
      resize_keyboard=True
    )
  )

@form_router.message(Form.role)
async def save_user_data(message: Message, state: FSMContext):
  await state.update_data(role=message.text)
  data = await state.get_data()
  # print(f"{data['name']}\n{data['phone']}\n{data['role']}")
  # Establish connection to Redis
  redis_conn = redis.StrictRedis(
    host=REDIS_CLOUD_HOST,
    port=REDIS_CLOUD_PORT,
    password=REDIS_CLOUD_PASSWORD,
    decode_responses=True,
  )
  user_key = f"user:{message.from_user.id}"
  success = []

  # Set each key-value pair in the Redis hash
  for key, value in data.items():
    success.append(redis_conn.hset(user_key, key, value))
 
  await message.answer("Your data has been saved!", reply_markup=ReplyKeyboardRemove())
  await state.clear()
  if message.text == 'Driver':
    await driver_dashboard(message)
  else:
    await passenger_dashboard(message)


# User dashboards
async def driver_dashboard(message: Message):
  await message.answer(
    "Welcome to the driver dashboard\nWhat would you like to do?", 
    reply_markup=ReplyKeyboardMarkup(
      keyboard=[
        [
          KeyboardButton(text="ManageProfile"),
        ]
      ],
      resize_keyboard=True,
    )
  )

async def passenger_dashboard(message: Message):
  await message.answer(
    "Welcome to the passenger dashboard\nWhat would you like to do?", 
    reply_markup=ReplyKeyboardMarkup(
      keyboard=[
        [
          KeyboardButton(text="ManageProfile"),
          KeyboardButton(text="BookRide"),
          KeyboardButton(text="History"),
        ]
      ],
      resize_keyboard=True,
    )
  )

# Manage profile
@form_router.message(F.text.casefold() == "manageprofile")
async def new_name(message: Message, state: FSMContext):
  await state.set_state(Form.name)
  await message.answer(
    "Enter your new name",
    reply_markup=ReplyKeyboardRemove()
  )
  
@form_router.message(F.text.casefold() == "history")
async def new_name(message: Message, state: FSMContext):
  history = await get_history_from_redis(message=message)
  # await message.answer("")
  if history is None:
    await message.answer("No History!!!", reply_markup=ReplyKeyboardRemove())
  else:
    history_text = ""
    history = json.loads(history)
    for transaction in history:
      # print(1, transaction)
      location = transaction["location"]
      driver = transaction["driver"]
      rating = transaction["rating"]
      time = transaction["time"]
      # Format the information
      history_text += f"\nLocation: {location}\nDriver: {driver}\nRating: {rating}\nTime: {time} \n"
    # print(history, history_text)
    await message.answer(history_text, reply_markup=ReplyKeyboardRemove())
    await passenger_dashboard(message=message)

@form_router.message(Form.name)
async def new_phone(message: Message, state: FSMContext):
  await state.update_data(name=message.text)
  await state.set_state(Form.phone)
  await message.answer(
    "Enter your new phone number"
  )

@form_router.message(Form.phone)
async def new_role(message: Message, state: FSMContext):
  await state.update_data(phone=message.text)
  await state.set_state(Form.role)
  await message.answer(
    "Please enter your role",
    reply_markup=ReplyKeyboardMarkup(
      keyboard=[
        [
          KeyboardButton(text="Passenger"),
          KeyboardButton(text="Driver"),
        ]
      ],
      resize_keyboard=True
    )
  )

@form_router.message(Form.phone)
async def update_user_info(message: Message, state: FSMContext):
  await state.update_data(role=message.text)
  data = await state.get_data()

  print(f"{data['name']}\n{data['phone']}\n{data['role']}")
  # Establish connection to Redis
  redis_conn = redis.StrictRedis(
    host=REDIS_CLOUD_HOST,
    port=REDIS_CLOUD_PORT,
    password=REDIS_CLOUD_PASSWORD,
    decode_responses=True,
  )

  user_key = f"user:{message.from_user.id}"
  success = []

  # Set each key-value pair in the Redis hash
  for key, value in data.items():
    success.append(redis_conn.hset(user_key, key, value))

  await message.answer("Your new version of data has been saved!", reply_markup=ReplyKeyboardRemove())
  await state.clear()

# Book a ride
async def get_drivers_from_redis():
  redis_conn = redis.StrictRedis(
    host=REDIS_CLOUD_HOST,
    port=REDIS_CLOUD_PORT,
    password=REDIS_CLOUD_PASSWORD,
    decode_responses=True,
  )

  all_users = redis_conn.keys("user:*")

  drivers = []

  for user_key in all_users:
    user_info = redis_conn.hgetall(user_key)
    if user_info.get('role') == 'Driver':
      drivers.append((user_key[5:], user_info))

  return drivers

async def get_history_from_redis(message: Message):
  user_key = f"user:{message.from_user.id}"
  redis_conn = redis.StrictRedis(
    host=REDIS_CLOUD_HOST,
    port=REDIS_CLOUD_PORT,
    password=REDIS_CLOUD_PASSWORD,
    decode_responses=True,
  )

  all_users = redis_conn.hget(user_key, "history")

  his = []

  if all_users is None:
    print("Empty")
  else:
    his = all_users

  return his

@form_router.message(F.text.casefold() == "bookride")
async def book_ride(message: Message, state: FSMContext):
  global userID
  
  userID =str(message.from_user.id)
  await state.update_data(user=userID)
  await state.set_state(Form.location)

  await message.answer("Whats your current location?")

@form_router.message(Form.location)
async def send_alerts_to_drivers(message: Message, state: FSMContext):
  global locationUser
  await state.update_data(location=message.text)
  locationUser = message.text
  location = message.text
  drivers = await get_drivers_from_redis()
  
  for driver_id, driver in drivers:
      try:
        await bot.send_message(
          driver_id,
          f"New ride request at {location}",
          reply_markup=ReplyKeyboardMarkup(
            keyboard=[
              [
                KeyboardButton(text=f"accept_{driver_id}")
              ],
            ],
            resize_keyboard=True
          )
        )
      except:
        print(f"Failed to send message to user")
        

@form_router.message(F.text.startswith("accept_"))
async def remove_book_request(message: Message, state: FSMContext):
  global driverID
  global userID
  global locationUser

  drivers = await get_drivers_from_redis()
  cur_driver = message.text[7:]
  data = await state.get_data()
  
  print(1, data)

  print(cur_driver)


  
  for driver_id, driver in drivers:
    try:
      if driver_id == cur_driver:
        driverID = driver_id
        await bot.send_message(
          driver_id,
          "Youre the ride",
          reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(Form.client_rating)
        # await rate_client(state=state)
      else:
        await bot.send_message(
          driver_id,
          "Ride has been booked",
          reply_markup=ReplyKeyboardRemove()
        )

      # await message.answer("You now have a driver")
    except:
      print("Failed to send message to someone")
  time = random.randint(10, 50)
  fee = time * 50
  # build = InlineKeyboardBuilder()
  # build.button(text = 'Rate Driver', callback_data = 'rate')

  # redis_conn = redis.StrictRedis(
  #   host=REDIS_CLOUD_HOST,
  #   port=REDIS_CLOUD_PORT,
  #   password=REDIS_CLOUD_PASSWORD,
  #   decode_responses=True,
  # )

  # user_key = f"history:{userID}"
  # success = []


# Set each key-value pair in the Redis hash
  # redis_conn.hset(user_key, mapping={
  #   "location": locationUser,
  #   "time": time,
  #   "fee": fee,  # Added comma here
  #   "driver": driverID
  # })
  historyStorage["location"] = locationUser
  historyStorage["time"] = time
  historyStorage["fee"] = fee
  historyStorage["driver"] = driverID
  
  print("Here")
  
  await bot.send_message(
        userID,
        f"Driver found!!!\nTime Taken 🕔:{time}\nToatal Cost 💲 :{fee} ",
        reply_markup=ReplyKeyboardRemove()
      )
  
  await rate_driver(state=state)
    
    
      
# passenger notification 
# async def passenger_accepted_handler(user, data):
#   global driverID
#   # print("Inside pass", user)
#   time = random.randint(10, 50)
#   fee = time * 50
#   # build = InlineKeyboardBuilder()
#   # build.button(text = 'Rate Driver', callback_data = 'rate')
  
#   redis_conn = redis.StrictRedis(
#     host=REDIS_CLOUD_HOST,
#     port=REDIS_CLOUD_PORT,
#     password=REDIS_CLOUD_PASSWORD,
#     decode_responses=True,
#   )

#   user_key = f"history:{user}"
#   success = []
 
  
#   # Set each key-value pair in the Redis hash
#   redis_conn.hset(user_key, mapping={
#     "location": data["location"],
#     "time": time,
#     "fee": fee,  # Added comma here
#     "driver": driverID,
#     "rating": ""
# })

#   #                 "location",  data["location"])
#   # redis_conn.hset(user_key, "time", time)
#   # redis_conn.hset(user_key, "fee", fee)
#   # redis_conn.hset(user_key, "driver", driverID)

  
  
#   await bot.send_message(
#           user,
#           f"Driver found!!!\nTime Taken 🕔:{time}\nToatal Cost 💲 :{fee}",
#           reply_markup=ReplyKeyboardRemove()
#         )
  
  

  
async def rate_driver(state: FSMContext):
    global userID
    print("Here in rate driver")
    
    # Create an inline keyboard with ratings 1 to 5
    builder = InlineKeyboardBuilder()
    builder.button(text="1", callback_data="1")
    builder.button(text="2", callback_data="2")
    builder.button(text="3", callback_data="3")
    builder.button(text="4", callback_data="4")
    builder.button(text="5", callback_data="5")
    

    # Send the inline keyboard to the user
    await bot.send_message(
        userID,
        "How was your Driver Rate from 1 to 5?",
        reply_markup=builder.as_markup()
    )
    
@form_router.callback_query(lambda c: c.data in ['1', '2','3','4','5'])
async def option_handler(callback_query: CallbackQuery, state: FSMContext):
    global userID
    rating = callback_query.data
    user_key = f"user:{userID}"

    # Update the rating in Redis under the 'history:userid' key
    # user_key = f"history:{callback_query.from_user.id}"
    redis_conn = redis.StrictRedis(
        host=REDIS_CLOUD_HOST,
        port=REDIS_CLOUD_PORT,
        password=REDIS_CLOUD_PASSWORD,
        decode_responses=True,
    )
    # redis_conn.hset(user_key, mapping={"rating": rating})
    historyStorage["rating"] = rating
    history = redis_conn.hget(user_key, "history")
    
    if history is None:
      history = []
    else:
      history = json.loads(history)
      
    history.append(historyStorage)
    updated_history = json.dumps(history)
    redis_conn.hset(user_key, "history", updated_history)

    # Send a confirmation message to the user
    await bot.send_message(callback_query.from_user.id, f"You have rated the driver {rating} stars.", reply_markup=ReplyKeyboardRemove())
    await passenger_dashboard(callback_query.message)

@form_router.message(Form.client_rating)
async def calculate_client_rating(message: Message, state: FSMContext):
  print("Here client rating")
  global userID
  await state.update_data(client_rating=message.text)
  redis_conn = redis.StrictRedis(
    host=REDIS_CLOUD_HOST,
    port=REDIS_CLOUD_PORT,
    password=REDIS_CLOUD_PASSWORD,
    decode_responses=True,
  )

  user_key = f"history:{userID}"
  success = []
 
  
  # Set each key-value pair in the Redis hash
  cur_rating = int(message.text)
  redis_conn.hset(user_key, mapping={
      "rating": cur_rating
  })
  await message.answer("Driver Rated !!!")
@form_router.message(Form.driver_rating)
async def calculate_driver_rating(message: Message, state: FSMContext):
  global driver_dashboard
  global userID
  await state.update_data(driver_rating=message.text)
  redis_conn = redis.StrictRedis(
    host=REDIS_CLOUD_HOST,
    port=REDIS_CLOUD_PORT,
    password=REDIS_CLOUD_PASSWORD,
    decode_responses=True,
  )

  user_key = f"history:{userID}"
  success = []
 
  
  # Set each key-value pair in the Redis hash
  cur_rating = int(message.text)
  redis_conn.hset(user_key, mapping={
      "rating": cur_rating
  })
  await message.answer("Driver Rated !!!")




















  
async def main():
  if await check_redis_connection():
    dp.include_router(form_router)
    print("Successfully connected")
    await dp.start_polling(bot)
  else:
    print("Failed to connect to Redis. Check your connection settings.")
    
if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO, stream=sys.stdout)
  asyncio.run(main())
